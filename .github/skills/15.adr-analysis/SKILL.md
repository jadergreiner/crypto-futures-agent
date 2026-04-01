---
name: 15.adr-analysis
description: 'Valida se toda mudanca de codigo e testes esta alinhada a uma ou mais ADRs em docs/ADRS.md. Use quando iniciar implementacao, revisar PR, criar testes, ou aprovar entrega tecnica. Fluxo binario: sem ADR aplicavel, bloqueia desenvolvimento e encaminha criacao de ADR ao Arquiteto de Software; em conflito com ADR vigente, bloqueia merge ate revisao arquitetural.'
argument-hint: 'Escopo da mudanca a validar contra ADRs (arquivo, modulo, tarefa ou PR)'
user-invocable: true
---

# Skill: ADR Analysis Gate

## Objetivo

Garantir padronizacao arquitetural obrigatoria para mudancas de codigo e
 testes em contexto critico (mercado financeiro).

Regra central (binaria):

- Com uma ou mais ADRs aplicaveis e aderencia comprovada: pode seguir.
- Sem ADR aplicavel ou com conflito arquitetural: nao segue adiante.

## Fonte de Verdade

- ADRs oficiais do projeto: `docs/ADRS.md`

## Quando usar

Use esta skill antes de:

- iniciar desenvolvimento de feature, bugfix ou refactor;
- escrever ou alterar testes unitarios/integracao/e2e;
- aprovar PR ou handoff tecnico;
- fechar item de backlog com status de implementado.

## Entradas esperadas

- descricao da mudanca (objetivo, escopo e risco);
- arquivos/modulos impactados;
- requisito de negocio associado (quando houver);
- referencia do item de backlog (quando existir).

## Procedimento

1. Ler `docs/ADRS.md` e identificar ADRs candidatas por tema, escopo e
   constraints.
2. Mapear a mudanca para uma ADR especifica (ou combinacao coerente de ADRs)
   com
   justificativa objetiva.
3. Verificar aderencia tecnica da mudanca aos principios e decisoes da ADR:
   - arquitetura e fronteiras de modulo;
   - contratos e invariantes;
   - estrategia de testes e evidencias.
4. Classificar resultado do gate:
   - `APROVADO_POR_ADR`: existe ADR aplicavel e mudanca aderente;
   - `BLOQUEADO_SEM_ADR`: nao existe ADR aplicavel;
   - `BLOQUEADO_CONFLITO_ADR`: existe ADR, mas a mudanca conflita.
5. Se `BLOQUEADO_SEM_ADR`, interromper fluxo de implementacao e emitir
   proposta formal para o Arquiteto de Software criar nova ADR.
6. Se `BLOQUEADO_CONFLITO_ADR`, marcar bloqueio explicito de merge e emitir
   proposta formal para revisao da ADR vigente com o Arquiteto de Software.
7. Registrar saida com rastreabilidade minima (ADRs, evidencias, decisao e
   proximo passo).

## Regras de Decisao (fail-safe)

- Em duvida sobre aderencia, tratar como bloqueado.
- Nao inferir ADR implicita quando nao houver evidencia textual em
  `docs/ADRS.md`.
- Nao permitir excecao operacional para "seguir e ajustar depois".

## Criterios de Qualidade

Uma analise so e valida quando incluir:

- identificacao explicita da ADR (id/titulo) ou ausencia confirmada;
- mapeamento `mudanca -> decisao arquitetural`;
- lista de conflitos (se houver) com impacto tecnico;
- decisao binaria final do gate;
- proximo passo acionavel.

## Saida padrao

Use sempre o formato abaixo:

- `status_gate`: `APROVADO_POR_ADR` | `BLOQUEADO_SEM_ADR` |
  `BLOQUEADO_CONFLITO_ADR`
- `adr_referencia`: `<id/titulo da ADR>` ou `NENHUMA_ADR_APLICAVEL`
- `adrs_combinadas`: lista de ADRs quando a aprovacao depender de mais de
   uma ADR
- `evidencias`: lista curta de pontos objetivos
- `decisao`: `PODE_SEGUIR` ou `NAO_PODE_SEGUIR`
- `acao_obrigatoria`:
  - quando aprovado: "Prosseguir com desenvolvimento aderente a ADR X"
   - quando bloqueado sem ADR: "Solicitar ao Arquiteto de Software criacao de
      ADR antes de iniciar desenvolvimento"
   - quando bloqueado por conflito: "Bloquear merge e solicitar ao Arquiteto
      revisao da ADR vigente antes de prosseguir"

## Prompt de bloqueio para Arquiteto (template)

Quando `status_gate` for bloqueado, emitir:

"Nao foi encontrada ADR aplicavel (ou foi detectado conflito com ADR vigente)
para a mudanca <escopo>. Conforme gate arquitetural binario do projeto,
o desenvolvimento permanece bloqueado e, em caso de conflito, o merge tambem
permanece bloqueado. Solicita-se ao Arquiteto de Software a criacao (ou
revisao) de ADR em `docs/ADRS.md` antes de qualquer continuidade."
