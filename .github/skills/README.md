# Skills Workflow

Workflow unico das skills do workspace, em ordem de uso mais provavel.

## Ordem

1. `1.backlog-development` — criar, atualizar ou sincronizar backlog.
2. `2.product-owner` — escolher o proximo item ou pacote.
3. `3.solution-architect` — refinar demanda do PO em prompt para QA-TDD.
4. `4.data-analysis` — validar dados, banco, exchange e conciliacao.
5. `5.performance-review` — revisar reward, Sharpe e degradacao.
6. `6.symbol-onboarding` — adicionar ou auditar simbolo no pipeline M2.
7. `7.m2-incident-response` — conter e reconciliar incidente fail-safe.
8. `8.live-release-readiness` — decidir GO, GO_COM_RESTRICOES ou NO_GO.
9. `9.commit` — validar qualidade, commitar e fazer push.
10. `10.close` — encerrar a sessao com custo minimo.

## Regras

- Todas as skills ativas vivem em `.github/skills`.
- Os nomes numerados servem apenas para ordenar o workflow.
- O `name` no frontmatter continua sendo o identificador de invocacao.
- Skills legadas em `.claude/skills` foram descontinuadas.

## Criterio de Economia

- Ler primeiro a evidencia mais direta.
- Ler o menor bloco util, nao o arquivo inteiro por padrao.
- Evitar exemplos longos, SQL extenso e checklists duplicadas dentro do
  `SKILL.md`.
- Deixar detalhes auxiliares em arquivos de apoio apenas quando agregarem valor.
