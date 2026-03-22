---
name: backlog-development
description: |
  Use para criar, atualizar e consultar itens em docs/BACKLOG.md com
  leitura minima, sincronizacao objetiva e foco em economia de tokens.
  Consulte docs/PRD.md e docs arquiteturais apenas quando houver impacto
  real em escopo, arquitetura, dados ou regras de negocio.
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

Use esta skill para:

- criar task nova em docs/BACKLOG.md
- atualizar status, sprint, prioridade ou dependencias
- consultar status do backlog ou de uma BLID
- sincronizar docs oficiais quando houver impacto real
- transformar evidencia de RL/live em item de backlog auditavel

## Modo Economico

Regra principal: ler apenas o necessario para cumprir o pedido.

Ordem de leitura:

1. Sempre ler docs/BACKLOG.md.
2. Ler docs/PRD.md apenas se o pedido mexer em escopo, prioridade,
   roadmap de produto ou iniciativa.
3. Ler docs/ARQUITETURA_ALVO.md, docs/ADRS.md, docs/DIAGRAMAS.md,
   docs/MODELAGEM_DE_DADOS.md e docs/REGRAS_DE_NEGOCIO.md apenas se a
   mudanca alterar arquitetura, schema, fluxo ou regra oficial.
4. Ler docs/SYNCHRONIZATION.md apenas quando for registrar sync ou checar
   trilha de auditoria.

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

## Regras de Escrita

- docs/BACKLOG.md e a fonte de verdade para tarefas e status.
- Nao impor template novo se a secao existente usar formato diferente.
- Gerar novo BLID apenas para itens que usam a familia BLID.
- Ao criar BLID, usar o maior numero existente + 1.
- Manter texto em portugues.
- Se o usuario pedir commit, usar ASCII puro e no maximo 72 caracteres.

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

### Criacao ou atualizacao

- item alterado
- campos mudados
- dependencias ou impactos reais
- docs sincronizados, se houve

### Sincronizacao

- arquivos alterados
- motivo objetivo
- pendencia residual, se existir

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
- menos texto repetido
- menos perguntas desnecessarias
- mais aderencia ao backlog real do repositorio
