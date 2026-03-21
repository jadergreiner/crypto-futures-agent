---
applyTo: docs/**
---

# Docs Sync - Checklist e Padrao MD013

Estas regras se aplicam a qualquer alteracao em documentacao em `docs/**`.

## Objetivo

- Manter a documentacao consistente, auditavel e sincronizada com o codigo.
- Evitar regressao de formato markdown, especialmente MD013 (80 colunas).

## Checklist Automatico de Sincronizacao

Ao editar qualquer arquivo em `docs/**`, verificar e aplicar:

1. Atualizar referencias cruzadas relevantes entre docs tecnicos e operacionais.
2. Registrar mudanca em `docs/SYNCHRONIZATION.md` com tag `[SYNC]` quando
   houver alteracao de conteudo oficial.
3. Se houver impacto em backlog/prioridades, sincronizar com
   `docs/BACKLOG.md` e `docs/TRACKER.md` (quando existir no workspace).
4. Se mudar regra de negocio, arquitetura ou schema, refletir nos docs fonte:
   `docs/REGRAS_DE_NEGOCIO.md`, `docs/ARQUITETURA_ALVO.md` e
   `docs/MODELAGEM_DE_DADOS.md`.

## Padrao de Qualidade Markdown

- Respeitar MD013: linhas com no maximo 80 colunas.
- Manter UTF-8 valido.
- Usar titulos descritivos e estrutura previsivel.
- Em blocos de codigo, sempre informar linguagem.
- Evitar duplicacao: preferir links para docs oficiais (link, nao duplicar).

## Validacao Minima Antes de Entregar

- Executar lint de docs: `markdownlint docs/*.md`.
- Executar teste de sincronizacao: `pytest -q tests/test_docs_model2_sync.py`.
- Confirmar que a mudanca ficou registrada no audit trail quando aplicavel.

## Guardrails

- Nao remover historico util de sincronizacao sem justificativa.
- Nao introduzir mudanca de formato ampla sem necessidade funcional.
- Nao deixar alteracao de doc sem rastreabilidade de impacto.
