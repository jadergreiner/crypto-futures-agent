# 🛠️ Backtest Engine — Implementação Concreta das Classes

**Versão:** 2.0  
**Foco:** Python production-ready, padrões boring + predictable  
**Status:** Scaffold pronto para coding  

---

## 📦 Estrutura de Diretórios Proposta

```
backtest/
├── __init__.py
├── core/                          # Núcleo do engine
│   ├── __init__.py
│   ├── orchestrator.py            # BacktestOrchestrator
│   ├── context.py                 # SimulationContext
│   ├── state_machine.py           # PositionStateMachine
│   └── types.py                   # Dataclasses + types
│
├── data/                          # Camada de dados
│   ├── __init__.py
│   ├── provider.py                # DataProvider ABC
│   ├── binance_feed.py            # BinanceHistoricalFeed
│   ├── cache.py                   # Cache multi-nível
│   └── validator.py               # Data validation
│
├── simulation/                    # Simulação
│   ├── __init__.py
│   ├── worker.py                  # TimeframeWorker
│   ├── order_engine.py            # OrderSimulator
│   ├── strategy.py                # Strategy ABC
│   └── smc_strategy.py            # SMC placeholder (v2.1)
│
├── risk/                          # Link com risk_gate
│   ├── __init__.py
│   ├── validator.py               # OrderValidator
│   └── integration.py             # RiskGate adapter
│
├── metrics/                       # Cálculo de métricas
│   ├── __init__.py
│   ├── calculator.py              # MetricsCalculator
│   ├── equity_tracker.py          # EquityCurveTracker
│   └── models.py                  # BacktestMetrics dataclass
│
├── reporting/                     # Geração de relatórios
│   ├── __init__.py
│   ├── report.py                  # BacktestReport
│   └── exporters.py               # JSON, HTML, Parquet
│
└── tests/
    ├── test_orchestrator.py
    ├── test_order_engine.py
    ├── test_risk_validation.py
    └── test_e2e.py
```

---

## 🔧 Implementação das Classes (Core)

### **1. types.py — Tipos + Dataclasses Imutáveis**

```python
"""
tipos.py — Contratos imutáveis para o engine.
Dataclasses frozen para safety semântico.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
import uuid


class TradeStatus(Enum):
    """Status de um trade."""
    PENDING = "pending"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    REJECTED = "rejected"


class PositionState(Enum):
    """Estado de uma posição."""
    IDLE = "idle"
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"


class SignalType(Enum):
    """Tipos de sinal de entrada/saída."""
    BUY = "buy"
    SELL = "sell"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    HOLD = "hold"


@dataclass(frozen=True)
class Candle:
    """Vela OHLCV imutável."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "4h"
    
    def __post_init__(self):
        """Validações pós-construção."""
        if not (self.low <= self.close <= self.high):
            raise ValueError(f"Candle inválida: close fora do range [L, H]")
        if self.volume < 0:
            raise ValueError("Volume não pode ser negativo")


@dataclass(frozen=True)
class TradeSignal:
    """Sinal de estratégia (imutável)."""
    signal_type: SignalType
    confidence: float           # 0.0 - 1.0
    entry_price: float
    stop_loss_pct: float        # e.g., -3.0
    take_profit_pct: float      # e.g., 6.0
    reason: str                 # Auditável: por que?
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence deve estar entre 0 e 1")
        if self.stop_loss_pct >= 0:
            raise ValueError("Stop loss deve ser negativo")


@dataclass
class Order:
    """Ordem de compra/venda."""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal: TradeSignal = None
    symbol: str = None
    side: Literal["buy", "sell"] = None
    quantity: float = None
    limit_price: Optional[float] = None
    is_market: bool = True
    timestamp_created: datetime = field(default_factory=datetime.utcnow)
    status: TradeStatus = TradeStatus.PENDING
    
    @classmethod
    def from_signal(cls, signal: TradeSignal, symbol: str, qty: float):
        """Factory para criar order a partir de signal."""
        side = "buy" if signal.signal_type in [SignalType.BUY] else "sell"
        return cls(
            signal=signal,
            symbol=symbol,
            side=side,
            quantity=qty,
            limit_price=signal.entry_price if not True else None  # market
        )


@dataclass
class Trade:
    """Trade executado (imutável após fechamento)."""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = None
    side: Literal["long", "short"] = None
    
    # Entrada
    entry_price: float = None
    entry_time: datetime = None
    entry_qty: float = None
    
    # Saída
    exit_price: float = None
    exit_time: datetime = None
    exit_qty: float = None
    
    # Resultados
    pnl: float = 0.0            # PnL realizado
    pnl_pct: float = 0.0        # PnL %
    commission: float = 0.0     # Comissão paga
    slippage: float = 0.0       # Slippage sofrido
    
    # Contexto
    reason_close: str = ""      # Por que fechou? TP/SL/Manual
    is_win: bool = False        # Win ou loss?
    
    def is_closed(self) -> bool:
        """Trade foi completado?"""
        return self.exit_price is not None


@dataclass(frozen=True)
class BacktestRequest:
    """Request imutável para iniciar backtest."""
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    leverage: float = 1.0
    mode: Literal["paper", "live"] = "paper"
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    risk_gate_overrides: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        if self.start_date >= self.end_date:
            raise ValueError("start_date deve ser menor que end_date")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital deve ser > 0")
        if self.leverage <= 0 or self.leverage > 10:
            raise ValueError("leverage deve estar entre 0 e 10")


@dataclass
class RiskEvent:
    """Evento de risco (SL/CB)."""
    event_type: Literal["stop_loss", "circuit_breaker", "max_position_size"]
    timestamp: datetime
    portfolio_value: float
    drawdown_pct: float
    message: str
```

