# 🚀 Gate 3 Execution Plan — S2-3 Backtesting Engine Validation

**Início:** 22 FEV 23:45 UTC
**Deadline:** 24 FEV 08:00 UTC (32h wall-time)
**Critical Path:** Performance + Coverage + Regression
**Squad:** Arch (#6), Quality (#12), Audit (#8), Data (#11), The Blueprint (#7)

---

## 🎯 Gate 3 Critérios (CRITERIOS_DE_ACEITE_MVP.md)

| Critério | Target | Status | Owner |
|----------|--------|--------|-------|
| 8 testes PASS | `pytest backtest/test_*.py` | ⏳ | Quality (#12) |
| Cobertura ≥ 80% | `pytest --cov=backtest` | ⏳ | Quality (#12) |
| **Cobertura ≥ 85%** | Coverage improvement | ⏳ | Quality (#12) |
| Zero regressions S1 | 70 testes Sprint 1 PASS | ⏳ | Audit (#8) |
| Risk Gate -3% Hard | Simular loss -3.1% | ⏳ | Arch (#6) |
| Performance < 30s | 6M × 60 = 360 days backtest | ⏳ | The Blueprint (#7) |

---

## 📋 Tarefas Paralelas (Sprint 4-6h)

### **Persona 1: Quality (#12) — Coverage Scanning & Test Suite**
**Tempo:** 4-5h | **Deadline:** 24 FEV 03:00 UTC

- [ ] **T1.1** Rodas `pytest --cov=backtest --cov-report=html`
  - Gerar relatório de cobertura
  - Identificar gaps (< 80% linhas)
  - Listar arquivos críticos não cobertos
  
- [ ] **T1.2** Analisar code_coverage_2_backtest.html
  - Files com cobertura < 70%:
    - [ ] backtest/core/backtest_engine.py
    - [ ] backtest/data/loader.py
    - [ ] backtest/validation/trade_validator.py
  - Criar checklist de testes adicionais
  
- [ ] **T1.3** Implementar missing tests (alvo +5% coverage)
  - Target: 80% → 85%
  - Focus: Edge cases em RiskGate, trade execution
  - Archivos: backtest/test_coverage_gap.py (novo)
  
- [ ] **T1.4** Validar 8/8 testes PASS
  - [ ] `pytest backtest/test_metrics.py -v` → 28/28 PASS ✅ (já feito)
  - [ ] `pytest backtest/test_backtest_core.py -v` → Precisar criar/rodar
  - [ ] `pytest backtest/test_*.py -v` → Suite completa
  - Commit: `[FEAT] Test coverage increase 82% → 85%`

---

### **Persona 2: Arch (#6) — Performance Test & Risk Gate Validation**
**Tempo:** 3-4h | **Deadline:** 24 FEV 04:00 UTC

- [ ] **T2.1** Criar performance benchmark
  - Script: backtest/benchmark/perf_test.py
  - Inputs: 6 meses (≈180 dias), 60 símbolos
  - Medição: tempo total, memória usada
  - Target: < 30 segundos
  
- [ ] **T2.2** Executar benchmark
  - Log: backtest/logs/performance_benchmark_22FEV.txt
  - Registrar: Start time, End time, Duration, Memory peak
  - Passar/Falhar: True if duration < 30s
  
- [ ] **T2.3** Validar Risk Gate -3% Hard Stop
  - Test: backtest/test_risk_gate_validation.py
  - Simulação: Trade LONG entrada 45000, cai para 43605 (-3.1%)
  - Validar: Engine fecha posição automaticamente
  - Evidence: Log de close order + trade.status == 'STOPPED_BY_RISKGATE'
  
- [ ] **T2.4** Regression: Validar compliance RiskGate
  - Verificar que nenhum trade fica aberto com loss > -3%
  - Query: `SELECT COUNT(*) FROM trades WHERE loss > -0.03` → 0
  - Commit: `[FEAT] Performance < 30s validated, RiskGate -3% enforced`

---

### **Persona 3: Audit (#8) — Regression Testing + Sign-Off**
**Tempo:** 3-4h | **Deadline:** 24 FEV 05:00 UTC

- [ ] **T3.1** Validar Sprint 1 Backward Compatibility
  - Rodar suite Sprint 1: 70 testes
  - [ ] `pytest tests/ -v --tb=short` → 70/70 PASS
  - Certificar: Zero quebras em modules S1 (data, risk, execution)
  
- [ ] **T3.2** Criar Regression Test Suite (S2-3)
  - File: backtest/test_regression_s2_3.py
  - Cobertura:
    - [ ] Backtest data loading não corrompe cache
    - [ ] Metrics não divergem de manual calcs
    - [ ] Trade history serializable (pickle/JSON)
    - [ ] RiskGate não interfere com estratégia
    - [ ] Performance degrada < 5% com dados 2x maiores
  
- [ ] **T3.3** Execute regression suite
  - `pytest backtest/test_regression_s2_3.py -v`
  - Objetivo: 100% PASS (5 testes)
  
- [ ] **T3.4** Sign-off Gate 3
  - [ ] All 70 S1 tests PASS? **✅**
  - [ ] 8 S2-3 tests PASS? **✅**
  - [ ] Coverage ≥ 80%? **✅**
  - [ ] Performance < 30s? **✅**
  - [ ] Risk Gate enforced? **✅**
  - **Sign:** Audit (#8) — APPROVED for Gate 4
  - Commit: `[SYNC] Gate 3 Regression Complete — Zero Breaking Changes`

---

### **Persona 4: Data (#11) — Data Integrity Validation (Paralelo)**
**Tempo:** 2-3h | **Deadline:** 24 FEV 03:30 UTC

- [ ] **T4.1** Validar S2-0 Data Gates (se não completo)
  - Gate 1: 60 símbolos carregados, sem gaps
  - `klines_cache_manager.py validate-all`
  
- [ ] **T4.2** Cache Parquet Performance
  - Validar: `backtest/cache/*.parquet` load < 100ms
  - Script: backtest/scripts/cache_performance_check.py
  - Evidence: backtest/logs/cache_perf_22FEV.txt
  
- [ ] **T4.3** Dados Históricos Completeness
  - Validar: 60 símbolos, mínimo 6 meses (180 dias)
  - Query: `SELECT MIN(timestamp), COUNT(DISTINCT date)` per symbol
  - Report: backtest/logs/data_completeness_22FEV.txt

---

### **Persona 5: The Blueprint (#7) — Infrastructure (Standby)**
**Tempo:** 1-2h | **Deadline:** 24 FEV 06:00 UTC

- [ ] **T5.1** Monitoring & Alerting Readiness
  - Validar que backtest/logs são centralizados
  - Setup: Log aggregation (preparar para Go-Live)
  - Script: monitoring/backtest_health_probe.py
  
- [ ] **T5.2** DB Recovery Procedure
  - Validar que backtest cache pode ser recuperado
  - Test: db_recovery.py —backtest
  - Evidence: Recovery < 5min

---

## 📊 Dependências & Timeline

```
T1.1-1.2 (Coverage Analysis) ═══════════════════
  ↓ (Informa T1.3)
T1.3-1.4 (Test Implementation) ═════════════════
  ↓
  ├─ T2.1-2.4 (Performance + RiskGate) ════════
  ├─ T3.1-3.2 (Regression Tests) ═════════════
  └─ T4.1-4.3 (Data Validation) ══════════════
    ↓
T3.3-3.4 (Final Sign-Off) ══════════════════════
```

**Critical Path:** T1.3 → T1.4 → T3.4 = ~6h
**Paralelo:** T2 + T3 (+ T4) = -2h (savings)
**Buffer:** 2-3h para troubleshooting

---

## ✅ Exit Criteria (Gate 3 Complete)

- [x] 28 testes metrics PASS (já completo)
- [ ] 8 testes core/engine PASS (T1.4)
- [ ] Coverage ≥ 85% (T1.3)
- [ ] 70 Sprint 1 testes PASS (T3.1)
- [ ] Performance < 30s (T2.2)
- [ ] Risk Gate -3% validated (T2.3)
- [ ] Zero regressions (T3.2-3.3)
- [ ] All owners sign-off (T3.4)

---

## 🎯 Next (Gate 4 — Documentation)

Após Gate 3 ✅:
- [ ] backtest/README.md (500+ words)
- [ ] DECISIONS.md § S2-3 trade-offs
- [ ] Docstrings 100% complete
- [ ] Final sync to STATUS_ENTREGAS.md

**Target:** Gate 4 complete 24 FEV 18:00 UTC
**Go-Live Liberado:** 25 FEV 10:00 UTC (TASK-005 kickoff)

