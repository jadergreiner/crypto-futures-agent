---
name: backlog
description: |
  Gerencia docs/BACKLOG.md com leitura minima e acao direta.
  Consulte docs de produto e arquitetura so quando houver impacto real.
metadata:
  focus:
    - economia-de-tokens
    - backlog
    - sync
---

# Skill: Backlog

## Objetivo

Gerenciar backlog com contexto minimo e saida curta.

## Modo Economico

Regra principal: ler apenas o necessario para cumprir o pedido.

1. Sempre ler `docs/BACKLOG.md`.
2. Ler `docs/PRD.md` apenas se o pedido mexer em escopo, prioridade
   macro, roadmap ou iniciativa.
3. Ler docs arquiteturais apenas se a mudanca alterar arquitetura,
   schema, fluxo ou regra oficial.
4. Ler `docs/SYNCHRONIZATION.md` apenas quando for registrar sync ou
   checar trilha de auditoria.

Evitar:

- reler arquivos ja suficientes para a decisao
- gerar tabelas longas sem pedido explicito
- pedir confirmacao quando o pedido de escrita for explicito
- citar arquivos inexistentes como `docs/TRACKER.md`

## Fluxo Operacional

1. Classificar o pedido: criar, atualizar, consultar ou sincronizar.
2. Ler somente os arquivos necessarios pela regra acima.
3. Agir diretamente se o pedido for explicito.
4. Perguntar apenas se houver ambiguidade material.
5. Ao escrever, preservar o formato ja adotado em `docs/BACKLOG.md`.
6. Registrar em `docs/SYNCHRONIZATION.md` quando houver alteracao em
   doc oficial.
7. Responder de forma curta com resultado, impacto e pendencias reais.

## Regras de Escrita

- `docs/BACKLOG.md` e a fonte de verdade para tarefas e status.
- Nao impor template novo se a secao existente usar formato diferente.
- Gerar novo BLID apenas para itens que usam a familia BLID.
- Ao criar BLID, usar o maior numero existente + 1.
- Manter texto em portugues.
- Se o usuario pedir commit, usar ASCII puro e no maximo 72 caracteres.

## Sincronizacao Minima

- Atualizar `docs/SYNCHRONIZATION.md` quando houver alteracao em
  `docs/BACKLOG.md` ou outra doc oficial.
- Atualizar `docs/PRD.md` apenas se houver impacto real em escopo.
- Nao sincronizar por reflexo: se um arquivo nao foi impactado, nao citar.

## Template Minimo

Use apenas quando for criar entrada nova e o bloco alvo aceitar esse formato.

```markdown
### BLID-XXX: Titulo Descritivo

Status: Backlog | Planned | In Progress | Done | WontDo
Sprint: S-N
Prioridade: Alta | Media | Baixa

Descricao:
Contexto do problema e por que importa.

Criterios de Aceite:
- [ ] Criterio 1
- [ ] Criterio 2

Dependencias:
- BLID-YYY ou Nenhuma
```

## Exemplos de Uso

```
/backlog Criar task para implementar dashboard de P&L por agente
/backlog Qual o status atual de S-2?
/backlog Mover BLID-055 de S-3 para S-2
/backlog BLID-042 esta bloqueada? Verificar dependencias
```
