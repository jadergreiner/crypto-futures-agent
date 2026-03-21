---
name: live-release-readiness
description: |
  Workflow de readiness para promover execucao do Modelo 2.0 para live.
  Use para: validar ambiente, risco, reconciliacao, evidencias e emitir
  decisao GO/NO-GO auditavel.
applyTo:
  - scripts/model2/go_live_preflight.py
  - core/model2/**
  - risk/**
  - docs/RUNBOOK_M2_OPERACAO.md
  - docs/SYNCHRONIZATION.md
keywords:
  - preflight
  - go-no-go
  - live
  - readiness
  - risco
  - reconciliacao
  - release
---

# Skill: Live Release Readiness

## Objetivo

Executar um workflow padrao para decidir se o ambiente esta apto para
promocao de `shadow` para `live` no Modelo 2.0.

## Quando usar

Use este skill quando houver:

- pedido de liberacao para live;
- mudanca recente em execucao/risco/reconciliacao;
- incidente anterior que exige nova validacao;
- duvida operacional sobre GO/NO-GO.

## Workflow

### Passo 1 - Coletar contexto

Coletar entradas:

- simbolo(s) alvo;
- janela UTC de validacao;
- mudancas recentes (codigo/config/docs);
- evidencias disponiveis (logs, testes, preflight).

Se houver lacuna critica de contexto, marcar como risco bloqueante.

### Passo 2 - Validar ambiente

Checklist:

- configuracoes criticas presentes;
- modo de execucao coerente;
- pre-condicoes de operacao live atendidas.

### Passo 3 - Validar risco e protecao

Checklist:

- `risk_gate` e `circuit_breaker` ativos;
- fluxo de protecao obrigatoria apos fill viavel;
- nenhum bypass de seguranca em caminho critico.

### Passo 4 - Validar reconciliacao e idempotencia

Checklist:

- sem divergencia critica banco vs exchange sem mitigacao;
- estrategia de idempotencia preservada;
- trilha de eventos suficiente para auditoria.

### Passo 5 - Decidir GO/NO-GO

Classificar resultado:

- `GO`: sem bloqueante;
- `GO_COM_RESTRICOES`: sem bloqueante critico, mas com limites operacionais;
- `NO_GO`: qualquer risco bloqueante ou evidencia insuficiente.

### Passo 6 - Plano de acao

Definir:

- acoes imediatas (T+0);
- monitoramento curto prazo (T+1);
- criterios objetivos para reavaliar liberacao.

## Criterios de conclusao

Readiness concluido quando:

- decisao GO/NO-GO esta justificada por evidencias;
- riscos bloqueantes estao explicitados;
- proximo passo operacional esta claro e rastreavel.

## Template de saida

```markdown
## Live Readiness Report

- Escopo: <symbol/all>
- Janela UTC: <inicio-fim>
- Mudancas recentes: <resumo>

### Evidencias
- <item 1>
- <item 2>

### Riscos Bloqueantes
- <lista>

### Riscos Nao Bloqueantes
- <lista>

### Decisao
- GO | GO_COM_RESTRICOES | NO_GO

### Acoes T+0
- <acao>

### Acoes T+1
- <acao>
```