---

### **2. context.py — SimulationContext (State Holder)**

```python
"""
context.py — Contexto thread-safe da simulação.
Gerencia estado compartilhado entre workers.
"""

import threading
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import numpy as np

from types import Trade, Position


@dataclass
class SimulationContext:
    """Container de estado thread-safe."""
    
    # Imutáveis na criação
    initial_capital: float
    symbol: str
    start_date: datetime
    end_date: datetime
    risk_gate: 'RiskGate'  # Instance do RiskGate
    
    # Mutáveis (protegidos por lock)
    _current_capital: float = field(init=False)
    _positions: Dict[str, 'Position'] = field(default_factory=dict, init=False)
    _equity_curve: List[float] = field(default_factory=list, init=False)
    _trade_journal: List[Trade] = field(default_factory=list, init=False)
    _order_queue: List['Order'] = field(default_factory=list, init=False)
    _risk_events: List['RiskEvent'] = field(default_factory=list, init=False)
    _peak_capital: float = field(init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)
    
    def __post_init__(self):
        """Inicializar estado mutável."""
        self._current_capital = self.initial_capital
        self._peak_capital = self.initial_capital
        self._equity_curve.append(self.initial_capital)
    
    @property
    def current_capital(self) -> float:
        """Capital atual (thread-safe)."""
        with self._lock:
            return self._current_capital
    
    @current_capital.setter
    def current_capital(self, value: float):
        """Atualizar capital (thread-safe)."""
        with self._lock:
            self._current_capital = value
            self._equity_curve.append(value)
            
            # Rastrear peak para drawdown
            if value > self._peak_capital:
                self._peak_capital = value
            
            # Atualizar RiskGate
            self.risk_gate.update_portfolio_value(value)
    
    def get_positions(self) -> Dict[str, 'Position']:
        """Obter cópia de posições (thread-safe)."""
        with self._lock:
            return dict(self._positions)
    
    def add_position(self, symbol: str, position: 'Position'):
        """Adicionar/atualizar posição."""
        with self._lock:
            self._positions[symbol] = position
    
    def remove_position(self, symbol: str):
        """Remover posição."""
        with self._lock:
            self._positions.pop(symbol, None)
    
    def add_trade(self, trade: Trade):
        """Registrar trade (auditável)."""
        with self._lock:
            self._trade_journal.append(trade)
    
    def add_order(self, order: 'Order'):
        """Enfileirar order."""
        with self._lock:
            self._order_queue.append(order)
    
    def get_pending_orders(self) -> List['Order']:
        """Obter ordens pendentes."""
        with self._lock:
            pending = [o for o in self._order_queue 
                      if o.status == TradeStatus.PENDING]
            return pending
    
    def add_risk_event(self, event: 'RiskEvent'):
        """Registrar evento de risco."""
        with self._lock:
            self._risk_events.append(event)
    
    def get_equity_curve(self) -> List[float]:
        """Obter curva de patrimônio."""
        with self._lock:
            return list(self._equity_curve)
    
    def get_drawdown_pct(self) -> float:
        """Calcular drawdown atual (% do peak)."""
        with self._lock:
            if self._peak_capital == 0:
                return 0.0
            dd = (self._current_capital - self._peak_capital) / self._peak_capital
            return dd * 100
```

---

### **3. orchestrator.py — BacktestOrchestrator**

