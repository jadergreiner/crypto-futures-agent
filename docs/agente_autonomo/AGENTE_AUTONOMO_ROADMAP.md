# 🗺️ ROADMAP DO AGENTE AUTÔNOMO

**Versão**: 1.0
**Data**: 2026-02-20
**Horizonte**: 12 meses (FEV 2026 — DEZ 2026)
**Responsável**: Product Owner

---

## 📅 Timeline Executiva

```text
FEV 2026              MAR          ABR-JUN       JUL-SET      OUT-DEZ
─────────────────────────────────────────────────────────────────────

v0.3 CRÍTICO    v0.3.1 POSIÇÃO  v0.4 BACKTEST   v1.0 PRODUCTION  v2.0 ENTERPRISE
├─ TODAY        ├─ 20-21 FEV     ├─ 24/02         ├─ 30/04         ├─ Scaling 3×
├─ Validação    ├─ Real SL/TP    ├─ Engine        ├─ Compliance    ├─ Multi-strat
├─ 0 → 5 trades ├─ Parciais      ├─ Pronto        ├─ 24/7 Ops      ├─ Multi-exchange
└─ Guardian     └─ Monitor 24/7  └─ Release       └─ Licensing     └─ Revenue model
```text

## 🎯 Roadmap Detalhado

### ✅ v0.3 — VALIDAÇÃO RL (20-23 FEV)

**Objetivo**: Validar modelo PPO em 3 pares, sair de Profit Guardian Mode

| Milestone | Data | Critério | Status |
|-----------|------|----------|--------|
| ACAO-001 → 005 | 20-21 FEV | 100 min completo | ⏳ Aprovação CFO |
| Training complete | 21 FEV | CV < 1.5 | ⏳ Pending |
| Signal validation | 22 FEV | 5+ sinais/dia | ⏳ Pending |
| Go/No-Go decision | 23 FEV | Release OK? | ⏳ Pending |
| v0.3 live | 23 FEV | Tag + deploy | ⏳ Pending |

**Features**:
- ✅ PPO training (100 episodes)
- ✅ Signal generation (working)
- ✅ Trade execution (ready)
- ✅ Risk management (live)
- ⏳ Profit Guardian reset (ACAO-001)

**Success Metrics**:
- Win rate ≥ 50%
- Sharpe > 0.5
- No crashes
- 5+ trades/day

---

### ⭐ v0.3.1 — POSIÇÃO MANAGEMENT (20-21 FEV — SPRINT RÁPIDO)

**Objetivo**: Ordens REAIS Binance + Gestão de Parciais + Monitor 24/7

| Milestone | Data | Status | Descr |
|-----------|------|--------|-------|
| F-09 complete | 20 FEV | ✅ DONE | MARKET + SL + TP real |
| F-10 complete | 20 FEV | ✅ DONE | Gestão parciais (50%, 75%) |
| F-11 complete | 21 FEV | ✅ DONE | Monitor health + PnL + timeout |
| Trade ID 7 | 20 FEV | ✅ PROVA | 3 Binance IDs verificados |
| v0.3.1 release | 21 FEV | ✅ READY | Deploy imediato |

**Features**:
- ✅ new_algo_order() API discovery
- ✅ MARKET + SL/TP real Binance
- ✅ Cancela/recria SL/TP em parciais
- ✅ Monitor background contínuo
- ✅ Trade partial_exits schema

**Problema Resolvido**:
- ❌ SL/TP simulados localmente (risco crítico)
- ✅ Ordens REAIS apregoadas Binance 24/7

**Prova Funcional**:
```
Trade ID 7: ANKRUSDT LONG
├─ MARKET: 5412778331 ✅
├─ SL Algo: 3000000742992546 ✅ (-5%)
└─ TP Algo: 3000000742992581 ✅ (+10%)
```

**Success Metrics**:
- ✅ 3 Binance IDs reais
- ✅ DB sincronizado
- ✅ Scripts compilam
- ✅ Zero erros API

---

### 🟠 v0.4 — BACKTEST ENGINE (21-28 FEV — SPRINT ATIVO + DECISION PANEL)

**Objetivo**: Ferramenta backtest pronta, risk gates validation, PPO training (Phase 3)

