---
name: "M2 Go No-Go Report"
description: "Gerar relatorio final GO/NO-GO para promocao de shadow para live"
argument-hint: "symbol, janela UTC, mudancas recentes, evidencias"
agent: "agent"
---

Gere um relatorio objetivo de decisao para promocao em live do Modelo 2.0.

## Entrada

Use os parametros fornecidos pelo usuario (quando disponiveis):

- `symbol` (ou `ALL`)
- `janela_utc`
- `mudancas_recentes`
- `evidencias` (logs, eventos, testes, preflight)

Se faltar algum item, explicite a lacuna e assuma postura conservadora.

## Tarefa

1. Consolidar evidencias operacionais, risco e reconciliacao.
2. Classificar achados em bloqueantes e nao bloqueantes.
3. Emitir decisao: `GO`, `GO_COM_RESTRICOES` ou `NO_GO`.
4. Definir plano de acao imediato antes de live.

## Criterios minimos

- Controles de risco ativos e sem bypass.
- Possibilidade de protecao obrigatoria apos fill.
- Sem divergencia critica banco vs exchange sem mitigacao.
- Evidencia auditavel suficiente para decisao.

## Formato de saida (obrigatorio)

Responder exatamente com:

1. `Resumo Executivo`
2. `Evidencias Validadas`
3. `Riscos Bloqueantes`
4. `Riscos Nao Bloqueantes`
5. `Decisao (GO | GO_COM_RESTRICOES | NO_GO)`
6. `Condicoes para Liberacao`
7. `Plano de Acoes (T+0 e T+1)`

## Regras

- Em duvida, decidir `NO_GO`.
- Nunca sugerir desativar `risk_gate` ou `circuit_breaker`.
- Usar linguagem objetiva e rastreavel.