```python
"""
orchestrator.py — Orquestrador principal do backtest.
Gerencia fluxo: validação → data → simulação → métricas → relatório.
"""

import logging
import asyncio
from typing import Optional, List
from datetime import datetime
import numpy as np

from types import BacktestRequest
from context import SimulationContext
from data.provider import DataProvider
from simulation.worker import TimeframeWorker
from metrics.calculator import MetricsCalculator
from reporting.report import BacktestReport
from risk.integration import RiskGateAdapter

logger = logging.getLogger(__name__)


class BacktestOrchestrator:
    """Orquestrador principal."""
    
    def __init__(
        self,
        data_provider: DataProvider,
        strategy: 'Strategy',
        risk_gate: Optional['RiskGate'] = None
    ):
        self.data_provider = data_provider
        self.strategy = strategy
        self.risk_gate = risk_gate
        self.metrics_calc = MetricsCalculator()
        
        logger.info("BacktestOrchestrator inicializado")
    
    async def run(self, req: BacktestRequest) -> BacktestReport:
        """
        Executar backtest completo.
        
        Args:
            req: BacktestRequest imutável
            
        Returns:
            BacktestReport com resultados
        """
        try:
            # 1. VALIDAÇÃO
            self._validate_request(req)
            logger.info(f"✓ Request validado para {req.symbol}")
            
            # 2. FETCH DATA
            logger.info(f"Fetching dados históricos: {req.start_date} → {req.end_date}")
            data = await self.data_provider.fetch_ohlcv(
                symbol=req.symbol,
                timeframe="4h",
                start_date=req.start_date,
                end_date=req.end_date
            )
            logger.info(f"✓ {len(data)} candles carregados")
            
            # 3. VALIDATION DATA
            validation_result = self.data_provider.validate_data(data)
            if not validation_result.passed:
                logger.error(f"❌ Dados inválidos: {validation_result.errors}")
                raise ValueError(validation_result.errors[0])
            logger.info("✓ Integridade de dados validada")
            
            # 4. CONTEXT INIT
            from risk.circuit_breaker import CircuitBreaker
            from risk_gate import RiskGate
            
            risk_gate_instance = RiskGate()
            if req.risk_gate_overrides:
                risk_gate_instance = self._apply_overrides(
                    risk_gate_instance,
                    req.risk_gate_overrides
                )
                logger.warning(f"⚠ Risk Gate customizado: {req.risk_gate_overrides}")
            
            ctx = SimulationContext(
                initial_capital=req.initial_capital,
                symbol=req.symbol,
                start_date=req.start_date,
                end_date=req.end_date,
                risk_gate=risk_gate_instance
            )
            logger.info(f"✓ Contexto inicializado: capital=${req.initial_capital:.2f}")
            
            # 5. SPAWN WORKERS
            num_workers = 4
            chunk_size = len(data) // num_workers + 1
            workers = []
            
            for i in range(num_workers):
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, len(data))
                
                if start_idx >= len(data):
                    break
                
                chunk = data.iloc[start_idx:end_idx]
                worker = TimeframeWorker(
                    context=ctx,
                    candles=chunk,
                    strategy=self.strategy,
                    worker_id=i
                )
                workers.append(worker)
            
            logger.info(f"✓ {len(workers)} workers spawned")
            
            # 6. EXECUTE WORKERS (PARALELO)
            results = await asyncio.gather(*[
                asyncio.to_thread(w.run) for w in workers
            ])
            logger.info("✓ Simulação completada")
            
            # 7. AGGREGATE RESULTS
            trade_journal = ctx._trade_journal  # Acesso direto é OK aqui
            equity_curve = ctx.get_equity_curve()
            risk_events = ctx._risk_events
            
            logger.info(f"   Total trades: {len(trade_journal)}")
            logger.info(f"   Equity curve points: {len(equity_curve)}")
            logger.info(f"   Risk events: {len(risk_events)}")
            
            # 8. CALCULATE METRICS
            metrics = self.metrics_calc.calculate_from_equity_curve(
                equity_curve=equity_curve,
                trades=trade_journal
            )
            logger.info(f"✓ Métricas calculadas")
            logger.info(f"   Sharpe: {metrics.sharpe_ratio:.2f}")
            logger.info(f"   Max DD: {metrics.max_drawdown_pct:.2f}%")
            logger.info(f"   Win Rate: {metrics.win_rate_pct:.2f}%")
            
            # 9. RISK CLEARANCE GATE
            metrics.is_go = self._evaluate_risk_gate(metrics)
            if metrics.is_go:
                logger.info("✅ APROVADO para operação")
            else:
                logger.warning("❌ REJEITADO: falha em critérios de risco")
            
            # 10. GENERATE REPORT
            report = BacktestReport(
                request=req,
                metrics=metrics,
                trades=trade_journal,
                equity_curve=equity_curve,
                risk_events=risk_events
            )
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Erro no backtest: {e}", exc_info=True)
            raise
    
    def _validate_request(self, req: BacktestRequest):
        """Validar request contra políticas."""
        # Leverage máximo
        if req.leverage > 10:
            raise ValueError("Leverage máximo é 10x")
        
        # Capital mínimo
        if req.initial_capital < 100:
            raise ValueError("Capital mínimo é $100")
        
        # Datas válidas
        if req.start_date >= req.end_date:
            raise ValueError("start_date deve ser < end_date")
        
        # Profundidade histórica mínima (1 ano)
        DAYS_PER_YEAR = 365
        days_diff = (req.end_date - req.start_date).days
        if days_diff < DAYS_PER_YEAR * 0.9:  # 90% de 1 ano
            raise ValueError("Período deve ser >= 1 ano")
    
    def _apply_overrides(self, gate: 'RiskGate', overrides: dict):
        """Aplicar overrides (com auditoria)."""
        for key, value in overrides.items():
            if key == "max_drawdown_pct":
                gate.MAX_DRAWDOWN_PCT = value
                logger.warning(f"⚠ MAX_DRAWDOWN_PCT override: {value}%")
        return gate
    
    def _evaluate_risk_gate(self, metrics: 'BacktestMetrics') -> bool:
        """
        Risk Clearance: passa em TODOS os critérios?
        
        GO criteria:
        - Sharpe >= 1.0
        - Max DD <= 15%
        - Win Rate >= 45%
        - Profit Factor >= 1.5
        - Consecutive Losses <= 5
        - Calmar Ratio >= 2.0
        """
        checks = [
            ("sharpe_ratio", metrics.sharpe_ratio >= 1.0),
            ("max_drawdown", metrics.max_drawdown_pct <= 15.0),
            ("win_rate", metrics.win_rate_pct >= 45.0),
            ("profit_factor", metrics.profit_factor >= 1.5),
            ("consecutive_losses", metrics.consecutive_losses <= 5),
            ("calmar_ratio", metrics.calmar_ratio >= 2.0)
        ]
        
        all_pass = all(check[1] for check in checks)
        
        for name, passed in checks:
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {name}")
        
        return all_pass
```

