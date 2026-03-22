---
name: "qa-tdd-integration"
description: |
  Integração entre Solution Architect e QA-TDD. Define como SA entrega
  requisitos para o agente QA-TDD iniciar escrita de testes.
applyTo: ".github/skills/3.solution-architect/**"
---

# Integração Solution Architect → QA-TDD

## Handoff Process

O Solution Architect, após completar análise e refinamento, deve emitir
um **prompt único e executável** para o agente QA-TDD.

## Formato de Entrega (Obrigatório)

O prompt final do SA deve seguir **exatamente** o formato compacto abaixo.
Este arquivo é a fonte canônica do contrato SA -> QA-TDD.

### Contrato Compacto (Canônico)

Limites por campo:
- `id`: até 20 chars
- `objetivo`: até 200 chars
- `escopo_in`: até 3 itens
- `escopo_out`: até 3 itens
- `requisitos`: 3 a 6 itens testáveis
- `componentes`: até 8 itens
- `criterios_aceite`: 2 a 6 checkboxes

Formato obrigatório:

```text
Voce e o agente 4.qa-tdd desta task.

Contexto da demanda:
- id: <BLID ou referencia>
- objetivo: <ate 200 chars>
- escopo_in: <item1>; <item2>; <item3>
- escopo_out: <item1>; <item2>; <item3>

Requisitos refinados:
1. <requisito testavel>
2. <requisito testavel>
3. <requisito testavel>

Arquitetura e integracao:
- componentes: <arquivos/modulos>
- extensoes: <funcoes/classes/interfaces>
- guardrails: risk_gate=ATIVO; circuit_breaker=ATIVO; decision_id=IDEMPOTENTE

Modelagem de dados:
- entidades: <lista>
- schema: <sem_alteracao | descricao curta>
- compatibilidade: <sim/nao + condicao>

Plano de implementacao orientado a testes:
1. RED para <comportamento A>
2. GREEN minimo para <comportamento A>
3. RED/GREEN para <comportamento B>
4. REFACTOR mantendo verde

Suite de testes minima obrigatoria:
- unitarios: <casos>
- integracao: <casos>
- regressao_risco: <casos>

Criterios de aceite objetivos:
- [ ] <criterio mensuravel 1>
- [ ] <criterio mensuravel 2>
- [ ] Guardrails de risco preservados.

Comandos de validacao:
- pytest -q tests/
- mypy --strict <modulos alterados>

Entregaveis esperados:
- Lista de arquivos alterados
- Resumo de risco de regressao
- Evidencia de testes executados e resultado
```

## O Que Acontece Após

O agente QA-TDD receberá este prompt e:

1. **Escreverá suite de testes unitários** que inicialmente falham (RED phase)
2. **Atualizará `docs/BACKLOG.md`** com referência de suite criada
3. **Gerará novo prompt para Software Engineer** contendo:
   - Todos os testes completos (prontos para executar)
   - Contexto completo da task
   - Invariantes de risco obrigatórios
   - Checklist de aceite

## Validação de Qualidade

O handoff é considerado **bem-formado** quando:

- ✅ Cada requisito é testável e verificável (não vago)
- ✅ Componentes/módulos específicos (não genérico)
- ✅ Invariantes de risco deixados explícitos
- ✅ Plano TDD está claro: Red → Green → Refactor
- ✅ Suite de testes mínima quantificada por tipo
- ✅ Critério de aceite é objetivo e mensurável
- ✅ Formato segue **exatamente** o template acima

## Exemplo Compacto

```text
Voce e o agente 4.qa-tdd desta task.

Contexto da demanda:
- id: BLID-042
- objetivo: validar decision_id no OrderLayer para garantir idempotencia
- escopo_in: OrderLayer.validate_decision_id; OrderRequest.decision_id
- escopo_out: migracao historica; relatorio retroativo

Requisitos refinados:
1. rejeitar signal sem decision_id
2. aceitar signal com decision_id valido
3. registrar motivo de rejeicao em log

Arquitetura e integracao:
- componentes: core/model2/order_layer.py; core/model2/signal_adapter.py
- extensoes: OrderLayer.validate_decision_id
- guardrails: risk_gate=ATIVO; circuit_breaker=ATIVO; decision_id=IDEMPOTENTE

Modelagem de dados:
- entidades: technical_signals
- schema: coluna decision_id unica
- compatibilidade: sim; legado pode ser nulo

Plano de implementacao orientado a testes:
1. RED para rejeicao sem decision_id
2. GREEN minimo para validacao
3. RED/GREEN para retry idempotente
4. REFACTOR com logs claros

Suite de testes minima obrigatoria:
- unitarios: 3 casos
- integracao: 2 casos
- regressao_risco: 2 casos

Criterios de aceite objetivos:
- [ ] 7 testes verdes em tests/test_order_layer.py
- [ ] mypy --strict sem erros no modulo alterado
- [ ] Guardrails de risco preservados

Comandos de validacao:
- pytest -q tests/test_order_layer.py
- mypy --strict core/model2/order_layer.py

Entregaveis esperados:
- Lista de arquivos alterados
- Resumo de risco de regressao
- Evidencia de testes executados e resultado
```

## Integração no Workflow

```
Product Owner (prioritiza)
    ↓
    └─→ Solution Architect (refina)
             ↓
             └─→ QA-TDD (escreve testes)
                      ↓
                      └─→ Software Engineer (implementa)
                               ↓
                               └─→ QA-Live (valida e promove)
```

Cada estágio de entrega tecnica (2 a 8) emite um
**prompt único e executável** para o próximo.
Nenhum stage emite output ambíguo ou requer clarificações.

## Templates de Referência

- **SA Output Template**: Veja seção "Formato de Entrega" acima
- **QA-TDD Output Template**: Veja `.github/skills/4.qa-tdd/SKILL.md`

Sempre validar que o handoff segue o template antes de pedir que QA-TDD processe.
