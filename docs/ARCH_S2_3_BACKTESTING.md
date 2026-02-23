# 🏗️ Arquitetura S2-3 — Backtesting Engine

**Versão:** 1.0.0
**Sprint:** Sprint 2-3
**Owner:** Arch (#6)
**Data:** 2026-02-22
**Status:** 🔵 DESIGN KICKOFF

---

## 📋 Sumário Executivo

O **Backtesting Engine (S2-3)** valida estratégias SMC em dados históricos 1 ano
antes do go-live. 4 Gates garantem ZERO capital em risco antes da ativação live.

| Gate | Validador | Type | Critério |
|------|-----------|------|----------|
| **Gate 1** | Data (#11) | Dados | 60 símbolos, sem gaps, preços válidos |
| **Gate 2** | Engine Core | Trade Logic | Execução, comissões, slippage |
| **Gate 3** | Quality (#12) | Validação | 8 testes PASS, cobertura ≥80% |
| **Gate 4** | Audit (#8) | Documentação | Docstrings + Trade-offs em DECISIONS.md |

---

## 🏗️ Estrutura Diretórios

```
backtest/
├── __init__.py                      # Exports principais
├── README.md                        # Guia de uso (500+ palavras)
├── core/
│   ├── __init__.py
│   ├── backtest_engine.py          # Motor principal (executa trades)
│   ├── trade_state.py              # Estado de posição (gerenciamento)
│   └── metrics.py                  # Cálculo PnL, drawdown, Sharpe
├── data/
│   ├── __init__.py
│   ├── data_provider.py            # Interface abstrata (fetch_ohlcv)
│   └── cache_reader.py             # Parquet reader da S2-0
├── strategies/
│   ├── __init__.py
│   ├── smc_strategy.py             # Estratégia SMC (BoS + OB detection)
│   └── signal_factory.py           # Gerador de sinais
├── validation/
│   ├── __init__.py
│   ├── gates.py                    # 4 Gates de validação
│   └── walk_forward.py             # Walk-Forward testing framework
├── tests/
│   ├── test_backtest_core.py       # 5 testes + 3 integration
│   ├── test_metrics.py             # 2 testes metricsvalidation
│   ├── test_data_provider.py       # 1 teste integração data
│   ├── fixtures.py                 # Fixtures (OHLCV mock, trade scenarios)
│   └── conftest.py                 # Pytest configuration
└── logs/
    ├── backtest_results.json       # Saída de cada execução
    └── walk_forward_summary.csv    # Resumo WF testing
```

---

## 🔌 Interfaces Críticas

### 1. DataProvider (Abstração)

```python
class DataProvider(ABC):
    """Interface para fontes de dados históricos."""

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        start_time: int,
        end_time: int
    ) -> List[Kline]:
        """Retorna OHLCV entre timestamps."""
        pass
```

**Implementação S2-0 ↔ S2-3:**
- S2-0 fornece `CacheReader` (Parquet SQLite)
- S2-3 consome via `DataProvider.fetch_ohlcv()`
- Sem refactoring S2-0, apenas plugin de interface

---

### 2. Strategy (Sinais SMC)

```python
class SMCStrategy:
    """Gerador de sinais Smart Money Concepts."""

    def detect_break_of_structure(self, candles: List[Kline]) -> Signal:
        """Identifica BoS (Higher Highs/Higher Lows)."""
        pass

    def detect_order_block(self, candles: List[Kline]) -> Signal:
        """Identifica suporte/resistência (OB)."""
        pass
```

**Precedência:** S2-3 Gate 1 ✅ antes SMC live (S2-1/S2-2).

---

### 3. BacktestEngine (Orquestrador)

```python
class BacktestEngine:
    """Motor de backtesting orquestrando trade execution."""

    def backtest(
        self,
        symbol: str,
        candles: List[Kline],
        strategy: SmartMoneyStrategy,
        initial_balance: float = 10000.0
    ) -> BacktestResult:
        """Simula trades em período histórico."""

        for candle in candles:
            signal = strategy.evaluate(candle)
            if signal:
                trade = self.execute_trade(signal, candle)
                state.add_trade(trade)

        return BacktestResult(metrics=state.compute_metrics())
```

---

## 📊 Fluxo S2-3 (4 Gates)

```
┌─────────────────────────────────────────┐
│ 1. DATA INTEGRITY (S2-0 Gates 1-2)      │ ← Bloqueador
│    ✅ 60 símbolos, 1Y, sem gaps         │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. ENGINE CORE (BacktestEngine)        │
│    • OHLCV loading (DataProvider)       │
│    • Trade execution (comissões)        │
│    • State management (PnL, drawdown)   │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. VALIDATION (8 Tests + Coverage ≥80%) │
│    • Unit tests (Core, Metrics)         │
│    • Integration tests (Engine ↔ Data)  │
│    • E2E (Full backtest 6M → Sharpe)    │
│    • Regression (70 Sprint 1 testes OK) │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 4. DOCUMENTATION (Code + Trade-offs)    │
│    • Docstrings 100% PT                 │
│    • README.md (500+ palavras)          │
│    • DECISIONS.md entry (Análise)       │
│    • CRITERIOS_DE_ACEITE atualizado     │
└─────────────────────────────────────────┘
                  ↓
         🟢 GO → Desbloqueia SMC
```

---

## ⚙️ Detalhes Técnicos

### Walk-Forward Testing

```python
class WalkForwardValidator:
    """Valida generalização SMC strategy."""

    def run(self, data: DataFrame, window=180, step=30):
        """
        Split: Train 180d → Test 30d (rolling)
        15 windows totalizando 1 ano.
        """
```

**Objetivo:** Confirmar que estratégia não over-fits a período histórico.

---

### RiskGate 1.0 Integration

```python
# Em BacktestEngine.execute_trade():

position_loss = (entry_price - current_price) / entry_price
if position_loss < -0.03:  # -3% drawdown
    self.circuit_breaker.trigger()  # Close immediately
    return TradeResult(status="STOPPED_BY_RISKGATE")
```

**Inviolável:** Nenhum trade pode escapar do -3% hard stop.

---

## 🔗 Dependências

| Componente | Status | Owner |
|-----------|--------|-------|
| S2-0 Data Strategy | ✅ Design | Data (#11) |
| Parquet + SQLite Cache | ✅ Ready | Data (#11) → usar em S2-3 |
| DataProvider Interface | 🟡 Design | Arch (#6) ← ESTE DOC |
| SMC Signals (BoS, OB) | 🟡 Design | The Brain (#3) |

---

## 📋 Critério de Pronto (Gate 💚 GO)

- [ ] Diretórios criados + `__init__.py` exportando
- [ ] `data_provider.py` interface completa
- [ ] `backtest_engine.py` core logic (executa trade sem erro)
- [ ] `metrics.py` calculando PnL, Drawdown, Sharpe
- [ ] `smc_strategy.py` sketch (BoS + OB placeholders)
- [ ] `fixtures.py` com 5 cenários teste
- [ ] 8 testes escritos (com `pytest.skip()` temporário)
- [ ] Este arquivo + README.md + TEST_PLAN_S2_3.md completos

---

## 🚩 Riscos Arquiteturais

| Risco | Mitigação |
|-------|-----------|
| Parquet read performance | Cache leitura < 100ms (S2-0) |
| Walk-Forward window selection | 180d train / 30d test (literatura padrão) |
| Comissão Binance mal calculada | Validar vs docs API + hardcoded 0.0004 |
| Slippage não considerado | Assumir 2 ticks spread (futura otimização) |

---

**Owner:** Arch (#6)
**Revisor:** Angel (#1)
**Próximo:** Kickoff da squad (22 FEV 14:00 UTC)
