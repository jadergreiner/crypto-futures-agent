# 🚀 BACKLOG QUICK START — ACESSO RÁPIDO

**Status:** ✅ READY FOR EXECUTION
**Última atualização:** 21 FEV 22:45 UTC
**Owner:** Planner (Gerente Projetos)

---

## 🎯 QUICK LINKS

| Documento | Propósito | Link |
|-----------|-----------|------|
| **Sprint Backlog** | Detalhes completos de cada task | [SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md](./SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md) |
| **Tracker Real-Time** | Status em tempo real + daily standups | [TASKS_TRACKER_REALTIME.md](./TASKS_TRACKER_REALTIME.md) |
| **Este arquivo** | Quick reference (você está aqui) | [BACKLOG_QUICK_START.md](./BACKLOG_QUICK_START.md) |

---

## 🔴 SPRINT 1: MUST (21-25 FEV) — EXECUTE NOW

### **Prioridade #1: Heurísticas Dev → QA → Go-Live**

```
┌─ TASK-001 (Dev: 6h)
│   "Implementar heurísticas conservadoras"
│   Owner: Dev (The Implementer)
│   When: 21 FEV 23:00 UTC → 22 FEV 06:00 UTC
│   Status: 🔴 STARTING NOW
│   Risk: Threshold agressivo
│
├─ TASK-002 (QA: 2h)
│   "Validação completa (9/9 tests)"
│   Owner: Audit (QA Manager)
│   When: 22 FEV 06:00 → 08:00 UTC
│   Gate: QUALITY GATE #1 (must pass to proceed)
│
├─ TASK-003 (Trading: 2h)
│   "Alpha SMC validation"
│   Owner: Alpha (Senior Trader)
│   When: 22 FEV 08:00 → 10:00 UTC
│   Gate: TRADER APPROVAL (must approve)
│
└─ TASK-004 (Ops: 4h)
    "Go-Live Heurísticas (canary 10%→50%→100%)"
    Owner: Dev + Guardian + Elo
    When: 22 FEV 10:00 → 14:00 UTC
    Gate: OPERATIONS GO/NO-GO (deploy decision)
```

**Critical Path:** 21 FEV 23:00 → 22 FEV 14:00 (15 horas wall time)

---

### **Prioridade #2: PPO Training (Paralelo) → Quality → Live**

```
┌─ TASK-005 (ML: 96h PARALELO)
│   "PPO Training Phase 2 (steps 500k)"
│   Owner: The Brain + Arch
│   When: 22 FEV 14:00 → 25 FEV 10:00 UTC (4 dias)
│   Status: 🔄 STARTS AFTER #1.4 GO-LIVE
│   Training: 96 hours (parallel to heurísticas live)
│   Target: Sharpe >1.0, Drawdown <5%
│   Risk: Overfit em phase-1 signals
│
├─ TASK-006 (QA: 4h)
│   "PPO Quality Gate (Sharpe, Drawdown, OOT)"
│   Owner: Audit (QA) + The Brain
│   When: 25 FEV 10:00 → 14:00 UTC
│   Gate: QUALITY GATE #2 (must pass)
│   Pass criteria: Sharpe >1.0, DD <5%, no look-ahead bias
│
└─ TASK-007 (Ops: 6h)
    "PPO Merge Live (canary 10%→50%→100%)"
    Owner: Dev + Guardian
    When: 25 FEV 14:00 → 20:00 UTC
    Gate: OPERATIONS MERGE GO/NO-GO
    Result: PPO 100% live, heurísticas retired
```

**Timeline:** 22 FEV 14:00 → 25 FEV 20:00 (82 horas wall time)

---

## 🟠 SPRINT 2: SHOULD (26-27 FEV) — DEPEND ON SPRINT 1

### **Prioridade #3: Decision #3 - Posições Underwater**

