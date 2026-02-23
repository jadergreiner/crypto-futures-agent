# 🚀 Backtest Engine — Quick Start Guide

**Versão:** 2.0  
**Para:** Desenvolvedores prontos para implementação  
**Integração:** Com Risk Gate 1.0 + Módulo de Dados existentes  

---

## 📋 Referência Rápida — 3 Documentos Principais

| Documento | Foco | Leitura estimada |
|-----------|------|------------------|
| [BACKTEST_ENGINE_ARCHITECTURE.md](BACKTEST_ENGINE_ARCHITECTURE.md) | Visão de alto nível, componentes, fluxo | 40 min |
| [BACKTEST_ENGINE_IMPLEMENTATION.md](BACKTEST_ENGINE_IMPLEMENTATION.md) | Código concreto, classes, scaffolds | 30 min |
| [BACKTEST_ENGINE_PERFORMANCE.md](BACKTEST_ENGINE_PERFORMANCE.md) | Cache, otimizações, benchmarks | 25 min |

**Total:** 95 min para domínio completo

---

## ⚡ Start Coding em 10 Minutos

### **1. Setup do Projeto**

```bash
# Criar estrutura de diretórios
mkdir -p backtest/{core,data,simulation,risk,metrics,reporting,tests}
touch backtest/__init__.py

# Instalar deps (se necessário)
pip install pandas numpy pyarrow sqlalchemy -q
```

### **2. Copiar + Estender Risk Gate Existente**

```python
# backtest/risk/integration.py
"""Adapter para integração com RiskGate existente."""

from risk.risk_gate import RiskGate
from risk.circuit_breaker import CircuitBreaker

class RiskGateAdapter:
    """Adapter para usar RiskGate v1.0 em backtesting."""
    
    def __init__(self):
        self.risk_gate = RiskGate()  # Importar do projeto
        self.cb = CircuitBreaker()
    
    def validate_order(self, order, context):
        """Validar order contra RiskGate antes de executar."""
        # Se RiskGate congelado, rejeitar
        if self.risk_gate.status.value == "congelado":
            return False, "RiskGate congelado"
        
        # Se CB acionado, rejeitar
        if self.cb.state.value == "trancado":
            return False, "Circuit breaker trancado"
        
        return True, "OK"
```

### **3. Implementação Mínima (MVP Backtest)**

```python
# backtest/core/minimal_engine.py
"""Engine mínimo para começar."""

import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class MinimalBacktest:
    capital: float = 10000
    trades: list = None
    equity: list = None
    
    def __post_init__(self):
        self.trades = []
        self.equity = [self.capital]
    
    def run(self, candles_df: pd.DataFrame, strategy_func):
        """Executar backtest minimal."""
        current_capital = self.capital
        position = None
        
        for idx, row in candles_df.iterrows():
            candle = {
                'time': row['timestamp'],
                'close': row['close'],
                'volume': row['volume']
            }
            
            # Aplicar strategy
            signal = strategy_func(candle, position)
            
            if signal == 'buy' and position is None:
                position = {'entry': row['close'], 'qty': 1}
            
            elif signal == 'sell' and position is not None:
                pnl = (row['close'] - position['entry']) * position['qty']
                current_capital += pnl
                self.trades.append(pnl)
                position = None
            
            self.equity.append(current_capital)
        
        return self._compute_metrics()
    
    def _compute_metrics(self):
        """Calcular métricas rápidas."""
        equity = np.array(self.equity)
        returns = np.diff(equity) / equity[:-1]
        
        return {
            'total_trades': len(self.trades),
            'win_rate': len([t for t in self.trades if t > 0]) / len(self.trades) if self.trades else 0,
            'total_pnl': equity[-1] - self.capital,
            'sharpe': np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252),
            'max_dd': np.min(np.maximum.accumulate(equity) - equity) / (np.max(equity) + 1e-8)
        }


# Uso:
backtest = MinimalBacktest(capital=10000)
results = backtest.run(
    candles_df,
    strategy_func=my_strategy
)
print(f"Sharpe: {results['sharpe']:.2f}")
```

