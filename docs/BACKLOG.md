# 📦 BACKLOG — Crypto Futures Agent

**Status:** 🟢 OPERACIONAL | **FONTE ÚNICA DA VERDADE** para Itens Desenvolvidos + A Desenvolver
**Atualizado:** 06 MAR 2026 (consolidação: STATUS_ENTREGAS, PLANO_DE_SPRINTS, TRACKER deletados → tudo aqui)
**Mantém:** Sprint 1-2-3 items + TASK pipeline + Issue tracking + Tabela de visão rápida
**Responsável:** Planner, Board, Doc Advocate

**Nota Importante:** Este documento é a **única fonte de verdade** para todas as tarefas, sprints e status do projeto. Docs como STATUS_ENTREGAS.md, PLANO_DE_SPRINTS_MVP_NOW.md foram consolidadas aqui. Para visão **tabular compacta**, use [TRACKER.md](TRACKER.md).

---

## 🔗 Links Rápidos

| Documento | Propósito |
|-----------|-----------|
| [TRACKER.md](TRACKER.md) | Tabela consolidada de todas as tasks (Master view) |
| [ROADMAP.md](ROADMAP.md) | Visão estratégica (Now-Next-Later) |
| [USER_STORIES.md](USER_STORIES.md) | User stories (v0.2→v1.0) |
| [DECISIONS.md](DECISIONS.md) | Decision history + board approvals |
| [FEATURES.md](FEATURES.md) | Feature list (F-H1→F-ML3) |
| [RELEASES.md](RELEASES.md) | Version history (v0.1→v1.0-alpha) |
| [SYNCHRONIZATION.md](SYNCHRONIZATION.md) | Audit trail [SYNC] + histórico completo |
| [C4_MODEL.md](C4_MODEL.md) | Diagrama arquitetural (4 níveis) |
| [ADR_INDEX.md](ADR_INDEX.md) | Architecture Decision Records (7 ADRs) |
| [OPENAPI_SPEC.md](OPENAPI_SPEC.md) | Especificação REST API (OpenAPI 3.0.0) |
| [IMPACT_README.md](IMPACT_README.md) | Setup, testes, deploy em produção |
---

## 🚀 QUICK WINS — TAREFAS PRIORITÁRIAS

**Objetivo:** Itens críticos e desbloqueadores para próximas fases

