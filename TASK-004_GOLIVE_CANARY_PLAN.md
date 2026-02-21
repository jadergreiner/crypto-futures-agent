# 🚀 TASK-004: Go-Live Canary Deployment Plan

**Data Início:** 22 FEV 2026 10:00 UTC
**Deadline:** 22 FEV 2026 14:00 UTC (4h)
**Owner:** Dev + Planner + Elo (Ops Lead)
**Status:** 🔄 PREPARAÇÃO

---

## 📋 Executivo Summary

Deploy das heurísticas conservadoras para ambiente live com monitoramento intensivo. Canary approach com 3 fases de gates:

| Fase | Volume | Duração | Latência | Drawdown | Erros |
|------|--------|---------|----------|----------|-------|
| **1 (10%)** | 10% | 30min | <500ms | <-1% | ✓ Zero |
| **2 (50%)** | 50% | 2h | <500ms | <-2% | ≤2 warnings |
| **3 (100%)** | Full | Ongoing | <500ms | <-3% | Circuit breaker ativo |

**Go/No-Go Gates:**
- ✅ TASK-003 Alpha approval (SMC validation)
- ✅ Pre-flight checks passing
- ✅ Database backup completo
- ✅ Rollback procedure armada

---

## 🔧 PRÉ-REQUISITOS (22 FEV 09:00-10:00)

### Team Allocation

| Role | Owner | Responsabilidade |
|------|-------|-------------------|
| **Dev** | The Implementer | Deploy code + monitoring |
| **Planner** | Orchestrator | Cronometragem + gates |
| **Elo** | Ops Lead | Infrastructure + rollback |
| **Audit** | QA Manager | Validation logs |
| **Alpha** | Senior Trader | Decisão stop-loss |

### Pre-Flight Checklist

```bash
PRÉ-REQUISITOS (09:00-10:00):
☐ API connectivity check (Binance REST + WebSocket)
☐ Database backup completo (states + trades)
☐ Environment variables validadas (.env)
☐ Heurísticas código deployado em `main` branch
☐ Monitoring stack ativo (prometheus + grafana)
☐ Alertas configurados (Slack + PagerDuty)
☐ Rollback scripts testados (1h restore time)
☐ Team comunicação (Slack + group call)
```

### Infrastructure Readiness

```
✓ Binance API keys loaded
✓ WebSocket subscriptions ready
✓ Database connections active
✓ Monitoring collectors running
✓ Alerting thresholds set
✓ Backup storage available
✓ Network latency baseline <50ms
```

---

## ⏱️ TIMELINE (22 FEV 10:00-14:00)

### **10:00-10:30 → FASE 1: PRÉ-FLIGHT & GO/NO-GO DECISION**

**Checkpoint #0: Pre-Flight Validation**

```
[10:00] Gates check:
  ✓ TASK-003 Alpha approval documented
  ✓ Code deployment verified (heuristic_signals.py in main)
  ✓ All pre-flight checks passing
  ✓ Team communication online

[10:05] Decision: GO / NO-GO
  → IF all gates green: Proceed to Phase 1
  → IF any gate red: CANCEL + troubleshoot (max 15min)
  → IF >15min troubleshoot: POSTPONE to 22 FEV 16:00
```

---

### **10:30-11:00 → FASE 1: CANARY 10% VOLUME**

**Target:** Test deployment with minimal capital exposure

```
[10:30] Deployment:
  - Enable heuristic_signals.py on 3 pairs: (BTCUSDT, ETHUSDT, BNBUSDT)
  - Risk settings: max_per_trade=0.1% → 10% of normal position size
  - Monitoring: 30min continuous watch
  
[10:30-11:00] Validation:
  ✓ Order placement latency <500ms (Binance response time)
  ✓ Fill rate: Esperado >95%
  ✓ Slippage: <0.1% (bid-ask variance)
  ✓ Drawdown: <-1% total
  ✓ Error count: ZERO (any error = ROLLBACK)
  ✓ Signal quality: ≥3/4 confluence
  
[11:00] Gate #1 Decision:
  → PASS (all metrics green) → Proceed to Phase 2
  → WARNING (1-2 non-critical issues) → Continue with caution
  → FAIL (critical issue OR drawdown worse) → IMMEDIATE ROLLBACK
```

