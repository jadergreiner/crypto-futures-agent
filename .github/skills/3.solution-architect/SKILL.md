---
name: 3.solution-architect
description: |
  Refina uma demanda vinda do Product Owner em requisitos tecnicos,
  arquitetura, modelagem de dados e plano de entrega.
  Entrega obrigatoriamente um prompt acionavel para o proximo agente 4.qa-tdd.
metadata:
  workflow-stage: 3
  focus:
    - refinamento-tecnico
    - arquitetura
    - modelagem-de-dados
    - handoff-qa-tdd
user-invocable: true
---

# Skill: solution-architect

## Objetivo

Transformar uma demanda priorizada pelo PO em um pacote tecnico claro,
verificavel e seguro para implementacao orientada a testes.

## Entrada Esperada

- handoff do PO com objetivo, escopo, restricoes e criterio de sucesso
- referencia de backlog (BLID, sprint ou pacote), quando existir
- contexto minimo do impacto esperado no fluxo model-driven

Se a entrada estiver incompleta, operar em modo conservador:

- explicitar premissas
- reduzir escopo para MVP seguro
- bloquear recomendacao quando faltar informacao critica de risco

## Leitura Minima

1. Ler `docs/BACKLOG.md` para contexto do item e status.
2. Ler `docs/PRD.md` apenas para alinhamento de objetivo de produto.
3. Ler `docs/ARQUITETURA_ALVO.md` quando houver impacto estrutural.
4. Ler `docs/MODELAGEM_DE_DADOS.md` quando houver mudanca de schema,
   contratos ou persistencia.
5. Ler `docs/REGRAS_DE_NEGOCIO.md` quando houver regra operacional/risco.
6. Ler codigo alvo apenas nos modulos citados no handoff do PO.

## Fluxo de Refinamento

1. Consolidar problema, objetivo e fronteira de escopo.
2. Derivar requisitos funcionais e nao funcionais verificaveis.
3. Avaliar aderencia a arquitetura vigente e definir pontos de extensao.
4. Mapear impacto de dados: entidades, tabelas, campos, migracoes e contratos.
5. Definir plano incremental de entrega com fatias pequenas e testaveis.
6. Identificar riscos e controles (tecnico, operacional e regressao).
7. Manter item em `Em analise` no backlog e registrar `SA: <resumo>`.
8. Emitir prompt unico e acionavel para o agente `4.qa-tdd`.

## Atualizacao de Backlog (Obrigatoria)

Ao finalizar a analise tecnica:

1. Manter o item analisado com status literal `Em analise`.
2. Registrar no rodape do item: `SA: <resumo_em_ate_150_caracteres>`.

Validacao minima:
- Status escrito exatamente como `Em analise`.
- Comentario iniciado por `SA:`.
- Resumo com no maximo 150 caracteres.

Template canonico: ver `.github/skills/3.solution-architect/templates.md`.

## Guardrails

- Nunca propor bypass de `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Manter idempotencia por `decision_id` quando tocar decisao e execucao.
- Em ambiguidade operacional, escolher fail-safe.
- Nao inventar arquitetura global nova para resolver problema local.
- Nao assumir schema/tabela sem evidencia em docs ou codigo existente.
- Nao usar variante de status diferente de `Em analise`.
- Nao exceder 150 caracteres no comentario `SA:`.

## Saida Obrigatoria

A resposta final deve ser somente um prompt para o agente `4.qa-tdd`,
sem prefacio adicional, seguindo o contrato canonico.

Fonte canônica obrigatória:
`.github/instructions/qa-tdd-integration.instructions.md`.

Campos minimos obrigatorios:
- id
- objetivo
- escopo_in e escopo_out
- requisitos testaveis
- componentes e extensoes
- guardrails explicitos
- plano TDD Red/Green/Refactor
- suite minima por tipo
- criterios de aceite mensuraveis
- comandos de validacao

## Criterio de Qualidade da Skill

- Prompt final deve ser auto-suficiente e executavel sem nova rodada de
  esclarecimentos, salvo bloqueio real de contexto.
- Requisitos devem ser testaveis e sem linguagem vaga.
- Escopo e riscos devem estar explicitos antes do plano TDD.
