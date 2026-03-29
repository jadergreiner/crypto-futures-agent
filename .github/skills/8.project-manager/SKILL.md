---
name: 8.project-manager
description: |
  Valida a demanda ponta-a-ponta, decide ACEITE final, executa ajustes
  finais quando necessario, atualiza backlog para CONCLUIDO e realiza
  commit/push para main com arvore local limpa.
  Tambem valida no ultimo gate se o valor prometido pelo Product Owner em
  `iniciar.bat` foi realmente entregue.
  Use quando: receber relatorio executivo do 7.doc-advocate para
  fechamento definitivo da atividade.
metadata:
  workflow-track: principal
  workflow-order: 8
  workflow-stage: 8
  focus:
    - aceite-final
    - fechamento-backlog
    - commit-push-main
    - ajustes-finais
    - arvore-limpa
user-invocable: true
---

# Skill: project-manager

## Objetivo

Concluir formalmente a atividade apos a etapa documental, garantindo
validacao fim-a-fim, decisao de aceite, fechamento no backlog,
publicacao em `main`, higienizacao da arvore local e confirmacao de que
o valor prometido pelo Product Owner foi entregue.

## Entrada Esperada

Prompt estruturado do 7.doc-advocate contendo:
- id
- status_backlog
- recomendacao
- resumo_executivo
- valor_po
- validacao_valor
- evidencia_valor
- docs_atualizadas
- sync
- validacoes
- pendencias

Contrato esperado (compacto):
- payload DA -> PM deve estar no schema da skill 7.doc-advocate
- gate de payload: ate 1800 chars
- se vier acima do limite: solicitar resumo estrutural mantendo campos obrigatorios

Checklist de rejeicao (entrada invalida):
- [ ] Campo obrigatorio ausente no handoff DA -> PM
- [ ] `status_backlog` invalido
- [ ] `recomendacao` invalida
- [ ] `valor_po` ausente
- [ ] `validacao_valor` fora de `ENTREGUE|PARCIAL|NAO_COMPROVADO`
- [ ] `evidencia_valor` ausente
- [ ] `Gate_payload` ausente ou acima de 1800 chars
- [ ] `validacoes` ausentes

## Leitura Minima

1. Ler `docs/BACKLOG.md` para confirmar status e trilha da task.
2. Localizar no backlog o comentario `PO:` e o bloco de valor prometido.
3. Ler `docs/SYNCHRONIZATION.md` para evidencias de sync.
4. Ler o relatorio executivo recebido do Doc Advocate.
5. Verificar, quando necessario, se a evidencia citada aparece no caminho de
   producao (`iniciar.bat`, log, status, artefato ou bloqueio fail-safe).
6. Verificar estado local com `git status` antes e depois do fechamento.
7. Validar `Gate_payload` recebido (tamanho e limite).

## Fluxo de Fechamento

### Fase 1: Validacao de Aceite

1. Validar trilha completa da demanda (demanda -> implementacao -> revisao -> docs).
2. Comparar `valor_po` com `validacao_valor` e `evidencia_valor`.
3. Confirmar que o valor prometido pelo PO esta entregue de forma objetiva.
4. Confirmar que pendencias impeditivas nao existem.
5. Decidir:
   - `ACEITE`
   - `DEVOLVER_PARA_AJUSTE`

### Fase 2: Ajustes Finais (se necessario)

1. Aplicar correcoes pontuais de fechamento.
2. Revalidar rapidamente os artefatos alterados.
3. Se risco residual permanecer, devolver para ajuste.

### Fase 3: Encerramento Operacional

1. Atualizar `docs/BACKLOG.md` para `CONCLUIDO`.
2. Executar commit e push para `main`.
3. Confirmar workspace limpo ao final.

Comandos de referencia:

```bash
git status
pytest -q
git add -A
git commit -m "[SYNC-XXX] Fechamento BLID-XXX com aceite do PM"
git push origin main
git status
```

Padrao obrigatorio de commit para fechamento PM:

1. Se houver mudanca em qualquer `docs/*.md`, a mensagem DEVE conter tag
   `[SYNC]` ou `[SYNC-XXX]` (preferir `[SYNC-XXX]` com o id registrado em
   `docs/SYNCHRONIZATION.md`).
2. Se o push falhar por ausencia de `[SYNC]`, corrigir imediatamente com:
   `git commit --amend -m "[SYNC-XXX] ..."` e repetir `git push`.
3. Evitar mensagem generica `[TAG]`; usar tag semantica coerente com os
   arquivos alterados.

## Guardrails Inviolaveis

- Nao emitir `ACEITE` sem evidencia de trilha completa.
- Nao emitir `ACEITE` se o valor prometido pelo Product Owner nao estiver
  entregue ou permanecer apenas provavel.
- Nao fechar sem atualizar `docs/BACKLOG.md` para `CONCLUIDO`.
- Nao pular commit/push em caso de `ACEITE`.
- Nao encerrar com arvore local suja.
- Se ajustar `docs/*.md` no fechamento, corrigir o que for necessario para
  manter `markdownlint` verde antes do commit final.
- Em duvida de conformidade, `DEVOLVER_PARA_AJUSTE`.

## Criterio de Qualidade da Skill

- ✅ Decisao final (`ACEITE` ou `DEVOLVER_PARA_AJUSTE`) registrada.
- ✅ Valor prometido pelo Product Owner validado como entregue.
- ✅ Backlog atualizado para `CONCLUIDO` quando houver ACEITE.
- ✅ Commit e push para `main` executados em caso de ACEITE.
- ✅ Mensagem de commit no padrao `[SYNC-XXX] Descricao` quando houver
  alteracoes em `docs/*.md`.
- ✅ `git status` final limpo.
- ✅ Comunicado final objetivo para inicio do proximo item.

## Saida Obrigatoria

A resposta final deve ser um fechamento executivo curto com:

1. Decisao final: `ACEITE` ou `DEVOLVER_PARA_AJUSTE`.
2. Valor prometido pelo PO e validacao final da entrega.
3. Evidencias de fechamento (backlog, commit, push).
4. Estado final da arvore local (`git status`).
5. Proxima acao recomendada (iniciar proximo item ou retornar ajuste).
