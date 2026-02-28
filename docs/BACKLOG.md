# 📦 BACKLOG — Crypto Futures Agent

**Status:** 🟢 OPERACIONAL | Fonte Única da Verdade para Itens Desenvolvidos + A Desenvolver
**Atualizado:** 27 FEV 2026 11:00 UTC (TASK-010 votada e TASK-011 ativada)
**Mantém:** Sprint 1-2-3 items + TASK pipeline + Issue tracking
**Responsável:** Planner, Board, Doc Advocate

---

## 🔗 Links Rápidos

| Documento | Propósito |
|-----------|-----------|
| [ROADMAP.md](ROADMAP.md) | Visão estratégica (Now-Next-Later) |
| [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) | Status das entregas do ROADMAP |
| [PLANO_DE_SPRINTS_MVP_NOW.md](PLANO_DE_SPRINTS_MVP_NOW.md) | Sprints e NOW items detalhes |
| [USER_STORIES.md](USER_STORIES.md) | User stories (v0.2→v1.0) |
| [DECISIONS.md](DECISIONS.md) | Decision history + board approvals |
| [FEATURES.md](FEATURES.md) | Feature list (F-H1→F-ML3) |
| [RELEASES.md](RELEASES.md) | Version history (v0.1→v1.0-alpha) |
| [TRACKER.md](TRACKER.md) | Sprint tracker detalhado |

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
  - Status: ✅ **PHASE 1 COMPLETA** | 🔄 **PHASES 2-4 IN PROGRESS**
  - Owner: Flux (#5), Squad B (Blueprint, Data, Quality, Arch, Executor)
  - Score: 0.92 | Effort: 11h total
  - Phase 1: ✅ 200/200 símbolos validados (100%)
  - Documentação: [BRIEFING_SQUAD_B_TASK_011_PHASE1.md](BRIEFING_SQUAD_B_TASK_011_PHASE1.md)

- **Issue #64** — Telegram Alerts Setup
  - Status: 🟡 **AWAITING Issue #65 COMPLETION**
  - Owner: The Blueprint (#7), Quality (#12)
  - Score: 0.75 | Effort: 1.5h
  - Descrição: Webhook integration + msg formatter (P&L, drawdown, trades alerts)
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

- **Issue #67** — Data Strategy Dev
  - Status: 🟡 **AWAITING Issue #65 COMPLETION**
  - Owner: Data (#11), Arch (#6)
  - Score: 0.80 | Effort: ~3 days
  - Descrição: 1-year historical data pipeline (60 symbols, Parquet 3-tier cache)
  - Prerequisite para: S2-3 Backtesting Engine
  - Documentação: [ISSUE_67_DATA_STRATEGY_SPEC.md](ISSUE_67_DATA_STRATEGY_SPEC.md)

- **S2-4** — Trailing Stop Loss Integration
  - Status: ✅ **COMPLETA**
  - Owner: Arch (#6)
  - Score: 0.75 | Effort: Merged
  - Descrição: TrailingStopManager integration com OrderExecutor
  - Ready para: Live testing
  - Documentação: [ARCH_S2_4_TRAILING_STOP.md](ARCH_S2_4_TRAILING_STOP.md)

- **S2-3** — Backtesting Engine
  - Status: 🟡 **DESIGN COMPLETE**
  - Owner: Arch (#6), Data (#11)
  - Score: 0.95 | Effort: ~15-20h
  - Descrição: Deterministic backtester (6 metrics: Sharpe, MaxDD, Win Rate, Profit Factor, Calmar, Consecutive Losses)
  - Prerequisite: Issue #67 Data Strategy
  - Documentação: [ARCH_S2_3_BACKTESTING.md](ARCH_S2_3_BACKTESTING.md)
---

## 🎯 COMPLETED ITEMS

**Status:** ✅ Entregues e operacionais em produção

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

