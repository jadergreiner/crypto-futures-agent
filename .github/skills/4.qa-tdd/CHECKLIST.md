# Checklist Rápido — QA-TDD Suite Validation

Use este checklist para validar que sua suite de testes foi bem formada
**antes** de emitir o prompt para Software Engineer.

## Antes de Iniciar (Preparação)

- [ ] Li o handoff do Solution Architect completo
- [ ] Identifiquei TODOS os requisitos (funcionais + não-funcionais)
- [ ] Localizei os módulos/arquivos que serão afetados
- [ ] Verifiquei guardrails de risco: risk_gate, circuit_breaker, decision_id
- [ ] Li testes similares existentes para padrão/fixtures da projeto

## Durante Escrita de Testes

### Nomenclatura

- [ ] Arquivo segue: `tests/test_<modulo>.py`
- [ ] Funções seguem: `test_<funcionalidade>_<condicao>_<resultado>`
- [ ] Exemplos:
  - `test_order_layer_admit_accepts_valid_signal_returns_true` ✅
  - `test_order_layer_admit_rejects_signal_without_decision_id_returns_false` ✅
  - `test_order()` ❌ (muito vago)

### Estrutura de Teste

- [ ] Cada teste tem Docstring explicando o quê e por quê
- [ ] Estrutura AAA respeitada: Arrange → Act → Assert
- [ ] Cada teste é isolado (não depende de outro teste)
- [ ] Cada teste usa fixtures para setup/cleanup repetitivo

### Exemplo de Teste bem Formado

```python
def test_ordem_layer_admit_accepts_valid_signal_returns_true(
    self, valid_signal, mock_risk_gate
):
    """
    Validar que OrderLayer.admit() aceita signal válido.

    Requisito: OrderLayer deve processar signals válidos conforme contrato.
    Importância: Bloqueia regressão de admissão de ordens legítimas.
    """
    # Arrange
    from core.model2.order_layer import OrderLayer
    layer = OrderLayer()

    # Act
    result = layer.admit(valid_signal)

    # Assert
    assert result is True, "Expected True for valid signal"
```

- [ ] Docstring explica o quê testa e por quê
- [ ] Imports localizados (dentro de teste ou fixture)
- [ ] Mock/fixtures claros (valid_signal, mock_risk_gate)
- [ ] Act é chamada clara da função
- [ ] Assert é específico com mensagem

### Cobertura Mínima

Para cada funcionalidade, validar:

- [ ] Teste de **caminho feliz** (sucesso esperado)
- [ ] Teste de **erro esperado** com msg clara
- [ ] Teste de **edge-case** crítico (limite, vazio, None)
- [ ] Teste de **invariante de risco** (decision_id, risk_gate, circuit_breaker)

Exemplo para OrderLayer.admit():

- [ ] ✅ Aceita signal válido (caminho feliz)
- [ ] ✅ Rejeita signal sem decision_id (erro esperado)
- [ ] ✅ Rejeita signal com format inválido (edge-case)
- [ ] ✅ Chama risk_gate.validate_order() antes de processar (invariante risco)
- [ ] ✅ Rejeita ordem se risk_gate falha (fail-safe)

### Guardrails de Risco

- [ ] **Nenhum teste mockeia risk_gate para contornar**
      (OK mockar para fins de teste, mas não perder proteção)
- [ ] **Nenhum teste mockeia circuit_breaker para contornar**
- [ ] **Tests validam que invariantes são preservados**:
  - [ ] decision_id é preservado (idempotência)
  - [ ] risk_gate é consultado ANTES de agir
  - [ ] circuit_breaker é consultado ANTES de agir

### Determinismo

- [ ] ❌ Nenhum `time.sleep()` em testes
- [ ] ❌ Nenhuma dependência de `datetime.now()` não-mockada
- [ ] ❌ Nenhum estado compartilhado entre testes
- [ ] ✅ Todos os I/O mockados (DB, APIs, files)
- [ ] ✅ Todos os timeouts/retries mockados

### Tipagem & Linting

- [ ] Imports estão corretos (não circular, não unused)
- [ ] Tipos de argumentos/returns estão anotados
- [ ] Syntax sem erros óbvios
- [ ] Rodei `mypy --strict tests/test_<modulo>.py` sem erros

## Testes de Suite Completa

