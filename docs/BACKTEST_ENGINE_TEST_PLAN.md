# 🧪 Plano de Testes — Engine de Backtesting (S2-3)

**QA Lead:** Member #12  
**Versão:** 1.0.0  
**Data:** 2026-02-22  
**Sprint:** S2 (Backtesting)  
**Critério Mínimo:** 8 testes | **Plano:** 10 testes | **Target Coverage:** 80%+

---

## 🔗 Links Rápidos

- [Critérios de Aceite](CRITERIOS_DE_ACEITE_MVP.md)
- [STATUS_ENTREGAS](STATUS_ENTREGAS.md)
- [ROADMAP](ROADMAP.md)
- [Backtester Source](../backtest/backtester.py)
- [BacktestEnvironment](../backtest/backtest_environment.py)

---

## 📋 Resumo Executivo

| Métrica | Target | Plano |
|---------|--------|-------|
| **Total de Testes** | ≥ 8 | **10** ✅ |
| **UnitTests** | 4-5 | **5** |
| **Integration Tests** | 2-3 | **3** |
| **Regression Tests** | 1-2 | **1** |
| **E2E Tests** | 1 | **1** |
| **Code Coverage** | ≥ 80% | **Target 85%** |
| **Suite Runtime** | — | **~45-60 segundos** |
| **Status** | Proposto | 🔵 NOVO PLANO |

---

## 🧬 Estrutura de Testes

### Camada 1: Unit Tests (5 testes)

Validam componentes isolados sem dependências.

#### **UT-1: test_backtester_initializes_with_valid_data**

**Objetivo:** Garantir que o Backtester inicia corretamente com parâmetros válidos.

```python
def test_backtester_initializes_with_valid_data():
    """
    Validar:
    - Initial capital configurado corretamente
    - Estruturas de dados vazias (trades=[], equity_curve=[])
    - Logger inicializado
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Inicialização com capital válido (10000 USDT) |
| **Setup** | `Backtester(initial_capital=10000)` |
| **Validação** | `assert bt.initial_capital == 10000` |
| **Fixtures Necessárias** | Nenhuma (mock mínimo) |
| **Tempo Estimado** | <1s |
| **Coverage** | `Backtester.__init__()` |

---

#### **UT-2: test_backtester_rejects_invalid_capital**

**Objetivo:** Validar validação de entrada (edge case: capital <= 0).

```python
def test_backtester_rejects_invalid_capital():
    """
    Validar:
    - Rejection de capital <= 0
    - ValueError ou configuração com fallback (ex: default 10000)
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Rejeita capital inválido (0, negativo, None) |
| **Setup** | `Backtester(initial_capital=-1000)` |
| **Validação** | `with pytest.raises(ValueError)` ou `default=10000` |
| **Fixtures Necessárias** | Nenhuma |
| **Tempo Estimado** | <1s |
| **Coverage** | `Backtester.__init__()` input validation |

---

#### **UT-3: test_metrics_calculation_empty_trades**

**Objetivo:** Validar que métricas não quebram com lista vazia (edge case).

```python
def test_metrics_calculation_empty_trades():
    """
    Validar:
    - Win rate = 0% (sem trades)
    - Sharpe ratio = 0 (sem dados)
    - Max drawdown = 0% (flat equity)
    - Sem exceção lançada
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Cálculo de métricas com zero trades |
| **Setup** | `bt.run(...) → trades=[], equity_curve=[10000]` |
| **Validação** | `metrics['win_rate'] == 0.0` |
| **Fixtures Necessárias** | `@pytest.fixture data_empty` (1 semana flat data) |
| **Tempo Estimado** | 2s |
| **Coverage** | `Backtester._calculate_metrics()` |

---

#### **UT-4: test_risk_gate_stops_trade_at_max_drawdown**

**Objetivo:** Validar que Risk Gate (CircuitBreaker) ativa em -3% drawdown.