```
├─ TASK-008 (Board: 2h)
│   "Decision #3 Vote (liquidate vs hedge vs 50/50)"
│   Owner: Angel (Investor)
│   When: 26 FEV 09:00 → 11:00 UTC
│   Participants: 16-member board
│   Options: A=Liquidate, B=Hedge, C=50/50
│
└─ TASK-009 (Exec: 7h)
    "Implement Decision #3"
    Owner: Dr. Risk + Guardian
    When: 26 FEV 11:00 → 18:00 UTC
    Execution: Resolve 21 underwater positions
```

**Timeline:** 26 FEV 09:00 → 18:00 (9 horas)

---

### **Prioridade #4: Decision #4 - Escalabilidade**

```
├─ TASK-010 (Board: 2h)
│   "Decision #4 Vote (expand 60→200 pares)"
│   Owner: Angel (Investor)
│   When: 27 FEV 09:00 → 11:00 UTC
│   Participants: 16-member board
│   Options: A=Agressivo, B=Profundidade
│
└─ TASK-011 (Data: 9h)
    "F-12b Parquet Expansion (60→200)"
    Owner: Flux (Architect) + Blueprint
    When: 27 FEV 11:00 → 20:00 UTC
    Result: 200 pares live, +30% throughput
```

**Timeline:** 27 FEV 09:00 → 20:00 (11 horas)

---

## 📊 VISUAL TIMELINE

```
21 FEV (Fri)
│
├─ 23:00 ──→ TASK-001 START (Dev heurísticas)
│
22 FEV (Sat)
│
├─ 06:00 ──→ TASK-001 END, TASK-002 START (QA testing)
├─ 08:00 ──→ TASK-002 END, TASK-003 START (Alpha validation)
├─ 10:00 ──→ TASK-003 END, TASK-004 START (Go-Live canary)
├─ 14:00 ──→ TASK-004 COMPLETE ✅, TASK-005 START (PPO training)
│           🚀 HEURÍSTICAS LIVE
│
23-24 FEV (Sun-Mon)
│
├─ ──────→ TASK-005 running (48h+ of 96h)
│           Heurísticas live monitoring
│
25 FEV (Tue)
│
├─ 10:00 ──→ TASK-005 COMPLETE, TASK-006 START (PPO quality gate)
├─ 14:00 ──→ TASK-006 END, TASK-007 START (PPO merge live)
├─ 20:00 ──→ TASK-007 COMPLETE ✅
│           🚀 PPO 100% LIVE
│
26 FEV (Wed)
│
├─ 09:00 ──→ TASK-008 START (Decision #3 board)
├─ 11:00 ──→ TASK-008 END, TASK-009 START
├─ 18:00 ──→ TASK-009 COMPLETE ✅
│           Positions resolved
│
27 FEV (Thu)
│
├─ 09:00 ──→ TASK-010 START (Decision #4 board)
├─ 11:00 ──→ TASK-010 END, TASK-011 START
├─ 20:00 ──→ TASK-011 COMPLETE ✅
│           200 pares live
```

---

## 🎯 BY ROLE: WHAT TO DO NOW?

### **👨‍💻 DEV (The Implementer)**

**RIGHT NOW (21 FEV 23:00 UTC):**
- [ ] Pull latest main branch
- [ ] Create feature branch: `feature/TASK-001-heuristics`
- [ ] Start implementing `execution/heuristic_signals.py`
- [ ] Timeline: 6 hours until 22 FEV 06:00 UTC
- [ ] Deliverable: 250 LOC + 100% test coverage

**Next:** TASK-004 (Go-Live Ops) @ 22 FEV 10:00 UTC

---

### **🧪 AUDIT/QA (QA Manager)**

**22 FEV 06:00 UTC (morning standup):**
- [ ] Receive code from Dev (TASK-001)
- [ ] Run test suite: 9/9 must pass
- [ ] Validate edge cases (5 scenarios)
- [ ] Approve or reject (gate decision)
- [ ] Deadline: 22 FEV 08:00 UTC (2h)

