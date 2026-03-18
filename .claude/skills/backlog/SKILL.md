---
name: backlog
description: |
  Adiciona, atualiza ou consulta itens em docs/BACKLOG.md.
  Sincroniza automaticamente TRACKER.md e SYNCHRONIZATION.md.
  Use para: criar task, mudar status, mover sprint, gerar relatorio.
---

# Skill: Backlog

## Comportamento Principal

- **Ler primeiro** `docs/BACKLOG.md` para entender o estado atual.
- **Agir diretamente**: inserir ou atualizar o item sem pedir confirmacao
  adicional, salvo ambiguidade explicita no pedido.
- Apos qualquer escrita em `docs/BACKLOG.md`:
  1. Atualizar `docs/TRACKER.md` (tabela compacta de sprint)
  2. Registrar em `docs/SYNCHRONIZATION.md` com timestamp e tag `[SYNC]`

## Formato de Task

```markdown
### BLID-XXX: Titulo Descritivo

**Sprint:** S-N
**Prioridade:** Alta | Media | Baixa
**Status:** Backlog | Planned | In Progress | Done | WontDo

**Descricao:**
Contexto do problema e por que importa.

**Criterios de Aceite:**
- [ ] Criterio 1
- [ ] Criterio 2

**Dependencias:**
- BLID-YYY ou Nenhuma
```

## IDs

- Gerar proximo ID sequencial: verificar o maior BLID existente + 1.
- Formato: `BLID-NNN` (tres digitos com zero a esquerda).

## Commit Apos Alteracao

Usar `[SYNC]` ou `[FEAT]` conforme o tipo de mudanca.
Mensagem ASCII puro, max 72 chars, sem acentos.

## Exemplos de Uso

```
/backlog Criar task para implementar dashboard de P&L por agente
/backlog Qual o status atual de S-2?
/backlog Mover BLID-055 de S-3 para S-2
/backlog BLID-042 esta bloqueada? Verificar dependencias
```