---

### **4. worker.py — TimeframeWorker (Strategy Executor)**

```python
"""
worker.py — Worker que processa candles sequencialmente.
Executa strategy e ordens por worker thread.
"""

import logging
from typing import List, Optional
import pandas as pd

from types import Candle, TradeSignal, SignalType
from context import SimulationContext
from simulation.order_engine import OrderSimulator

logger = logging.getLogger(__name__)


class TimeframeWorker:
    """Worker de simulação para timeframe específico."""
    
    def __init__(
        self,
        context: SimulationContext,
        candles: pd.DataFrame,
        strategy: 'Strategy',
        worker_id: int = 0
    ):
        self.context = context
        self.candles_df = candles
        self.strategy = strategy
        self.worker_id = worker_id
        self.order_simulator = OrderSimulator(context)
        
        self.signals_generated = 0
        self.orders_executed = 0
        
        logger.info(f"[Worker {worker_id}] Inicializado com {len(candles)} candles")
    
    def run(self) -> dict:
        """
        Processar candles sequencialmente.
        Retorna dict com estatísticas.
        """
        logger.info(f"[Worker {self.worker_id}] Iniciando processamento")
        
        for idx, row in self.candles_df.iterrows():
            # 1. Criar Candle object
            candle = Candle(
                timestamp=pd.Timestamp(row['timestamp']).to_pydatetime(),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume']),
                timeframe="4h"
            )
            
            # 2. Atualizar RiskGate com preço
            self.context.risk_gate.update_price_feed(candle.close)
            
            # 3. Processar candle
            self._process_candle(candle)
            
            # 4. Executar ordens pendentes
            self._execute_pending_orders()
            
            # 5. Verificar circuito breaker
            if self._check_circuit_breaker():
                logger.warning(f"[Worker {self.worker_id}] ⚡ CB TRIGGERED - finalizando")
                break
        
        logger.info(f"[Worker {self.worker_id}] Concluído: {self.signals_generated} sinais, {self.orders_executed} ordens")
        
        return {
            "worker_id": self.worker_id,
            "signals": self.signals_generated,
            "orders": self.orders_executed
        }
    
    def _process_candle(self, candle: Candle):
        """Processar um candle."""
        try:
            # Aplicar strategy
            signal = self.strategy.evaluate(candle, self.context)
            
            if signal and signal.confidence >= 0.7:
                logger.debug(f"[Worker {self.worker_id}] 📊 Sinal: {signal.signal_type.value} @ {candle.close}")
                self.signals_generated += 1
                
                # Validar setup
                if not self.strategy.validate_setup(signal):
                    logger.debug(f"   Setup inválido após validação")
                    return
                
                # Enfileirar order
                from types import Order
                order = Order.from_signal(
                    signal,
                    symbol=self.context.symbol,
                    qty=self._calculate_position_size(signal, candle)
                )
                self.context.add_order(order)
        
        except Exception as e:
            logger.error(f"[Worker {self.worker_id}] Erro ao processar candle: {e}")
    
    def _execute_pending_orders(self):
        """Executar ordens pendentes."""
        pending = self.context.get_pending_orders()
        
        for order in pending:
            result = self.order_simulator.execute(order)
            
            if result.success:
                logger.info(f"[Worker {self.worker_id}] ✓ Order executada: {result.trade_id}")
                self.orders_executed += 1
                self.context.add_trade(result.trade)
            else:
                logger.warning(f"[Worker {self.worker_id}] ✗ Order rejeitada: {result.error}")
    
    def _check_circuit_breaker(self) -> bool:
        """Verificar se circuit breaker foi acionado."""
        if hasattr(self.context.risk_gate, 'is_circuit_breaker_triggered'):
            if self.context.risk_gate.is_circuit_breaker_triggered():
                return True
        return False
    
    def _calculate_position_size(
        self,
        signal: TradeSignal,
        candle: Candle
    ) -> float:
        """
        Calcular tamanho da posição.
        Risk-based sizing: arriscar 2% do capital por trade.
        """
        capital = self.context.current_capital
        risk_amount = capital * 0.02  # 2% risk
        
        # Distance to SL em dólares
        sl_pct = abs(signal.stop_loss_pct)
        sl_dollars = candle.close * (sl_pct / 100)
        
        # Quantidade = risk / SL distance
        qty = risk_amount / sl_dollars if sl_dollars > 0 else 0
        
        # Limitar ao capital disponível
        max_qty = capital / candle.close
        qty = min(qty, max_qty * 0.5)  # máx 50% do capital
        
        return qty
```

