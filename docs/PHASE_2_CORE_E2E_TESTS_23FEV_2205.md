# 🧪 PHASE 2: Core E2E Tests Execution

**Date:** 23 FEV 2205 UTC (22:05-01:35 = 4h)  
**Lead:** Quality (#12)  
**Support:** Arch (#6) code review, The Brain (#3) signal quality monitoring  
**Status:** 🟡 SCHEDULED (depends on Phase 1 Go decision)

---

## 📋 Test Execution Plan (4h SLA)

### Test Suite: 8/8 E2E Tests

```python
# tests/test_issue_66_smc_e2e_integration.py

## UNIT TESTS (Target: 15-20s)

Test #1: test_smc_signal_generation_e2e
  ├─ Input: 10 symbols × 1Y data (from S2-0 cache)
  ├─ Process: indicators/smc.py → volume threshold SMA(20) + order blocks
  ├─ Output: signals list, each signal has:
  │  ├─ symbol
  │  ├─ signal_type (order_block | bos | confluent)
  │  ├─ confidence (0.0-1.0, target >0.7)
  │  ├─ strength (volume ratio)
  │  └─ timestamp
  ├─ Expected: signal_count ≥ 50 (reasonable density)
  ├─ Assert: all signals confidence > 0.7 ✅
  ├─ Duration: ~5s
  └─ Status: 🟡 TO-RUN

Test #2: test_order_executor_receives_smc_signals
  ├─ Input: Valid SMC signal from Test #1
  ├─ Process: execution/heuristic_signals.py._validate_smc()
  ├─ Output: validated signal (+order blocks confluence check)
  ├─ Expected: signal approved (passes all validations)
  ├─ Assert: heuristic_signals._validate_smc() returns True ✅
  ├─ Duration: ~5s
  └─ Status: 🟡 TO-RUN

Test #3: test_risk_gates_active_with_smc
  ├─ Input: Position in paper mode + SMC signal
  ├─ Process: Order executor + risk gates (SL -3%, CB, TSL)
  ├─ Scenario: Simulate loss -3.1% → expect CB close
  ├─ Expected: Position closed by circuit breaker
  ├─ Assert: position.status == 'CLOSED' ✅
  ├─ Assert: close_reason == 'CIRCUIT_BREAKER' ✅
  ├─ Duration: ~10s
  └─ Status: 🟡 TO-RUN

## INTEGRATION TESTS (Target: 45-60s)

Test #4: test_signal_generation_to_order_execution_e2e
  ├─ Full Flow: SMC signal gen → heuristic validation → order exec → position monitor
  ├─ Input: 10 symbols, 1Y data
  ├─ Expected: Complete flow completes within latency SLA
  ├─ Timing Checkpoints:
  │  ├─ signal_gen start: T0
  │  ├─ signal_gen end: T0 + 50ms (target)
  │  ├─ heuristic validation: T0 + 100ms (target)
  │  ├─ order exec: T0 + 150ms (target)
  │  └─ position monitor: T0 + 250ms (target)
  ├─ Assert: latency < 250ms ✅
  ├─ Duration: ~15s (per signal × 5-10 signals)
  └─ Status: 🟡 TO-RUN

Test #5: test_edge_cases_gaps_ranging_lowliq
  ├─ Scenario A: Gap detection
  │  ├─ Input: OHLCV with overnight gap
  │  ├─ Expected: Gap detected, signal filtered
  │  └─ Assert: gap_signal rejected ✅
  ├─ Scenario B: Ranging market
  │  ├─ Input: range > 50% in last 1h
  │  ├─ Expected: Ranging identified, signal marked uncertain
  │  └─ Assert: ranging_confidence < 0.5 ✅
  ├─ Scenario C: Low liquidity
  │  ├─ Input: volume < 10 BTC
  │  ├─ Expected: Low-liq signal handled safely
  │  └─ Assert: low_liq_signal rejected ✅
  ├─ Duration: ~20s (3 scenarios × ~7s each)
  └─ Status: 🟡 TO-RUN

Test #6: test_latency_profile_98p
  ├─ Process: Run 100+ signal cycles, measure latency
  ├─ Metric: Calculate 98th percentile latency
  ├─ Expected: latency_98p < 250ms
  ├─ Output: {"mean": XXXms, "p50": XXXms, "p95": XXXms, "p98": XXXms}
  ├─ Assert: latency_98p < 250ms ✅
  ├─ Duration: ~20s (100 cycles × 0.2s overhead)
  └─ Status: 🟡 TO-RUN

## EDGE CASE + REGRESSION TESTS (Target: 30-45s)

Test #7: test_regression_sprint1_70_tests
  ├─ Command: `pytest tests/ -v --tb=short` (all Sprint 1 tests)
  ├─ Expected: ALL 70 tests PASS (0 failures)
  ├─ Timeout: 60s (conservative)
  ├─ Assert: test_count == 70, failures == 0 ✅
  ├─ Duration: ~45s
  └─ Status: 🟡 TO-RUN

Test #8: test_regression_s24_50_tests
  ├─ Command: `pytest tests/test_s2_4*.py -v` (S2-4 TSL tests)
  ├─ Expected: ALL 50+ tests PASS
  ├─ Timeout: 60s
  ├─ Assert: test_count >= 50, failures == 0 ✅
  ├─ Duration: ~30s
  └─ Status: 🟡 TO-RUN
```

---

## ⏱️ Execution Timeline (4h = 240min)

```
22:05 — PHASE 2 KICKOFF
│
├─ 22:05-22:15 (10min): Setup + fixtures load
│  ├─ Load test data (10 symbols × 1Y)
│  ├─ Initialize test fixtures
│  └─ Start CI/CD pipeline logging
│
├─ 22:15-22:35 (20min): UNIT TESTS (1-3)
│  ├─ Test #1 (SMC signal gen): 5min
│  ├─ Test #2 (Executor signal receive): 5min
│  ├─ Test #3 (Risk gates): 10min
│  └─ Result: ✅ 3/3 PASS (target)
│
├─ 22:35-23:35 (60min): INTEGRATION TESTS (4-6)
│  ├─ Test #4 (E2E signal→exec): 15min
│  ├─ Test #5 (Edge cases): 20min
│  ├─ Test #6 (Latency profile): 20min
│  └─ Result: ✅ 3/3 PASS (target)
│
├─ 23:35-00:10 (35min): REGRESSION TESTS (7-8)
│  ├─ Test #7 (Sprint 1 regression): 45min BUT PARALLEL
│  ├─ Test #8 (S2-4 regression): 30min BUT PARALLEL
│  └─ Result: ✅ 70+ PASS + 50+ PASS
│
├─ 00:10-01:20 (70min): COVERAGE REPORT + BUFFER
│  ├─ Generate coverage report: `pytest --cov=execution`
│  ├─ Target: ≥85% coverage (execution/heuristic_signals.py)
│  ├─ Contingency buffer for failures
│  └─ Re-run any failed tests
│
└─ 01:35: PHASE 2 COMPLETE
    └─ Phase 2 Summary: 8/8 PASS? Yes/No? Coverage ≥85%?
        └─ Go/No-Go Phase 3 decision
```

---

## 📊 Phase 2 Monitoring

### Real-Time Dashboard (to update every 15min)

```
Phase 2 Progress: ⏳ IN PROGRESS

Unit Tests (1-3):
  [ ] Test #1 (signal gen): ⏳ RUNNING
  [ ] Test #2 (exec receive): ⏳ QUEUED
  [ ] Test #3 (risk gates): ⏳ QUEUED
  Status: 0/3 PASS

Integration Tests (4-6):
  [ ] Test #4 (E2E flow): ⏳ QUEUED
  [ ] Test #5 (edge cases): ⏳ QUEUED
  [ ] Test #6 (latency): ⏳ QUEUED
  Status: 0/3 PASS

Regression Tests (7-8):
  [ ] Test #7 (Sprint 1): ⏳ QUEUED (runs parallel)
  [ ] Test #8 (S2-4): ⏳ QUEUED (runs parallel)
  Status: 0/2 PASS

Coverage:
  [ ] Pending (after Phase 2 complete)
  Target: ≥85%

Blockers:
  [ ] None identified
  
Latency Budget Used:
  [ ] Signal gen: TBD (target 50ms)
  [ ] Heuristic: TBD (target 50ms)
  [ ] Executor: TBD (target 100ms)
  [ ] Monitor: TBD (target 50ms)
  [ ] Total: TBD (target <250ms)
```

---

## 🔴 Failure Scenarios & Recovery

### If Test #1 Fails (SMC signal gen)

**Issue:** Signal generation not producing expected signals  
**Recovery:**
```
1. Check test data: Verify 10 symbols loaded from S2-0 cache ✅
2. Debug Issue #63: Review indicators/smc.py volume_threshold logic
3. Check thresholds: Confirm SMA(20) calculated correctly
4. Re-run with DEBUG logging enabled
5. If still fails: Escalate to Arch (#6) for code review
   → Max 15min debug time, then pivot to Phase 3 (edge cases)
```

### If Test #4 Fails (E2E latency)

**Issue:** Latency > 250ms (98p)  
**Recovery:**
```
1. Profile each stage: signal_gen | heuristic | executor | monitor
2. Identify bottleneck (likely: signal_gen or executor)
3. If signal_gen: Check IO bottleneck (cache hit?)
4. If executor: Check Risk Gate evaluation (unnecessary loops?)
5. Optimization options:
   a) Cython compilation for hot paths
   b) Parallel signal generation (if safe)
   c) Caching optimization
6. Re-run latency profile
7. If still > 250ms at 98p: Escalate, document trade-off
   → PPO may need real-time signal buffer (acceptable risk)
```

### If Regression Tests Fail (#7 or #8)

**Issue:** Sprint 1 or S2-4 tests broken by Issue #66 changes  
**Recovery:**
```
1. Identify which test broke: Sprint 1 (70 tests) or S2-4 (50 tests)
2. Isolate failure: Which module changed?
   - execution/heuristic_signals.py? (likely)
   - execution/order_executor.py? (possible)
   - risk/circuit_breaker.py? (less likely)
3. Revert problematic change (if introduced in Phase 2)
4. OR: Fix root cause (if Issue #63 integration issue)
5. Re-run regression suite
6. Max 20min debug time, else escalate to Arch (#6)
```

---

## 📞 Escalation Matrix

| Issue | Severity | Owner | Max Resolution Time |
|-------|----------|-------|---------------------|
| Test #1-3 failure | 🔴 CRITICAL | Arch (#6) | 15min |
| Latency > 250ms (98p) | 🟠 HIGH | Arch (#6) | 30min |
| Regression fail (Sprint 1) | 🔴 CRITICAL | Arch (#6) + Quality (#12) | 20min |
| Coverage < 80% | 🟡 MEDIUM | Quality (#12) | Accept &continue |
| Any test timeout (>30s) | 🟠 HIGH | Quality (#12) + Arch (#6) | 15min debug |

---

## ✅ Phase 2 Success Criteria

**All Must-Have (GO to Phase 3):**
- ✅ Tests #1-3: 3/3 PASS
- ✅ Tests #4-6: 3/3 PASS (or latency documented)
- ✅ Tests #7-8: 70+ PASS + 50+ PASS
- ✅ Coverage: ≥80% (target 85%)
- ✅ 0 CRITICAL blockers unresolved

**Go/No-Go Phase 3 Decision:** Arch (#6) + Audit (#8)

---

## 📌 Phase 2 → Phase 3 Handoff (01:35 UTC)

**Phase 3 Readiness:**
- [ ] All 8/8 core tests PASS ✅
- [ ] Latency profiled ✅
- [ ] Regression baseline established ✅
- [ ] Coverage report ready ✅
- [ ] Blockers resolved ✅

**Phase 3 Kick-Off (01:35 UTC):**
```
Phase 3 Scope: Edge cases + latency optimization
  ├─ 60 symbols (vs 10 in Phase 2)
  ├─ Stress testing: gaps, ranging, low-liq extreme cases
  ├─ Latency optimization if needed
  └─ Performance baseline validation
```

**Checkpoint: 05:30 UTC (after Phase 3)**
- Phase 3 Go/No-Go Phase 4 decision

---

**Phase 2 Status:** 🟡 SCHEDULED (23 FEV 22:05-01:35)  
**Lead:** Quality (#12)  
**Support:** Arch (#6), The Brain (#3)
