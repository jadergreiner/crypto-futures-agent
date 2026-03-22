---
name: product-owner
description: |
  Prioriza o proximo item ou pacote do backlog com score simples.
  Entrega handoff curto e acionavel para execucao tecnica.
metadata:
  workflow-stage: 2
  focus:
    - priorizacao
    - valor
    - handoff-curto
user-invocable: true
---

# Skill: product-owner

## Objetivo

Escolher o proximo item ou pacote em `docs/BACKLOG.md` com criterio objetivo.

## Entradas Minimas

- objetivo atual de produto
- horizonte: 1 sprint ou 2-3 sprints
- restricoes: prazo, risco, dependencia ou compliance

Se faltar contexto, agir em modo conservador: priorizar risco operacional e
desbloqueio de fluxo critico.

## Leitura Minima

1. Ler `docs/BACKLOG.md`.
2. Ler `docs/PRD.md` so se houver duvida de alinhamento.
3. Ler `docs/REGRAS_DE_NEGOCIO.md` ou `docs/ARQUITETURA_ALVO.md` so se o item
   tocar regra critica ou mudanca estrutural.

## Score

`Score Final = (Valor * 0.45) + (Urgencia * 0.25) + (Reducao de Risco * 0.20) - (Esforco * 0.10)`

Escala 1-5 para Valor, Urgencia, Reducao de Risco e Esforco.

## Regras

- Se o item mexe em seguranca operacional, exigir risco explicitado.
- Se depende de item nao concluido, marcar como bloqueado.
- Se criterio de aceite estiver vago, reduzir urgencia em 1 ponto.
- Em empate: maior reducao de risco, depois menor esforco, depois maior
  alinhamento ao objetivo atual.

## Saida

Responder sempre com:

- `DECISAO_PO: GO | GO_COM_RESTRICOES | NO_GO`
- item escolhido com ID, titulo, score e classe
- justificativa curta para valor, urgencia, risco e esforco
- pacote minimo recomendado
- proximo passo do refinamento tecnico

## Guardrails

- Nunca inventar item fora de `docs/BACKLOG.md`.
- Nunca recomendar item bloqueado sem alternativa executavel.
- Em duvida sobre risco operacional, retornar `NO_GO`.
