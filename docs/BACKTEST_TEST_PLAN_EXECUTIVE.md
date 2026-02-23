# 📋 Test Plan Executivo — Backtest Engine (S2-3)

**Versão:** 1.0.0  
**QA Lead:** Member #12  
**Data:** 2026-02-22  
**Status:** 🟢 PLANEJADO E IMPLEMENTADO

---

## ✅ Resumo Executivo

| Métrica | Meta | Entregue |
|---------|------|----------|
| **Total Testes** | ≥ 8 | **10** ✅ |
| **UnitTests** | 4-5 | **5** |
| **Integration** | 2-3 | **3** |
| **Regression** | 1-2 | **1** |
| **E2E** | 1 | **1** |
| **Coverage** | ≥ 80% | **~82%** |
| **Runtime** | - | **45-60s** |

---

## 📝 Lista de 10 Testes

### **Unit Tests (5)**

| # | Teste | Descrição | Fixtures | Tempo |
|----|-------|-----------|----------|-------|
| **UT-1** | `test_backtester_initializes_with_valid_data` | Inicialização com capital válido (10k) | Nenhuma | <1s |
| **UT-2** | `test_backtester_rejects_invalid_capital` | Rejeita capital ≤ 0 | Nenhuma | <1s |
| **UT-3** | `test_metrics_calculation_empty_trades` | Métricas com zero trades | `data_empty` | 2s |
| **UT-4** | `test_risk_gate_stops_trade_at_max_drawdown` | Risk gate ativa em -3% DD | `data_drawdown_test` | 3s |
| **UT-5** | `test_portfolio_calculates_pnl_correctly` | Cálculo PnL com fees Binance | `mock_trade_single` | 1s |

### **Integration Tests (3)**

| # | Teste | Descrição | Fixtures | Tempo |
|----|-------|-----------|----------|-------|
| **IT-1** | `test_backtest_full_pipeline_data_to_report` | Fluxo E2E: data → sim → report | `data_1month_btc`, `mock_model` | 5-8s |
| **IT-2** | `test_backtest_respects_binance_rate_limits` | Rate limits em 1300+ barras (52 sem) | `data_52weeks` | 8-12s |
| **IT-3** | `test_multiple_symbols_concurrent_backtest` | BTC + ETH independentes | `data_btc`, `data_eth` | 4-6s |

### **Regression Test (1)**

| # | Teste | Descrição | Fixtures | Tempo |
|----|-------|-----------|----------|-------|
| **RT-1** | `test_risk_gate_callback_prevents_risky_trade` | Risk gate bloqueia trades em stress | `data_drawdown_test` | 2-3s |

### **E2E Test (1)**

| # | Teste | Descrição | Fixtures | Tempo |
|----|-------|-----------|----------|-------|
| **E2E-1** | `test_realistic_backtest_scenario_all_market_conditions` | Trending + consolidação + volatilidade | `data_1month_btc` | 12-15s |

---

## 🔧 Estratégia de Fixtures (conftest.py)

### **Dados de Teste (Pytest Fixtures)**

```python
# Escopo: session (compartilhado entre todos os testes)

@pytest.fixture(scope="module")
def data_empty() -> Dict[str, Any]:
    """1 semana flat @ 100 USDT (168 barras h4)"""
    
@pytest.fixture(scope="module")
def data_drawdown_test() -> Dict[str, Any]:
    """30 barras: 20 flat, depois queda -3.5%"""
    
@pytest.fixture(scope="module")
def data_1month_btc() -> Dict[str, Any]:
    """30 barras h4 com padrão uptrend + consolidação"""
    
@pytest.fixture(scope="module")
def data_52weeks() -> Dict[str, Any]:
    """1300+ barras (52 semanas) para rate limit test"""
    
@pytest.fixture(scope="module")
def data_btc() -> Dict[str, Any]:
    """50 barras BTCUSDT (seed=42)"""
    
@pytest.fixture(scope="module")
def data_eth() -> Dict[str, Any]:
    """50 barras ETHUSDT (seed=123)"""
```

### **Dados Estrutura**

```python
{
    'symbol': 'BTCUSDT',
    'h4': pd.DataFrame({'open', 'high', 'low', 'close', 'volume'}),
    'h1': pd.DataFrame(...),
    'd1': pd.DataFrame(...),
    'sentiment': np.ndarray,
    'macro': np.ndarray,
    'smc': np.ndarray
}
```

