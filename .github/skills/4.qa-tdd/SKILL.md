---
name: 4.qa-tdd
description: |
  Escreve testes unitários orientados a requisitos, atualiza backlog
  e gera prompt executável para Software Engineer implementar com TDD.
  Use quando: receber demanda refinada do arquiteto de soluções.
metadata:
   workflow-track: principal
   workflow-order: 4
   workflow-stage: 4
   focus:
      - escrita-testes-red-phase
      - validacao-requisitos
      - atualizacao-backlog
      - handoff-software-engineer
user-invocable: true
---

# Skill: qa-tdd

## Objetivo

Implementar ciclo Red-Green-Refactor com testes unitários primeiro,
garantindo cobertura, rastreabilidade e qualidade antes da implementação.

## Entrada Esperada

- Prompt estruturado do Solution Architect (ou demanda direta)
- Requisitos funcionais/não-funcionais verificáveis
- Componentes/módulos/arquivos afetados
- Invariantes obrigatórios (risk_gate, circuit_breaker, decision_id)
- Plano incremental de entrega

Se incompleto, operar em modo conservador:
- Explicitar premissas
- Reduzir escopo para MVP seguro
- Bloquear quando faltar informação crítica de risco/teste

## Leitura Mínima

1. Ler `docs/BACKLOG.md` para ID do item e contexto.
2. Ler `docs/REGRAS_DE_NEGOCIO.md` para validações obrigatórias.
3. Ler código existente **apenas** dos módulos citados.
4. Ler testes existentes similares para padrão/fixtures.
5. Ler `docs/ARQUITETURA_ALVO.md` se houver impacto estrutural.

## Fluxo de Escrita de Testes

### Fase 1: Análise & Planejamento

1. **Consolidar requisitos testáveis**
   - Cada requisito deve ser observável/verificável
   - Separar casos: sucesso, erro, edge-case, rejeição esperada

2. **Identificar escopos de teste**
   - Unitários: função individual, comportamento determinístico
   - Integração: contato entre módulos, contratos respeitados
   - Regressão/Risk: invariantes críticas (risk_gate, circuit_breaker, decision_id)

3. **Referência de padrão**
   - Ler testes existentes similares em `tests/`
   - Identificar fixtures reutilizáveis
   - Notar convenção de nomenclatura local

### Fase 2: Escrita de Testes (RED)

1. **Criar arquivo de teste**
   ```
   tests/test_<modulo>.py
   ```
   - Importar módulo a testar
   - Importar fixtures e helpers do projeto
   - MockarIO/DB/APIs externas conforme necessário

2. **Escrever testes que FALHAM inicialmente**
   - Implementar função vazia ou stub
   - Teste falha com `AssertionError` ou `AttributeError`
   - Nunca deixar teste passar acidentalmente

3. **Estrutura AAA por teste**
   ```python
   def test_funcionalidade_condicao_resultado():
       """Docstring: por que este teste é importante"""
       # Arrange: preparar fixtures, dados, contexto
       # Act: chamar função/método
       # Assert: validar resultado esperado
   ```

4. **Cobertura mínima obrigatória**
   - [ ] Caminho feliz (sucesso esperado)
   - [ ] Erro esperado com msg clara
   - [ ] Edge-case crítico (limite, vazio, None)
   - [ ] Invariante de risco (decision_id, risk_gate, circuit_breaker)

### Fase 3: Validação de Suite

1. **Executar testes (devem falhar)**
   ```bash
   pytest -q tests/test_<modulo>.py
   ```
   - Verificar que todos falham com mensagens claras
   - Ajustar mensagens de erro se ambíguas

2. **Validar syntax e tipos**
   ```bash
   mypy --strict tests/test_<modulo>.py
   ```
   - Sem erros de tipo, mesmo que testes ainda falhem funcionalmente

3. **Revisar cobertura esperada**
   ```bash
   pytest --cov=<modulo> tests/test_<modulo>.py
   ```
   - Não precisa passar, mas deve mostrar quais linhas serão cobertas

### Fase 4: Atualizar Backlog

1. **Registrar em `docs/BACKLOG.md`**
   - Item: `[BLID] <titulo da task>`
   - Status: mude para `TESTES_PRONTOS`
   - Adicione linha:
     ```
     - Testes em: `tests/test_<modulo>.py`
     - Suite: <N> testes unitários + <N> integração + <N> risk
     - Comando validação: pytest -q tests/test_<modulo>.py
     ```

