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

Meta de custo: minimizar leitura e escrita sem perder rastreabilidade.

## Modo Economico

Regra principal: ler apenas o necessario para cumprir o pedido.

1. Buscar primeiro no backlog por chave (BLID, iniciativa, sprint, status).
2. Ler apenas o bloco alvo em `docs/BACKLOG.md` (janela local), nao o arquivo
  inteiro, quando o pedido for pontual.
3. Ler `docs/PRD.md` apenas se o pedido mexer em escopo, prioridade
  macro, roadmap ou iniciativa.
4. Ler docs arquiteturais apenas se a mudanca alterar arquitetura,
  schema, fluxo ou regra oficial.
5. Ler `docs/SYNCHRONIZATION.md` apenas quando for registrar sync.

Politica de leitura por tipo:

- Consulta de status: 1 busca + 1 leitura local.
- Atualizacao de item existente: 1 busca + 1 leitura local + edicao.
- Criacao de item novo: 1 busca de numeracao BLID + 1 leitura da secao alvo.
- Sync de docs: ler apenas arquivos realmente impactados.

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

Atalho para consultas simples:

1. Identificar entidade alvo (BLID, sprint, iniciativa).
2. Ler so o bloco da entidade.
3. Responder em ate 5 linhas.

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

Regra de custo:

- Se a mudanca ficou restrita ao backlog e nao mudou escopo/arquitetura,
  sincronizar apenas `docs/SYNCHRONIZATION.md`.

## Formato de Resposta

- Consulta: ate 5 linhas.
- Criacao/atualizacao: ate 8 linhas.
- Sincronizacao: ate 6 linhas.
- Nao gerar tabela ou diff longo sem pedido explicito.

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