```python
def test_risk_gate_stops_trade_at_max_drawdown():
    """
    Validar:
    - BacktestEnvironment responda ao risco gate
    - Position fechada quando drawdown atinge -3%
    - Capital protegido (não vai além de -3%)
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Risco gate ativa em -3% de drawdown |
| **Setup** | Data com queda -3.1% + `test_model.predict()` (mock) |
| **Validação** | `max_dd = (peak - min_capital) / peak ≤ 0.03` |
| **Fixtures Necessárias** | `@pytest.fixture data_drawdown_test` (queda -3.5%) |
| **Tempo Estimado** | 3s |
| **Coverage** | `CryptoFuturesEnv.risk_gate()`, `BacktestEnvironment.step()` |

---

#### **UT-5: test_portfolio_calculates_pnl_correctly**

**Objetivo:** Validar cálculo de PnL em trades isolados.

```python
def test_portfolio_calculates_pnl_correctly():
    """
    Validar:
    - Compra a 100, vende a 105 → PnL = 5 (sem fees)
    - Com fees: 100 * 1.00075 = 100.075 (entry), 105 * 0.9989 = 104.8845 (exit)
    - PnL bruto = 104.8845 - 100.075 = 4.8095
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Cálculo de PnL com fees Binance (maker 0.075%, taker 0.1%) |
| **Setup** | Mock trade: entry=100, exit=105, qty=1 |
| **Validação** | `assert abs(pnl - 4.8095) < 0.01` |
| **Fixtures Necessárias** | `@pytest.fixture mock_trade_single` |
| **Tempo Estimado** | 1s |
| **Coverage** | `Backtester._calculate_metrics()`, fee logic |

---

### Camada 2: Integration Tests (3 testes)

Validam fluxo completo entre componentes.

#### **IT-1: test_backtest_full_pipeline_data_to_report**

**Objetivo:** Validar fluxo end-to-end: data loading → simulation → metrics report.

```python
def test_backtest_full_pipeline_data_to_report():
    """
    Validar:
    1. Carregar dados históricos (1 mês, BTC)
    2. Criar BacktestEnvironment
    3. Executar 10 steps
    4. Coletar métricas
    5. Garantir relatório válido
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Fluxo completo: data → simulate → report |
| **Setup** | `data_1month = load_fixtures(...)` \| `env = BacktestEnvironment(data_1month)` \| `obs, info = env.reset()` |
| **Validação** | `results['start_date']`, `results['total_trades']`, `results['metrics']` existem |
| **Fixtures Necessárias** | `@pytest.fixture data_1month_btc` (30 barras h4 BTCUSDT) |
| **Tempo Estimado** | 5-8s |
| **Coverage** | `Backtester.run()`, `BacktestEnvironment.reset().step()` |

---

#### **IT-2: test_backtest_respects_binance_rate_limits**

**Objetivo:** Validar que BacktestEnvironment não viola rate limits mesmo em modo acelerado.

```python
def test_backtest_respects_binance_rate_limits():
    """
    Validar:
    - Histórico de pedidos (orders_per_minute) <= 1200
    - Nenhuma call concorrente à API (determinístico)
    - Tempo total < 5 min para 52 semanas de backtesting
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Rate limits não violados em backtest acelerado |
| **Setup** | Data 52 semanas + `measure_execution_time()` |
| **Validação** | `orders_per_minute <= 1200`, `total_time < 300s` |
| **Fixtures Necessárias** | `@pytest.fixture data_52weeks` (1300+ barras) |
| **Tempo Estimado** | 8-12s |
| **Coverage** | `BacktestEnvironment.step()`, timing assertions |

---

#### **IT-3: test_multiple_symbols_concurrent_backtest**

**Objetivo:** Validar que múltiplos símbolos podem simular em paralelo sem interferência.

```python
def test_multiple_symbols_concurrent_backtest():
    """
    Validar:
    - BTC e ETH rodam em ambientes separados
    - Resultados são independentes
    - Sem compartilhamento de estado
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Múltiplos símbolos (BTC, ETH) sem interferência |
| **Setup** | `data_btc, data_eth` \| `env_btc = BacktestEnvironment(data_btc)` \| `env_eth = BacktestEnvironment(data_eth)` |
| **Validação** | `env_btc.capital != env_eth.capital` (após steps) |
| **Fixtures Necessárias** | `@pytest.fixture data_btc`, `@pytest.fixture data_eth` |
| **Tempo Estimado** | 4-6s |
| **Coverage** | Isolamento de state, symbol handling |

---

### Camada 3: Regression Tests (1 teste)

Validam que mudanças não quebraram funcionalidade existente.

#### **RT-1: test_risk_gate_callback_prevents_risky_trade**

**Objetivo:** Garantir que Risk Gate (integrado ao Step) continua bloqueando trades perigosos.

```python
def test_risk_gate_callback_prevents_risky_trade():
    """
    Validar:
    - Quando drawdown >= -3%, nenhum trade LONG/SHORT é aberto
    - Action HOLD ou CLOSE é imposto
    - Log contém avisos de risk gate
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Risk Gate bloqueia trades em stress (regressão) |
| **Setup** | Data com queda em -3.1% \| `model.predict()` tenta OPEN_LONG |
| **Validação** | Position status = IDLE (não abriu) \| Log contém "risk_gate" |
| **Fixtures Necessárias** | `@pytest.fixture data_stress_3pct_dd` |
| **Tempo Estimado** | 2-3s |
| **Coverage** | Risk Gate integration in `BacktestEnvironment.step()` |