**Status**: Phase 3 Complete (22 FEV) — 2/6 gates passados, CTO decision required

| Milestone | Data | Status | Descr |
|-----------|------|--------|-------|
| F-12a complete | 20 FEV | ✅ DONE | BacktestEnvironment |
| F-12b complete | 22 FEV | ✅ DONE | Data pipeline 3-layer (460L) |
| F-12c complete | 22 FEV | ✅ DONE | Trade state machine (270L) |
| F-12d complete | 22 FEV | ✅ DONE | Backtest metrics (260L) |
| F-12e complete | 22 FEV | ✅ DONE | Unit tests (9/9 passing) |
| **Phase 3: Risk Gates** | 22 FEV | ⚠️ NO-GO | 2/6 gates passed (need CTO decision) |
| CTO Decision (A/B/C) | 22 FEV | 🔴 PENDING | Override / Train / Hybrid |
| **Option B: PPO Training** | 23-28 FEV | ⏳ IF SELECTED | Train 5-7 days, revalidate gates |
| v0.4 release | 28 FEV (if B) | ⏳ CONDITIONAL | Depends on CTO choice |

**Features (Completed)**:
- ✅ BacktestEnvironment (deterministic)
- ✅ ParquetCache 3-tier pipeline (SQLite→Parquet→NumPy)
- ✅ TradeStateMachine (state machine + PnL)
- ✅ BacktestMetrics (6 risk gates)
- ✅ Full backtest execution (500 candles)
- ✅ Reward function validation (7/7 ML checks)

**Risk Gates Results (22 FEV 12:21 UTC)**:
```
Sharpe Ratio................ 0.06 ❌ (need ≥ 1.0)
Max Drawdown................ 17.24% ❌ (need ≤ 15%)
Win Rate.................... 48.51% ✅ (need ≥ 45%)
Profit Factor............... 0.75 ❌ (need ≥ 1.5)
Consecutive Losses.......... 5 ✅ (need ≤ 5)
Calmar Ratio................ 0.10 ❌ (need ≥ 2.0)
─────────────────────────────────
Gates Passed: 2/6 (33%) — BELOW MINIMUM 5/6
Root Cause: Model not trained (random actions); F-12 architecture 100% OK
```

**Executive Options (CTO DECISION REQUIRED)**:
- **Option A** (⚠️ Medium risk): Override restrictions + capital limits → Start paper trading now
- **Option B** (✅ Low risk): Train PPO model 5-7 days → Re-validate gates → Authorization 28 FEV
- **Option C** (Balanced): Hybrid (start paper + train parallel) → Upgrade live when ready

**Next Step**: CTO choose A/B/C by 22 FEV EOD → Triggers Phase 4 (training or deployment)
| F-12e complete | 23 FEV (Quinta) | ⏳ IN PROGRESS | Comprehensive tests |
| v0.4 release | 23-24 FEV | ⏳ PENDING | Engine ready (Sexta buffer) |

**Features**:
- ✅ BacktestEnvironment (deterministic)
- ⏳ Data pipeline (Parquet cache)
- ⏳ Trade state machine
- ⏳ Reporter
- ⏳ 8+ test suites

**Success Metrics**:
- 90 dias backtest em <10s
- 85%+ test coverage
- Sem regressions

---

### 🟡 v0.5 — SCALING + RISK (01-09 MAR)

**Objetivo**: Scale to 10-20 concurrent, real-time monitoring, co-location

| Sprint | Foco | Resultado |
|--------|------|-----------|
| Sprint 1 (01-05 MAR) | Risk mgmt v2 | Real-time monitoring live |
| Sprint 2 (06-09 MAR) | Infrastructure | Co-location <1ms |
| Sprint 3 | Scaling | 20 concurrent positions |

**Features**:
- Max drawdown 5% → 3%
- Real-time Sharpe monitoring
- Emergency stops
- Co-location setup (Tokyo/SG)
- Latency: 19ms → <1ms
- Concurrent: 10 → 20

**Success Metrics**:
- 20+ trades/day
- $500k AUM (from $50k)
- Sharpe ≥ 1.2
- Uptime 99.9%

---

