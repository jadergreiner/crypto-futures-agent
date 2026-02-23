# 🏗️ Arquitetura de Engine de Backtesting — Crypto Futures Agent

**Versão:** 2.0 (Production-Ready)  
**Arquiteto:** Arch (#6)  
**Status:** ✅ Design APROVADO  
**Data:** 2026-02-22  
**Escopo:** Production (não MVP)  

---

## 📋 Sumário Executivo

Engine de backtesting que:
- 📊 Processa **1 ano de dados históricos** via Binance REST API  
- 🛡️ Valida **TODAS** as ordens contra Risk Gate 1.0 (CB -3.1%, SL -3%)  
- 📈 Produz **6 métricas críticas** (Sharpe, DD, Win-Rate, PF, etc)  
- 🔌 Preparado para **integração SMC** (Order Blocks + BoS) sem refactor  
- ⚡ **Escalável**: Parallelismo thread-safe, cache multi-nível, formato columnar  

**Padrões de Design**
- Domain-Driven Design (separação clara de responsabilidades)
- Strategy Pattern (simuladores plugáveis)
- Observer Pattern (eventos de trade/risco)
- State Machine (transições de posição validadas)

---

## 🔧 1. Diagrama de Componentes (Visão Estratégica)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKTEST ENGINE v2.0                            │
└─────────────────────────────────────────────────────────────────────┘

                        INPUT LAYER
┌──────────────────────────────────────────────────────────┐
│  DataProvider (BinanceHistoricalFeed)                    │
│  ├─ REST API Binance (1Y historical)                     │
│  ├─ Cache Multi-Nível (SQLite/Parquet)                   │
│  └─ Validation: Gaps, duplicates, OHLCV integrity        │
└──────────────────────────────────────────────────────────┘
                            ↓
                   REQUEST PIPELINE
┌──────────────────────────────────────────────────────────┐
│  BacktestRequest (objeto imutável)                       │
│  ├─ symbol, start_date, end_date                         │
│  ├─ initial_capital, leverage, mode (paper/live)         │
│  ├─ strategy_params                                      │
│  └─ risk_gate_overrides (≠ padrão = auditado)            │
└──────────────────────────────────────────────────────────┘
                            ↓
              ORCHESTRATION + VALIDATION LAYER
┌──────────────────────────────────────────────────────────┐
│  BacktestOrchestrator (Orquestrador Principal)           │
│  ├─ Valida request contra restrições políticas           │
│  ├─ Inicializa SimulationContext (state)                 │
│  ├─ Cria RiskGate instance (copy funcional)              │
│  └─ Agenda workers paralelos (TimeframeWorker x N)       │
└──────────────────────────────────────────────────────────┘
                            ↓
         ┌──────────────────┴──────────────────┐
         ↓                                      ↓
    SIMULATION WORKERS (Paralelo)         RISK VALIDATION
┌──────────────────────────────┐  ┌──────────────────────┐
│ TimeframeWorker[H4]          │  │ RiskGate (Singleton) │
│ ├─ Lê OHLCV                  │  │ ├─ MAX_DD -3%        │
│ ├─ Aplica strategy           │  │ ├─ SL -3%            │
│ ├─ Gera sinais de entrada    │  │ ├─ CB -3.1%          │
│ ├─ Enfilera orders           │  │ └─ Audit trail       │
│ └─ Publica eventos           │  └──────────────────────┘
└──────────────────────────────┘         ↑
         ↓                                │
    ORDER ENGINE               VALIDATION GATE
┌──────────────────────────────┐  ┌──────────────────────┐
│ OrderSimulator               │  │ OrderValidator       │
│ ├─ Prix, slippagem, comissão │  │ ├─ Risk check        │
│ ├─ Market/Limit execution    │  │ ├─ Saldo check       │
│ ├─ Stop Loss + TP entry      │  │ ├─ Leverage check    │
│ ├─ Position reconciliation   │  │ └─ Anti-fraud checks │
│ └─ Emite TradeExecuted       │  └──────────────────────┘
└──────────────────────────────┘         ↑
         │                                │
         └────────────┬────────────────────┘
                      ↓
         POSITION STATE MACHINE
┌──────────────────────────────────────┐
│ PositionStateMachine                 │
│ ├─ IDLE → OPENING → OPEN → CLOSING   │
│ ├─ Transições auditadas              │
│ ├─ PnL tracking real-time            │
│ └─ Events: PositionOpened,           │
│    PositionClosed, SLTriggered       │
└──────────────────────────────────────┘
                      ↓
         METRICS + REPORTING LAYER
┌──────────────────────────────────────┐
│ EquityCurveTracker                   │
│ ├─ Registra capital @ cada candle    │
│ ├─ Drawdown tracking                 │
│ └─ Risk-free rate normalization      │
└──────────────────────────────────────┘
         ↓              ↓              ↓
    ┌────────────┬─────────────┬─────────────┐
    ↓            ↓             ↓             ↓
  SHARPE    MAX_DRAWDOWN  WIN_RATE   PROFIT_FACTOR
┌──────────────────────────────────────────────────┐
│ MetricsCalculator (Fórmulas Standard)            │
│ ├─ Sharpe = (μ - rf) / σ * √252                  │
│ ├─ DD = (P - Peak) / Peak                        │
│ ├─ Calmar = Return / MaxDD                       │
│ ├─ Sortino = (μ - rf) / σ_down * √252            │
│ └─ PF = GrossProfit / GrossLoss                  │
└──────────────────────────────────────────────────┘
                      ↓
         OUTPUT LAYER (Relatório)
┌──────────────────────────────────────────────────┐
│ BacktestReport                                   │
│ ├─ metrics: BacktestMetrics (6 góticos)          │
│ ├─ trades: List[Trade] (auditável)               │
│ ├─ equity: List[float] (série temporal)          │
│ ├─ risk_events: List[RiskEvent] (CB/SL)          │
│ ├─ performance_by_hour: Dict (seasonality)       │
│ └─ export: JSON, Parquet, HTML (charts)          │
└──────────────────────────────────────────────────┘
```

---

## 🎯 2. Classes Principais (Nomes + Responsabilidades)

### **2.1 Camada de Dados**

#### `DataProvider` (ABC)
Abstração para feeds de dados históricos.  
**Responsabilidades:**
- Buscar OHLCV de 1Y via Binance REST API
- Validar integridade (gaps, duplicatas, extremos)
- Cache multi-nível (memória → SQLite → Parquet)
- Thread-safe para acesso concorrente

**Assinatura:**
```python
class DataProvider(ABC):
    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,  # "1h", "4h", "1d"
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame: ...
    
    @abstractmethod
    def validate_data(self, df: pd.DataFrame) -> ValidationResult: ...
```

#### `BinanceHistoricalFeed` (implements DataProvider)
**Responsabilidades:**
- Fragmentar request em chunks (Binance limit 1000 candles/request)
- Rate limiting (Binance Spot 1200 req/min, Futures 2400 req/min)
- Cache em SQLite (chave: symbol + timeframe + date_range)
- Fallback para Parquet em prod (mais rápido)

**Validações críticas:**
- Sem gaps > 1 candle
- Timestamps monotonicamente crescentes
- Volume + close consistentes (não extremos)

---

### **2.2 Camada de Orquestração**

#### `BacktestRequest` (dataclass imutável)
Contrato de entrada. **VALIDADO antes de processamento.**  
```python
@dataclass(frozen=True)
class BacktestRequest:
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float  # USDT
    leverage: float = 1.0  # 1.0 = sem alavancagem
    mode: Literal["paper", "live"] = "paper"
    strategy_params: Dict[str, Any]
    # Overrides: só com auditoria
    risk_gate_overrides: Optional[Dict[str, float]] = None
```

#### `BacktestOrchestrator` (Padrão Strategy)
**Responsabilidades:**
- Validar request contra políticas (e.g., max leverage = 10x)
- Inicializar `SimulationContext` (state compartilhado)
- Spawn `TimeframeWorker` threads paralelas
- Agregar resultados em `BacktestReport`
- Tratamento de erros + retry logic

**Pseudocódigo:**
```python
class BacktestOrchestrator:
    async def run(self, req: BacktestRequest) -> BacktestReport:
        # 1. Validação
        self._validate_request(req)
        
        # 2. Context init
        ctx = SimulationContext(
            initial_capital=req.initial_capital,
            risk_gate=RiskGate()  # Copy funcional do RiskGate
        )
        
        # 3. Fetch data
        data = await self.data_provider.fetch_ohlcv(
            req.symbol, "4h", req.start_date, req.end_date
        )
        
        # 4. Workers paralelos
        workers = [
            TimeframeWorker(ctx, chunk) 
            for chunk in chunk_data(data, chunk_size=1000)
        ]
        results = await asyncio.gather(*workers)
        
        # 5. Agregação + Relatório
        return self._aggregate_results(results, ctx)
```

---

### **2.3 Camada de Simulação**

#### `SimulationContext` (State Holder)
Thread-safe container para estado compartilhado.  
**Responsabilidades:**
- `positions: Dict[str, Position]` (rastreamento de PnL)
- `equity_curve: List[float]` (capital ao longo do tempo)
- `risk_gate: RiskGate` (instância, não singleton)
- `trade_journal: List[Trade]` (auditoria completa)
- Locks para acesso concorrente

**Garantias:**
- Nenhuma race condition em updates de `equity_curve`
- Nenhuma ordem executa sem passar por RiskGate

---

#### `TimeframeWorker` (Strategy + Executor)
**Responsabilidades:**
- Ler candles sequencialmente (respeita ordem temporal)
- Aplicar strategy (SMC/BoS em v2.1+)
- Gerar sinais de entrada/saída (sem ordem)
- Enfileirar orders em `OrderQueue`
- Emitir eventos (TradeOpened, etc)

**Pseudocódigo:**
```python
class TimeframeWorker:
    def process_candle(self, candle: Candle) -> List[TradeSignal]:
        # 1. Atualizar RiskGate com preço atual
        self.ctx.risk_gate.update_price_feed(candle.close)
        
        # 2. Aplicar strategy
        signal = self.strategy.evaluate(candle, self.ctx)
        
        # 3. Validar signal
        if not signal or signal.confidence < 0.7:
            return []
        
        # 4. Enfileirar order (não executa aqui!)
        order = Order.from_signal(signal)
        self.ctx.order_queue.append(order)
        
        return [signal]
```

#### `OrderSimulator` (Order Execution Engine)
**Responsabilidades:**
- Simular execução market/limit com slippagem realista
- Calcular comissão (Binance 0.02% maker, 0.04% taker)
- Validar saldo (capital - margin)
- Criar posição ou agregar (se já em posição)
- Registrar preço médio de entrada

**Fórmulas críticas:**
```
entry_price_slippage = entry_price * (1 + slippage_bps / 10000)
commission = position_value * (fee_rate)
position_pnl = (current_price - entry_price) * qty
unrealized_pnl_pct = position_pnl / margin_used

# Stop Loss trigger
if current_price <= entry_price * (1 - MAX_DRAWDOWN_PCT / 100):
    TRIGGER SL  # RiskGate validates & closes
```

---

### **2.4 Camada de Risco + Validação**

#### `OrderValidator` (Gate Padrão)
**Responsabilidades:**
- Runtime validation de cada order
- Checks: saldo, leverage, margin, risk gate
- Rejeita orders violando limites
- Registra rejeição em audit trail

**Pseudocódigo:**
```python
class OrderValidator:
    def validate(
        self,
        order: Order,
        ctx: SimulationContext
    ) -> ValidationResult:
        checks = [
            self._check_risk_gate_status(ctx),
            self._check_balance(order, ctx),
            self._check_leverage(order, ctx),
            self._check_max_position_size(order, ctx),
            self._check_anti_martingale(order, ctx)
        ]
        
        failed = [c for c in checks if not c.passed]
        return ValidationResult(
            passed=len(failed) == 0,
            failures=failed
        )
```

#### `PositionStateMachine` (State Pattern)
**Responsabilidades:**
- Transições: IDLE → OPENING → OPEN → CLOSING → CLOSED
- Validação de transições permitidas
- Event emission para cada mudança
- Cálculo de PnL na transição

**Diagrama de Estados:**
```
    IDLE
     ↓
  OPENING (order na fila/executando)
     ↓
    OPEN (ordem executada, posição ativa)
     ↑
     │ (SL triggered? BoS saída? TP atingido?)
     ↓
  CLOSING (ordem de fechamento)
     ↓
  CLOSED (PnL realizado, saído de mercado)
```

---

### **2.5 Camada de Métricas + Relatório**

#### `BacktestMetrics` (dataclass)
**6 Métricas Críticas (GO/NO-GO):**

```python
@dataclass
class BacktestMetrics:
    # 🎯 Critérios de Passagem (Risk Clearance Gates)
    sharpe_ratio: float              # MIN >= 1.0
    max_drawdown_pct: float          # MAX <= 15%
    win_rate_pct: float              # MIN >= 45%
    profit_factor: float             # MIN >= 1.5
    consecutive_losses: int          # MAX <= 5
    calmar_ratio: float              # MIN >= 2.0
    
    # 📊 Métricas Informativas
    sortino_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_return_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    recovery_factor: float
    
    # ✓ Resultado Final
    is_go: bool  # True se passa em TODOS os critérios
```

#### `MetricsCalculator` (Fórmulas Padrão)
**Responsabilidades:**
- Sharpe = (μ_ret - rf) / σ_ret * √252
- DD = (Peak - Valley) / Peak
- Calmar = Total_Return / Max_DD
- Sortino = (μ_ret - rf) / σ_downside * √252
- PF = Gross_Profit / |Gross_Loss|

**Pseudocódigo:**
```python
class MetricsCalculator:
    @staticmethod
    def calculate_sharpe_ratio(
        equity_curve: List[float],
        risk_free_rate: float = 0.02
    ) -> float:
        returns = np.diff(equity_curve) / equity_curve[:-1]
        excess_return = returns - (risk_free_rate / 252)
        return np.mean(excess_return) / np.std(excess_return) * np.sqrt(252)
```

#### `EquityCurveTracker` (Time Series)
**Responsabilidades:**
- Registrar capital ao final de cada candle
- Tracking de peak (para drawdown)
- Normalização para risk-free rate
- Cache em array numpy (rápido)

---

#### `BacktestReport` (Output)
**Responsabilidades:**
- Agregação de resultados finais
- Serialização para JSON/Parquet/HTML
- Grafos (equity curve, drawdown, win/loss)
- Auditoria completa

**Estrutura:**
```python
@dataclass
class BacktestReport:
    metrics: BacktestMetrics
    trades: List[Trade]              # Auditável
    equity_curve: List[float]        # Curva de capital
    risk_events: List[RiskEvent]     # CB/SL triggers
    performance_by_hour: Dict[int, float]
    performance_by_day: Dict[str, float]
    
    def export_json(self) -> str: ...
    def export_html(self) -> str: ...
    def export_parquet(self) -> None: ...
```

---

## 📍 3. Fluxo de Dados (Entrada → Processamento → Saída)

### **Sequência Temporal Completa**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ INPUT: BacktestRequest                                                  │
│ {symbol: "BTCUSDT", start: "2025-02-22", end: "2026-02-22", ...}        │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │ 1. VALIDATION GATE                                    │
        │ ├─ Policy checks (leverage, capital, etc)            │
        │ └─ ✅ Passa → continue                               │
        └───────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │ 2. DATA FETCHING (async paralelo)                     │
        │ ├─ BinanceHistoricalFeed.fetch_ohlcv()               │
        │ ├─ Cache check (SQLite/Parquet)                      │
        │ ├─ Fallback: REST API + Rate Limit                   │
        │ └─ DataFrame[timestamp, open, high, low, close, vol] │
        └───────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │ 3. SIMULATION INIT                                    │
        │ ├─ SimulationContext(capital=init_cap)               │
        │ ├─ RiskGate copy (standalone)                        │
        │ ├─ PositionStateMachine [IDLE]                       │
        │ └─ EquityCurveTracker init                           │
        └───────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │ 4. WORKER THREADS (ParallelExecutor)                 │
        │ [Por cada 1000 candles → TimeframeWorker]            │
        │                                                       │
        │  Loop para cada candle sequencialmente:              │
        │  ├─ RiskGate.update_price_feed(candle.close)        │
        │  ├─ Strategy.evaluate()                              │
        │  ├─ Enfileirar Order se sinal                        │
        │  └─ OrderSimulator.execute()                         │
        │      ├─ RiskGate.validate_order()                    │
        │      ├─ Slippagem + comissão                         │
        │      ├─ PositionStateMachine [CLOSING/OPENING]       │
        │      └─ Registrar Trade em journal                   │
        │                                                       │
        │  Após execução:                                       │
        │  ├─ EquityCurveTracker.record(capital)               │
        │  ├─ Check RiskGate → CB triggered?                   │
        │  │  └─ SIM: Fechar TUDO + halt                       │
        │  └─ Emitir evento (TradeExecuted, etc)               │
        └───────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │ 5. AGREGAÇÃO DE RESULTADOS                           │
        │ ├─ Merge simulation contexts                         │
        │ ├─ Concatenar equity curves                          │
        │ ├─ Compilar trade journal                            │
        │ └─ Detectar risk events (CB/SL)                      │
        └───────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │ 6. METRICS CALCULATION                               │
        │ ├─ MetricsCalculator.calculate_all()                 │
        │ ├─ Sharpe, DD, Calmar, Sortino, etc                  │
        │ ├─ Trade statistics (win%, PF, etc)                  │
        │ └─ Performance by hour/day                           │
        └───────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │ 7. RISK CLEARANCE GATE                               │
        │ ├─ sharpe_ratio >= 1.0?                              │
        │ ├─ max_drawdown <= 15%?                              │
        │ ├─ win_rate >= 45%?                                  │
        │ ├─ profit_factor >= 1.5?                             │
        │ ├─ consecutive_losses <= 5?                          │
        │ ├─ calmar_ratio >= 2.0?                              │
        │ └─ is_go = ALL PASS? (bool)                          │
        └───────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │ 8. REPORT GENERATION                                 │
        │ ├─ BacktestReport(metrics, trades, equity_curve)     │
        │ ├─ Export: JSON, Parquet, HTML                       │
        │ └─ Audit trail integrado                             │
        └───────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ OUTPUT: BacktestReport                                                  │
│ {is_go: True/False, sharpe: 1.45, max_dd: 8.3%, trades: [...], ...}    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 4. Interfaces de Integração com SMC

**Contrato Future para Order Blocks + BoS (v2.1+)**

### **Interface: `Strategy` (ABC)**
Toda strategy deve herdar desta interface para plugabilidade.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class SignalType(Enum):
    """Tipos de sinal."""
    BUY = "buy"
    SELL = "sell"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    HOLD = "hold"

@dataclass
class TradeSignal:
    """Contrato de sinal gerado pela strategy."""
    signal_type: SignalType
    confidence: float          # 0.0 - 1.0
    entry_price: float
    stop_loss_pct: float       # e.g., -3.0 = -3%
    take_profit_pct: float     # e.g., 6.0 = +6%
    reason: str                # log do porquê (auditável)
    metadata: Dict[str, Any]   # dados adicionais para auditoria

class Strategy(ABC):
    """Interface base para strategies."""
    
    @abstractmethod
    def evaluate(
        self,
        candle: Candle,
        ctx: SimulationContext
    ) -> Optional[TradeSignal]:
        """
        Avaliar candle e gerar sinal.
        
        Args:
            candle: Candle atual
            ctx: Estado da simulação
            
        Returns:
            TradeSignal se há setup, None caso contrário
        """
        pass
    
    @abstractmethod
    def validate_setup(self, signal: TradeSignal) -> bool:
        """Validação adicional antes de execução."""
        pass

# Exemplo: Strategy SMC (v2.1+)
class SmcStrategy(Strategy):
    """
    Smart Money Concepts strategy.
    Detecta Order Blocks e Break of Structure.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.order_block_detector = OrderBlockDetector(config)
        self.bos_detector = BreakOfStructureDetector(config)
    
    def evaluate(
        self,
        candle: Candle,
        ctx: SimulationContext
    ) -> Optional[TradeSignal]:
        """
        1. Detecta Order Block recente
        2. Detecta Break of Structure
        3. Computa risk/reward ratio
        4. Retorna sinal se R:R >= 1:2
        """
        # Implementação em v2.1
        pass
```

### **Interface: `OrderBlockDetector` (v2.1+)**
```python
@dataclass
class OrderBlock:
    """Estrutura de um order block identificado."""
    timestamp: datetime
    high: float
    low: float
    break_direction: Literal["up", "down"]  # para qual lado quebrou
    confirmation_candle: int  # candle que confirmou
    strength: float  # 0.0-1.0 (força do bloco)

class OrderBlockDetector(ABC):
    """Detecta order blocks no chart."""
    
    @abstractmethod
    def detect(
        self,
        candles: List[Candle],
        lookback_bars: int = 50
    ) -> List[OrderBlock]:
        """Buscar order blocks nos últimos N candles."""
        pass
```

### **Interface: `BreakOfStructureDetector` (v2.1+)**
```python
@dataclass
class BreakOfStructure:
    """Estrutura de um BoS identificado."""
    timestamp: datetime
    price_level: float
    direction: Literal["up", "down"]  # qual estrutura quebrou
    confirmation_strength: float  # 0.0-1.0

class BreakOfStructureDetector(ABC):
    """Detecta BoS (Higher Highs/Lows quebradas)."""
    
    @abstractmethod
    def detect(
        self,
        candles: List[Candle],
        lookback_bars: int = 50
    ) -> Optional[BreakOfStructure]:
        """Buscar BoS recente (últimos N candles)."""
        pass
```

### **Contrato de Integração**
```python
# Em TimeframeWorker, após integração SMC (v2.1+):

def process_candle_with_smc(self, candle: Candle) -> List[TradeSignal]:
    """
    1. Detectar Order Block
    2. Detectar BoS
    3. Combinar com strategy existente
    4. Validar risk/reward
    """
    # Pseudocódigo
    order_block = self.smc_detector.detect_order_block(
        self.candle_buffer[-50:]
    )
    bos = self.smc_detector.detect_bos(self.candle_buffer[-50:])
    
    if order_block and bos:
        # Existe setup SMC
        signal = self.strategy.evaluate_smc_setup(
            order_block, bos, candle, self.ctx
        )
        return [signal] if signal else []
    
    return []
```

---

## ⚡ 5. Recomendações de Performance + Caching

### **5.1 Estratégia de Cache Multi-Nível**

```
Request de candles
    ↓
[L1: In-Memory Cache]  ← 1-24h (LRU, máx 1GB)
    ↓ miss
[L2: SQLite Local]     ← 1 semana (thread-safe)
    ↓ miss
[L3: Parquet Archive]  ← Full history (columnar, rápido)
    ↓ miss
[L4: Binance REST API] ← Rede (rate limited, 2400 req/min)
```

**Implementação:**
```python
class CachedDataProvider(DataProvider):
    """DataProvider com caching automático."""
    
    def __init__(self):
        self.l1_cache = LRUCache(max_size_mb=1024)
        self.l2_db = SqliteCache("./data/cache.db")
        self.l3_archive = ParquetArchive("./data/history/")
    
    async def fetch_ohlcv(self, symbol, tf, start, end):
        cache_key = f"{symbol}:{tf}:{start}:{end}"
        
        # L1 check
        if cache_key in self.l1_cache:
            return self.l1_cache[cache_key]
        
        # L2 check
        cached = self.l2_db.get(cache_key)
        if cached is not None:
            self.l1_cache[cache_key] = cached
            return cached
        
        # L3 check (Parquet bulk read)
        try:
            df = pd.read_parquet(
                f"{self.l3_archive}/{symbol}/{tf}.parquet",
                filters=[(
                    ('timestamp', '>=', start),
                    ('timestamp', '<=', end)
                )]
            )
            self.l1_cache[cache_key] = df
            return df
        except FileNotFoundError:
            pass
        
        # L4: Fetch from Binance
        df = await self._fetch_from_binance(symbol, tf, start, end)
        
        # Populate all caches
        self.l1_cache[cache_key] = df
        self.l2_db.set(cache_key, df)
        
        return df
```

### **5.2 Paralelismo + Thread Safety**

```python
# Usar asyncio + ThreadPoolExecutor para I/O
class BacktestOrchestrator:
    async def run(self, req: BacktestRequest):
        # Fetch data (async)
        data_task = asyncio.create_task(
            self.data_provider.fetch_ohlcv(...)
        )
        
        # Enquanto espera: preparar config
        config = self._prepare_config(req)
        
        # Aguardar data
        data = await data_task
        
        # Spawn workers (threads paralelos, thread-safe)
        executor = ThreadPoolExecutor(max_workers=4)
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            workers = [
                executor.submit(
                    TimeframeWorker(ctx, chunk).run
                )
                for chunk in self._chunk_data(data)
            ]
            results = [w.result() for w in workers]
```

### **5.3 Formato Columnar (Parquetização)**

```python
# Em vez de salvar trades em JSON, usar Parquet
# Mais rápido em leitura, compressão melhor

class BacktestReport:
    def export_parquet(self, path: str):
        """Export eficiente para histórico."""
        trades_df = pd.DataFrame([
            asdict(trade) for trade in self.trades
        ])
        trades_df.to_parquet(
            f"{path}/trades.parquet",
            compression="snappy",
            index=False
        )
        
        equity_df = pd.DataFrame({
            'timestamp': self.timestamps,
            'equity': self.equity_curve,
            'drawdown_pct': self.drawdowns_pct
        })
        equity_df.to_parquet(
            f"{path}/equity.parquet",
            compression="snappy"
        )
```

### **5.4 Otimizações Críticas**

| Otimização | Impacto | Implementação |
|------------|---------|----------------|
| **NumPy vectorization** | 100x mais rápido | Evitar loops em arrays |
| **Parquet over JSON** | 10x menor storage | Guardar históricos em .parquet |
| **LRUCache em L1** | 1000x acesso local | Máx 1GB em memória |
| **Chunking & multiprocessing** | 4x parallelismo | 4 workers simultâneos |
| **Pre-computed indicators** | 50% menos CPU | Calcular antes do backtest |

---

## 📖 Padrões Implementados

| Padrão | Uso | Benefício |
|--------|-----|----------|
| **Domain-Driven Design** | Separação clara entre camadas | Manutenibilidade |
| **Strategy Pattern** | Strategies plugáveis (SMC futura) | Extensibilidade |
| **Observer Pattern** | Eventos (TradeExecuted, RiskEvent) | Desacoplamento |
| **State Machine** | Transições Position (IDLE → OPEN) | Safety semântico |
| **Builder Pattern** | BacktestRequest imutável | Immutability |
| **Template Method** | DataProvider ABC | Contrato claro |
| **Singleton (RiskGate em SimContext)** | Uma instância por simulação | Consistency |

---

## 🛡️ Garantias de Segurança (Risk Gate 1.0)

✅ **Nenhuma ordem executa sem validação RiskGate**  
✅ **Stop Loss -3% SEMPRE ativo (hardcoded)**  
✅ **Circuit Breaker -3.1% fecha TUDO + para por 24h**  
✅ **Auditoria completa de cada decisão (logs + DB)**  
✅ **Drawdown tracking real-time (peak tracking)**  
✅ **Validação anti-martingale (impede oversizing)**

---

## 📊 Exemplo de Uso (E2E)

```python
# 1. Criar request
req = BacktestRequest(
    symbol="BTCUSDT",
    start_date=datetime(2025, 2, 22),
    end_date=datetime(2026, 2, 22),
    initial_capital=10000.0,
    leverage=1.0,
    mode="paper",
    strategy_params={"lookback": 50, "threshold": 0.7}
)

# 2. Executar
orchestrator = BacktestOrchestrator(
    data_provider=BinanceHistoricalFeed(),
    strategy=MyStrategy(req.strategy_params)
)
report = await orchestrator.run(req)

# 3. Validar GO/NO-GO
if report.metrics.is_go:
    print("✅ Estratégia APROVADA para operação")
    print(f"   Sharpe: {report.metrics.sharpe_ratio:.2f}")
    print(f"   Max DD: {report.metrics.max_drawdown_pct:.2f}%")
else:
    print("❌ Estratégia REJEITADA")
    print(f"   Razões: {report.metrics.get_failure_reasons()}")

# 4. Exportar
report.export_json("./backtests/report_20260222.json")
report.export_html("./reports/chart_20260222.html")
```

---

## 🔄 v2.1+: Roadmap SMC Integration

- [ ] `OrderBlockDetector` implementation
- [ ] `BreakOfStructureDetector` implementation
- [ ] `SmcStrategy` base class
- [ ] Risk/reward ratio validation (min 1:2)
- [ ] Order block breakdown signals
- [ ] Multi-timeframe confluence (1h + 4h + 1d)
- [ ] A/B testing framework (SMC vs original)

---

**Autor:** Arch (#6) | **Guardião:** Board  
**Versão:** 2.0 | **Status:** 🟢 Production-Ready Design  
**Próxima Review:** Sprint 2 (Planning)

