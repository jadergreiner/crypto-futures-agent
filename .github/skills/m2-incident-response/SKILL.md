---
name: m2-incident-response
description: |
  Playbook para incidentes de execucao do Modelo 2.0.
  Use para: coleta de evidencias, mitigacao fail-safe, reconciliacao e
  registro auditavel em docs.
applyTo:
  - core/model2/**
  - scripts/model2/**
  - risk/**
  - logs/**
  - docs/RUNBOOK_M2_OPERACAO.md
  - docs/SYNCHRONIZATION.md
keywords:
  - incidente
  - live
  - execucao
  - protecao
  - reconciliacao
  - fail-safe
  - auditoria
  - modelo2
---

# Skill: M2 Incident Response

## Objetivo

Aplicar um fluxo padrao para responder incidentes de execucao no Modelo 2.0,
com prioridade para seguranca operacional, preservacao de capital e trilha de
auditoria.

## Quando usar

Use este skill quando houver sinais como:

- posicao aberta sem protecao;
- divergencia entre banco e exchange;
- ordem duplicada, rejeitada ou com estado inconsistente;
- fill sem atualizacao de `signal_executions`;
- comportamento inesperado em `live_service` ou `live_exchange`.

## Principios

- Seguranca antes de performance.
- Em duvida, falhar fechado e bloquear continuidade.
- Nunca desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Registrar o que foi observado, decidido e executado.

## Workflow de Resposta

### Passo 1 - Classificar severidade

Classificar o incidente em uma das categorias:

- `SEV-1`: risco imediato de perda relevante ou posicao desprotegida.
- `SEV-2`: risco moderado com impacto operacional parcial.
- `SEV-3`: anomalia sem risco imediato, mas com necessidade de correcao.

Saida esperada:

- severidade;
- componente afetado;
- simbolo e execution_id (quando houver).

### Passo 2 - Conter e mitigar risco imediato

Aplicar mitigacao fail-safe antes de investigar detalhes:

- interromper novas entradas no fluxo afetado;
- priorizar armamento de protecao para posicoes abertas;
- evitar qualquer fallback permissivo para ordem de mercado de protecao.

Se houver ambiguidade de estado, manter bloqueio ate reconciliacao.

### Passo 3 - Coletar evidencias minimas

Coletar e preservar artefatos para diagnostico:

- estado da execucao em banco (`signal_executions`, eventos relacionados);
- ordens/fills/posicao no exchange;
- logs operacionais no intervalo do incidente;
- payloads de request/response relevantes (sem expor segredo).

Checklist de evidencias:

- execution_id e symbol;
- order_id(s) de entrada/protecao;
- status de SL/TP;
- horario UTC e sequencia de eventos.

### Passo 4 - Reconciliar estado

Comparar estado esperado vs estado observado:

- banco indica `ENTRY_FILLED`, exchange sem posicao;
- posicao aberta, banco sem protecao armada;
- ordem existe no exchange, mas nao em metadata/evento.

Regra de decisao:

- se houver divergencia critica, manter fluxo bloqueado;
- somente liberar fluxo apos estado consistente e auditado.

### Passo 5 - Corrigir causa raiz

Aplicar correcao minima e localizada, com foco em:

- idempotencia (evitar duplicidade);
- retries com backoff para falhas transientes;
- validacao de parametros de protecao antes de envio;
- atualizacao de eventos com `reason`, `status`, `metadata` e timestamp.

Evitar mudancas arquiteturais amplas para corrigir problema local.

### Passo 6 - Validar e registrar

Antes de encerrar incidente:

- validar comportamento corrigido com teste(s) relevante(s);
- validar fluxo seguro (sem posicao desprotegida);
- registrar resultado em `docs/SYNCHRONIZATION.md` quando houver alteracao de
  docs/processo;
- registrar licao operacional em runbook quando aplicavel.

## Criterios de Conclusao

Considerar incidente encerrado apenas quando:

- risco imediato foi mitigado;
- estado banco/exchange esta reconciliado;
- evidencia minima foi preservada;
- acao corretiva foi aplicada e validada;
- registro operacional foi atualizado.

## Template de Relatorio de Incidente

```markdown
## Incidente M2 - Resumo

- Severidade: SEV-X
- Componente: core/model2/<arquivo>
- Symbol: <SYMBOL>
- Execution ID: <ID>
- Janela UTC: <inicio> -> <fim>

### Evidencias
- Exchange: <ordens/posicao>
- Banco: <execucao/eventos>
- Logs: <arquivos>

### Mitigacao Imediata
- <acao 1>
- <acao 2>

### Causa Raiz
- <descricao objetiva>

### Correcao Aplicada
- <mudanca minima>

### Validacao
- <teste/check>

### Follow-up
- <acao futura>
```

## Prompts de Exemplo

```text
Use o skill m2-incident-response para investigar uma posicao sem SL/TP apos
ENTRY_FILLED e proponha mitigacao fail-safe.
```

```text
Aplique o playbook m2-incident-response para reconciliar divergencia entre
signal_executions e ordens da exchange para execution_id 42.
```
