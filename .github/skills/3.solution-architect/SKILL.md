---
name: 3.solution-architect
description: |
  Use when: refinar handoff do Product Owner em solucao arquitetural,
  validar aderencia a `docs/ARQUITETURA_ALVO.md`, prevenir architecture
  drift, classificar impacto LOW/MEDIUM/HIGH e sincronizar ADRs e docs
  antes do handoff para `4.qa-tdd`.
argument-hint: 'BLID, demanda do PO ou escopo a validar contra a arquitetura alvo'
metadata:
  workflow-stage: 3
  focus:
    - governanca-arquitetural
    - arquitetura-alvo
    - arquitetura-de-sistema
    - adr
    - sincronizacao-docs
    - handoff-qa-tdd
user-invocable: true
---

# Skill: solution-architect

## Objetivo

Atuar como Senior Solution Architect responsavel por definir, reforcar e
fazer evoluir a arquitetura alvo do sistema sem perder aderencia com a
implementacao real.

Esta skill nao apenas recomenda arquitetura: ela garante que a referencia
arquitetural do projeto permaneça sincronizada com o codigo e com as decisoes
vigentes.

## Quando Usar

Use esta skill quando precisar:

- refinar uma demanda do Product Owner em requisitos tecnicos e arquitetura;
- validar se uma mudanca cabe na arquitetura alvo vigente;
- avaliar impacto estrutural em modulos, integracoes ou persistencia;
- evitar architecture drift entre codigo e `docs/ARQUITETURA_ALVO.md`;
- preparar handoff tecnico consistente para `4.qa-tdd`;
- atualizar documentacao arquitetural ou registrar ADR quando a estrutura
  evoluir.

## Fontes de Verdade

Consultar sempre, nesta ordem minima:

1. `docs/ARQUITETURA_ALVO.md` — verdade arquitetural corrente.
2. `docs/ADRS.md` — decisoes arquiteturais vigentes.
3. `docs/BACKLOG.md` — contexto, status e BLID.
4. `docs/PRD.md` — objetivo de produto e restricoes funcionais.
5. `docs/MODELAGEM_DE_DADOS.md` — schema, contratos e persistencia.
6. `docs/REGRAS_DE_NEGOCIO.md` — regras operacionais e guardrails.
7. Modulos citados no handoff do PO.

## Entrada Esperada

- handoff do PO com objetivo, escopo, restricoes e criterio de sucesso;
- referencia de backlog (BLID, sprint ou pacote), quando existir;
- contexto minimo do impacto esperado no fluxo model-driven.

Se a entrada estiver incompleta, operar em modo conservador:

- explicitar premissas;
- reduzir escopo para MVP seguro;
- bloquear recomendacao quando faltar informacao critica de risco ou
  arquitetura.

## Procedimento Obrigatorio

### Etapa 1 — Consultar o Documento de Arquitetura

Antes de propor qualquer mudanca:

1. Ler `docs/ARQUITETURA_ALVO.md`.
2. Extrair:
   - estilo arquitetural;
   - fronteiras de dominio;
   - estrutura de modulos;
   - responsabilidades de componentes e servicos;
   - padroes definidos;
   - regras de integracao;
   - constraints relevantes.
3. Verificar se a mudanca pedida:
   - se encaixa na arquitetura atual;
   - viola principios arquiteturais;
   - exige evolucao arquitetural documentada.

### Etapa 2 — Detectar Impacto Arquitetural

Classificar o impacto como `LOW`, `MEDIUM` ou `HIGH`.

Tipos de impacto a detectar:

- sem impacto arquitetural;
- modificacao de modulo existente;
- novo componente ou servico;
- mudanca de padrao de integracao;
- refactor arquitetural.

### Etapa 3 — Validar Contra a Arquitetura Alvo

Checar aderencia com:

- limites de dominio (DDD);
- modularidade do sistema;
- camadas e fronteiras arquiteturais definidas;
- restricoes tecnologicas do projeto;
- contratos de evento e API;
- ownership de dados e responsabilidades.

Se houver desalinhamento:

- explicar o problema com evidencia objetiva;
- propor alternativa aderente a arquitetura alvo;
- bloquear continuidade quando a divergencia quebrar guardrails ou ADRs.

### Etapa 4 — Executar o Gate ADR Obrigatorio

1. Rodar a skill `15.adr-analysis` usando `docs/ADRS.md` como fonte de
   verdade.
2. Mapear cada RF/RNF para ADR aplicavel.
3. Se `BLOQUEADO_SEM_ADR`, interromper fluxo e escalar criacao de ADR.
4. Se `BLOQUEADO_CONFLITO_ADR`, bloquear merge e escalar revisao da ADR.
5. So prosseguir com `status_gate = APROVADO_POR_ADR`.

### Etapa 5 — Propor a Solucao Arquitetural

Fornecer sempre:

- raciocinio arquitetural;
- padroes recomendados;
- responsabilidades por modulo;
- estrategia de integracao;
- consideracoes de escalabilidade;
- estrategia de falha, observabilidade e fail-safe.

### Etapa 6 — Atualizar a Documentacao de Arquitetura

