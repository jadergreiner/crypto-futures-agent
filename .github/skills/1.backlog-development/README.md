---
name: backlog-development-readme
description: |
  Guia rapido da skill backlog-development.
user-invocable: false
---

# backlog-development

Skill para operar o backlog com pouca leitura e pouca verbosidade.

## Quando usar

- criar item em docs/BACKLOG.md
- mover status, sprint ou prioridade
- consultar status de BLID ou sprint
- sincronizar docs oficiais impactados
- registrar aprendizado vindo de RL/live no backlog

## Como a skill economiza tokens

- le docs/BACKLOG.md primeiro e quase sempre apenas ele
- consulta PRD e docs arquiteturais so quando ha impacto real
- evita tabelas longas e checklists repetidas
- edita direto quando o pedido e explicito
- nao menciona arquivos que nao existem no repositorio

## Uso rapido

```text
/backlog-development Criar task para revisar slippage no live
/backlog-development Mover BLID-072 para Done
/backlog-development Qual o status da sprint S-2?
/backlog-development Sincronizar backlog e PRD apos repriorizacao da BLID-073
```

## Arquivos desta skill

- SKILL.md: regras operacionais e guardrails
- examples.md: prompts curtos de referencia
- templates.md: blocos minimos para criacao e sync

Leia SKILL.md para o comportamento completo.
