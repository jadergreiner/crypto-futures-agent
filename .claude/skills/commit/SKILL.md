---
name: commit
description: |
  Executa o ciclo completo de qualidade e commit: roda testes, mypy strict,
  faz git add -A, gera mensagem de commit em portugues e faz push.
  Use quando quiser commitar e publicar as alteracoes atuais.
---

# Skill: Commit & Push

## Passos

1. Rodar testes: `pytest -q`
   - Se falhar: corrigir os erros antes de prosseguir.

2. Rodar mypy: `mypy --strict` nos modulos alterados
   - Se falhar: corrigir os erros antes de prosseguir.

3. Checar arquivos alterados: `git diff --stat` e `git status`

4. Fazer stage de tudo: `git add -A`
   - Inclui arquivos novos, modificados e deletados — sem perguntar.

5. Gerar mensagem de commit seguindo o padrao:
   `[TAG] Descricao breve em portugues ASCII puro (max 72 chars)`
   - Tags validas: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`
   - Sem acentos, sem emojis, apenas ASCII 0-127.

6. Criar o commit.

7. Fazer push para a branch atual.

## Regras

- Nunca usar `--no-verify` ou pular hooks.
- Nunca commitar sem testes e mypy passando.
- Sempre incluir arquivos deletados no stage.
- Se `docs/` foi alterado, atualizar `docs/SYNCHRONIZATION.md` com tag
  `[SYNC]` antes do commit.
