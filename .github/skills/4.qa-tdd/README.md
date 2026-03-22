# Skill: QA - TDD (Integração Modelo 2.0)

## Visão Geral

O skill **QA-TDD** implementa o ciclo Red-Green-Refactor com foco em testes
unitários orientados a requisitos. Ele é acionado automaticamente pelo
Solution Architect ou pode ser invocado diretamente.

## Estrutura da Pasta

```
.github/skills/4.qa-tdd/
├── SKILL.md              # Definição completa do skill (leia isto primeiro)
├── README.md             # Este arquivo
├── examples/
│   ├── test_order_layer.py      # Exemplo de suite de testes bem formada
│   └── prompt_output_example.md  # Exemplo de saída para Software Engineer
└── fixtures/
    └── conftest.py       # Fixtures reutilizáveis (pytest plugins)
```

## Entrada & Saída

### Entrada
Prompt estruturado do Solution Architect contendo:
- ID/Referencia da task
- Requisitos funcionais/não-funcionais verificáveis
- Componentes/módulos/arquivos afetados
- Invariantes obrigatórios (risk_gate, circuit_breaker, decision_id)
- Plano incremental de entrega

### Saída
1. Suite de testes unitários (RED phase — testes que falham)
2. Atualização de `docs/BACKLOG.md` com status `TESTES_PRONTOS`
3. Prompt executável para Software Engineer contendo:
   - Testes completos (código pronto para copiar/executar)
   - Contexto e requisitos
   - Guardrails de risco
   - Checklist de aceite

## Quick Start

### 1. Invocar o Skill

```bash
# Via slash command no chat
/qa-tdd

# Ou copiar o prompt do Solution Architect e colar no chat com skill invocado
```

### 2. Fornecer Input

Cole o prompt do Solution Architect. Exemplo:

```text
Voce e o agente QA-TDD desta task.

Contexto da demanda:
- ID/Referencia: BLID-042
- Objetivo de negocio: Implementar validacao de decision_id
- ...
```

### 3. Acompanhar Execução

O skill vai:

1. ✅ Analisar requisitos
2. ✅ Escrever testes que falham (RED phase)
3. ✅ Atualizar `docs/BACKLOG.md`
4. ✅ Emitir prompt para Software Engineer

## Padrões de Teste

### Nomenclatura Obrigatória

```python
# ❌ Ruim: nome genérico
def test_order():
    ...

# ✅ Bom: nome descritivo
def test_order_layer_admit_rejects_invalid_signal_returns_false():
    ...
```

### Estrutura AAA (Arrange → Act → Assert)

```python
def test_order_layer_admit_accepts_valid_signal_returns_true():
    """
    Validar que OrderLayer.admit() aceita signal válido.

    Requisito: OrderLayer deve processar signals válidos conforme contrato.
    Importância: Bloqueia regressão de admissão de ordens legítimas.
    """
    # Arrange: preparar dados e contexto
    from core.model2.order_layer import OrderLayer
    layer = OrderLayer()
    valid_signal = {
        "status": "CREATED",
        "symbol": "BTCUSDT",
        "decision_id": "dec_12345"
    }

    # Act: executar operação
    result = layer.admit(valid_signal)

    # Assert: validar resultado
    assert result is True, "Expected True for valid signal"
    assert layer.last_admitted_id() == "dec_12345"
```

### Cobertura Mínima por Teste

1. **Caminho feliz**: sucesso esperado
2. **Erro esperado**: rejeição com mensagem clara
3. **Edge-case**: limite, vazio, None
4. **Invariante de risco**: decision_id, risk_gate, circuit_breaker

### Exemplo Completo

Veja [examples/test_order_layer.py](examples/test_order_layer.py) para uma
suite completa de testes bem formada.

## Guardrails Invioláveis

### Nunca

❌ Mockear `risk_gate` ou `circuit_breaker`
❌ Criar testes não-determinísticos (dependência de clock, sleep, estado externo)
❌ Omitir testes para comportamento crítico
❌ Deixar testes rodando sem erro claro (RED phase = falha explícita)

### Sempre

✅ Documentar cada teste com docstring explicando o quê e por quê
✅ Isolar testes: cada teste roda independente
✅ Usar fixtures para setup/cleanup repetitivo
✅ Nomear testes descritivamente: `test_<funcionalidade>_<condicao>_<resultado>`

## Validação de Saída

O skill é considerado **bem-sucedido** quando:

- ✅ Suite de testes é executável e **todos falham inicialmente** (RED)
- ✅ Cada teste mapeia exatamente um requisito
- ✅ Testes cobrem 100% dos requisitos especificados
- ✅ Nenhum teste mockeia guardrails de risco
- ✅ Arquivo de teste segue convenção: `tests/test_<modulo>.py`
- ✅ `docs/BACKLOG.md` atualizado com status `TESTES_PRONTOS`
- ✅ Prompt para Software Engineer é auto-suficiente e contém tudo
- ✅ Prompt segue template exato (veja SKILL.md)

## Próximos Passos

Após a saída do skill QA-TDD:

1. **Software Engineer** recebe o prompt com testes + requisitos
2. SE implementa código para fazer testes passarem (GREEN phase)
3. SE refatora mantendo testes verdes (REFACTOR phase)
4. SE valida sem regressões: `pytest -q tests/`
5. **QA-Live** (futuro) audita e decide GO/NO-GO para live

## Referências

- **SKILL.md completo**: [.github/skills/4.qa-tdd/SKILL.md](SKILL.md)
- **Integração com Solution Architect**: [.github/instructions/qa-tdd-integration.instructions.md](../../instructions/qa-tdd-integration.instructions.md)
- **Agentes do projeto**: [AGENTS.md](../../../AGENTS.md)
- **Padrão de testes no projeto**: Veja `tests/test_*.py` existentes

## Contribuições

Se você está refinando o skill QA-TDD:

1. Atualize `SKILL.md` com novas convenções ou padrões
2. Adicione exemplos em `examples/` conforme necessário
3. Atualize `README.md` (este arquivo) com mudanças de fluxo
4. Atualize `docs/SYNCHRONIZATION.md` com tag `[SYNC]`

---

**Criado**: 2026-03-22
**Versão**: 1.0 (MVP - Modelo 2.0)
