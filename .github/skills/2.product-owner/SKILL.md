---
name: 2.product-owner
description: |
  Prioriza o proximo item ou pacote do backlog com foco em valor real
  capturado em producao via `iniciar.bat`. Usa a skill
  `14.production-value-review` quando a evidencia for fraca, contesta lacunas
  de valor e entrega prompt acionavel para o agente Arquiteto de Solucoes.
metadata:
  workflow-stage: 2
  focus:
    - priorizacao
    - valor
    - valor-real
    - iniciar-bat
    - handoff-arquiteto
user-invocable: true
---

# Skill: product-owner

## Objetivo

Escolher o proximo item ou pacote em `docs/BACKLOG.md` com criterio objetivo,
sem confundir implementacao tecnica com valor real de producao.

## Entradas Minimas

- objetivo atual de produto
- horizonte: 1 sprint ou 2-3 sprints
- restricoes: prazo, risco, dependencia ou compliance
- contexto operacional do `iniciar.bat` quando existir
- evidencias observaveis: log, status, artefato, bloqueio fail-safe ou lacuna

Se faltar contexto, agir em modo conservador: priorizar risco operacional e
desbloqueio de fluxo critico.

## Leitura Minima

1. Ler `docs/BACKLOG.md`.
2. Ler `docs/PRD.md` so se houver duvida de alinhamento.
3. Ler `docs/REGRAS_DE_NEGOCIO.md` ou `docs/ARQUITETURA_ALVO.md` so se o item
   tocar regra critica ou mudanca estrutural.
4. Se o valor real em `iniciar.bat` estiver indireto, fraco ou puramente
   tecnico, usar `.github/skills/14.production-value-review/SKILL.md` antes de
   pontuar.

## Score

`Score Final = (Valor Real Capturado * 0.35) + (Valor * 0.25) + (Urgencia * 0.20) + (Reducao de Risco * 0.15) - (Esforco * 0.05)`

Escala 1-5 para Valor Real Capturado, Valor, Urgencia, Reducao de Risco e
Esforco.

## Regras

- Se o item mexe em seguranca operacional, exigir risco explicitado.
- Se depende de item nao concluido, marcar como bloqueado.
- Se criterio de aceite estiver vago, reduzir urgencia em 1 ponto.
- Se o valor real em `iniciar.bat` nao estiver comprovado, registrar a lacuna
  ou escalar ao usuario; nao inferir beneficio por simpatia tecnica.
- Se o valor estiver indireto, puramente tecnico ou contestado, usar
  `.github/skills/14.production-value-review/SKILL.md` antes de pontuar.
- Em empate: maior reducao de risco, depois menor esforco, depois maior
  alinhamento ao objetivo atual.
- Ao priorizar, atualizar no backlog o status exato: `Em analise`.
- No rodape do item, registrar:
  `PO: <resumo>. Ao fim deste desenvolvimento estarei feliz se <resultado mensuravel>.`
- Nao ultrapassar 260 caracteres no comentario `PO:`.

## Template de Comentario PO

Usar formato fixo no rodape do item priorizado:

```text
PO: <resumo>. Ao fim deste desenvolvimento estarei feliz se <resultado mensuravel>.
```

Validacao minima antes da saida:
1. Status aplicado no item: `Em analise` (exato, sem acento).
2. Comentario iniciado por `PO:`.
3. Comentario contem literalmente `Ao fim deste desenvolvimento estarei feliz se`.
4. Tamanho maximo de 260 caracteres no comentario completo.

## Saida

A resposta final deve ser somente um prompt acionavel para o agente
`3.solution-architect`, sem prefacio adicional, no formato abaixo.

Bloco padrao canonico: ver `.github/skills/2.product-owner/templates.md`.

```text
Voce e o agente 3.solution-architect desta task.

Contexto de priorizacao do PO:
- DECISAO_PO: <GO | GO_COM_RESTRICOES | NO_GO>
- Referencia do backlog: <BLID/ID>
- Titulo do item: <titulo>
- Objetivo de negocio: <resultado esperado>
- Justificativa de prioridade: <valor real, valor, urgencia, risco e esforco>
- Valor real capturado em iniciar.bat:
  - Mudanca perceptivel: <o que muda no terminal, log, status ou runtime>
  - Evidencias ou lacuna: <logs, artefatos, bloqueios ou lacuna declarada>
  - Contestacao restante: <nenhuma ou pergunta objetiva>
- Status aplicado no backlog: Em analise
- Comentario PO (<=260): PO: <resumo>. Ao fim deste desenvolvimento estarei feliz se <resultado mensuravel>.

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

## Guardrails

- Nunca inventar item fora de `docs/BACKLOG.md`.
- Nunca recomendar item bloqueado sem alternativa executavel.
- Em duvida sobre risco operacional, retornar `NO_GO`.
- Nunca usar variante de status diferente de `Em analise`.
- Nunca afirmar valor real sem evidencia operacional ou lacuna declarada.
- Se a lacuna for de negocio, escalar ao usuario humano com pergunta objetiva.
- Nunca exceder 260 caracteres no comentario `PO:`.
- Ao editar `docs/*.md`, preservar wrapping, indentacao e listas para nao
  introduzir erro de `markdownlint` nos arquivos alterados.
