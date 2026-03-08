# 🔴 Issue #65 — SMC Integration QA Specification

**Sprint:** 2 | **Lead:** Arch (#6) | **Squad:** Arch + Audit (#8) + Quality (#12) + The Brain (#3)
**Deadline:** 24 FEV 10:00 ⚡ (SLA 14h) | **Bloqueador:** TASK-005 PPO
**Status:** 🟡 SQUAD KICKOFF 23 FEV 20:40 UTC | **GitHash:** 9e8dd1c

---

## 📋 Objetivo

Validar SMC signals (Order Blocks + Break of Structure) com cobertura E2E em produção:
- ✅ Volume threshold integrado com SMA(20)
- ✅ Order blocks detecção + validação força
- ✅ Edge cases (gaps, ranging, baixa liquidez)
- ✅ Core signals para TASK-005 PPO

**Critério Aceite:** 8/8 E2E testes PASS + 85%+ coverage + sign-off Arch + Audit

---

## 🎬 Timeline — 4 Fases (14h)

| Phase | Lead | Time | Output | Bloqueio |
|-------|------|------|--------|----------|
| **1: Spec Review** | Arch (#6) | 21:35–22:05 (30min) | Architecture consensus + Test matrix approval | START |
| **2: Core E2E Tests** | Quality (#12) | 22:05–01:35 (4h) | 8/8 E2E executed + logs captured + Sharpe monitoring | Phase 1 ✅ |
| **3: Edge Cases** | Quality (#12) + Brain (#3) | 01:35–05:35 (4h) | Latency optimization + 60 symbols validation + Signal quality | Phase 2 ✅ |
| **4: QA Polish** | Audit (#8) | 05:35–10:00 (4.5h) | Sign-off checklist + Docs finalization + Angel escalation if needed | Phase 3 ✅ |

---

## 📝 Phase 1: Spec Review (21:35–22:05 UTC)

**Lead:** Arch (#6) | **Audience:** Squad + The Brain (#3)

### Tasks

- [ ] **Code Review** — `indicators/smc.py` + `execution/heuristic_signals.py`
  - [ ] Validate `detect_order_blocks()` — volume threshold + SMA(20) ✅
  - [ ] Validate `_validate_smc()` — edge cases (gaps, ranging, low-liq) ✅
  - [ ] Confirm 28 unit tests passing (Issue #63 baseline)
  
- [ ] **Test Matrix Approval**
  - [ ] 8 E2E test cases documented
  - [ ] Coverage matrix: unit → integration → edge → regression
  - [ ] Acceptance criteria locked
  
- [ ] **Architecture Consensus**
  - [ ] Signal flow: Data → SMC → RiskGate → Execution
  - [ ] Sharpe monitoring hooks ready (Brain input)
  - [ ] No performance regressions vs. baseline

### Output
- ✅ Test matrix signed off
- ✅ Phase 2 ready to go (22:05 UTC)

**Escalate if:** > 15min over, escalation = Arch → Angel (#1)

---

## 🧪 Phase 2: Core E2E Tests (22:05–01:35 UTC)

**Lead:** Quality (#12) | **Support:** The Brain (#3) — Sharpe monitoring

### 8 Mandatory E2E Test Cases

| # | Test | Input | Expected | Coverage | Priority |
|---|------|-------|----------|----------|----------|
| 1 | Order Blocks Detection (60 symbols) | OHLCV 1Y | All OBs identified | indicators/ | P0 |
| 2 | Volume Threshold SMA(20) Filter | OB + volume data | OBs ≥ SMA(20) selected | indicators/ | P0 |
| 3 | Break of Structure (BoS) Validation | 3-candle pattern | BoS detected correctly | indicators/ | P0 |
| 4 | Signal Integration RiskGate | SMC pass → RiskGate | CB -3% applied to SMC | execution/ | P0 |
| 5 | Edge Case: Gap Detection | Gap in OHLCV | Signal blocked (low confidence) | edge-case | P1 |
| 6 | Edge Case: Ranging Market | Low volatility | Signal suppressed | edge-case | P1 |
| 7 | Edge Case: Low Liquidity | Volume < threshold | Signal flagged risky | edge-case | P1 |
| 8 | Latency Test (60 symbols) | Full cycle | Decision < 100ms | performance | P0 |

### Execution Checklist

- [ ] Run 8/8 tests locally → `pytest tests/test_smc_e2e_*.py -v`
- [ ] Capture logs: decision latency, signal counts, risk rejects
- [ ] Brain monitoring: Sharpe signal quality during runs
- [ ] No regressions: All 70 Sprint 1 tests still passing
- [ ] Coverage check: `pytest --cov=indicators,execution --cov-report=html` ≥ 85%

### Output Files
- ✅ `test_results_phase2_23FEV_TIMESTAMP.json` — All 8/8 PASS logs
- ✅ `sharpe_monitoring_phase2.csv` — Real-time signal quality
- ✅ `coverage_report_phase2.html` — ≥85% coverage verified

**Escalate if:** Any test FAIL → Arch (#6) + Brain (#3) root cause

---

## 🔍 Phase 3: Edge Cases + Latency (01:35–05:35 UTC)

**Lead:** Quality (#12) + The Brain (#3)

### Tasks

- [ ] **Edge Case Validation (60 symbols live)**
  - [ ] Gap detection: Verify suppression working
  - [ ] Ranging market: Confirm signal reduction > 50%
  - [ ] Low liquidity: Risk flag persists 3+ candles
  
- [ ] **Latency Profiling**
  - [ ] Core decision time: < 50ms P99
  - [ ] Full cycle (fetch → signal → risk → exec): < 100ms P99
  - [ ] No CPU spikes > 10% on Intel i7 baseline
  
- [ ] **Signal Quality Monitoring** (Brain leads)
  - [ ] Sharpe ratio prediction: ≥ 1.0 minimum
  - [ ] False positive rate < 5% vs. manual backtested
  - [ ] Win rate consistency 60%+
  
- [ ] **Documentation**
  - [ ] Edge case summary → CRITERIOS_DE_ACEITE_MVP.md
  - [ ] Latency benchmarks → performance log
  - [ ] Known limitations → KNOWN_ISSUES.md (new file if needed)

### Output Files
- ✅ `edge_cases_validation_phase3.md`
- ✅ `latency_profile_phase3.json`
- ✅ `sharpe_monitoring_phase3.csv`

**Escalate if:** Latency > 150ms → architecture review needed

---

## ✅ Phase 4: QA Polish & Sign-Off (05:35–10:00 UTC)

**Lead:** Audit (#8)

### Sign-Off Checklist

- [ ] **Test Results Consolidated**
  - [ ] 8/8 E2E tests PASS
  - [ ] 70 Sprint 1 regression tests PASS
  - [ ] Coverage ≥ 85% in indicators/ + execution/
  - [ ] No new warnings (pylint ≥ 8.0)
  
- [ ] **Documentation Completeness**
  - [ ] Phase 1–4 execution logs archived
  - [ ] Test matrix + results → CRITERIOS_DE_ACEITE_MVP.md#s2-1/s2-2
  - [ ] Edge cases documented → RUNBOOK_OPERACIONAL.md
  - [ ] SYNCHRONIZATION.md updated with [SYNC] tag
  
- [ ] **Approval Sign-Offs**
  - [ ] ✅ Arch (#6) — Architecture OK
  - [ ] ✅ Audit (#8) — QA OK
  - [ ] ✅ Quality (#12) — All tests passing
  - [ ] ✅ The Brain (#3) — Signal quality ≥ 1.0 Sharpe
  
- [ ] **Go/No-Go Decision** (Angel #1 override if critical)
  - [ ] If ALL above ✅ → **GO** → Unblock TASK-005 PPO
  - [ ] If ANY FAIL → **NO-GO** → Escalate + replan

### Output Files
- ✅ `ISSUE_65_FINAL_SIGN_OFF_24FEV_1000.md`
- ✅ `consolidated_test_report.json`
- ✅ Commits pushed + PR ready

**If delayed > 2h past 10:00:** Escalate to Angel (#1)

---

## 🚀 Desbloqueia (On Success)

✅ **TASK-005 PPO** — 96h wall-time allocation begins (24 FEV 10:00+)
✅ **Issue #64** — Telegram setup can kick-off (24 FEV ~14:00)
✅ **Issue #67** — Data Strategy dev can kick-off (24 FEV ~15:00)

---

## 📊 Success Metrics

| Métrica | Target | Verificação |
|---------|--------|------------|
| Test Pass Rate | 8/8 = 100% | CI logs |
| Code Coverage | ≥ 85% | pytest --cov report |
| Latency P99 | < 100ms | performance benchmark |
| Sharpe Prediction | ≥ 1.0 | Brain monitoring logs |
| No Regressions | 70/70 Sprint 1 PASS | full test suite |
| Documentation | 100% of phase outputs | audit checklist |
| Sign-Off Count | 4/4 personas ✅ | FINAL_SIGN_OFF.md |

---

## 🔗 Referências

- **Baseline:** Issue #63 — SMC Volume + Order Blocks (28 tests ✅)
- **Risk Context:** [docs/CRITERIOS_DE_ACEITE_MVP.md#s2-1/s2-2](CRITERIOS_DE_ACEITE_MVP.md#s2-1/s2-2)
- **Runbook:** [docs/RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md)
- **Best Practices:** [.github/copilot-instructions.md](../.github/copilot-instructions.md)
- **Board Profiles:** [prompts/board_16_members_data.json](../prompts/board_16_members_data.json)

---

**Squad Ready:** ✅ Arch + Audit + Quality + Brain + Doc Advocate
**Kickoff:** 23 FEV 20:40 UTC AGORA
**Deadline:** 24 FEV 10:00 ⚡ NO BUFFER
**Status:** 🟡 READY TO EXECUTE