**Next:** TASK-006 (PPO Quality Gate) @ 25 FEV 10:00 UTC

---

### **📈 ALPHA (Senior Trader)**

**22 FEV 08:00 UTC (after QA pass):**
- [ ] Receive heurísticas signals
- [ ] Run simulação 1h (live market conditions)
- [ ] Validate SMC rules (Order Blocks, FVG, etc.)
- [ ] Approve signals or request changes
- [ ] Deadline: 22 FEV 10:00 UTC (2h)

**Next:** TASK-007 monitoring (25 FEV)

---

### **🚀 PLANNER (Gerente Projetos)**

**TODAY (21 FEV):**
- [ ] Confirm team assignments
- [ ] Set up daily standup @ 08:00 & 16:00 UTC
- [ ] Create incident channel (alerts)
- [ ] Prepare gate checkpoints

**Daily:**
- [ ] Lead standup (15 min)
- [ ] Monitor blockers
- [ ] Track metrics (velocity, test pass rate)

**Critical dates:**
- 22 FEV 08:00h: Gate #1 decision (QA)
- 22 FEV 14:00h: Go-Live decision (Ops)
- 25 FEV 10:00h: Gate #2 decision (PPO)

---

### **🧠 THE BRAIN (ML Engineer)**

**22 FEV 14:00 UTC (after heurísticas go-live):**
- [ ] Initialize PPO training environment
- [ ] Load data pipeline (500k timesteps)
- [ ] Start training (steps 500k target)
- [ ] Monitor hourly: loss curve, reward trend
- [ ] Deadline: 25 FEV 10:00 UTC (4 days)

**Target:** Sharpe >1.0, Drawdown <5%

---

### **💰 DR. RISK & GUARDIAN (Risk Team)**

**22 FEV 14:00 UTC (heurísticas live monitoring):**
- [ ] Arm circuit breaker: -3% kill switch
- [ ] Set max drawdown: 5% hard cap
- [ ] Monitor position sizing (Kelly criterion)
- [ ] Prepare position management plan

