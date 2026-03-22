---
name: backlog-development
description: |
  Gerencia docs/BACKLOG.md com leitura minima e sync objetivo.
  Consulte docs de produto e arquitetura so quando houver impacto real.
metadata:
  tags:
    - backlog
    - sync
    - rl
  focus:
    - economia-de-tokens
    - acao-direta
user-invocable: true
---

# Skill: backlog-development

## Objetivo

Gerenciar backlog com contexto minimo e acao direta.

Meta de custo: minimizar leitura e escrita sem perder rastreabilidade.

Use esta skill para:

- criar task nova em docs/BACKLOG.md
- atualizar status, sprint, prioridade ou dependencias
- consultar status do backlog ou de uma BLID
- sincronizar docs oficiais quando houver impacto real
- transformar evidencia de RL/live em item de backlog auditavel

## Modo Economico

Regra principal: ler apenas o necessario para cumprir o pedido.

Ordem de leitura:

1. Buscar primeiro no backlog por chave (BLID, iniciativa, sprint, status).
2. Ler apenas o bloco alvo em docs/BACKLOG.md (janela local), nao o arquivo
  inteiro, quando o pedido for pontual.
3. Ler docs/PRD.md apenas se o pedido alterar escopo, prioridade macro,
  roadmap ou iniciativa.
4. Ler docs/ARQUITETURA_ALVO.md e docs/ADRS.md apenas se a mudanca alterar
  camada, contrato, fluxo ou decisao arquitetural.
5. Ler docs/MODELAGEM_DE_DADOS.md e docs/REGRAS_DE_NEGOCIO.md apenas se
  houver mudanca de schema ou regra oficial.
6. Ler docs/SYNCHRONIZATION.md somente para registrar sync.

Politica de leitura por tipo:

- Consulta de status: 1 busca + 1 leitura local.
- Atualizacao de item existente: 1 busca + 1 leitura local + edicao.
- Criacao de item novo: 1 busca de numeracao BLID + 1 leitura da secao alvo.
- Sync de docs: ler apenas arquivos realmente impactados.

Evitar:

- reler arquivos ja suficientes para a decisao
- gerar tabelas longas sem pedido explicito
- repetir checklist completa no texto final
- pedir confirmacao quando o pedido de escrita for explicito e sem
  ambiguidade
- citar arquivos inexistentes como docs/TRACKER.md ou docs/ROADMAP.md

## Fluxo Operacional

1. Classificar o pedido: criar, atualizar, consultar ou sincronizar.
2. Ler somente os arquivos necessarios pela regra acima.
3. Agir diretamente se o pedido for explicito.
4. Perguntar apenas se houver ambiguidade material, risco de editar item
   errado ou ausencia de dado obrigatorio.
5. Ao escrever, preservar o formato ja adotado em docs/BACKLOG.md.
6. Registrar em docs/SYNCHRONIZATION.md quando houver alteracao em doc
   oficial.
7. Responder de forma curta com resultado, impacto e pendencias reais.

Atalho para consultas simples:

1. Identificar entidade alvo (BLID, sprint, iniciativa).
2. Ler so o bloco da entidade.
3. Responder em ate 5 linhas.

## Regras de Escrita

- docs/BACKLOG.md e a fonte de verdade para tarefas e status.
- Nao impor template novo se a secao existente usar formato diferente.
- Gerar novo BLID apenas para itens que usam a familia BLID.
- Ao criar BLID, usar o maior numero existente + 1.
- Manter texto em portugues.
- Se o usuario pedir commit, usar ASCII puro e no maximo 72 caracteres.
- Preservar a estrutura existente do backlog; evitar reformatar secoes antigas.

## Sincronizacao Minima

Sincronizar apenas quando houver impacto real:

- docs/PRD.md: mudou escopo, objetivo, prioridade macro ou iniciativa.
- docs/ARQUITETURA_ALVO.md: mudou camada, componente, contrato ou fluxo.
- docs/ADRS.md: houve nova decisao arquitetural ou revisao de decisao ativa.
- docs/DIAGRAMAS.md: mudou diagrama, fluxo ou relacao entre componentes.
- docs/MODELAGEM_DE_DADOS.md: mudou schema, tabela, campo, indice ou
  migracao.
- docs/REGRAS_DE_NEGOCIO.md: mudou regra oficial, criterio operacional ou
  comportamento validado.
- docs/SYNCHRONIZATION.md: houve alteracao em doc oficial ou backlog oficial.

Nao sincronizar por reflexo. Se um arquivo nao foi impactado, nao citar.

Regra de custo:

- Se a mudanca ficou restrita ao backlog e nao mudou escopo/arquitetura,
  sincronizar apenas docs/SYNCHRONIZATION.md.

## Guardrails

- Nunca desabilitar risk gate ou circuit breaker.
- Em caso de duvida operacional, bloquear a acao e explicar a lacuna.
- Decisoes e registros devem ser rastreaveis por BLID ou evidencia.
- Nao inventar arquivo auxiliar ausente no repositorio.
- Nao abrir analise extensa se o usuario pediu apenas uma alteracao direta.

## Evidencia para backlog derivado de RL/live

So criar ou repriorizar task com base em RL/live quando houver evidencia
concreta. Minimo esperado:

- metrica observada
- periodo ou janela analisada
- impacto operacional
- acao proposta

Exemplos validos:

- Sharpe caiu de 2.1 para 1.4 nas ultimas 500 epocas.
- Reward entrou em plateau por N episodios relevantes.
- Execucao live teve slippage recorrente acima do limite definido.

Evitar itens vagos como "melhorar modelo" sem metrica ou sintoma.

## Formato de Resposta

Para economizar tokens, use saida curta por tipo de tarefa.

### Consulta

- resumo direto
- no maximo 3 bloqueadores ou riscos
- proximos passos so se agregarem valor
- limite alvo: ate 5 linhas

### Criacao ou atualizacao

- item alterado
- campos mudados
- dependencias ou impactos reais
- docs sincronizados, se houve
- limite alvo: ate 8 linhas

### Sincronizacao

- arquivos alterados
- motivo objetivo
- pendencia residual, se existir
- limite alvo: ate 6 linhas

Nao gerar tabelas, grafos ASCII ou diff textual longo sem pedido explicito.

## Template Minimo de Task

Use apenas quando precisar criar entrada nova e o bloco alvo aceitar esse
formato.

```markdown
### BLID-XXX: Titulo curto e especifico

Status: Backlog | Planned | In Progress | Done
Sprint: S-N
Prioridade: P0 | Alta | Media | Baixa

Descricao:
Contexto e motivacao em 2-4 linhas.

Criterios de Aceite:
- [ ] Item 1
- [ ] Item 2

Dependencias:
- Nenhuma
```

## Exemplos de Acionamento

```text
/backlog-development Criar task para revisar reward shaping com base na
queda de Sharpe das ultimas 500 epocas

/backlog-development Mover BLID-072 para Done e registrar sync

/backlog-development Qual o status da BLID-073?

/backlog-development Validar se a prioridade da BLID-072 ainda faz sentido
frente ao PRD atual
```

## Resultado Esperado

Uma skill mais previsivel e barata em tokens:

- menos arquivos lidos por padrao
- leitura local por bloco ao inves de arquivo inteiro
- menos texto repetido
- menos perguntas desnecessarias
- mais aderencia ao backlog real do repositorio
