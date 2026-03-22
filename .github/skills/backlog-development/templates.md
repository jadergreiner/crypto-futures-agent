---
name: backlog-templates
description: |
  Templates minimos para o skill backlog-development.
user-invocable: false
---

# Templates

## Criar task nova

```markdown
### BLID-XXX: Titulo curto e especifico

Status: Backlog
Sprint: S-N
Prioridade: P0 | Alta | Media | Baixa

Descricao:
Contexto, sintoma ou oportunidade em 2-4 linhas.

Criterios de Aceite:
- [ ] Item 1
- [ ] Item 2

Dependencias:
- Nenhuma
```

## Registrar sincronizacao

```markdown
## [SYNC] DD-MMM-YYYY HH:MM - backlog-development

Acao: criar | atualizar | repriorizar | sync
Itens: BLID-XXX
Arquivos: docs/BACKLOG.md, docs/SYNCHRONIZATION.md
Motivo: resumo curto e objetivo
```

## Mensagem de commit ASCII

```text
[SYNC] Atualiza BLID-072 no backlog
[FEAT] Cria BLID-074 por queda de Sharpe
```
