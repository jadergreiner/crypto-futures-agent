# 📦 S2-3 Deliverable Specification — Backtesting Engine

**Versão:** 1.0.0  
**Sprint:** Sprint 2-3  
**Owner:** Audit (#8) + Doc Advocate (#17)  
**Data:** 2026-02-22  
**Ref:** [ARCH_S2_3_BACKTESTING.md](ARCH_S2_3_BACKTESTING.md) | [CRITERIOS_DE_ACEITE_MVP.md](CRITERIOS_DE_ACEITE_MVP.md#s2-3)

---

## 📋 Checklist de Entrega (13 Itens)

### Gate 1: Dados Históricos ✅

Responsável: **Data (#11)**  
Validador: **Audit (#8)**

- [ ] **1.1** Dados OHLCV carregados para 60 símbolos via `DataProvider.fetch_ohlcv()`
- [ ] **1.2** Sem gaps, duplicatas, preços válidos (via S2-0 validation)
- [ ] **1.3** Parquet cache funciona (leitura < 100ms)
- [ ] **1.4** Mínimo 6 meses de dados por símbolo
- [ ] **1.5** Testes de integração S2-0 ↔ S2-3 PASS (`test_data_provider.py` #1)

---

### Gate 2: Engine de Backtesting ✅

Responsável: **Arch (#6)**  
Validador: **Quality (#12)**

- [ ] **2.1** `BacktestEngine` executa trade sem erro
  - Arquivo: `backtest/core/backtest_engine.py`
  - Método: `BacktestEngine.backtest()`
  - Tipo: Orquestrador de execução

- [ ] **2.2** PnL realized + unrealized correto
  - Arquivo: `backtest/core/metrics.py`
  - Método: `BacktestMetrics.compute_pnl()`
  - Validação: vs. manual calculation

- [ ] **2.3** Max Drawdown calculado corretamente
  - Arquivo: `backtest/core/metrics.py`
  - Método: `BacktestMetrics.compute_drawdown()`
  - Teste: `test_metrics.py` (#2)

- [ ] **2.4** Risk Gate 1.0 aplicado (-3% hard stop)
  - Arquivo: `backtest/core/backtest_engine.py`
  - Método: `BacktestEngine._apply_risk_gate()`
  - Teste: Simular posição -3.1% → Ordem close

- [ ] **2.5** Walk-Forward testing suportado
  - Arquivo: `backtest/validation/walk_forward.py`
  - Classe: `WalkForwardValidator`
  - Padrão: 180d train / 30d test (15 windows)
  - Teste: `test_walk_forward.py` (#5)

---

### Gate 3: Validação & Testes ✅

Responsável: **Quality (#12)**  
Validador: **Audit (#8)**

- [ ] **3.1** 8 testes PASS (unit + integration + e2e)
  - `test_backtest_core.py`: 3 testes (engine, trade exec, risk gate)
  - `test_metrics.py`: 2 testes (PnL, drawdown)
  - `test_data_provider.py`: 1 teste (S2-0 integração)
  - `test_walk_forward.py`: 2 testes (validation, generalization)
  - Comando: `pytest backtest/tests/ -v`
  - Esperado: `8 passed`

- [ ] **3.2** Cobertura ≥ 80% em `backtest/`
  - Comando: `pytest --cov=backtest --cov-report=html backtest/tests/`
  - Arquivo: `htmlcov/index.html`
  - Esperado: Lines: 80%+

- [ ] **3.3** Nenhuma regressão em Sprint 1 (70 testes)
  - Comando: `pytest tests/ -v`
  - Esperado: `70 passed`

- [ ] **3.4** Performance: 6 meses × 60 símbolos < 30s
  - Teste: E2E backtest completo 180 dias
  - Log: `backtest/logs/backtest_results.json`
  - Métrica: `execution_time_seconds < 30`

---

### Gate 4: Documentação ✅

Responsável: **Audit (#8) + Doc Advocate (#17)**  
Validador: **Angel (#1)**

- [ ] **4.1** Docstrings em classes/funções (100%, PT)
  - Arquivos: `backtest/core/*.py`, `backtest/data/*.py`, etc.
  - Padrão: Google-style (Args, Returns, Raises)
  - Validação: `pylint backtest/ --disable=all --enable=missing-docstring`
  - Esperado: 0 warnings

- [ ] **4.2** `backtest/README.md` com guia de uso
  - Comprimento: ≥ 500 palavras
  - Seções: Overview, Quick Start, API Reference, Examples, Troubleshooting
  - Link: [backtest/README.md](../backtest/README.md)

- [ ] **4.3** `CRITERIOS_DE_ACEITE_MVP.md` atualizado com S2-3
  - Seção: [§ S2-3](CRITERIOS_DE_ACEITE_MVP.md#s2-3)
  - 4 Gates completos + matriz de critérios
  - Status: ✅ Completo (este arquivo)

- [ ] **4.4** Trade-offs críticos em `DECISIONS.md`
  - Entrada S2-3: "Walk-Forward 180d/30d rationale"
  - Entrada S2-3: "Parquet vs. PostgreSQL para S2-3"
  - Entrada S2-3: "Slippage 2-ticks assumption"
  - Ref: [DECISIONS.md](DECISIONS.md) § S2-3

- [ ] **4.5** Código comentado (trade_state, walk_fwd)
  - Arquivos: `backtest/core/trade_state.py`, `backtest/validation/walk_forward.py`
  - Padrão: Comments em PT explicando lógica crítica
  - Review: Code review inline comments ✓

---

## 📊 Pré-vôo Checklist (Pre-Flight)

### Antes de Commit (4h antes)

- [ ] **Integração com S2-0:** Testar `DataProvider` com cache S2-0 real
- [ ] **Compatibilidade RiskGate:** -3% hard stop ativando corretamente
- [ ] **Performance baseline:** Backtest 6M em < 30s (no hots pots)
- [ ] **Lint + Format:** `black`, `pylint`, `mypy` zero warnings

### Antes de Push (1h antes)

- [ ] **Testes 100%:** `pytest backtest/ -v` = 8 PASS
- [ ] **Cobertura:** `pytest --cov=backtest backtest/` = ≥80%
- [ ] **Regressão Sprint 1:** `pytest tests/ -v` = 70 PASS
- [ ] **Docs build:** Markdown lint backtest/README.md (≤80 chars/linha)

### Quorum de Aprovação (Antes de Merge)

| Função | Pessoa | Sign-Off | Prazo |
|--------|--------|----------|-------|
| Tech Lead | Arch (#6) | ✓ Código-ok? | 20:00 UTC |
| QA | Audit (#8) | ✓ Tests-ok? | 20:00 UTC |
| Exec | Angel (#1) | ✓ Aprova merge? | 21:00 UTC |

---

## 📈 Critério de Sucesso (Definition of Done)

### Implementação

✅ **Todos os 4 Gates com novos arquivos:**

```
backtest/
├── core/
│   ├── backtest_engine.py      ← Gate 2.1 + 2.4 + 2.5
│   ├── trade_state.py          ← Gate 2.1 trade state
│   └── metrics.py              ← Gate 2.2 + 2.3
├── data/
│   ├── data_provider.py        ← Gate 1 interface
│   └── cache_reader.py         ← Gate 1.3 Parquet reader
├── strategies/
│   ├── smc_strategy.py         ← Sinais SMC (sketch)
│   └── signal_factory.py
├── validation/
│   └── walk_forward.py         ← Gate 2.5 walk-forward
├── tests/
│   ├── conftest.py             ← Fixtures
│   ├── test_backtest_core.py   ← 3 unit tests
│   ├── test_metrics.py         ← 2 unit tests
│   ├── test_data_provider.py   ← 1 integration
│   └── test_walk_forward.py    ← 2 validation tests
└── logs/
    └── backtest_results.json   ← Exemplos output
```

### Validação

✅ **Testes:** 8/8 PASS  
✅ **Cobertura:** ≥80%  
✅ **Regressão:** 70 Sprint 1 tests PASS  
✅ **Performance:** < 30s para 6M × 60 símbolos

### Documentação

✅ **Docstrings:** 100% classes e funções (PT)  
✅ **README.md:** 500+ palavras, guia completo  
✅ **CRITERIOS_DE_ACEITE_MVP.md § S2-3:** Atualizado  
✅ **DECISIONS.md § S2-3:** Trade-offs justificados  
✅ **ARCH_S2_3_BACKTESTING.md:** Design + 4 Gates

---

## 🚛 Deliverables Paralelos (Squads Independentes)

| Squad | Entrega | Owner | Status | Prazo |
|-------|---------|-------|--------|-------|
| **Arch** | ARCH_S2_3_BACKTESTING.md + dirs | #6 | 🔄 | 22 FEV 16:00 |
| **Data** | data_provider.py interface | #11 | ⏳ | 22 FEV 18:00 |
| **Quality** | fixtures.py + test suite | #12 | ⏳ | 22 FEV 18:00 |
| **Audit** | TEST_PLAN_S2_3.md + checklist | #8 | ⏳ | 22 FEV 18:00 |
| **Doc Advocate** | STATUS_ENTREGAS.md sync | #17 | ⏳ | 22 FEV 19:00 |
| **The Brain** | smc_strategy.py sketch | #3 | ⏳ | 22 FEV 19:00 |

---

## 🎯 Go/No-Go Decision

**Critério GO:** Todos os 13 checkboxes (Gate 1-4) = ✅

- [ ] Gate 1 (Dados): 5/5 ✅
- [ ] Gate 2 (Engine): 5/5 ✅
- [ ] Gate 3 (Testes): 4/4 ✅
- [ ] Gate 4 (Docs): 5/5 ✅

**Quando GO:** 
- → Desbloqueia **S2-1/S2-2** (SMC Strategy live)
- → Libera **TASK-005** (ML PPO training)

**Quando NO-GO:**
- → Ativa retorno ao squad de origem (Arch, Data, Quality)
- → Re-plan: próximo kickoff 25 FEV 09:00 UTC

---

**Owner:** Audit (#8) + Doc Advocate (#17)  
**Revisor:** Angel (#1)  
**Próximo:** Merge em main + tag v0.1.0 RC1  
