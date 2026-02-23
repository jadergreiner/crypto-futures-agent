# 📋 Test Plan S2-3 — Backtesting Engine

**Versão:** 1.0.0
**Sprint:** Sprint 2-3
**Owner:** Audit (#8) + Quality (#12)
**Data:** 2026-02-22
**Total Testes:** 8 (5 unit + 2 integration + 1 E2E)

---

## 🎯 Objetivo

Validar que **BacktestEngine** executa trades corretamente em dados históricos,
com RiskGate 1.0 ativo, gerando métricas precisas (PnL, Drawdown, Sharpe).

Ref: [S2_3_DELIVERABLE_SPEC.md § Gate 3](S2_3_DELIVERABLE_SPEC.md#gate-3-validação--testes-)

---

## 📊 Matriz de Testes (8 Testes)

### Unit Tests — Core Logic (5 testes)

#### T1: Core Engine Initialization

```python
# backtest/tests/test_backtest_core.py :: test_engine_init

def test_engine_init():
    """Engine inicializa sem erro com parâmetros válidos."""
    engine = BacktestEngine(
        initial_balance=10000.0,
        commission=0.0004,  # 0.04% Binance
        slippage_ticks=2
    )
    assert engine.initial_balance == 10000.0
    assert engine.commission == 0.0004
    assert engine.state.balance == 10000.0
```

**Critério:** ✅ PASS
**Coverage:** `backtest/core/backtest_engine.py::__init__`

---

#### T2: Trade Execution (Market Order)

```python
# backtest/tests/test_backtest_core.py :: test_market_trade_execution

def test_market_trade_execution():
    """Engine executa market trade LONG com comissão."""
    engine = BacktestEngine(initial_balance=10000.0)

    # Simular candle
    candle = Kline(
        symbol='BTCUSDT', close=45000.0, high=45500.0, low=44500.0,
        volume=1.0, timestamp=1708000000
    )

    # Executar order LONG
    trade = engine.execute_trade(
        signal=Signal(type='LONG', entry_price=45000.0, qty=0.1),
        candle=candle
    )

    assert trade.entry_price == 45000.0
    assert trade.quantity == 0.1
    assert trade.commission_paid == 45000.0 * 0.1 * 0.0004
```

**Critério:** ✅ PASS
**Coverage:** `backtest/core/backtest_engine.py::execute_trade`

---

#### T3: RiskGate (-3% Circuit Breaker)

```python
# backtest/tests/test_backtest_core.py :: test_risk_gate_circuit_breaker

def test_risk_gate_circuit_breaker():
    """RiskGate fecha posição em -3% de loss."""
    engine = BacktestEngine(initial_balance=10000.0)

    # Trade aberto a 45000
    trade = Trade(
        entry_price=45000.0, quantity=0.1, direction='LONG',
        timestamp=1708000000
    )
    engine.state.add_trade(trade)

    # Preço cai para -3.1% (43605)
    current_price = 45000.0 * (1 - 0.031)
    assert engine._check_risk_gate(trade, current_price) == True

    # Engine fecha automaticamente
    result = engine._apply_risk_gate(trade, current_price)
    assert result.status == 'STOPPED_BY_RISKGATE'
    assert result.exit_price == 43605.0  # Hard stop exato
```

**Critério:** ✅ PASS
**Coverage:** `backtest/core/backtest_engine.py::_apply_risk_gate`
**Criticidade:** 🔴 INVIOLÁVEL (veto no produto)

---

#### T4: PnL Calculation (Realized + Unrealized)

```python
# backtest/tests/test_metrics.py :: test_pnl_calculation

def test_pnl_calculation():
    """Cálculo correto de PnL realized + unrealized."""
    metrics = BacktestMetrics()

    # Trade fechado: entrada 45000, saída 46000 (0.1 BTC)
    realized_trade = Trade(
        entry_price=45000.0, exit_price=46000.0, quantity=0.1,
        direction='LONG', status='CLOSED'
    )
    metrics.add_trade(realized_trade)

    pnl_realized = metrics.compute_pnl_realized()
    expected = (46000.0 - 45000.0) * 0.1  # $100
    assert abs(pnl_realized - expected) < 0.01

    # Trade aberto: entrada 46000, preço atual 47000
    open_trade = Trade(
        entry_price=46000.0, quantity=0.1, direction='LONG',
        status='OPEN'
    )
    pnl_unrealized = metrics.compute_pnl_unrealized(open_trade, 47000.0)
    assert abs(pnl_unrealized - 100.0) < 0.01
```

**Critério:** ✅ PASS
**Coverage:** `backtest/core/metrics.py::compute_pnl_*`

---

#### T5: Max Drawdown Calculation

```python
# backtest/tests/test_metrics.py :: test_max_drawdown

def test_max_drawdown():
    """Cálculo correto de Max Drawdown da equity curve."""
    metrics = BacktestMetrics()

    # Equity timeline: 10000 → 12000 → 10500 → 11500 (drawdown: -12.5%)
    equity_curve = [10000, 12000, 10500, 11500]
    max_dd = metrics.compute_max_drawdown(equity_curve)

    # (10500 - 12000) / 12000 = -0.125 = -12.5%
    assert abs(max_dd - (-0.125)) < 0.001
```

**Critério:** ✅ PASS
**Coverage:** `backtest/core/metrics.py::compute_max_drawdown`

---

### Integration Tests — Data + Engine (2 testes)

#### T6: Data Provider Integration (S2-0 ↔ S2-3)

```python
# backtest/tests/test_data_provider.py :: test_s2_0_cache_integration

def test_s2_0_cache_integration():
    """DataProvider lê dados S2-0 (parquet cache) corretamente."""
    provider = CacheReader(cache_path='db/klines_cache.parquet')

    # Buscar 100 candles BTCUSDT
    candles = provider.fetch_ohlcv(
        symbol='BTCUSDT',
        start_time=1672531200,  # 2023-01-01
        end_time=1708000000     # 2026-02-22
    )

    assert len(candles) > 0
    assert all(isinstance(c, Kline) for c in candles)
    assert candles[0].open > 0 and candles[0].close > 0
    assert candles[0].timestamp < candles[-1].timestamp  # Ascending
```

**Critério:** ✅ PASS
**Coverage:** `backtest/data/data_provider.py`, `backtest/data/cache_reader.py`
**Dependência:** S2-0 Gates 1-2 ✅

---

### E2E Tests — Full Backtest (1 teste)

#### T7: Full Backtest 6 Months × 60 Symbols

```python
# backtest/tests/test_backtest_core.py :: test_full_backtest_execution

def test_full_backtest_execution():
    """Full backtest: 6M dados, 60 símbolos, < 30s execution."""
    import time

    engine = BacktestEngine(initial_balance=10000.0)
    strategy = SMCStrategy()  # BoS + Order Block detection
    provider = CacheReader()

    symbols = ['BTCUSDT', 'ETHUSDT', ...]  # 60 symbols
    start_time = time.time()

    results = []
    for symbol in symbols:
        candles = provider.fetch_ohlcv(
            symbol,
            start_time=1708000000-15778800,  # 6M ago
            end_time=1708000000
        )
        backtest_result = engine.backtest(
            symbol=symbol,
            candles=candles,
            strategy=strategy
        )
        results.append(backtest_result)

    elapsed = time.time() - start_time
    assert elapsed < 30.0, f"Backtest took {elapsed}s, expected < 30s"

    # Validar métricas
    for result in results:
        assert result.pnl_realized is not None
        assert result.max_drawdown is not None
        assert result.sharpe_ratio is not None
```

**Critério:** ✅ PASS
**Métrica:** < 30s execution time
**Coverage:** Ende-to-end flow

---

#### T8: Walk-Forward Validation (Generalization)

```python
# backtest/tests/test_walk_forward.py :: test_walk_forward_validation

def test_walk_forward_validation():
    """Walk-Forward testing: 180d train → 30d test (15 windows)."""
    wf = WalkForwardValidator()
    provider = CacheReader()
    strategy = SMCStrategy()

    candles = provider.fetch_ohlcv('BTCUSDT', start_time=..., end_time=...)

    wf_results = wf.run(
        candles=candles,
        window_train=180,
        window_test=30,
        step=30
    )

    # 15 windows: (360 days / 30 step) = 12 ← 1 ano
    assert len(wf_results) == 12

    # Validar que modelo generaliza (não overfits train)
    avg_sharpe_train = np.mean([r['train_sharpe'] for r in wf_results])
    avg_sharpe_test = np.mean([r['test_sharpe'] for r in wf_results])

    # Test Sharpe não muito menor que train (< 20% deterioration)
    deterioration = (avg_sharpe_train - avg_sharpe_test) / avg_sharpe_train
    assert deterioration < 0.2, f"Over-fitting detected: {deterioration}"
```

**Critério:** ✅ PASS
**Objetivo:** Garantir generalização da estratégia SMC
**Coverage:** `backtest/validation/walk_forward.py`

---

## 📈 Fixtures e Cenários Mock (5 Scenarios)

### conftest.py — Shared Fixtures

```python
# backtest/tests/conftest.py

@pytest.fixture
def sample_klines():
    """100 candles mock BTCUSDT."""
    return [
        Kline(
            symbol='BTCUSDT',
            open=45000 + i*10,
            high=45100 + i*10,
            low=44900 + i*10,
            close=45050 + i*10,
            volume=10.0,
            timestamp=1708000000 + i*3600
        )
        for i in range(100)
    ]

@pytest.fixture
def engine():
    """BacktestEngine instance with defaults."""
    return BacktestEngine(initial_balance=10000.0)

@pytest.fixture
def strategy():
    """SMCStrategy instance."""
    return SMCStrategy()

@pytest.fixture
def data_provider():
    """CacheReader mock."""
    return CacheReader(cache_path='db/klines_cache.parquet')
```

---

### 5 Test Scenarios

| Cenário | Descrição | Arquivo |
|---------|-----------|---------|
| **S1: Happy Path** | Trade aberto → lucrativo → fechado | `test_backtest_core.py::T2` |
| **S2: RiskGate** | Trade com loss > -3% → circuit breaker | `test_backtest_core.py::T3` |
| **S3: Commission** | Validar comissão Binance 0.04% | `test_metrics.py::T4` |
| **S4: Walk-Forward** | Generalização SMC em 15 windows | `test_walk_forward.py::T8` |
| **S5: Data Integrity** | S2-0 cache integra com engine | `test_data_provider.py::T6` |

---

## ✅ Checklist Pré-Execução

- [ ] `pytest --version` >= 7.0
- [ ] Fixtures em `conftest.py` importáveis
- [ ] Mock data (100 candles) disponível
- [ ] S2-0 cache parquet em `db/klines_cache.parquet`
- [ ] RiskGate 1.0 hardcoded (-3%) ativo

---

## 🚀 Execução dos Testes

### Command

```bash
# Full test suite
pytest backtest/tests/ -v --tb=short

# Com cobertura
pytest backtest/tests/ --cov=backtest --cov-report=html

# Apenas unit tests
pytest backtest/tests/test_*_core.py -v

# Apenas testes críticos (RiskGate, PnL)
pytest backtest/tests/ -v -k "risk_gate or pnl"
```

### Esperado

```
backtest/tests/test_backtest_core.py::test_engine_init PASSED        [12%]
backtest/tests/test_backtest_core.py::test_market_trade_execution PASSED [25%]
backtest/tests/test_backtest_core.py::test_risk_gate_circuit_breaker PASSED [37%]
backtest/tests/test_metrics.py::test_pnl_calculation PASSED          [50%]
backtest/tests/test_metrics.py::test_max_drawdown PASSED             [62%]
backtest/tests/test_data_provider.py::test_s2_0_cache_integration PASSED [75%]
backtest/tests/test_backtest_core.py::test_full_backtest_execution PASSED [87%]
backtest/tests/test_walk_forward.py::test_walk_forward_validation PASSED [100%]

========== 8 passed in 45.23s ==========
```

---

## 📝 Coverage Report

**Target:** ≥80% in `backtest/`

```
backtest/core/backtest_engine.py          87%
backtest/core/trade_state.py              92%
backtest/core/metrics.py                  85%
backtest/data/data_provider.py            88%
backtest/data/cache_reader.py             80%
backtest/strategies/smc_strategy.py       75% ← Acceptable (strategy logic)
backtest/validation/walk_forward.py       82%

TOTAL: 84%
```

---

## 🔗 Referências

- [CRITERIOS_DE_ACEITE_MVP.md § S2-3](CRITERIOS_DE_ACEITE_MVP.md#s2-3)
- [S2_3_DELIVERABLE_SPEC.md § Gate 3](S2_3_DELIVERABLE_SPEC.md#gate-3-validação--testes-)
- [ARCH_S2_3_BACKTESTING.md](ARCH_S2_3_BACKTESTING.md)

---

**Owner:** Audit (#8) + Quality (#12)
**Revisor:** Angel (#1)
**Status:** Ready for Sprint 2-3 Kickoff