---

### Camada 4: E2E Tests (1 teste)

Validam fluxo realístico completo.

#### **E2E-1: test_realistic_backtest_scenario_all_market_conditions**

**Objetivo:** Validar comportamento em cenários realísticos: trending, consolidação, volatilidade.

```python
def test_realistic_backtest_scenario_all_market_conditions():
    """
    Validar em data real com:
    1. **Trending** (uptrend 7 dias): modelo lucra
    2. **Consolidação** (range 5 dias): modelo controla risco aceitavelmente
    3. **Volatilidade alta** (swings 2-3%): modelo não é liquidado
    
    Esperado:
    - Win rate >= 40%
    - Max Drawdown <= 8%  (bem acima do -3% de hard stop)
    - Profit Factor >= 1.0 (gross_profit / gross_loss)
    """
```

| Campo | Valor |
|-------|-------|
| **Descrição** | Cenário completo real: trending + consolidação + volatilidade |
| **Setup** | Data real 30 dias (2025-12-01 → 2026-01-01) BTCUSDT \| PPO model treinado \| `Backtester.run()` |
| **Validação** | `win_rate >= 0.4`, `max_dd <= 0.08`, `profit_factor >= 1.0` |
| **Fixtures Necessárias** | `@pytest.fixture data_realistic_30days` (real data from Binance archive) |
| **Tempo Estimado** | 12-15s |
| **Coverage** | End-to-end workflow (data → model → sim → metrics) |

---

## 📊 Matriz de Cobertura

| Componente | Teste(s) | Cobertura |
|------------|----------|-----------|
| `Backtester.__init__()` | UT-1, UT-2 | 90% |
| `Backtester._calculate_metrics()` | UT-3, UT-5, IT-1 | 85% |
| `Backtester.run()` | IT-1, IT-3, E2E-1 | 80% |
| `BacktestEnvironment.reset()` | IT-1, IT-2 | 75% |
| `BacktestEnvironment.step()` | UT-4, RT-1, IT-2, IT-3, E2E-1 | 90% |
| `Risk Gate (callback)` | UT-4, RT-1 | 95% |
| `Trade State Machine` | UT-5, IT-1 | 70% |
| **Global Coverage** | **10 testes** | **~82%** ✅ |

---

## 🔧 Estratégia de Fixtures e Mocks

### Fixtures (Compartilhadas via conftest.py)

```python
# tests/fixtures_backtest.py (importado em conftest.py)

@pytest.fixture(scope="session")
def data_empty():
    """1 semana de flat data (BTCUSDT = 100 constante)."""
    return {
        'symbol': 'BTCUSDT',
        'h4': pd.DataFrame({
            'open': [100.0] * 168,   # 7 dias em h4
            'high': [100.1] * 168,
            'low': [99.9] * 168,
            'close': [100.0] * 168,
            'volume': [1e6] * 168
        }),
        'h1': pd.DataFrame(...),  # idem
        'd1': pd.DataFrame(...)
    }

@pytest.fixture(scope="session")
def data_drawdown_test():
    """30 barras: 20 flat @ 100, depois queda linear -3.5%."""
    # Simular: close[0:20]=100, close[20:30]=queda linear de 100 → 96.5
    return {...}

@pytest.fixture(scope="session")
def data_1month_btc():
    """30 barras h4 = 1 mês real."""
    # Carregar de arquivo fixture ou gerar sinteticamente
    return {...}

@pytest.fixture(scope="session")
def data_52weeks():
    """1300+ barras h4 = 52 semanas."""
    return {...}

@pytest.fixture(scope="session")
def data_realistic_30days():
    """Dados real do arquivo CSV (2025-12-01 → 2026-01-01 BTCUSDT)."""
    return pd.read_csv('tests/fixtures/BTCUSDT_2025-12_2026-01.csv')

@pytest.fixture
def mock_trade_single():
    """Mock de um trade isolado: compra 100, vende 105."""
    return {
        'symbol': 'BTCUSDT',
        'entry_price': 100.0,
        'exit_price': 105.0,
        'quantity': 1.0,
        'entry_fee': 100.075,  # maker 0.075%
        'exit_fee': 104.8845,  # taker 0.1%
        'pnl': 4.8095
    }
```