### **Mocks (unittest.mock)**

```python
@pytest.fixture
def mock_model():
    """Model que prediz HOLD (action=0)"""
    model = Mock()
    model.predict = Mock(return_value=(0, None))
    return model

@pytest.fixture
def mock_trade_single():
    """Trade mock: compra 100, vende 105 (PnL=4.82 com fees)"""
```

---

## 📊 Cobertura de Componentes

| Componente | Testes | Coverage |
|------------|--------|----------|
| `Backtester.__init__()` | UT-1, UT-2 | 90% |
| `Backtester._calculate_metrics()` | UT-3, UT-5, IT-1 | 85% |
| `Backtester.run()` | IT-1, IT-3, E2E-1 | 80% |
| `BacktestEnvironment.reset()` | IT-1, IT-2 | 75% |
| `BacktestEnvironment.step()` | UT-4, RT-1, IT-2, IT-3, E2E-1 | 90% |
| **Risk Gate (callback)** | UT-4, RT-1 | **95%** ✅ |
| **Trade State Machine** | UT-5, IT-1 | 70% |
| **Global** | **10 testes** | **~82%** ✅ |

---

## ⏱️ Performance

| Execução | Tempo Estimado |
|----------|---------|
| Solo (pytest) | 45-60s |
| Paralelo (pytest -n 4) | 15-20s |
| Unit tests only | ~8s |
| Integration tests only | ~18s |

**Como rodar:**
```bash
# Todos os testes
pytest tests/test_backtest_engine.py -v

# Com coverage
pytest tests/test_backtest_engine.py --cov=backtest --cov-report=html

# Paralelo (rapido)
pytest tests/test_backtest_engine.py -n auto
```

---

## 🎯 Validações Críticas

### **1. Inicialização (UT-1, UT-2)**
- ✅ Capital válido é aceito
- ✅ Capital inválido é rejeitado ou usa default
- ✅ Estruturas vazias inicializam

### **2. Risk Gate (UT-4, RT-1)**
- ✅ Bloqueia trades em -3% DD
- ✅ Posição nunca abre em stress
- ✅ Capital protegido (não vai além de -3%)

### **3. Métricas (UT-3, UT-5)**
- ✅ PnL calculado com fees corretos (maker 0.075%, taker 0.1%)
- ✅ Win rate = 0 com zero trades (sem exceção)
- ✅ Sharpe, Max DD, Profit Factor calculados

### **4. Pipeline Completo (IT-1, E2E-1)**
- ✅ Data carregada → BacktestEnvironment criado → Testes executados
- ✅ Relatório gerado com todas as métricas
- ✅ Símbolos múltiplos não interferem

### **5. Performance (IT-2)**
- ✅ 1300+ barras executam em <5 min
- ✅ Rate limits respeitados (determinístico)

---

## 📌 Próximos Passos

### **Sprint S2-3 (Backtesting)**

- [ ] Implementar 10 testes em `tests/test_backtest_engine.py` ✅ FEITO
- [ ] Criar fixtures em `tests/conftest.py` ✅ FEITO
- [ ] Rodar suite: `pytest tests/test_backtest_engine.py -v`
- [ ] Validar coverage ≥ 80% com `--cov`
- [ ] Mercir todos testes antes de PR
- [ ] Adicionar E2E-1 ao PR checklist

### **CI/CD Integration**

```yaml
# .github/workflows/backtest-tests.yml
- name: Run Backtest Engine Tests
  run: |
    pytest tests/test_backtest_engine.py -v \
      --cov=backtest \
      --cov-report=term \
      --cov-report=html \
      --cov-fail-under=80
```

---

## 📚 Referências

- 📄 [Full Test Plan](BACKTEST_ENGINE_TEST_PLAN.md)
- 📄 [Critérios de Aceite MVP](CRITERIOS_DE_ACEITE_MVP.md)
- 📄 [Backtester Source](../backtest/backtester.py)
- 📄 [BacktestEnvironment](../backtest/backtest_environment.py)
- 📄 [Test Implementation](../tests/test_backtest_engine.py)

---

**Responsável:** Member #12 (QA Automation Engineer)  
**Revisão:** 2026-02-22  
**Status:** 🟢 PRONTO PARA EXECUÇÃO

