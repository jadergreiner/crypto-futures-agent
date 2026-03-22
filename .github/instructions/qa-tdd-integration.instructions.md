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

O prompt final do SA deve seguir **exatamente** este formato:

```text
Voce e o agente QA-TDD desta task.

Contexto da demanda:
- ID/Referencia: <BLID ou referencia>
- Objetivo de negocio: <objetivo>
- Escopo fechado: <o que entra>
- Fora de escopo: <o que nao entra>

Requisitos refinados:
1. <requisito funcional verificavel>
2. <requisito funcional verificavel>
3. <requisito nao funcional verificavel>

Arquitetura e integracao:
- Componentes afetados: <arquivos/modulos>
- Pontos de extensao: <funcoes/classes/interfaces>
- Invariantes obrigatorios: <risk_gate, circuit_breaker, decision_id>

Modelagem de dados:
- Entidades/tabelas afetadas: <lista>
- Alteracoes de schema/contrato: <se houver>
- Compatibilidade retroativa: <sim/nao + condicao>

Plano de implementacao orientado a testes:
1. Escreva primeiro os testes que falham para <comportamento A>.
2. Implemente o minimo para passar os testes de <comportamento A>.
3. Repita ciclo TDD para <comportamento B>.
4. Refatore mantendo todos os testes verdes.

Suite de testes minima obrigatoria:
- Unitarios: <casos>
- Integracao: <casos>
- Regressao/risk: <casos>

Criterios de aceite objetivos:
- [ ] <criterio mensuravel 1>
- [ ] <criterio mensuravel 2>
- [ ] Nenhuma quebra de guardrails de risco.

Comandos de validacao:
- `pytest -q tests/`
- `mypy --strict <modulos alterados>`

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

## Exemplo de Handoff Bem-Formado

```text
Voce e o agente QA-TDD desta task.

Contexto da demanda:
- ID/Referencia: BLID-042
- Objetivo de negocio: Implementar validação de decision_id em OrderLayer
  para garantir idempotência de entrada
- Escopo fechado: OrderLayer.validate_decision_id(), novo campo em OrderRequest
- Fora de escopo: Migração de dados históricos, relatório de duplicatas

Requisitos refinados:
1. OrderLayer.admit() deve rejeitar signal sem decision_id (validação)
2. OrderLayer.admit() deve permitir signal com decision_id válido (idempotência)
3. OrderLayer deve logar rejeição com motivo detalhado (observabilidade)

Arquitetura e integracao:
- Componentes afetados: core/model2/order_layer.py, core/model2/signal_adapter.py
- Pontos de extensao: OrderLayer.validate_decision_id() (novo método)
- Invariantes obrigatorios: risk_gate ATIVO | circuit_breaker ATIVO | decision_id IDEMPOTENTE

Modelagem de dados:
- Entidades/tabelas afetadas: technical_signals (nova coluna decision_id)
- Alteracoes de schema/contrato: ADD COLUMN decision_id VARCHAR(255) UNIQUE
- Compatibilidade retroativa: SIM - registo novo, legacy pode ser null

Plano de implementacao orientado a testes:
1. Escreva primeiro os testes que falham para: rejeição de signal sem decision_id
2. Implemente o minimo: OrderLayer.admit() + validação decision_id
3. Repita ciclo TDD para: idempotência (retry com mesmo decision_id)
4. Refatore: extrair validação para método isolado, melhorar logs

Suite de testes minima obrigatoria:
- Unitarios: test_admit_rejects_no_decision_id, test_admit_accepts_valid_id, test_admit_idempotent_retry
- Integracao: test_order_layer_signal_adapter_contract, test_db_decision_id_unique
- Regressao/risk: test_risk_gate_not_mocked, test_circuit_breaker_still_fires

Criterios de aceite objetivos:
- [ ] Todos 7 testes em tests/test_order_layer.py passam (GREEN)
- [ ] 100% do código novo coberto por testes
- [ ] mypy --strict core/model2/order_layer.py sem erros
- [ ] Nenhuma quebra de guardrails de risco

Comandos de validacao:
- pytest -q tests/test_order_layer.py
- mypy --strict core/model2/order_layer.py

Entregaveis esperados:
- tests/test_order_layer.py (nova suite)
- core/model2/order_layer.py (modificado com validate_decision_id)
- db/migration_YYYYMMDD_add_decision_id.sql (ou scripts/migrate.py)
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

Cada estágio emite um **prompt único e executável** para o próximo.
Nenhum stage emite output ambíguo ou requer clarificações.

## Templates de Referência

- **SA Output Template**: Veja seção "Formato de Entrega" acima
- **QA-TDD Output Template**: Veja `.github/skills/4.qa-tdd/SKILL.md`

Sempre validar que o handoff segue o template antes de pdir que QA-TDD processe.