2. **Atualizar `docs/SYNCHRONIZATION.md`**
   - Registre mudança com tag `[SYNC]`
   - Referência: `QA-TDD: Suite de testes escritos para BLID-XXX`

## Guardrails Invioláveis

### Testes & Qualidade

- **Sem mocks de guardrails**: Nunca mockear `risk_gate`, `circuit_breaker`.
- **Determinismo**: Sem sleeps, clocks, dependências de estado externo.
- **Isolamento**: Cada teste roda independente; use fixtures para cleanup.
- **Nomenclatura**: `test_<funcionalidade>_<condicao>_<resultado>`

### Risco Operacional

- Preservar idempotência `decision_id` em testes de decisão + execução.
- Em ambiguidade de comportamento, escolher fail-safe.
- Nenhum teste deve contornar validações de `risk_gate` ou `circuit_breaker`.

### Documentação

- Docstring em cada função de teste explicando o quê e por quê.
- Comentários em lógica não-óbvia.
- Nenhum teste oculto; todos com nome descritivo.

## Critério de Qualidade da Skill

- ✅ Todo teste é executável e inicialmente falha (`RED`)
- ✅ Testes cobrem 100% dos requisitos especificados
- ✅ Nenhum teste mockeia guardrails de risco
- ✅ Arquivo de teste segue convenção nomenclatura
- ✅ `docs/BACKLOG.md` atualizado com referência de suite
- ✅ `docs/SYNCHRONIZATION.md` atualizado com tag `[SYNC]`
- ✅ Prompt final é auto-suficiente para Software Engineer
- ✅ Prompt contém: testes + contexto + guardrails + checklist completo

## Saída Obrigatória

A resposta final deve ser **apenas um prompt para o agente 5.software-engineer**,
sem prefácio adicional, no formato compacto abaixo.

```text
Voce e o agente 5.software-engineer desta task.

Contexto:
- id: <BLID-XXX>
- objetivo: <ate 200 chars>
- escopo_in: <ate 3 itens>
- escopo_out: <ate 3 itens>

Suite RED:
- arquivo: tests/test_<modulo>.py
- codigo: <codigo completo dos testes>

Mapeamento requisito -> teste:
1. <requisito testavel> -> test_<funcao>_<caso>()
2. <requisito testavel> -> test_<funcao>_<caso>()
3. <requisito testavel> -> test_<funcao>_<caso>()

Guardrails obrigatorios:
- risk_gate=ATIVO
- circuit_breaker=ATIVO
- decision_id=IDEMPOTENTE

Plano Green/Refactor:
1. GREEN minimo para todos os testes da suite
2. REFACTOR mantendo testes verdes
3. Validacao final sem regressao

Checklist de aceite:
- [ ] Suite da task passa
- [ ] mypy --strict sem erros
- [ ] Sem mock de risk_gate/circuit_breaker
- [ ] Backlog em IMPLEMENTADO apos entrega

Comandos de validacao:
- pytest -q tests/test_<modulo>.py
- mypy --strict <modulos alterados>
- pytest -q tests/
```

Limites de tamanho recomendados:
- contexto total: ate 600 chars
- mapeamento: 3 a 6 requisitos
- checklist: 4 a 8 itens

## Referência de Fixtures

Adicionar ao arquivo de teste fixtures do projeto conforme necessário:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock

# Exemplo: fixture para contexto de banco
@pytest.fixture
def mock_db():
    db = Mock()
    db.query.return_value = []
    yield db
    db.close()

# Exemplo: fixture para logger
@pytest.fixture
def mock_logger(caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog
```

## Exemplo de Teste Bem Formado

```python
def test_order_layer_rejects_invalid_signal_returns_false():
    """
    Validar que order_layer retorna False quando signal invalido.

    Requisito: OrderLayer deve sanitar entrada antes de processar.
    Importância: Bloqueia ordens inválidas antes do risk_gate.
    """
    # Arrange
    from core.model2.order_layer import OrderLayer
    layer = OrderLayer()
    invalid_signal = {"status": "INVALID"}

    # Act
    result = layer.admit(invalid_signal)

    # Assert
    assert result is False, "Expected False for invalid signal"
```

Siga este pattern para todos os testes.