**Success Criteria Phase 1:**
- ✅ 0 critical errors
- ✅ Latency <500ms on all trades
- ✅ Drawdown <-1%
- ✅ Fill rate >95%

---

### **11:00-13:00 → FASE 2: CANARY 50% VOLUME**

**Target:** Extended testing with moderate capital

```
[11:00] Scaling:
  - Expand to 5-7 pairs (+ SOL, ADA, XRP)
  - Risk settings: 50% of normal position size
  - Monitoring: 2h continuous watch
  
[11:00-13:00] Validation:
  ✓ Order latency <500ms (sustained)
  ✓ Fill consistency: >95% on all pairs
  ✓ Slippage average: <0.15%
  ✓ Drawdown cumulative: <-2%
  ✓ Warnings: ≤2 (non-critical)
  ✓ Circuit breaker logic: Tested if needed
  ✓ Signal quality maintained: ≥3/4 confluence
  
[13:00] Gate #2 Decision:
  → PASS (all metrics green) → Proceed to Phase 3 (100%)
  → WARNING (2 non-critical issues) → Proceed with monitoring increase
  → FAIL (>2 issues OR drawdown worse) → IMMEDIATE ROLLBACK
```

**Success Criteria Phase 2:**
- ✅ ≤2 non-critical warnings
- ✅ Latency <500ms sustained
- ✅ Drawdown <-2%
- ✅ Fill rate >95% all pairs
- ✅ Zero liquidation errors

---

### **13:00-14:00 → FASE 3: FULL DEPLOYMENT (100% VOLUME)**

**Target:** Full operational deployment with circuit breaker active

```
[13:00] Full Deployment:
  - Expand to ALL operational pairs (≤20 pairs)
  - Risk settings: 100% of normal position size
  - Circuit breaker: ARMED (-3% drawdown trigger)
  - Monitoring: Ongoing 24/7
  
[13:00-14:00] Validation:
  ✓ Operational latency <500ms
  ✓ Order success rate: >99%
  ✓ Drawdown cumulative: <-3% (monitoring)
  ✓ Audit trail: 100% logging active
  ✓ Risk gates: All armed & responsive
  ✓ Team confidence: Ready for unattended operation
  
[14:00] Fine-tuning & Handoff:
  - Baseline metrics documented
  - Incident response crew briefed
  - Monitoring dashboard pinned
  - Team rotates to monitoring mode
```

**Success Criteria Phase 3:**
- ✅ All pairs operational
- ✅ Circuit breaker tested & armed
- ✅ Monitoring dashboard active
- ✅ Incident response ready

---

## 🚨 ROLLBACK PROCEDURE (TRIGGER: IMMEDIATE)

**Rollback Trigger Conditions:**
```
AUTOMATIC (>0s response):
  ❌ Circuit breaker -3% drawdown triggered
  ❌ Database connectivity lost
  ❌ WebSocket stream interrupted >30s
  ❌ Order placement error rate >5%

MANUAL (Alpha/Planner decision):
  ❌ Multiple liquidation errors
  ❌ Fill rate drops <90%
  ❌ Latency consistently >1s
  ❌ Unexplained signal quality drop
```

**Rollback Execution (< 5 min):**

1. **Immediate Actions (0-30s):**
   ```
   ✓ Disable heuristic_signals engine
   ✓ Close all open positions (market order)
   ✓ Disable paper trading mode
   ✓ Alert team on Slack + call
   ```

2. **Investigation (30s-3min):**
   ```
   ✓ Capture error logs
   ✓ Database backup status
   ✓ Calculate P&L at rollback
   ✓ Determine root cause
   ```

3. **Post-Mortem (3-5min):**
   ```
   ✓ Document incident
   ✓ Team discussion
   ✓ Fix + re-test OR postpone
   ✓ Commit post-mortem to git
   ```

**Restore from Backup:**
```bash
# If database corruption:
$ scripts/restore_database_backup.sh --timestamp 22FEV-1000
# Expected time: ~1h (acceptable, monitored close)
```

---

## 📊 MONITORAMENTO REAL-TIME