### **4. Integração com Dados Existentes**

```python
# backtest/data/fetch_binance_1y.py
"""Fetch dados Binance para 1 ano."""

import asyncio
from data.binance_feed import BinanceHistoricalFeed
from datetime import datetime, timedelta

async def fetch_1y_backtest_data(symbol: str):
    """Buscar 1 ano de dados para backtest."""
    feed = BinanceHistoricalFeed()
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365)
    
    # Fetch com cache automático
    df = await feed.fetch_ohlcv(
        symbol=symbol,
        timeframe="4h",
        start_date=start_date,
        end_date=end_date
    )
    
    # Validar
    result = feed.validate_data(df)
    if not result.passed:
        raise ValueError(f"Dados inválidos: {result.errors}")
    
    print(f"✓ {len(df)} candles para {symbol}")
    return df

# Uso:
df = asyncio.run(fetch_1y_backtest_data("BTCUSDT"))
```

---

## 🎯 Sprint 0: Deliverables (2-3 dias dev)

### **Dia 1: Setup + Tipos**
- [ ] Criar estrutura `backtest/`
- [ ] Implementar `types.py` (Candle, Trade, Order, BacktestRequest)
- [ ] Implementar `context.py` (SimulationContext thread-safe)
- [ ] ✅ Teste: `pytest tests/test_types.py`

### **Dia 2: Engine Minimal**
- [ ] Implementar `core/orchestrator.py` (MinimalBacktest → Full)
- [ ] Implementar `simulation/worker.py` (TimeframeWorker)
- [ ] Integrar RiskGate adapter (`risk/integration.py`)
- [ ] ✅ Teste: `pytest tests/test_minimal_backtest.py`

### **Dia 3: Dados + Métricas**
- [ ] Implementar `data/binance_feed.py` (fetch + cache)
- [ ] Implementar `metrics/calculator.py` (6 métricas críticas)
- [ ] Implementar `reporting/report.py` (BacktestReport)
- [ ] ✅ Teste E2E: `python scripts/run_backtest_e2e.py`

---

## 🔌 Integração com Módulos Existentes

### **Risk Gate 1.0**
```python
# Em OrderValidator
from backtest.risk.integration import RiskGateAdapter

validator = RiskGateAdapter()
is_valid, reason = validator.validate_order(order, ctx)

if not is_valid:
    logger.warning(f"Order rejeitada: {reason}")
    return None
```

### **Data Provider (Binance)**
```python
# backtest/data/binance_feed.py já implementa DataProvider ABC
# Herda de data.provider.DataProvider
# Usa cache multi-nível padrão do projeto

from backtest.data.binance_feed import BinanceHistoricalFeed

feed = BinanceHistoricalFeed()
df = feed.fetch_ohlcv_sync(...)
```

### **Strategy Factory**
```python
# Usar strategy existente ou criar nova
from playbooks.sma_strategy import SimpleMovingAverageStrategy

strategy = SimpleMovingAverageStrategy(params={
    'lookback': 50,
    'threshold': 0.7
})

# Ou criar nova strategy herdando de base
from backtest.simulation.strategy import Strategy

class MyStrategy(Strategy):
    def evaluate(self, candle, ctx):
        # Implementar lógica
        pass
```

---

## 📊 Estrutura Mínima de Teste

