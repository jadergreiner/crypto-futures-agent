---
name: commit
description: |
  Executa qualidade e commit com saida curta.
  Roda pytest -q, mypy nos modulos alterados, depois add, commit e push.
metadata:
  focus:
    - economia-de-tokens
    - commit
    - qualidade
---

# Skill: Commit & Push

## Objetivo

Publicar alteracoes com minimo de leitura, minimo de repeticao e sem
omitir validacao obrigatoria.

## Fluxo Economico

1. Checar `git status` e os arquivos alterados.
2. Rodar `pytest -q` uma vez.
3. Rodar `mypy --strict` apenas nos modulos Python alterados.
4. Se `docs/` mudou, garantir atualizacao de
   `docs/SYNCHRONIZATION.md` antes do commit.
5. Fazer `git add -A`.
6. Gerar mensagem no formato
   `[TAG] Descricao breve em portugues ASCII puro (max 72 chars)`.
7. Criar o commit.
8. Fazer push para a branch atual.

## Guardrails

- Nunca usar `--no-verify` ou pular hooks.
- Nunca commitar com testes ou mypy falhando.
- Sempre incluir arquivos novos, modificados e deletados no stage.
- Nao imprimir logs longos sem necessidade; resumir apenas falhas,
  arquivos afetados e acao corretiva.
- Nao pedir confirmacao para incluir deletados: usar `git add -A`.
- Tags validas: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`.