---

## 📊 Exemplo de Uso Completo

```python
# main.py — E2E backtest execution

import asyncio
import logging
from datetime import datetime, timedelta

from backtest.core.orchestrator import BacktestOrchestrator
from backtest.core.types import BacktestRequest
from backtest.data.binance_feed import BinanceHistoricalFeed
from backtest.simulation.strategy import SimpleMovingAverageStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # 1. Configurar
    req = BacktestRequest(
        symbol="BTCUSDT",
        start_date=datetime(2025, 2, 22),
        end_date=datetime(2026, 2, 22),
        initial_capital=10000.0,
        leverage=1.0,
        strategy_params={"lookback": 50, "threshold": 0.7}
    )
    
    # 2. Instanciar orchestrator
    orchestrator = BacktestOrchestrator(
        data_provider=BinanceHistoricalFeed(),
        strategy=SimpleMovingAverageStrategy(req.strategy_params)
    )
    
    # 3. Executar
    try:
        report = await orchestrator.run(req)
        
        # 4. Validar resultado
        if report.metrics.is_go:
            logger.info("✅ ESTRATÉGIA APROVADA")
        else:
            logger.warning("❌ ESTRATÉGIA REJEITADA")
        
        # 5. Exportar
        report.export_json("./reports/backtest_20260222.json")
        report.export_html("./reports/backtest_20260222.html")
        
    except Exception as e:
        logger.error(f"Erro: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🎯 Checklist de Implementação

- [ ] Types + Dataclasses (types.py)
- [ ] SimulationContext (context.py)
- [ ] BacktestOrchestrator (orchestrator.py)
- [ ] TimeframeWorker (worker.py)
- [ ] OrderSimulator (order_engine.py)
- [ ] DataProvider + BinanceHistoricalFeed (data/)
- [ ] MetricsCalculator (metrics/)
- [ ] BacktestReport + Exporters (reporting/)
- [ ] Testes unitários (tests/)
- [ ] Integração RiskGate (risk/)
- [ ] E2E test
- [ ] Documentação inline + docstrings

---

**Próxima fase:** v2.1 - SMC Integration (OrderBlocks + BoS)