```python
# tests/test_backtest_e2e.py
"""Teste E2E minimal."""

import pytest
from datetime import datetime, timedelta
from backtest.core.types import BacktestRequest
from backtest.core.orchestrator import BacktestOrchestrator
from backtest.data.binance_feed import BinanceHistoricalFeed
from backtest.simulation.strategy import DummyStrategy


@pytest.mark.asyncio
async def test_backtest_e2e():
    """Teste E2E completo."""
    req = BacktestRequest(
        symbol="BTCUSDT",
        start_date=datetime(2025, 2, 22),
        end_date=datetime(2026, 2, 22),
        initial_capital=10000.0
    )
    
    orchestrator = BacktestOrchestrator(
        data_provider=BinanceHistoricalFeed(),
        strategy=DummyStrategy()  # Strategy simples para teste
    )
    
    report = await orchestrator.run(req)
    
    # Validações
    assert report.metrics.sharpe_ratio >= 0
    assert report.metrics.max_drawdown_pct >= 0
    assert len(report.trades) >= 0
    assert len(report.equity_curve) > 0


def test_risk_gate_integration():
    """Teste integração RiskGate."""
    from backtest.risk.integration import RiskGateAdapter
    
    adapter = RiskGateAdapter()
    assert adapter.risk_gate is not None
    assert adapter.cb is not None
    
    # Simular validação
    is_valid, reason = adapter.validate_order(None, None)
    # Return valores variáveis conforme estado


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 📈 Próximos Passos (v2.1+)

### **Roadmap**
1. **v2.0.1:** Bug fixes + otimizações cache (1-2 semanas)
2. **v2.1:** SMC Integration (Order Blocks + BoS) (3-4 semanas)
3. **v2.2:** Walk-Forward Analysis (backtesting robusto) (2-3 semanas)
4. **v2.3:** ML Integration (PPO optimizer) (4-6 semanas)

### **SMC Placeholder (v2.1)**
```python
# backtest/simulation/smc_strategy.py (TODO v2.1)
"""
Smart Money Concepts Strategy.
Detectar Order Blocks e Break of Structure.
"""

from backtest.simulation.strategy import Strategy

class SmcStrategy(Strategy):
    def evaluate(self, candle, ctx):
        """
        TODO v2.1:
        1. Detectar Order Block recente
        2. Detectar Break of Structure
        3. Validar risk/reward >= 1:2
        4. Retornar signal se setup válido
        """
        pass
```

---

## 🆘 Troubleshooting

### **Problema: API Rate Limit**
```python
# Solução: Usar cache L2/L3
from backtest.data.cache import CachedDataProvider

provider = CachedDataProvider()  # Automático
df = provider.fetch_ohlcv(...)  # Usa cache primeiro
```

### **Problema: Memory Overflow (1Y dados)**
```python
# Solução: Chunked processing
from backtest.core.chunked_processor import ChunkedProcessor

results = ChunkedProcessor.process_with_chunking(
    data,
    processor=TimeframeWorker.run,
    chunk_size=2000  # ~1 semana
)
```

### **Problema: Risk Gate muito restritivo**
```python
# Solução: Override com auditoria
req = BacktestRequest(
    ...,
    risk_gate_overrides={
        "max_drawdown_pct": 5.0,  # Override de -3%
        "stop_loss_threshold": -5.0
    }
)
logger.warning(f"⚠ Risk Gate customizado via override")
```

---

## 📚 Arquivos de Referência

### **Código Existente (Reutilizar)**
- `risk/risk_gate.py` — RiskGate 1.0 (core protection)
- `risk/circuit_breaker.py` — Circuit Breaker (-3.1%)
- `data/binance_feed.py` (se existente) — Data source
- `config/symbols.py` — Symbol config

### **Novos Arquivos (Criar)**
- `backtest/core/orchestrator.py`
- `backtest/core/context.py`
- `backtest/core/types.py`
- `backtest/simulation/worker.py`
- `backtest/metrics/calculator.py`
- `backtest/reporting/report.py`
- `tests/test_*.py`

---

## ✅ Definition of Done

- [ ] Código roda sem erros
- [ ] Todos os testes PASS (`pytest -v`)
- [ ] Docstrings em português (3-4 linhas por função)
- [ ] Risk Gate validações funcionando (auditável)
- [ ] Relatório JSON/HTML gerável
- [ ] Performance: 100k candles/sec mín
- [ ] Cache funcionando (L1, L2 verificados)
- [ ] Docs sincronizadas ([SYNC] tag)

---

## 🎓 Learning Path

**Iniciante:** `types.py` → `context.py` → `orchestrator.py`  
**Intermediário:** `binance_feed.py` → `worker.py` → `order_engine.py`  
**Avançado:** `cache.py` → `parallel_executor.py` → `metrics.py`  

---

**Questões?** Consultar documentos arquiteturais ou abrir issue no GitHub.

