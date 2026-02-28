# Instruções para o GitHub Copilot

Orientações para mudanças no repositório `crypto-futures-agent`.

## Princípios Essenciais

- **Segurança operacional**: Nunca remover controles de risco existentes.
- **Previsibilidade**: Mudanças pequenas, focadas, compatíveis com estilo.
- **Rastreabilidade**: Todas as decisões críticas devem ser auditáveis.
- **Português**: Código, docs, logs em português (termos técnicos excetuados).

## Stack

- **Linguagem**: Python
- **Módulos críticos**: `agent/` (RL), `execution/` (ordens), `data/` (Binance),
  `risk/` (controles), `backtest/` (F-12), `tests/`
- **Modo compatibilidade**: `paper` e `live` preservados

---

## Como identificar a próxima tarefa

Ao receber qualquer pedido sobre próxima task, prioridade ou o que fazer a
seguir, siga esta ordem de leitura:

1. `docs/STATUS_ENTREGAS.md` — status atual de cada entrega do ROADMAP
2. `docs/PLANO_DE_SPRINTS_MVP_NOW.md` — sprint corrente e itens NOW
3. `docs/ROADMAP.md` — visão estratégica e milestones
4. Issues abertas e milestones no GitHub

---

## ⚡ BACKLOG INSTRUCTIONS REFERENCE

**IMPORTANTE:** Quando usuário pedir qualquer coisa sobre backlog/prioridades:
→ Leia: `.github/copilot-backlog-instructions.md` PRIMEIRO
→ Responda com tabela de status MUST items atual
→ Use arquivo maestro: `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`

**Trigger keywords que acionam backlog response:**

- "backlog", "prioridades", "sprint", "tarefas", "próximos itens",
  "o que é prioritário"

**Referência rápida:**

- **Detalhes técnicos:** `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`
- **Status real-time:** `backlog/TASKS_TRACKER_REALTIME.md`
- **Quick reference:** `backlog/BACKLOG_QUICK_START.md`

---

## Regras Críticas

### 1. Português Obrigatório

- Diálogos, comentários, logs, docs: **SEMPRE português**
- Exceção: APIs, bibliotecas, termos propriedade

### 2. Commits ASCII, Max 72 Chars