- [ ] Rodei `pytest -q tests/test_<modulo>.py` e TODOS os testes **FALHAM** (RED phase)
- [ ] Cada falha tem mensagem de erro CLARA (não genérica)
- [ ] Nenhum teste está `@skip` ou `@pytest.mark.skip`
- [ ] Nenhum teste está passando acidentalmente

```bash
# Validação
pytest -q tests/test_<modulo>.py
# Esperado:
# FAILED test_order_layer_admit_accepts_valid_signal_returns_true
# FAILED test_order_layer_admit_rejects_signal_without_decision_id_returns_false
# ... (todos FALHANDO)
# ==== 11 failed in 0.23s ====
```

## Atualização de Documentação

- [ ] Identifiquei o BLID (ex: BLID-042) na tarefa
- [ ] Criei nova entrada em `docs/BACKLOG.md` OU atualizei item existente
- [ ] Registrei suite de testes:
  ```
  - Testes em: tests/test_<modulo>.py
  - Suite: N testes unitários + N integração + N risk
  - Comando validação: pytest -q tests/test_<modulo>.py
  ```
- [ ] Mude status de item para `TESTES_PRONTOS`
- [ ] Adicionei referência em `docs/SYNCHRONIZATION.md` com tag `[SYNC]`

## Prompt para Software Engineer

Antes de emitir, validar:

- [ ] Prompt segue template **EXATO** (veja SKILL.md)
- [ ] Contém título: "CONTEXTO DA TASK"
- [ ] Contém seção: "SUITE DE TESTES (RED PHASE)"
- [ ] Contém seção: "REQUISITOS A IMPLEMENTAR"
- [ ] Contém seção: "GUARDRAILS & INVARIANTES OBRIGATORIOS"
- [ ] Contém seção: "PLANO GREEN-REFACTOR"
- [ ] Contém seção: "CHECKLIST DE ACEITE OBJETIVOS"
- [ ] Contém seção: "COMANDOS DE VALIDACAO"
- [ ] Código completo de testes está **COPIADO INTEIRO** (não resumido, não link)
- [ ] Cada teste mapeia EXATAMENTE um requisito
- [ ] Prompt é **auto-suficiente** (SE não precisa voltar pedir clarificação)

## Exemplo de Prompt Bem Formado

```text
Voce e o agente 5.software-engineer desta task.

═══════════════════════════════════════════════════════════════════

CONTEXTO DA TASK

ID/Referencia: BLID-042
Objetivo de negocio: ...

═══════════════════════════════════════════════════════════════════

SUITE DE TESTES (RED PHASE - TESTES QUE FALHAM INICIALMENTE)

Arquivo: tests/test_order_layer.py

[... CÓDIGO COMPLETO AQUI ...]

═══════════════════════════════════════════════════════════════════

REQUISITOS A IMPLEMENTAR (Mapeamento Testes → Requisitos)

1. Requisito A ← test_xxx()
2. Requisito B ← test_yyy()
3. ...

═══════════════════════════════════════════════════════════════════

[... seções obrigatórias ...]

═══════════════════════════════════════════════════════════════════
```

- [ ] Prompt segue estrutura acima
- [ ] Nenhum prefácio ou explicação ANTES do prompt
- [ ] Prompt é entregue como **texto puro** (não markdown block com ```):

```text
Voce e o agente 5.software-engineer...
```

#### ❌ Evitar:

```text
Aqui está o prompt para o Software Engineer:

Voce e o agente...
```

## Validação Final

- [ ] Rodei checklist todo
- [ ] Todos os checkboxes ✅ estão marcados
- [ ] Nenhum item "em doubt" ou "precisa validar depois"
- [ ] Suite é **executável imeditamente** sem ajustes
- [ ] Prompt para SE é **claro e auto-suficiente**

## Próximas Ações (Para SE)

Apos passar neste checklist, você vai:

1. Emitir prompt para Software Engineer (SEM prefácio adicional)
2. Atualizar `docs/BACKLOG.md` com status `TESTES_PRONTOS`
3. Registrar em `docs/SYNCHRONIZATION.md` com tag `[SYNC]`

**Sucesso!** ✅

---

**Prompt para você após finalizar**: Copie o checklist para seu contexto e marque conforme avança. Quando TODOS estiverem ✅, emita o prompt para Software Engineer.