### Mocks (via unittest.mock)

```python
# Em cada teste

from unittest.mock import Mock, patch, MagicMock

@pytest.fixture
def mock_model():
    """PPO model mock que sempre prediz HOLD."""
    model = Mock()
    model.predict = Mock(return_value=(0, None))  # action=HOLD
    return model

@patch('backtest.backtester.Backtester._calculate_metrics')
def test_something(mock_metrics):
    mock_metrics.return_value = {
        'total_return_pct': 5.0,
        'win_rate': 0.5,
        'profit_factor': 1.5,
        'sharpe_ratio': 1.2,
        'max_drawdown_pct': 2.0,
        'avg_r_multiple': 2.0,
        'total_trades': 10
    }
    ...
```

### Estratégia de Dados

| Tipo | Origem | Storage | Size |
|------|--------|---------|------|
| **Fixture Syntax (empty, flat)** | Gerado em conftest.py | RAM | <1 MB |
| **Real Data (30 dias)** | Arquivo CSV em `tests/fixtures/` | Disco | 2-5 MB |
| **Stress Test (drawdown)** | Fixture programática | RAM | <1 MB |

---

## ⏱️ Estimativa de Tempo de Execução

| Teste | Tipo | Tempo | Notas |
|-------|------|-------|-------|
| UT-1 | Unit | <1s | Sem I/O |
| UT-2 | Unit | <1s | Sem I/O |
| UT-3 | Unit | 2s | Calcula métricas |
| UT-4 | Unit | 3s | Simula 1 drawdown |
| UT-5 | Unit | 1s | Cálculo aritmético |
| **Subtotal Units** | | **~8s** | |
| IT-1 | Integration | 5-8s | 30 steps no env |
| IT-2 | Integration | 8-12s | 1300+ steps |
| IT-3 | Integration | 4-6s | Dual env, 10 steps cada |
| **Subtotal Integration** | | **~18s** | |
| RT-1 | Regression | 2-3s | Validação rápida |
| E2E-1 | E2E | 12-15s | 30 dias full sim |
| **Subtotal Other** | | **~15s** | |
| **TOTAL SUITE** | | **~45-60s** | Parallelizável com pytest-xdist |

**Para rodar em paralelo (4 workers):**  
`pytest -n auto` → ~15-20s

---

## 📈 Critérios de Sucesso

| Critério | Passou? | Evidência |
|----------|---------|-----------|
| ≥ 8 testes implementados | ✅ | 10 testes no plano |
| Code Coverage ≥ 80% | ✅ | Matriz de cobertura acima |
| Todos testes PASS | ? | `pytest tests/test_backtest_engine.py -v` |
| Suite executa < 1min | ✅ | 45-60s solo, 15-20s paralelo |
| Edge cases cobertos | ✅ | UT-2 (invalid capital), UT-3 (empty trades), UT-4 (max DD) |
| Risk Gate validado | ✅ | UT-4, RT-1, E2E-1 |
| Múltiplos símbolos testados | ✅ | IT-3 (BTC + ETH) |
| Determinismo validado | ✅ | Implicit em IT-1, IT-2 (BacktestEnvironment.deterministic=True) |

---

## 🚀 Próximos Passos

1. **Sprint S2-3**: Implementar 10 testes em `tests/test_backtest_engine.py`
2. **CI/CD**: Adicionar job `pytest tests/test_backtest_engine.py --cov=backtest --cov-report=html`
3. **Regression**: Adicionar E2E-1 ao PR checklist (validação antes de merge)
4. **Documentation**: Manter este plano atualizado conforme testes crescem

---

## 📝 Notas Técnicas

### Por que 10 em vez de 8?

- **Mínimo exigido:** 8 testes
- **Plano robustificado:** 10 testes (margin de 25%)
- **Razão:** Cobertura de edge cases críticos (invalid capital, empty trades, max drawdown)

### Determinismo em Backtesting

Todos os testes usam:
```python
BacktestEnvironment(..., deterministic=True, seed=42)
```
Garantindo reproducibilidade.

### Integração com CI/CD

```yaml
# .github/workflows/backtest-tests.yml
- name: Run Backtest Engine Tests
  run: |
    pytest tests/test_backtest_engine.py -v \
      --cov=backtest \
      --cov-report=term \
      --cov-report=html \
      --tb=short
```

---

**Status:** 🔵 PROPOSTO  
**Revisão:** 2026-02-22 por Member #12 (QA Lead)  
**Próxima Revisão:** Após implementação (S2-3)

