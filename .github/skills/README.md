# Skills Workflow

Workflow das skills do workspace, com foco em invocacao segura.

Este indice usa dois campos diferentes:

- Indice do workflow: identificador unico para leitura humana.
- Nome da skill: valor exato do campo `name` no frontmatter.

## Fluxo Principal (Agentes)

1. WF-01 | `backlog-development` (pasta `1.backlog-development`) — criar,
  atualizar ou sincronizar backlog.
2. WF-02 | `2.product-owner` — escolher o proximo item ou pacote.
3. WF-03 | `3.solution-architect` — refinar demanda do PO para o QA-TDD.
4. WF-04 | `4.qa-tdd` — escrever suite RED e entregar handoff de
  implementacao.
5. WF-05 | `5.software-engineer` — implementar GREEN/REFACTOR com evidencias.
6. WF-06 | `6.tech-lead` — revisar entrega e decidir APROVADO ou DEVOLVIDO.
7. WF-07 | `9.commit` — validar qualidade, commitar e fazer push.
8. WF-08 | `10.close` — encerrar a sessao com custo minimo.

## Skills de Apoio (Uso Sob Demanda)

1. AUX-01 | `11.data-analysis` — validar dados, banco, exchange e conciliacao.
2. AUX-02 | `12.performance-review` — revisar reward, Sharpe e degradacao.
3. AUX-03 | `13.symbol-onboarding` — adicionar ou auditar simbolo no
  pipeline M2.
4. AUX-04 | `7.m2-incident-response` — conter e reconciliar incidente
  fail-safe.
5. AUX-05 | `8.live-release-readiness` — decidir GO, GO_COM_RESTRICOES
  ou NO_GO.

## Encadeamento Recomendado

WF-01 -> WF-02 -> WF-03 -> WF-04 -> WF-05 -> WF-06 -> WF-07 -> WF-08

Mapeamento rapido:

- WF-01: `backlog-development`
- WF-02: `2.product-owner`
- WF-03: `3.solution-architect`
- WF-04: `4.qa-tdd`
- WF-05: `5.software-engineer`
- WF-06: `6.tech-lead`
- WF-07: `9.commit`
- WF-08: `10.close`

## Regras

- Todas as skills ativas vivem em `.github/skills`.
- O nome oficial para invocacao e sempre o campo `name` do frontmatter.
- Prefixos numericos podem repetir entre trilhas de apoio e fluxo principal.
- Em caso de duvida, priorizar o nome `WF-XX` neste indice e o `name` da skill.
- Skills legadas em `.claude/skills` foram descontinuadas.

## Criterio de Economia

- Ler primeiro a evidencia mais direta.
- Ler o menor bloco util, nao o arquivo inteiro por padrao.
- Evitar exemplos longos, SQL extenso e checklists duplicadas dentro do
  `SKILL.md`.
- Deixar detalhes auxiliares em arquivos de apoio apenas quando agregarem valor.