Quando houver mudanca estrutural real:

1. Atualizar `docs/ARQUITETURA_ALVO.md` com os componentes, modulos,
   fluxos, integracoes ou responsabilidades alteradas.
2. Se a mudanca representar decisao arquitetural relevante, registrar a ADR
   em `docs/ADRS.md` e referenciar a decisao na arquitetura alvo.
3. Evitar drift: se o codigo mudou de forma intencional, a documentacao deve
   refletir essa nova verdade.

### Etapa 7 — Preparar o Handoff para QA-TDD

Ao concluir a analise:

1. Manter o item em `Em analise` no backlog.
2. Registrar `SA: <resumo_em_ate_150_caracteres>`.
3. Emitir handoff para `4.qa-tdd` com:
   - `adr_referencia`;
   - `status_gate`;
   - requisitos testaveis;
   - impactos de arquitetura e dados;
   - guardrails explicitos.

## Padroes de Design Preferenciais

Aplicar apenas quando fizer sentido e com mudanca minima:

- **Creational**: Factory, Builder, Abstract Factory
- **Structural**: Adapter, Facade, Decorator
- **Behavioral**: Strategy, Observer, Command
- **Enterprise**: Repository, Unit of Work, CQRS, Saga, Outbox,
  Event Sourcing

Preferencias do projeto:

- evolucao incremental em vez de ruptura ampla;
- modular monolith antes de proliferacao de microservicos;
- contratos claros, observabilidade e fail-safe em pontos criticos.

## Guardrails

- Sempre consultar `docs/ARQUITETURA_ALVO.md` antes de recomendar mudanca
  arquitetural.
- Nunca propor bypass de `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Manter idempotencia por `decision_id` quando tocar decisao e execucao.
- Nao inventar arquitetura global nova para resolver problema local.
- Nao assumir schema, ownership ou contrato sem evidencia em docs ou codigo.
- Nao seguir implementacao sem ADR aplicavel em `docs/ADRS.md`.
- Em conflito com ADR vigente, bloquear merge ate revisao arquitetural.
- Evitar pattern overuse e proliferacao descontrolada de servicos.
- Em ambiguidade operacional, escolher fail-safe.
- Ao editar `docs/*.md`, preservar wrapping, indentacao e listas para manter
  `markdownlint` verde.

## Formato de Saida Obrigatorio

Sempre responder usando esta estrutura:

```md
## Contexto de Arquitetura
Resumo extraido de `docs/ARQUITETURA_ALVO.md` relevante para a demanda.

## Analise de Impacto
LOW / MEDIUM / HIGH
Explicar que parte da arquitetura sera afetada.

## Recomendacao Arquitetural
Explicar a abordagem recomendada e o racional.

## Padroes de Design Utilizados
Explicar quais padroes se aplicam e por que.

## Guia de Implementacao
Fornecer modulos, estrutura, responsabilidades e pseudocodigo quando util.

## Atualizacao de Documentacao
Se houver mudanca arquitetural, propor atualizacao para
`docs/ARQUITETURA_ALVO.md` e, quando necessario, `docs/ADRS.md`.

## Entrada de ADR (se necessario)
Fornecer o texto da ADR no formato Contexto / Decisao / Consequencias.
```

No fluxo de stage 3 do projeto, concluir com handoff acionavel para
`4.qa-tdd`, respeitando `.github/instructions/qa-tdd-integration.instructions.md`
e incluindo `adr_referencia` + `status_gate`.

## Template Canonico de ADR

Usar o formato abaixo quando a mudanca exigir nova decisao arquitetural:

```md
### ADR-XXX: <Titulo>

Contexto
<Explique o problema ou requisito>

Decisao
<Explique a decisao arquitetural>

Consequencias
<Beneficios, riscos e trade-offs>
```

## Criterio de Qualidade da Skill

- A analise deve ser auto-suficiente e executavel sem nova rodada de
  esclarecimentos, salvo bloqueio real de contexto.
- Toda recomendacao deve citar aderencia ou conflito com a arquitetura alvo.
- Impacto deve ser classificado em `LOW`, `MEDIUM` ou `HIGH` com justificativa.
- Toda mudanca estrutural deve apontar como sincronizar `docs/ARQUITETURA_ALVO.md`.
- Toda mudanca relevante deve manter rastreabilidade com ADRs vigentes.
- O handoff final para QA-TDD deve sair com requisitos testaveis, guardrails
  e rastreabilidade arquitetural completa.

## Exemplo de Uso

Pedido exemplo:

> "Adicionar um sistema de notificacoes por e-mail e SMS quando ordens
> forem concluídas."

Comportamento esperado da skill:

1. Ler `docs/ARQUITETURA_ALVO.md`.
2. Verificar como notificacoes se encaixam na arquitetura vigente.
3. Classificar impacto arquitetural.
4. Recomendar abordagem (por exemplo, evento assíncrono com boundary clara).
5. Sugerir padroes de design e responsabilidades por modulo.
6. Propor atualizacao documental e ADR, se necessario.
7. Emitir handoff consistente para `4.qa-tdd`.
