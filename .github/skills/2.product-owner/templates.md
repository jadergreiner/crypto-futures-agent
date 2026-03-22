---
name: 2.product-owner-templates
description: |
  Templates fixos para comentario PO no backlog e handoff PO -> SA.
user-invocable: false
---

# Templates Product Owner

## 1) Template Fixo de Comentario PO (Backlog)

Formato obrigatorio no rodape do item priorizado:

```text
PO: <resumo_em_ate_150_caracteres>
```

Regras:
- Prefixo literal obrigatorio: `PO:`
- Limite maximo: 150 caracteres no resumo
- Linguagem objetiva, sem multiline
- Nao incluir markdown extra, bullets ou tags

Checklist rapido:
1. O item foi marcado como `Em analise`.
2. O comentario comeca com `PO:`.
3. O resumo tem no maximo 150 caracteres.

## 2) Bloco Padrao de Handoff PO -> SA

Usar exatamente este bloco no chat apos a priorizacao:

```text
Voce e o agente 3.solution-architect desta task.

Contexto de priorizacao do PO:
- DECISAO_PO: <GO | GO_COM_RESTRICOES | NO_GO>
- Referencia do backlog: <BLID/ID>
- Titulo do item: <titulo>
- Objetivo de negocio: <resultado esperado>
- Justificativa de prioridade: <valor, urgencia, risco e esforco>
- Status aplicado no backlog: Em analise
- Comentario PO (<=150): PO: <resumo>

Escopo para refinamento tecnico:
- Escopo fechado (entra): <lista objetiva>
- Fora de escopo (nao entra): <lista objetiva>
- Restricoes: <prazo, compliance, dependencia, custo>
- Premissas do PO: <premissas validas>

Criterios de sucesso orientados a produto:
1. <criterio mensuravel 1>
2. <criterio mensuravel 2>
3. <criterio mensuravel 3>

Riscos e guardrails obrigatorios:
- Risco operacional principal: <descricao>
- Controles obrigatorios: manter risk_gate e circuit_breaker ativos.
- Em duvida operacional: fail-safe.

Sua tarefa como Arquiteto de Solucoes:
1. Refinar requisitos funcionais e nao funcionais verificaveis.
2. Revisar aderencia arquitetural e pontos de extensao.
3. Revisar impacto de modelagem de dados e contratos.
4. Gerar prompt final acionavel para o agente `4.qa-tdd`.
```

## 3) Regra de Consistencia de Status

Para backlog priorizado pelo PO, usar somente:

```text
Em analise
```

Nao usar variantes, por exemplo:
- Em análise
- Em Analise
- EmAnalise