### 🟢 v1.0 — PRODUCTION READY (10-30 ABR)

**Objetivo**: Enterprise-grade, compliance-ready, 24/7 ops

| Phase | Foco | Output |
|-------|------|--------|
| Compliance | Auditoria externa | ✅ Reports |
| Automation | 24/7 sem manual | ✅ Scripts |
| Multi-pair | Suporte dinâmico 16+ | ✅ Config |
| Launch | Production deploy | ✅ Live |

**Features**:
- External audit complete
- ANOD/CVM reporting
- 24/7 no intervention
- Dynamic pair support
- Auto-scaling

**Success Metrics**:
- $2M+ AUM
- 100+ trades/day
- Sharpe > 1.5
- Revenue > $0 (após custos)

---

### 🟣 v2.0 — ENTERPRISE (01-31 DEZ)

**Objetivo**: Multi-clientela, multi-exchange, licensing, revenue

| Quarter | Focus | Output |
|---------|-------|--------|
| Q3 2026 | Multi-account | 3+ clientes |
| Q4 2026 | Multi-exchange | Deribit + OKEx |
| Q4 2026 | Licensing | SaaS model |

**Features**:
- Multi-account orchestration
- Multi-exchange APIs
- Licensing dashboard
- Client management
- Billing system

**Revenue Target**: $500k/ano

---

## 📈 Capacidade por Versão

```text
v0.3:  5 trades/day    | $50k AUM    | Sharpe 0.5-1.0
v0.4:  10 trades/day++ | $100k AUM   | Backtest validação
v0.5:  20+ trades/day  | $500k AUM   | Sharpe 1.0-1.5
v1.0:  100 trades/day  | $2M AUM     | Sharpe >1.5 (target)
v2.0:  500+ trades/day | Multi-$M    | Revenue >$500k
```text

## 🎁 Feature Roadmap Consolidado

```text
v0.3 (HOJE):
├─ RL Training ✅
├─ Signal generation ✅
├─ Live trading ✅
└─ Risk constraints ✅

v0.4 (24-28 FEV):
├─ BacktestEnvironment ✅ (F-12a)
├─ Data pipeline ⏳ (F-12b)
├─ State machine ⏳ (F-12c)
├─ Reporter ⏳ (F-12d)
└─ Comprehensive tests ⏳ (F-12e)

v0.5 (01-09 MAR):
├─ Risk mgmt v2 ⏳
├─ Real-time monitoring ⏳
├─ Co-location ⏳
└─ Scaling to 20 ⏳

v1.0 (10-30 ABR):
├─ Compliance ⏳
├─ 24/7 automation ⏳
├─ Multi-pair dynamic ⏳
└─ Enterprise deployment ⏳

v2.0 (01-31 DEZ):
├─ Multi-account ⏳
├─ Multi-exchange ⏳
└─ Licensing model ⏳
```text

## 🚨 Risco & Mitigação

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| v0.3 fails validation | BAIXA (10%) | Extended testing, v0.2 rollback |
| Market crash | ALTA (50%) | Drawdown limits, emergency stops |
| Co-location latency | BAIXA (5%) | Fallback to cloud (19ms acceptable) |
| Regulatory change | MÉDIA (30%) | Compliance team, legal counsel |

## 🎯 Decisão Gates

```text
GATE 1: 22:00 BRT (HOJE)
├─ CFO: Aprova ACAO-001?
└─ Bloqueador para ACAO-002-005

GATE 2: 09:00 BRT (22 FEV)
├─ CTO: v0.3 validation OK?
├─ Métrica: Win rate ≥50%, Sharpe >0.5
└─ Bloqueador para v0.3 release

GATE 3: 10:00 BRT (23 FEV)
├─ PO: v0.3 release decision
├─ Baseado em 24h live data
└─ Kickoff v0.4 se aprovado

GATE 4: 28 FEV
├─ PO + CTO: v0.4 ready?
└─ Start v0.5

GATE 5: 09 MAR
├─ CFO + CTO: v0.5 performance?
└─ Roadmap adjustment se needed
```text

---

**Mantido por**: Product Owner + CTO
**Frequência revisão**: Semanal (ou por release)
**Last Updated**: 2026-02-20 22:15 UTC

