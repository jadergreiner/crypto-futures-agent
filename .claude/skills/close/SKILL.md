---
name: close
description: |
  Executa o processo de fechamento da sessao de desenvolvimento:
  garante que tudo esta testado, commitado e pushado.
  Use ao final de cada sessao de trabalho.
---

# Skill: Fechamento de Sessao

## Passos

1. **Verificar estado do repositorio**: `git status`
   - Ha arquivos nao commitados? Continuar.
   - Tudo limpo? Pular para passo 5.

2. **Rodar testes**: `pytest -q`
   - Se falhar: corrigir antes de prosseguir.

3. **Rodar mypy**: `mypy --strict` nos modulos alterados
   - Se falhar: corrigir antes de prosseguir.

4. **Commitar tudo**: `git add -A` + commit com mensagem adequada
   - Seguir padrao `[TAG] Descricao ASCII puro max 72 chars`.
   - Se `docs/` foi alterado, atualizar `docs/SYNCHRONIZATION.md` primeiro.

5. **Push**: enviar para a branch atual.

6. **Relatorio de fechamento**: listar o que foi feito na sessao:
   - Arquivos alterados
   - Testes passando
   - Commits realizados

## Regras

- Nunca fechar sessao com testes falhando.
- Nunca fechar sessao com arquivos nao commitados (salvo intencional).
- Se houver tarefas pendentes, listar para a proxima sessao.