- Padrão: `[TAG] Descricao breve em portugues`
- Tags: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`
- Apenas ASCII (0-127), sem caracteres corrompidos

### 3. Markdown Lint: Max 80 Chars

- Usar `markdownlint *.md docs/*.md`
- Sem linhas > 80 caracteres, UTF-8 válido
- Títulos descritivos, blocos com linguagem (` ```python `)

## Regras de Domínio (Trading/Risk)

**Invioláveis:**

- Nunca desabilitar validações de risco (sizing, alavancagem, stop, liquidação).
- Alterações em reward/risk devem: manter segurança por padrão + fallback
  conservador + auditoria.
- Em dúvida: bloquear operação, não assumir risco.

## Sincronização Obrigatória

Toda mudança em código → sincronizar documentação. Checklist mínimo:

- [ ] Código funcional + testes passam (`pytest -q`)
- [ ] Docs dependentes atualizadas (ref: `docs/SYNCHRONIZATION.md`)
- [ ] Commit message com tag (`[SYNC]`, `[FEAT]`, etc.)

**Dependências principais:**

- `config/symbols.py` → `README.md`, `playbooks/__init__.py`,
  `docs/SYNCHRONIZATION.md`
- `docs/*` → sempre registrar em `docs/SYNCHRONIZATION.md`
- `README.md` versão → `docs/CHANGELOG.md`, `docs/ROADMAP.md`

## O Que Evitar

- Não criar features "nice-to-have" sem solicitação.
- Não alterar arquitetura para resolver problema local.
- Não deixar documentação desatualizada.

---

## Hierarquia de Documentação

O repositório possui **duas camadas** de documentação que convivem sem
conflito:

### Camada 1 — Core Docs Estratégicos (Decision #3, 22 FEV)

Documentos de governança, histórico e arquitetura. São a fonte de verdade
para decisões passadas, requisitos e lições aprendidas.

1. **[docs/RELEASES.md](../docs/RELEASES.md)** — Versões, deliverables, status
2. **[docs/ROADMAP.md](../docs/ROADMAP.md)** — Timeline, milestones, v0.3→v1.0
3. **[docs/FEATURES.md](../docs/FEATURES.md)** — Feature list, F-01→F-ML3
4. **[docs/TRACKER.md](../docs/TRACKER.md)** — Sprint tracker, backlog
5. **[docs/USER_STORIES.md](../docs/USER_STORIES.md)** — US-01→US-05, critérios
6. **[docs/LESSONS_LEARNED.md](../docs/LESSONS_LEARNED.md)** — Insights
7. **[docs/STATUS_ATUAL.md](../docs/STATUS_ATUAL.md)** — Dashboard go-live
8. **[docs/DECISIONS.md](../docs/DECISIONS.md)** — Histórico decisões board
9. **[docs/USER_MANUAL.md](../docs/USER_MANUAL.md)** — Onboarding, operação
10. **[docs/SYNCHRONIZATION.md](../docs/SYNCHRONIZATION.md)** — Audit trail

### Camada 2 — Docs de Execução/Visibilidade (MVP NOW)

Documentos operacionais para acompanhamento diário do MVP. São atualizados
com mais frequência e servem como visibilidade para o usuário único.

Futura consolidação planejada: STATUS_ENTREGAS → STATUS_ATUAL,
PLANO_DE_SPRINTS → TRACKER, CRITERIOS → USER_STORIES/USER_MANUAL,
RUNBOOK → USER_MANUAL, CHANGELOG → RELEASES.

| Documento | Propósito |
| --------- | --------- |
| [docs/STATUS_ENTREGAS.md](../docs/STATUS_ENTREGAS.md) | **Fonte da verdade** para status das entregas do ROADMAP |
| [docs/PLANO_DE_SPRINTS_MVP_NOW.md](../docs/PLANO_DE_SPRINTS_MVP_NOW.md) | Sprint corrente e itens NOW |
| [docs/CRITERIOS_DE_ACEITE_MVP.md](../docs/CRITERIOS_DE_ACEITE_MVP.md) | Critérios de aceite MVP |
| [docs/RUNBOOK_OPERACIONAL.md](../docs/RUNBOOK_OPERACIONAL.md) | Runbook operacional |
| [docs/CHANGELOG.md](../docs/CHANGELOG.md) | Registro de mudanças |

**Regra de convivência:** Ao atualizar qualquer doc da Camada 2, verifique se
há informação relevante que deve ser propagada para a Camada 1 (ex.: decisão
nova → DECISIONS.md, feature concluída → FEATURES.md).

### Camada 3 — Documentação Técnica (28 FEV 2026)

Documentação de referência técnica para arquitetura, decisões de design e
implementação. Estrutura C4 Model + ADR + OpenAPI.

1. **[docs/C4_MODEL.md](../docs/C4_MODEL.md)** — 4 níveis de arquitetura:
   Context (usuários) → Containers (tech stack) → Components (módulos) →
   Code (classes). Inclui diagramas ASCII e decision matrix.

2. **[docs/ADR_INDEX.md](../docs/ADR_INDEX.md)** — 7 Architecture Decision
   Records (ADR-001 a ADR-007) com Status, Champion, Contexto, Decisão,
   Consequências e Alternativas consideradas.

3. **[docs/OPENAPI_SPEC.md](../docs/OPENAPI_SPEC.md)** — Especificação
   OpenAPI 3.0.0 para REST API futura (12 endpoints, autenticação API key,
   rate limiting 1000 req/min).

4. **[docs/IMPACT_README.md](../docs/IMPACT_README.md)** — Guia prático de
   setup (venv, deps), testes (unit/integration/backtest), modos paper/live,
   monitoramento e deployment (Linux systemd + Docker futuro).

---

## Sincronização Manual via Copilot (Gatilho)

O processo de sincronização de docs é manual e acionado pelo usuário via
Copilot no VS Code. A política completa está em:

`prompts/board_16_members_data.json` → campo `docs_sync_policy`

**Prompt de gatilho** (campo `sync_trigger_prompt`):

> Sincronize os docs oficiais do projeto. Para cada arquivo em official_docs:
> (1) verifique se a seção Links Rápidos existe e está completa conforme a
> matriz cross_links; (2) atualize docs/STATUS_ENTREGAS.md com o status atual
> dos itens NOW do ROADMAP (Sprint, Issue, PR, Evidência, Status); (3) atualize
> o bloco Execução / Visibilidade em docs/ROADMAP.md com sprint atual, data de
> hoje e progresso NOW contando itens concluídos/total; (4) registre o sync em
> docs/SYNCHRONIZATION.md com tag [SYNC] e timestamp. Mantenha todo o
> conteúdo em Português.

**Não usar GitHub Actions como gatilho.** O gatilho é exclusivamente manual
via Copilot.

---

## Protocolo [SYNC] — Obrigatório

Todo commit que altera docs deve incluir:

- Tag `[SYNC]` na mensagem
- Referência aos docs impactados (Camada 1 e/ou Camada 2)
- Atualização em `docs/SYNCHRONIZATION.md`

Exemplo:

```text
[SYNC] Atualizado STATUS_ENTREGAS.md sprint 2 + ROADMAP.md progresso NOW
```

---

## Detalhes: Referência em BEST_PRACTICES.md

Para mais contexto:

- **Padrões**: Log, estilo código, testes → `BEST_PRACTICES.md`
- **Sincronização**: Matriz de dependências, histórico → `docs/SYNCHRONIZATION.md`
- **Decisões**: Phase 3 gates, opções PPO → `docs/DECISIONS.md`