**26 FEV 09:00 UTC (Decision #3):**
- [ ] Present 3 options (liquidate/hedge/50-50)
- [ ] Analyze 21 underwater positions
- [ ] Risk impact assessment
- [ ] Recommendation to Angel

---

### **👑 ANGEL (Investor)**

**Status check:**
- [ ] Decision #2 (Opção C) → Already APPROVED ✅
- [ ] TASK-001 starts 21 FEV 23:00 UTC
- [ ] Receive daily updates (smart metrics)

**Critical decisions:**
- [ ] 26 FEV 09:00h: Decision #3 vote
- [ ] 27 FEV 09:00h: Decision #4 vote

---

## 🔔 CRITICAL GATES (Go/No-Go Checkpoints)

| Gate | Date | Time | Owner | Criteria |
|------|------|------|-------|----------|
| **#1 QA** | 22 FEV | 08:00h | Audit(QA) | 9/9 tests pass |
| **#2 Trading** | 22 FEV | 10:00h | Alpha | SMC approval |
| **#3 Operations** | 22 FEV | 14:00h | Planner | Canary #1 healthy |
| **#4 PPO Conv** | 25 FEV | 10:00h | Brain | Sharpe >1.0 |
| **#5 PPO QA** | 25 FEV | 14:00h | Audit(QA) | OOT valid, DD <5% |
| **#6 PPO Ops** | 25 FEV | 20:00h | Dev | Canary merge OK |

**If any gate FAILS:**
```
Gate #1 (QA) fails    → Extend TASK-001 (dev fixes bugs)
Gate #2 (Trading) fails → Adjust threshold, revalidate
Gate #3 (Ops) fails    → Rollback, investigate canary issue
Gate #4 (PPO) fails    → Extend training +2d (sharpe <1.0)
Gate #5 (PPO QA) fails → Extend training +1d, re-validate
Gate #6 (PPO Ops) fails → Rollback to heurísticas (1h max)
```

---

## 📞 ESCALATION PATH

```
Issue discovered
      ↓
Standup report (08:00 UTC)
      ↓
Planner assesses severity
      ├─ P4 (low): Log, weekly review
      ├─ P3 (medium): Flag, daily track
      ├─ P2 (high): Escalate to team lead
      └─ P1 (critical): Call Investor directly
      ↓
Owner resolves with resources assigned
      ↓
Next standup: Report status & resolution
```

---

## ✅ ACCEPTANCE CRITERIA (Each Sprint)

### **Sprint 1 Completion (25 FEV 20:00 UTC):**
- ✅ Heurísticas live & operacional (4 days)
- ✅ PPO trained, Sharpe >1.0, live & operacional
- ✅ 21 positions still managed (risk gates active)
- ✅ Zero critical bugs in production
- ✅ Audit trail 100% complete

### **Sprint 2 Completion (27 FEV 20:00 UTC):**
- ✅ Positions resolved (Decision #3 implemented)
- ✅ 200 pares live (Decision #4 implemented)
- ✅ Performance: +30% throughput achieved
- ✅ Backlog groomed for Week 2 (COULD items ready)

---

## 📧 COMMUNICATION

**Daily standup:** 08:00 & 16:00 UTC (15 min each)
**Slack channel:** #board-decisions
**Escalation channel:** #critical-alerts
**Status page:** GitHub project board

**Who gets emails:**
- Gate approvals (failures/rare events)
- Daily digest (16:30 UTC)
- Weekly summary (Friday 17:00 UTC)

---

## 🎯 SUCCESS METRICS (End of Week)

| KPI | Target | Acceptable | Fail |
|-----|--------|-----------|------|
| Heurísticas Uptime | 99.5% | 98% | <98% |
| PPO Training Sharpe | 1.2+ | 1.0+ | <1.0 |
| Live Drawdown | <-3% | <-5% | >-5% |
| Test Pass Rate | 100% | 95% | <95% |
| Critical Bugs | 0 | 0 | >0 |

---

## 🚦 STATUS AT A GLANCE

```
                    21 FEV          22 FEV          25 FEV          27 FEV
                  (Kickoff)     (Go-Live Heur)   (Go-Live PPO)   (Scaling)
                      │             │               │               │
MUST Sprint 1:   ┌─────────────────────┬───────────┬───────────┐
                 │                     │ EXECUTING │           │
                 │                     └─────◆─────┘           │
                 │                           └─────────────◆───┘
                 │
SHOULD Sprint 2: │                                       ┌───┬───┐
                 │                                       │   │   │
                 │                                       └─◆─┴─◆─┘

BACKLOG Sprint 3:│                                           (Week 2+)
                 │
                 └ ALL SPRINT 1 TASKS COMPLETED BY 25 FEV 20:00 UTC

STATUS: ️✅ ON TRACK — EXECUTION BEGINS NOW
```

---

## 🔗 SYNC WITH MAIN DOCS

**This backlog connects to:**
- `/docs/CHRONOGRAM.md` → Timeline coordination
- `/docs/DECISIONS.md` → Decision registry (Decision #2 approva
d)
- `/docs/ROADMAP.md` → Feature detail alignment
- `/README.md` → Current status updates

**Sync Protocol:** [SYNC] tag in all commits

---

## 📞 CONTACT & QUESTIONS

**Questions about:**
- **Backlog (overall):** Planner (Gerente Projetos)
- **Individual tasks:** Owner listed per task
- **Technical detail:** Tech Lead (The Blueprint)
- **Risk/Decision:** Angel (Investor)

---

**Status:** ✅ READY FOR EXECUTION
**Release:** Dev starts now (21 FEV 23:00 UTC)
**Next review:** 22 FEV 08:00 UTC (daily standup)
