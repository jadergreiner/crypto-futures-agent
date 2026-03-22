---
name: backlog-development
description: |
  Opera docs/BACKLOG.md com leitura local e sync minimo.
  Consulta docs de produto so quando houver impacto real.
metadata:
  workflow-stage: 1
  focus:
    - economia-de-tokens
    - acao-direta
user-invocable: true
---

# Skill: backlog-development

## Objetivo

Criar, atualizar, consultar e sincronizar backlog com o menor contexto util.

## Leitura Minima

1. Buscar a chave no backlog: BLID, sprint, iniciativa ou status.
2. Ler apenas o bloco alvo em `docs/BACKLOG.md`.
3. Ler `docs/PRD.md` so se houver mudanca de escopo ou prioridade macro.
4. Ler `docs/ARQUITETURA_ALVO.md`, `docs/ADRS.md`,
   `docs/MODELAGEM_DE_DADOS.md` ou `docs/REGRAS_DE_NEGOCIO.md` so se a
   alteracao tocar arquitetura, schema ou regra oficial.
5. Ler `docs/SYNCHRONIZATION.md` apenas para registrar sync.

## Fluxo

1. Classificar o pedido: consultar, criar, atualizar ou sincronizar.
2. Ler apenas os arquivos exigidos pelo tipo do pedido.
3. Agir direto quando a instrucao for explicita.
4. Perguntar so se houver ambiguidade material.
5. Preservar o formato existente do backlog.
6. Registrar sync apenas quando houver alteracao em doc oficial.

## Guardrails

- `docs/BACKLOG.md` e a fonte de verdade.
- Nao citar `docs/TRACKER.md` ou `docs/ROADMAP.md` como dependencias.
- Gerar novo BLID usando o maior numero existente + 1.
- Nao reformatar secoes antigas sem necessidade.
- Se a mudanca veio de RL/live, exigir evidencia minima: metrica, janela,
  impacto e acao proposta.

## Saida

- Consulta: ate 5 linhas.
- Criacao ou atualizacao: ate 8 linhas.
- Sync: ate 6 linhas.
- Nao gerar tabela, checklist longa ou diff textual sem pedido explicito.
