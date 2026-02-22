# Instruções para o GitHub Copilot

Orientações para mudanças no repositório `crypto-futures-agent`.

## Princípios Essenciais

- **Segurança operacional**: Nunca remover controles de risco existentes.
- **Previsibilidade**: Mudanças pequenas, focadas, compatíveis com estilo.
- **Rastreabilidade**: Todas as decisões críticas devem ser auditáveis.
- **Português**: Código, docs, logs em português (termos técnicos propriedade excetuados).

## Stack

- **Linguagem**: Python
- **Módulos críticos**: `agent/` (RL), `execution/` (ordens), `data/` (Binance),
  `risk/` (controles), `backtest/` (F-12), `tests/`
- **Modo compatibilidade**: `paper` e `live` preservados

## Status: F-12 PHASE 3 → PHASE 4 (21/02/2026)

**Backtest Engine**: ✅ 100% funcional (9/9 testes passando)
**Decision #2**: ✅ APROVADA — Opção C (Híbrido, 3-4 dias)
**Operacionalização**: 🔄 INICIADA 21 FEV (Heurísticas + PPO training paralelo)

**Sprint atual**: Sprint 1 MUST items (21-25 FEV)
**Próximo checkpoint**: Gate #1 QA (22 FEV 08:00 UTC)

---

## 📊 CONSOLIDAÇÃO DOCUMENTÁRIA — Decision #3 Status

**IMPORTANTE:** Consolidação documentária está em execução (Decision #3 aprovada 22 FEV).

**Plano Completo:** [PLANO_MAESTRO_CONSOLIDACAO_DOCUMENTARIA.md](../PLANO_MAESTRO_CONSOLIDACAO_DOCUMENTARIA.md)

**Análises por Pasta:**
- [docs/DOC_ADVOCATE_CLASSIFICATION_ANALYSIS.md](../docs/DOC_ADVOCATE_CLASSIFICATION_ANALYSIS.md) (58 arquivos)
- [backlog/DOC_ADVOCATE_CONSOLIDACAO_BACKLOG.md](../backlog/DOC_ADVOCATE_CONSOLIDACAO_BACKLOG.md) (15 arquivos)
- [checkpoints/ppo_training/DOC_ADVOCATE_CONSOLIDACAO_PPO_TRAINING.md](../checkpoints/ppo_training/DOC_ADVOCATE_CONSOLIDACAO_PPO_TRAINING.md) (1 arquivo)
- [prompts/DOC_ADVOCATE_CONSOLIDACAO_PROMPTS.md](../prompts/DOC_ADVOCATE_CONSOLIDACAO_PROMPTS.md) (19 arquivos)
- [reports/DOC_ADVOCATE_CONSOLIDACAO_REPORTS.md](../reports/DOC_ADVOCATE_CONSOLIDACAO_REPORTS.md) (15 arquivos)
- [scripts/DOC_ADVOCATE_CONSOLIDACAO_SCRIPTS.md](../scripts/DOC_ADVOCATE_CONSOLIDACAO_SCRIPTS.md) (1 arquivo)
- [DOC_ADVOCATE_CONSOLIDACAO_RAIZ.md](../DOC_ADVOCATE_CONSOLIDACAO_RAIZ.md) (60+ arquivos, human review pending)

**Próxima Ação:** Kickoff Fase 2A (prompts/) após aprovação Elo

---

## ⚡ BACKLOG INSTRUCTIONS REFERENCE

**IMPORTANTE:** Quando usuário pedir qualquer coisa sobre backlog/prioridades:
→ Leia: `.github/copilot-backlog-instructions.md` PRIMEIRO
→ Responda com tabela de status MUST items atual
→ Use arquivo maestro: `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`

**Trigger keywords que acionam backlog response:**
- "backlog", "prioridades", "sprint", "tarefas", "próximos itens", "o que é prioritário"

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

- Padrão: `[TAG] Descrição breve em português`
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
- Em dúvida: bloquear operação, não asumir risco.

## Sincronização Obrigatória

Toda mudança em código → sincronizar documentação. Checklist mínimo:

- [ ] Código funcional + testes passam (`pytest -q`)
- [ ] Docs dependentes atualizadas (ref: `docs/SYNCHRONIZATION.md`)
- [ ] Commit message com tag (`[SYNC]`, `[FEAT]`, etc.)

**Dependências principais:**
- `config/symbols.py` → `README.md`, `playbooks/__init__.py`, `docs/SYNCHRONIZATION.md`
- `docs/*` → sempre registrar em `docs/SYNCHRONIZATION.md`
- `README.md` versão → `CHANGELOG.md`, `docs/ROADMAP.md`

## O Que Evitar

- Não criar features "nice-to-have" sem solicitação.
- Não alterar arquitetura para resolver problema local.
- Não deixar documentação desatualizada.

## 📚 Fonte da Verdade Documentária — 10 Core Docs (Decision #3)

**CRÍTICO:** Não criar ou atualizar docs fora desta lista. Consolidar conteúdo
nestasliterais em docs oficiais.

### Core Docs (Manter & Sincronizar)

1. **[docs/RELEASES.md](docs/RELEASES.md)** — Versões, deliverables, status
2. **[docs/ROADMAP.md](docs/ROADMAP.md)** — Timeline, milestones, v0.3→v1.0
3. **[docs/FEATURES.md](docs/FEATURES.md)** — Feature list, F-01→F-ML3, prioridades
4. **[docs/TRACKER.md](docs/TRACKER.md)** — Sprint tracker, backlog, velocidade
5. **[docs/USER_STORIES.md](docs/USER_STORIES.md)** — US-01→US-05, critérios
6. **[docs/LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md)** — Insights, decisões
7. **[docs/STATUS_ATUAL.md](docs/STATUS_ATUAL.md)** — Dashboard, status real-time
8. **[docs/DECISIONS.md](docs/DECISIONS.md)** — Histórico decisões board
9. **[docs/USER_MANUAL.md](docs/USER_MANUAL.md)** — Onboarding, operação
10. **[docs/SYNCHRONIZATION.md](docs/SYNCHRONIZATION.md)** — Audit trail, metadados

**Análise de Governança**: [docs/DOC_ADVOCATE_CLASSIFICATION_ANALYSIS.md](docs/DOC_ADVOCATE_CLASSIFICATION_ANALYSIS.md)

### Protocolo [SYNC] — Obrigatório

Todo commit que altera docs deve incluir:
- Tag `[SYNC]` na mensagem
- Referência aos 10 core docs impactados
- Atualização em `docs/SYNCHRONIZATION.md`

Exemplo:
```
[SYNC] Atualizado FEATURES.md F-H1-H5 + ROADMAP.md timeline v1.0-alpha
```

## Detalhes: Referência em BEST_PRACTICES.md

Para mais contexto:
- **Padrões**: Log, estilo código, testes → `BEST_PRACTICES.md`
- **Sincronização**: Matriz de dependências, histórico → `docs/SYNCHRONIZATION.md`
- **Decisões**: Phase 3 gates, opções PPO → `docs/DECISIONS.md`