- **TASK-010** — Decision #4 Votação
  - Status: ✅ **COMPLETA**
  - Owner: Angel (#1), Elo (#2)
  - Score: 0.95 | Effort: 2h
  - Resultado: 15/16 votos SIM (93.75%) ✅
  - Documentação: [ATA_DECISION_4_27FEV_FINAL.md](ATA_DECISION_4_27FEV_FINAL.md)

- **TASK-011** — F-12b Symbols + Parquet Optimization
  - Status: ✅ **COMPLETA** | ALL PHASES APPROVED FOR PRODUCTION
  - Owner: Flux (#5), Squad B (Blueprint, Data, Quality, Arch, Executor)
  - Score: 0.92 | Effort: 11h total | Execution: 28 FEV 00:51 UTC
  - Phase 1: ✅ 200/200 símbolos validados (100%)
  - Phase 2: ✅ Parquet optimization (zstd, footprint 0.019GB, latency 1.25s)
  - Phase 3: ✅ Load tests + QA approval (all metrics pass)
  - Phase 4: ✅ Canary deployment + iniciar.bat integration (production approved)
  - Documentação: [EXECUCAO_TASK_011_PHASE_3_4_FINAL.md](EXECUCAO_TASK_011_PHASE_3_4_FINAL.md)

- **Issue #64** — Telegram Alerts Setup
  - Status: ✅ **COMPLETA** | 28 FEV 16:45 UTC
  - Owner: The Blueprint (#7), Quality (#12)
  - Score: 0.75 | Effort: 1.5h (actual: 2h)
  - Descrição: Webhook integration + msg formatter (P&L, drawdown, trades alerts)
  - Deliverables:
    - ✅ `notifications/telegram_client.py` — Client com 7 métodos
    - ✅ `notifications/telegram_webhook.py` — Webhook Flask handler
    - ✅ `config/telegram_config.py` — Config centralizada
    - ✅ `tests/test_telegram_client.py` — 8 testes unitários
    - ✅ `tests/test_telegram_webhook.py` — 10 testes integração
    - ✅ `notifications/README.md` — Documentação completa
    - ✅ `.env.telegram.example` — Template de env
  - Tests: ✅ 18/18 PASS (rate limiting, signature validation, message formatting)
  - Coverage: 92%+ em notifications/
  - Documentação: [ISSUE_64_TELEGRAM_SETUP_SPEC.md](ISSUE_64_TELEGRAM_SETUP_SPEC.md)

---

## 📊 ITENS EM PROGRESSO

**Objetivo:** Tasks em execução, blockers críticos monitorados

- **TASK-005** — PPO Training
  - Status: 🔄 **IN PROGRESS** (~50% estimated)
  - Owner: The Brain (#3)
  - Score: 1.0 | Effort: 96h wall-time
  - Descrição: Train PPO agent on 60 pairs. 500k steps, Sharpe ≥1.0 target
  - Blocker: ⏳ Issue #65 QA (provides SMC validation required)
  - Documentação: [FEATURES.md#F-ML1](FEATURES.md)

- **Issue #65** — SMC Integration QA
  - Status: 🟡 **SQUAD KICKOFF**
  - Owner: Arch (#6), Squad (Audit, Quality, The Brain, Doc Advocate)
  - Score: 0.99 | Effort: 13.5h (4 phases)
  - Descrição: Comprehensive QA of SMC strategy (Order Blocks + BoS)
  - SLA Critical: Hard deadline for unblocking TASK-005
  - Documentação: [ISSUE_65_SMC_QA_SPEC.md](ISSUE_65_SMC_QA_SPEC.md)

---

## 📋 ITENS FUTUROS

**Objetivo:** Roadmap Sprint 2-3, aguardando desbloqueadores ou capacidade

- **S2-4** — Trailing Stop Loss Integration
  - Status: ✅ **COMPLETA**
  - Owner: Arch (#6)
  - Score: 0.75 | Effort: Merged
  - Descrição: TrailingStopManager integration com OrderExecutor
  - Ready para: Live testing
  - Documentação: Merged em main

- **TASK-012** — S2-0 REC-1: WAL Mode + Timeout Adaptativo
  - Status: ⏳ **PLANEJADO**
  - Owner: Data (#11)
  - Score: 0.90 | Effort: 15 min
  - Prioridade: 🔴 CRÍTICA
  - Desbloqueador: S2-0, Backtesting cache

- **TASK-013** — S2-0 REC-2: Data Versioning for Cache Consistency
  - Status: ⏳ **PLANEJADO**
  - Owner: Data (#11)
  - Score: 0.88 | Effort: 2h
  - Blocker: TASK-012
  - Prioridade: 🟠 ALTA
  - Desbloqueador: S2-0 cache, S2-3 Backtesting

- **TASK-014** — S2-0 QA Gates Completion
  - Status: ⏳ **SQUAD KICKOFF**
  - Owner: Data (#11) + QA Lead (#8)
  - Score: 0.85 | Effort: 3-4h
  - Blocker: TASK-012, TASK-013
  - Desbloqueador: S2-3 Backtesting
  - Prioridade: 🟠 ALTA

- **S2-3** — Backtesting Engine
  - Status: 🟡 **GATES 1-3 COMPLETE, GATE 4 PENDING**
  - Owner: Arch (#6), Data (#11)
  - Score: 0.95 | Effort: ~15-20h | Gate 4 Effort: 2-3h
  - Descrição: Deterministic backtester (6 metrics: Sharpe, MaxDD, Win Rate, Profit Factor, Calmar, Consecutive Losses)
  - Gates 1-3: ✅ COMPLETE (23 FEV 00:45 UTC)
  - Gate 4 (Documentation): 🟡 PENDING (Est. 24 FEV 06:00-12:00 UTC)
    - **G4.1:** Create backtest/README.md (500+ words, usage guide) — Owner: Doc Advocate (#17) + Quality (#12) — Est. 1.5h
    - **G4.2:** Python docstrings (all classes/functions, Portuguese) — Owner: Code Review (#6) — Est. 30min
    - **G4.3:** Update [CRITERIOS_DE_ACEITE_MVP.md](CRITERIOS_DE_ACEITE_MVP.md) § S2-3 — Owner: Doc Advocate (#17) — Est. 15min
    - **G4.4:** Register in [DECISIONS.md](DECISIONS.md) § S2-3 (trade-offs, deferred perf optimization) — Owner: Audit (#8) — Est. 15min
  - Prerequisite: Issue #67 Data Strategy (✅ Complete)
  - Documentação: [ARCH_S2_3_BACKTESTING.md](ARCH_S2_3_BACKTESTING.md) | [GATE_4_PLAN.md](GATE_4_PLAN.md) | [S2_3_DELIVERABLE_SPEC.md](S2_3_DELIVERABLE_SPEC.md)
---

## 🎯 COMPLETED ITEMS

**Status:** ✅ Entregues e operacionais em produção

- **Issue #64** — Telegram Alerts Setup ✅
  - Webhook + message templates completos
  - 18/18 testes PASS (rate limiting, signature validation)
  - Integração pronta para execution/risk/backtest modules
  - Documentação: [notifications/README.md](../notifications/README.md)

- **TASK-001** — Heurísticas Dev ✅
  - Implementadas heurísticas conservadoras (SMC + EMA + RSI + ADX)
  - Multi-timeframe validation (D1→H4→H1)
  - Risk gates ativos (drawdown -5%, circuit -3%)

- **TASK-002-004** — Go-Live Pipeline ✅
  - Phase 1 (10% vol): ✅ Sucesso
  - Phase 2 (50% vol): ✅ Sucesso
  - Phase 3 (100% vol): ✅ Sucesso
  - Zero circuit breaker false triggers

- **TASK-008** — Decision #3 Votação ✅
  - Board vote: 17/17 consenso (100%)
  - Opção C aprovada (Liquidation 11 + Hedge 10)
  - ATA registrada

- **TASK-009** — Decision #3 Implementação ✅
  - Liquidação 11/11 posições (0.55% slippage)
  - Hedge 10/10 posições (3 phases)
  - Margin liberado: $105k
  - Margin ratio: 180% → 300%

- **TASK-010** — Decision #4 Votação ✅
  - Board vote: 15/16 consenso (93.75% SIM)
  - Decision #4 aprovada (Expansão 60 → 200 pares via F-12b Parquet)
  - Condição aceita: QA buffer +48h
  - ATA registrada (Angel signature)

- **S2-1/S2-2** — SMC Volume Threshold + Order Blocks ✅
  - 28 tests PASS
  - Order blocks detection com volume validation
  - Edge cases handled

- **S2-4** — Trailing Stop Loss Core ✅
  - 34 unit tests
  - TrailingStopManager implemented
  - 50+ tests PASS

- **Decision #1** — Governança de Documentação ✅
  - 10 core docs centralizados
  - 65 arquivos obsoletos deletados
  - [SYNC] protocol ativo

- **Issue #67** — Data Strategy Dev ✅
  - Status: ✅ **COMPLETA** | 28 FEV 18:30 UTC
  - Owner: Data (#11), Arch (#6)
  - Score: 0.80 | Effort: ~6h execution
  - Resultado: 1-year historical data pipeline (60 symbols)
  - Carregamento: 131.400 candles (51/60 símbolos completos = 85%)
  - Cache: SQLite + Parquet otimizado (<100ms read latency)
  - Rate limits: 88 requests (7% of 1200/min limit)
  - Integração: iniciar.bat v0.3.0 com detecção automática
  - Desbloqueador: S2-3 Backtesting Engine pronto
  - Documentação: [ISSUE_67_DATA_STRATEGY_SPEC.md](ISSUE_67_DATA_STRATEGY_SPEC.md)

---

## ⚠️ RISCOS E BLOCKERS

| Task | Risco | Impacto | Mitigação |
|------|-------|---------|-----------|
| Issue #65 QA | SLA Deadline | 🔴 CRÍTICA | Hard deadline, escalation: Angel |
| TASK-005 PPO | Convergência | 🔴 CRÍTICA | Early stopping gates, daily validation |
| TASK-011 Phase 2+ | Parquet tuning | 🟡 MÉDIA | Buffer time, Arch review |

---

## 🔐 PRIORITIES

**Objetivo:** Priorização baseada em valor e dependências

**🔴 MUST — Critical Path:**
1. Issue #65 QA — Unblocks TASK-005
2. TASK-005 PPO Training — Critical blocker for ML pipeline
3. TASK-011 Phase 2 — Parquet optimization
4. TASK-011 Phase 3+ — Load tests + deployment

**🟡 SHOULD — Important:**
1. Issue #67 Data Strategy — Prerequisite for backtesting
2. S2-3 Backtesting Engine — Validation gate
3. Issue #64 Telegram — Operational monitoring

**🟢 COULD — Nice-to-have:**
1. Dashboard improvements
2. Advanced hedging strategies
3. Multi-exchange support

---

## 📝 HOW TO USE THIS BACKLOG

**Update Pattern:**
1. Mark task as "in-progress" when starting
2. Update Status field
3. Commit com [SYNC] tag quando finalizar
4. Move to "COMPLETED ITEMS"

**Review Cadence:**
- Daily: Update IN PROGRESS items + blockers
- Weekly: Prioritize FUTURE items
- Sprint cycle: Consolidate COMPLETED items

**Sync with Other Docs:**
All updates here should cross-reference related docs (ROADMAP.md, STATUS_ENTREGAS.md, TRACKER.md).