### Key Metrics (via Prometheus + Grafana)

```
Trading Metrics:
  • Trade latency (ms): target <500ms
  • Fill rate (%): target >95%
  • Slippage (bps): target <15bps
  • Order error rate (%): target <1%
  
Risk Metrics:
  • Cumulative drawdown (%): target <-3%
  • Current drawdown (%): real-time alert >-2%
  • Max drawdown intraday (%): real-time alert >-1%
  • Circuit breaker status: ARMED / TRIGGERED
  
Signal Quality:
  • Confluence score (avg): target ≥3.2/4
  • Signal frequency (/h): target 1-3/h
  • Confidence score (avg): target >75%
  • SMC alignment (%): target ≥80%
```

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Latency | >750ms | >1500ms → ROLLBACK |
| Fill rate | <95% | <90% → INVESTIGATE |
| Slippage | >20bps | >50bps → CHECK_MARKET |
| Drawdown | -1.5% | -2.5% → CIRCUIT_BREAKER |
| Confluence | <2.5/4 | <2/4 → SIGNAL_SUSPEND |
| Error rate | >1% | >3% → IMMEDIATE_STOP |

---

## 📝 DOCUMENTATION & LOGGING

### Logging Requirements

```python
# Cada operação deve logar:
{
    "timestamp": "2026-02-22T10:30:15Z",
    "pair": "BTCUSDT",
    "event": "order_placed",
    "signal_confidence": 78.5,
    "confluence_score": 3.5,
    "risk_gate": "CLEARED",
    "drawdown_pct": -0.8,
    "latency_ms": 245,
    "order_id": "Binance_Order_ID",
    "status": "FILLED",
    "fill_price": 42500.50,
    "quantity": 0.05,
    "side": "BUY"
}
```

### Audit Trail

- ✅ All trades logged
- ✅ All signal triggers documented
- ✅ All risk gate decisions recorded
- ✅ All errors captured with stack trace
- ✅ Timestamp accuracy: <100ms

---

## ✅ ACCEPTANCE CRITERIA (END OF TASK-004)

### Canary Phase 1 ✅
- [ ] Zero critical errors
- [ ] Latency <500ms sustained
- [ ] Drawdown <-1%
- [ ] Signal quality 3+/4 confluence

### Canary Phase 2 ✅
- [ ] ≤2 non-critical warnings
- [ ] Latency <500ms sustained
- [ ] Drawdown <-2%
- [ ] Fill rate >95% all pairs

### Canary Phase 3 ✅
- [ ] All pairs operational
- [ ] Circuit breaker tested & armed
- [ ] 100% logging active
- [ ] Monitoring dashboard live

### Final Sign-off ✅
- [ ] TASK-004 completion report generated
- [ ] Incident response team briefed
- [ ] Baseline metrics documented
- [ ] Git commit with tag `[DEPLOY]`

---

## 🎯 SIGNAL: GO-LIVE INICIAÇÃO

```
22 FEV 10:00 UTC: TASK-004 Go-Live Begins
    ↓
10:30 UTC: Phase 1 (10%) — 30min test
    ↓
11:00 UTC: Phase 2 (50%) — 2h extended test
    ↓
13:00 UTC: Phase 3 (100%) — Full operational
    ↓
14:00 UTC: TASK-004 Complete — Heurísticas LIVE
    ↓
Post-22 FEV: Parallel TASK-005 PPO training iniciação
```

---

## 🔗 LINKS & REFERÊNCIAS

- `execution/heuristic_signals.py` — Core signal generator
- `TASK-002_QA_TESTING_REPORT.md` — QA validation results
- `TASK-003_ALPHA_SMC_VALIDATION.md` — Alpha trader approval (pending)
- `scripts/pre_flight_canary_checks.py` — Pre-flight validation script
- `scripts/canary_monitoring.py` — Real-time monitoring
- `docs/CANARY_ROLLBACK_PROCEDURE.md` — Rollback playbook

---

**Preparado por:** Copilot Agent  
**Data Preparo:** 21 FEV 2026  
**Status:** 🔄 PRONTO PARA GO-LIVE (Aguardando TASK-003 Alpha approval)
