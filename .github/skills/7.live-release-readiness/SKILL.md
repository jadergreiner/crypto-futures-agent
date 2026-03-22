---
name: live-release-readiness
description: |
  Decide GO, GO_COM_RESTRICOES ou NO_GO para promocao a live.
  Usa evidencias minimas, guardrails de risco e resposta curta.
metadata:
  workflow-stage: 7
  focus:
    - go-no-go
    - seguranca-operacional
    - leitura-minima
user-invocable: true
---

# Skill: live-release-readiness

## Objetivo

Decidir se o ambiente esta apto para promocao de `shadow` para `live`
com base em evidencias minimas e criterio auditavel.

## Quando usar

Use este skill quando houver:

- pedido de liberacao para live;
- mudanca recente em execucao/risco/reconciliacao;
- incidente anterior que exige nova validacao;
- duvida operacional sobre GO/NO-GO.

## Leitura Minima

Regra principal: ler apenas o necessario para decidir.

Ordem de leitura:

1. Ler a evidência mais direta do pedido: preflight, testes, diff,
  logs ou configuracao citada pelo usuario.
2. Ler `scripts/model2/go_live_preflight.py`, `risk/risk_gate.py` e
  `risk/circuit_breaker.py` apenas se a decisao depender da logica.
3. Ler `core/model2/**` apenas no trecho afetado por mudanca recente,
  incidente ou duvida especifica.
4. Ler `docs/RUNBOOK_M2_OPERACAO.md` e `docs/SYNCHRONIZATION.md`
  apenas se o pedido exigir validar processo ou registrar sync.

Evitar reler modulos inteiros, repetir checklist e recomendar live sem
preflight ou evidencias minimas.

## Fluxo

1. Definir escopo: simbolo, janela UTC, ambiente e mudancas recentes.
2. Marcar lacunas criticas como risco bloqueante, sem prolongar leitura.
3. Validar ambiente e pre-condicoes live.
4. Confirmar guardrails de risco e protecao obrigatoria.
5. Verificar reconciliacao e idempotencia apenas no caminho afetado.
6. Classificar a decisao: `GO`, `GO_COM_RESTRICOES` ou `NO_GO`.
7. Responder com evidencias, riscos reais e acoes T+0/T+1.

## Criterios Minimos

- Preflight coerente com o modo live.
- `risk_gate` e `circuit_breaker` ativos.
- Sem divergencia critica banco vs exchange sem mitigacao.
- Trilha de eventos suficiente para auditoria.
- Nenhum risco bloqueante sem plano de contencao.

## Regra de Decisao

- `GO`: sem bloqueante e com evidencia suficiente.
- `GO_COM_RESTRICOES`: sem bloqueante critico, mas com limite operacional
  explicito.
- `NO_GO`: risco bloqueante, evidencia insuficiente ou protecao incerta.

## Saida

Responder em bloco curto.

- Escopo
- Evidencias
- Riscos bloqueantes
- Riscos nao bloqueantes
- Decisao
- Acoes T+0
- Acoes T+1

Nao gerar relatorio longo se a decisao couber em 8-12 linhas.
