---
name: "M2 Preflight Live Check"
description: "Validar ambiente e risco antes de executar em live no Modelo 2.0"
argument-hint: "symbol, modo, janela UTC, contexto da mudanca"
agent: "agent"
---

Execute um preflight operacional para liberacao de execucao `live` no
Modelo 2.0, com foco em seguranca, risco e consistencia de estado.

## Entradas

Considere estes parametros (quando informados pelo usuario):

- `symbol` (ou lista de simbolos)
- `modo_atual` (`shadow`, `paper`, `live`)
- `janela_utc` de verificacao
- `mudanca_recente` (codigo/config/docs)

Se algum parametro faltar, assuma valores conservadores e explicite.

## Tarefa

1. Verificar prontidao de ambiente:
   - configuracao critica (`.env`, modo de execucao, limites diarios);
   - integridade basica de dependencias e caminhos operacionais;
   - pre-condicoes de execucao live disponiveis.
2. Verificar risco e protecoes:
   - regras de risco ativas (`risk_gate`, `circuit_breaker`);
   - capacidade de armar protecao obrigatoria apos fill;
   - condicoes de bloqueio (fail-safe) para cenarios ambiguos.
3. Verificar reconciliacao e auditabilidade:
   - consistencia entre estado esperado e observavel;
   - trilha de eventos/logs minima para auditoria;
   - risco de duplicidade/idempotencia em execucao.
4. Classificar decisao final:
   - `GO` (apto para live),
   - `GO_COM_RESTRICOES` (apto com limites),
   - `NO_GO` (bloquear live).

## Formato de Saida (obrigatorio)

Responda exatamente com as secoes abaixo:

1. `Resumo`
2. `Checklist de Ambiente`
3. `Checklist de Risco e Protecoes`
4. `Checklist de Reconciliacao e Auditoria`
5. `Riscos Bloqueantes`
6. `Decisao Final (GO | GO_COM_RESTRICOES | NO_GO)`
7. `Acoes Imediatas Antes do Live`

## Regras

- Em duvida, retornar `NO_GO`.
- Nunca sugerir desativar controles de risco.
- Priorizar mitigacao de risco sobre continuidade operacional.
- Usar linguagem objetiva, com itens verificaveis.
