---
name: product-owner
description: |
  Varre docs/BACKLOG.md e classifica o proximo item/pacote por prioridade e valor.
  Entrega saida acionavel para refinamento do Arquiteto de Solucoes.
metadata:
  focus:
    - backlog
    - priorizacao
    - valor
    - planejamento
    - handoff-arquitetura
user-invocable: true
---

# Skill: Product Owner - Priorizacao do Proximo Pacote

## Objetivo

Selecionar o proximo item ou pacote de desenvolvimento em
`docs/BACKLOG.md` com criterio objetivo de prioridade e valor.

A skill devolve uma recomendacao acionavel para o Arquiteto de Solucoes
refinar e preparar execucao tecnica.

## Quando Usar

Use esta skill para:

- decidir o proximo item a entrar em execucao
- comparar opcoes concorrentes no backlog
- montar um pacote minimo de entrega com alto valor
- produzir handoff claro para refinamento tecnico

## Entradas Minimas

- objetivo atual de produto (1-2 linhas)
- horizonte de entrega: curto (1 sprint) ou medio (2-3 sprints)
- restricoes conhecidas: prazo, risco, dependencia, compliance

Se alguma entrada faltar, assumir modo conservador:

- priorizar risco operacional e desbloqueio de fluxo critico
- evitar itens de alto custo e valor incerto

## Modo Economico

Ler apenas o necessario para decidir com seguranca:

1. `docs/BACKLOG.md` (fonte principal, sempre obrigatorio)
2. `docs/PRD.md` apenas se houver duvida de alinhamento de escopo
3. `docs/REGRAS_DE_NEGOCIO.md` apenas se houver impacto em regra critica
4. `docs/ARQUITETURA_ALVO.md` apenas se houver impacto estrutural

Evitar leitura ampla sem ganho de decisao.

## Metodo de Classificacao

Aplicar score simples por item candidato:

`Score Final = (Valor * 0.45) + (Urgencia * 0.25) + (Reducao de Risco * 0.20) - (Esforco * 0.10)`

Escalas de 1 a 5:

- Valor: impacto em resultado de negocio ou confiabilidade operacional
- Urgencia: custo de adiar (prazo, janela de oportunidade, dependencia)
- Reducao de Risco: quanto evita falha, incidente ou bloqueio
- Esforco: complexidade tecnica e coordenacao necessaria

### Regra de Gate (Fail-safe)

Antes da recomendacao final:

- se item mexe em seguranca operacional, exigir risco explicitado
- se item depende de outro nao concluido, marcar como bloqueado
- se criterio de aceite estiver vago, reduzir urgencia em 1 ponto

### Regra de Desempate

Quando houver empate de score:

1. escolher item com maior reducao de risco
2. persistindo empate, escolher menor esforco
3. persistindo empate, escolher maior alinhamento com objetivo atual

## Montagem de Pacote

Apos ranquear, definir pacote recomendado:

- Pacote minimo: 1 item principal + ate 2 itens habilitadores
- Evitar pacote com dependencias cruzadas nao resolvidas
- Se houver bloqueio, retornar alternativa imediatamente executavel

## Saida Obrigatoria (Handoff para Arquiteto)

Responder sempre neste formato:

```markdown
DECISAO_PO: GO | GO_COM_RESTRICOES | NO_GO

ITEM_ESCOLHIDO:
- ID: <BLID ou identificador>
- Titulo: <titulo>
- Score_Final: <0.00 a 5.00>
- Classe: Quick Win | Estrategico | Reducao de Risco | Habilitador

JUSTIFICATIVA_CURTA:
- Valor: <1 linha>
- Urgencia: <1 linha>
- Risco: <1 linha>
- Esforco: <1 linha>

PACOTE_RECOMENDADO:
- Escopo minimo: <itens>
- Dependencias: <itens ou Nenhuma>
- Fora de escopo agora: <itens>

PRONTO_PARA_REFINAMENTO_ARQUITETURA:
- Problema a resolver: <1-2 linhas>
- Criterios de aceite iniciais: <3 bullets objetivas>
- Restricoes tecnicas: <risco, compliance, observabilidade>
- Duvidas em aberto: <itens>

PROXIMO_PASSO:
- Acao imediata do Arquiteto: <acao>
```

## Checklist de Qualidade

Antes de concluir, verificar:

- item recomendado existe de fato no `docs/BACKLOG.md`
- score esta coerente com justificativa textual
- dependencias e bloqueios foram explicitados
- criterios de aceite iniciais estao testaveis
- saida final permite acao sem reuniao adicional

## Exemplo de Prompt

```text
/product-owner Classifique o proximo pacote do backlog para 1 sprint,
priorizando valor de negocio sem abrir risco operacional.
```

## Guardrails

- nunca inventar item fora de `docs/BACKLOG.md`
- nunca recomendar execucao de item bloqueado sem alternativa
- em duvida sobre risco operacional, retornar NO_GO
- manter saida curta, objetiva e acionavel
