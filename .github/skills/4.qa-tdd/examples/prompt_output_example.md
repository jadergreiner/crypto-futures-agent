# Exemplo: Prompt de Saída do QA-TDD para Software Engineer

Este arquivo demonstra o **formato exato** do prompt que o agente 4.qa-tdd emite
para o Software Engineer após completar a escrita de testes.

---

```text
Voce e o agente 5.software-engineer desta task.

═══════════════════════════════════════════════════════════════════

CONTEXTO DA TASK

ID/Referencia: BLID-042
Objetivo de negocio: Implementar validacao de decision_id em OrderLayer
  para garantir idempotencia de entrada de sinais. Prevenir ordens duplicadas
  no mesmo decision_id em caso de retry de requisicao.
Escopo fechado:
  - Classe OrderLayer com validacao de decision_id
  - Novo metodo OrderLayer.validate_decision_id()
  - Persistencia de signals no banco com decision_id como check de duplicata
Fora de escopo:
  - Migracao de dados historicos
  - Relatorio de duplicatas existentes
  - Mudanca de schema em outras tabelas

═══════════════════════════════════════════════════════════════════

SUITE DE TESTES (RED PHASE - TESTES QUE FALHAM INICIALMENTE)

Arquivo: tests/test_order_layer.py

[... CÓDIGO COMPLETO COPIADO DE examples/test_order_layer.py ...]

═══════════════════════════════════════════════════════════════════

REQUISITOS A IMPLEMENTAR (Mapeamento Testes → Requisitos)

1. OrderLayer.admit() deve aceitar signals válidos (conforme contrato)
   ← test_order_layer_admit_accepts_valid_signal_returns_true()

2. OrderLayer.admit() deve rejeitar signals sem decision_id
   ← test_order_layer_admit_rejects_signal_without_decision_id_returns_false()

3. OrderLayer.admit() deve rejeitar signals sem symbol
   ← test_order_layer_admit_rejects_signal_without_symbol_returns_false()

4. OrderLayer deve logar motivo detalhado de rejeição
   ← test_order_layer_admit_logs_rejection_reason()

5. OrderLayer.validate_decision_id() deve aceitar format válido (dec_YYYYMMDD_###)
   ← test_order_layer_validate_decision_id_accepts_valid_format()

6. OrderLayer.validate_decision_id() deve rejeitar format inválido
   ← test_order_layer_validate_decision_id_rejects_invalid_format()

7. OrderLayer deve ser idempotente: retry com mesmo decision_id retorna sucesso
   ← test_order_layer_admit_idempotent_retry_same_decision_id()

8. OrderLayer.admit() deve chamar risk_gate.validate_order() ANTES de processar
   ← test_order_layer_admit_calls_risk_gate_validate()

9. OrderLayer.admit() deve rejeitar order se risk_gate falha (fail-safe)
   ← test_order_layer_admit_rejects_order_if_risk_gate_fails()

10. OrderLayer deve persistir signals aceitos em banco de dados
    ← test_order_layer_admit_persists_signal_to_db()

11. OrderLayer NÃO deve persistir signals rejeitados
    ← test_order_layer_admit_does_not_persist_rejected_signal()

═══════════════════════════════════════════════════════════════════

GUARDRAILS & INVARIANTES OBRIGATORIOS

Componentes afetados:
  - core/model2/order_layer.py (NOVO)
  - core/model2/signal_adapter.py (consulta apenas)
  - db/schema.py (referencia de contrato)

Pontos de extensao:
  - OrderLayer.admit(signal: Dict) -> bool
  - OrderLayer.validate_decision_id(decision_id: str) -> bool

Invariantes OBRIGATORIOS:
  - risk_gate DEVE SER ATIVO (nunca mockear sem motivo crítico)
  - circuit_breaker DEVE SER ATIVO (nunca mockear sem motivo crítico)
  - decision_id DEVE PRESERVAR IDEMPOTENCIA (retry com mesmo ID retorna sucesso)

Compatibilidade retroativa:
  - SIM [com condicao]: signals legacies sem decision_id devem ser rejeitados
  - Novo campo decision_id nao quebra signals existentes (new field, nullable)

═══════════════════════════════════════════════════════════════════

PLANO GREEN-REFACTOR (Ciclo TDD)

FASE 1: FAZER TESTES PASSAREM (GREEN)

  1.1 Criar arquivo: core/model2/order_layer.py
      ```python
      from typing import Dict, Optional
      import logging

      logger = logging.getLogger(__name__)

      class OrderLayer:
          def __init__(self, db=None, risk_gate=None, circuit_breaker=None):
              self.db = db
              self.risk_gate = risk_gate
              self.circuit_breaker = circuit_breaker

          def admit(self, signal: Dict) -> bool:
              """Processa signal e valida conforme contrato."""
              # Implementar validacoes minimas para fazer testes passarem
              # TODO: Implementar lógica
              pass

          def validate_decision_id(self, decision_id: str) -> bool:
              """Valida format de decision_id."""
              # TODO: Implementar validação
              pass
      ```

  1.2 Implementar metodo admit():
      - Validar presenca de 'decision_id' em signal
      - Validar presenca de 'symbol' em signal
      - Chamar self.risk_gate.validate_order(signal) se existe
      - Validar format de decision_id
      - Persistir em self.db.insert(signal) se banco existe
      - Logar motivo de rejeição se recusado
      - Retornar True (sucesso) ou False (falha)

  1.3 Implementar metodo validate_decision_id():
      - Validar pattern: dec_YYYYMMDD_### (regex)
      - Retornar True se válido, False caso contrário

  1.4 Executar testes:
      ```bash
      pytest -q tests/test_order_layer.py
      ```
      Esperado: Todos os 11 testes PASSAM (GREEN).

FASE 2: REFATORE MANTENDO TESTES VERDES (REFACTOR)

  2.1 Separar validacoes em metodos privados:
      ```python
      def _validate_require_fields(signal: Dict) -> bool:
          """Valida presenca de campos obrigatorios."""
          pass

      def _log_rejection(reason: str):
          """Centraliza logging de rejeicoes."""
          pass
      ```

  2.2 Melhorar mensagens de log:
      - Incluir decision_id e symbol em cada log
      - Indicar razao exata de rejeição

  2.3 Adicionar docstrings em todos os metodos:
      - Explicar contrato esperado
      - Indicar quando retorna True vs False

  2.4 Executar testes novamente:
      ```bash
      pytest -q tests/test_order_layer.py
      ```
      Esperado: Todos os 11 testes CONTINUAM passando.

  2.5 Validar tipos:
      ```bash
      mypy --strict core/model2/order_layer.py
      ```
      Esperado: Sem erros de tipo.

FASE 3: VALIDAR SEM REGRESSAO

  3.1 Executar suite completa:
      ```bash
      pytest -q tests/
      ```
      Esperado: Todos os testes passam (novo + existentes).

  3.2 Validar tipos em modulos afetados:
      ```bash
      mypy --strict core/model2/
      ```
      Esperado: Sem erros de tipo.

═══════════════════════════════════════════════════════════════════

CHECKLIST DE ACEITE OBJETIVOS

- [ ] Todos os 11 testes em tests/test_order_layer.py PASSAM (GREEN)
- [ ] Nenhum teste mockeia risk_gate ou circuit_breaker INTENCIONALMENTE
      (OK mockar para fins de teste, nao permetir bypass)
- [ ] decision_id preserva idempotencia conforme test_order_layer_admit_idempotent_retry_same_decision_id()
- [ ] Cobertura: 100% das funcoes publicas (admit, validate_decision_id) testadas
- [ ] mypy --strict core/model2/order_layer.py retorna SEM ERROS
- [ ] pytest -q tests/ retorna SEM ERROS (nao introducir regressoes)
- [ ] docs/BACKLOG.md atualizado com status IMPLEMENTADO para BLID-042
- [ ] docs/SYNCHRONIZATION.md registra mudanca com tag [SYNC]
- [ ] Arquivo core/model2/order_layer.py segue convencoes do projeto (idioma PT-BR em comentarios, nomes descritivos)

═══════════════════════════════════════════════════════════════════

COMANDOS DE VALIDACAO

# Testes unitarios — devem PASSAR
pytest -q tests/test_order_layer.py

# Testes com verbosidade — para debug se falhar
pytest -vv tests/test_order_layer.py

# Validar tipos — sem erros
mypy --strict core/model2/order_layer.py

# Suite completa — sem regressoes
pytest -q tests/

# Cobertura de testes (opcional)
pytest --cov=core.model2.order_layer tests/test_order_layer.py

# Comitar com formato obrigatorio
git add -A
git commit -m "[FEAT] Implementar validacao de decision_id em OrderLayer para idempotencia"

# Atualizar backlog
# 1. Editar docs/BACKLOG.md: mude "BLID-042" de "TESTES_PRONTOS" para "IMPLEMENTADO"
# 2. Editar docs/SYNCHRONIZATION.md: adicione linha "[SYNC] Implementacao de BLID-042 concluida"

═══════════════════════════════════════════════════════════════════
```

---

## Notas Importantes

1. **RED → GREEN → REFACTOR**: Siga rigorosamente este ciclo TDD.
2. **Nunca deixar testes mockados ou ignorados**: Todos os 11 testes devem passar sem `@skip` ou `@mock.patch` indevido.
3. **risk_gate é guardrail crítico**: Mesmo que teste passe localmente, sempre validar que risk_gate é processado on live.
4. **decision_id é idempotente**: Retry com mesmo decision_id **não** deve gerar duplicate ou erro.
5. **Comandos de validação são obrigatórios**: Rodar TODOS antes de comitar.
6. **Documentação é código**: Adicionar docstrings, comentários em lógica não-óbvia, e manter BACKLOG sincronizado.

---

**Saída gerada por**: Agente 4.qa-tdd
**Data**: 2026-03-22
**BLID Alvo**: BLID-042
