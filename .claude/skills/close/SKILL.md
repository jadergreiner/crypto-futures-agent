---
name: close
description: |
   Fecha a sessao com custo minimo de contexto.
   Se houver alteracoes, reutiliza commit; se estiver limpo, resume o estado.
metadata:
  focus:
    - economia-de-tokens
    - fechamento
    - delegacao
---

# Skill: Fechamento de Sessao

## Objetivo

Encerrar a sessao sem duplicar checklist e sem reler contexto desnecessario.

## Fluxo Economico

1. Rodar `git status`.
2. Se o repositorio estiver limpo, responder apenas com estado limpo e
   pendencias reais da sessao, se existirem.
3. Se houver alteracoes, executar a skill `commit` em vez de repetir o
   fluxo completo aqui.
4. Entregar resumo curto com:
   - grupos de arquivos alterados
   - status de `pytest -q` e `mypy --strict`
   - commit/push realizados ou motivo do bloqueio

## Guardrails

- Nunca fechar sessao com testes falhando.
- Nunca duplicar o passo a passo da skill `commit`.
- Nao gerar inventario longo de arquivos se um resumo por area basta.
- Se houver pendencias, listar apenas as relevantes para a proxima sessao.
