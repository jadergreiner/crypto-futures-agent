# 🏗️ Arquitetura do Sistema — Crypto Futures Agent

**Versão:** 1.0.0  
**Data:** 27 FEV 2026  
**Status:** ✅ PRODUCTION-READY  
**Owner:** Arch (#6) — Software Architect

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Componentes Principais](#componentes-principais)
3. [Fluxos de Dados](#fluxos-de-dados)
4. [Camadas Aplicacionais](#camadas-aplicacionais)
5. [Padrões de Design](#padrões-de-design)
6. [Segurança e Risco](#segurança-e-risco)
7. [Performance e Escalabilidade](#performance-e-escalabilidade)
8. [Deployment e Operações](#deployment-e-operações)
9. [Decisões Arquiteturais](#decisões-arquiteturais)

---

## Visão Geral

### 🎯 Objetivo do Sistema

Agente autônomo de trading de futuros criptográficos com:
- **Preservação de capital** como prioridade #1
- **Execução precisa** de estratégias baseadas em Smart Money Concepts (SMC)
- **Risco controlado** via circuitos de proteção invioláveis
- **Machine Learning** (PPO) para otimização contínua

### 🏗️ Arquitetura em Camadas

```
┌─────────────────────────────────────────────────────────────┐
│                      USER LAYER                             │
│  (Dashboard Web, Telegram Alerts, REST API)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              APPLICATION LAYER                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Orchestrator (main.py)                              │   │
│  │ ├─ Strategy Deploy (Heurísticas → PPO)             │   │
│  │ ├─ Position Manager                                │   │
│  │ └─ Risk Guardian (Circuit Breaker)                 │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│            BUSINESS LOGIC LAYER                             │
│  ┌──────────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  Strategy Engine │  │  Risk Gates  │  │  Execution  │  │
│  │  ├─ SMC Detect   │  │  ├─ RiskGate│  │  ├─ Orders  │  │
│  │  ├─ Signals      │  │  ├─ Circuit │  │  ├─ Position│  │
│  │  └─ Confidence   │  │  └─ Alerts  │  │  └─ Monitor │  │
│  └──────────────────┘  └──────────────┘  └─────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│            DATA & INFRASTRUCTURE LAYER                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐│
│  │ Data Pipeline    │  │ Binance API      │  │ Database  ││
│  │ ├─ OHLCV Cache   │  │ ├─ REST (Orders) │  │ ├─ Trades ││
│  │ ├─ Indicators    │  │ ├─ WebSocket     │  │ ├─ Pos    ││
│  │ └─ Features      │  │ └─ Rate Limits   │  │ └─ Risk   ││
│  └──────────────────┘  └──────────────────┘  └───────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes Principais

### 1. **Data Pipeline** (`data/`)

**Responsabilidade:** Coletar, processar e cacheáveis dados históricos e live.

**Componentes:**
- **Binance API Integration** (`binance_api.py`)
  - REST: Ordens, saldos, posições abertas
  - WebSocket: Streams de preço em tempo real
  - Rate limit control: 1.200 req/min
  - Retry logic com backoff exponencial

- **OHLCV Cache** (Parquet storage)
  - Dados históricos: 1 ano × 60-200 símbolos
  - Compressão: zstd (melhor ratio)
  - Latência: <100ms read
  - TTL: 24h com invalidação inteligente

- **Feature Engineering** (`indicators/`)
  - EMA, RSI, MACD, Bollinger Bands
  - Volume Profile, OBV, ATR, ADX
  - Smart Money Concepts (SMC) indicators
  - 104+ features para ML training

**Fluxo de Dados:**
```
Binance API → Cache (Parquet) → Feature Engineering → Strategy/Backtest
    ↓
Reconnect logic (exponential backoff)
Rate limit queue
```

---

### 2. **Strategy Engine** (`execution/` + `agent/`)

**Responsabilidade:** Gerar sinais de trading e decidir sobre posições.

**Componentes:**

#### **Layer 0: Heurísticas** (`execution/heuristic_signals.py`)
Regras determinísticas hand-crafted para go-live imediato:
- **SMC Detection** (Order Blocks, Break of Structure)
- **Confluence Scoring** (8+ confirmações simultâneas)
- **EMA Alignment** (D1 → H4 → H1 estrutura)
- **RSI Position** (Oversold/Overbought validation)
- **ADX Trending** (Confirmar tendência)
- **Risk Gates** inline (Max drawdown 5%, -3% circuit breaker)
- **Signal Confidence** (>70% threshold)

**Saída:** LONG/SHORT/HOLD com confiança

#### **Layer 1-6: PPO Model** (Machine Learning)
Reinforcement Learning (Proximal Policy Optimization):
- **State Space:** 104 features normalizados
- **Action Space:** LONG / SHORT / HOLD / CLOSE
- **Reward:** Sharpe-optimized (profit + drawdown penalty)
- **Training:** 500k timesteps em dados 1Y
- **Validation:** Walk-forward OOT testing

**Saída:** Policy π(a|s) com confiança

#### **Decision Logic** (`position_manager.py`)
Combina Layer 0 + Layer 1:
```python
if Layer0_Confidence > 0.7:
    signal = Layer0_signal  # Heurísticas confiantes
else if Layer1_Confidence > 0.6:
    signal = Layer1_signal  # PPO backup
else:
    signal = HOLD  # Espera by default
```

---

### 3. **Risk Management** (`risk/`)

**Responsabilidade:** Proteger capital contra perdas catastróficas.

**Componentes:**

#### **RiskGate 1.0** (`circuit_breaker.py`)
Proteção inviolável contra drawdown:
- **Limite Duro:** -3% por semana (triggers automatic halt)
- **Callback:** Notificação em tempo real (Telegram)
- **Recovery:** Manual intervention ou 50% position close
- **Logic:** Sempre ativo, sem bypass

#### **Position Manager** (`position_monitor.py`)
Gerenciamento dinâmico de posições abertas:
- **Trailing Stop Loss** (1.5x ATR, ajustável)
- **Take Profit** (3.0x ATR target)
- **Liquidation Alert:** Margin ratio > 90%
- **Underwater Position:** Gestão ativa (Decision #3)

#### **Risk Validators** (`validators.py`)
Validações em cada operação:
- Tamanho de posição (max leverage 10x)
- Fundrise rate extremo (>2% ao ano = skip)
- Liquidity check (min 10 BTC volume)
- Slippage estimate (<2% tolerance)

---

### 4. **Order Execution** (`execution/order_executor.py`)

**Responsabilidade:** Executar ordens com segurança e eficiência.

**Componentes:**
- **Order Types:** Market, Limit, VWAP (para grandes volumes)
- **Pre-flight Checks:** Saldo, margin ratio, rate limits
- **Execution:** Parallelizable em múltiplos pares
- **Telemetry:** Latency, slippage, fill ratio
- **Rollback:** Cancel position se falha crítica

**Fluxo:**
```
Signal → RiskGate OK? → Validators OK? → Pre-flight OK? 
  ↓ YES
  → Place Order (Market order para imediatismo)
  → Monitor fill (callback in <500ms)
  → Update position state
  → Log telemetry
```

---

### 5. **Backtesting Engine** (`backtest/`)

**Responsabilidade:** Validar estratégias em dados históricos antes de go-live.

**Componentes:**
- **Backtester** (`backtest_core.py`): Simulação full
- **Trade State Machine** (`trade_state_machine.py`): Gerencia trades
- **Walk-Forward Validator** (`walk_forward.py`): OOT testing
- **Metrics** (`metrics.py`): Sharpe, MaxDD, WinRate, ProfitFactor

**Métricas de Validação:**
- Sharpe Ratio: ≥1.0 (quality standard)
- Max Drawdown: ≤15% (risk target)
- Profit Factor: ≥1.5 (win rate)
- Consecutive Losses: ≤5 (stop loss discipline)

---

### 6. **Logging & Telemetria** (`logs/`)

**Responsabilidade:** Registrar todas operações para auditoria.

**Componentes:**
- **Trade Log:** Cada ordem (timestamp, symbol, side, price, size, fee)
- **Event Log:** Sinais gerados, gates triggered, erros
- **Performance Log:** Latência API, fill rates, slippage
- **Audit Trail:** Completo para compliance (blockchain-style hash)

---

## Fluxos de Dados

### 🔄 Fluxo Principal: Trading Loop

```
┌─────────────────────────────────────────────────────────┐
│                      MAIN LOOP (5s tick)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. Fetch Live Data (WebSocket)                 │   │
│  │    ├─ OHLC atualizado para 60+ símbolos       │   │
│  │    └─ Compute 104 features (fast, cached)      │   │
│  └─────────────────────────────────────────────────┘   │
│                       ↓                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 2. Generate Signals (Determinístico)            │   │
│  │    ├─ Layer 0: Heurísticas (sempre rápido)    │   │
│  │    ├─ Layer 1-6: PPO (se disponível, <100ms)  │   │
│  │    └─ Combine lógica (confidence-weighted)     │   │
│  └─────────────────────────────────────────────────┘   │
│                       ↓                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 3. Risk Check (Inviolável)                     │   │
│  │    ├─ RiskGate: -3% limit OK?                  │   │
│  │    ├─ Margin: <90% ratio?                      │   │
│  │    ├─ Validators: Size, liquidity, slippage OK?│   │
│  │    └─ IF ANY FAIL → SKIP signal, alert         │   │
│  └─────────────────────────────────────────────────┘   │
│                       ↓ (IF PASS)                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 4. Execute Order (Async, Parallelizable)       │   │
│  │    ├─ Place Market Order (Binance)             │   │
│  │    ├─ Monitor Fill Callback (<500ms)           │   │
│  │    └─ Update Position State                    │   │
│  └─────────────────────────────────────────────────┘   │
│                       ↓                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 5. Monitor & Log                               │   │
│  │    ├─ Trailing Stop Loss check                 │   │
│  │    ├─ Log telemetry (latency, slippage)        │   │
│  │    ├─ Send alerts (Telegram, if critical)      │   │
│  │    └─ Audit trail append (database + file)     │   │
│  └─────────────────────────────────────────────────┘   │
│                       ↓                                  │
│                  NEXT TICK (5s)                         │
└─────────────────────────────────────────────────────────┘
```

### 📊 Fluxo de Backtesting

```
┌────────────────────────────────────────────────────────┐
│              BACKTEST WORKFLOW                         │
│  ┌──────────────────────────────────────────────┐    │
│  │ 1. Load Historical Data (1Y × 60 symbols)   │    │
│  │    └─ Parquet → DataFrame (Pandas)          │    │
│  └──────────────────────────────────────────────┘    │
│                     ↓                                  │
│  ┌──────────────────────────────────────────────┐    │
│  │ 2. Walk-Forward Testing (OOT validation)    │    │
│  │    ├─ Split: Train (80%) ← Test (20%)      │    │
│  │    ├─ Janela rolante: 4 semanas train      │    │
│  │    └─ Validar em future data (1 semana)    │    │
│  └──────────────────────────────────────────────┘    │
│                     ↓                                  │
│  ┌──────────────────────────────────────────────┐    │
│  │ 3. Simulate Trades (Trade State Machine)    │    │
│  │    ├─ For each bar: Generate signal         │    │
│  │    ├─ Apply RiskGate (-3% limit)           │    │
│  │    ├─ Update position state                 │    │
│  │    └─ Compute P&L (realized + unrealized)  │    │
│  └──────────────────────────────────────────────┘    │
│                     ↓                                  │
│  ┌──────────────────────────────────────────────┐    │
│  │ 4. Compute Metrics                          │    │
│  │    ├─ Sharpe Ratio (target ≥1.0)           │    │
│  │    ├─ Max Drawdown (target ≤15%)            │    │
│  │    ├─ Win Rate (target >55%)                │    │
│  │    └─ Profit Factor (target ≥1.5)           │    │
│  └──────────────────────────────────────────────┘    │
│                     ↓                                  │
│  ┌──────────────────────────────────────────────┐    │
│  │ 5. Validation Gate                          │    │
│  │    ├─ IF Sharpe ≥1.0 && DD ≤15%  → GO ✅  │    │
│  │    └─ ELSE → FAIL ❌ (no go-live)          │    │
│  └──────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

---

## Camadas Aplicacionais

### **Camada 1: Presentation (API/Dashboard)**

Interfaces de usuário:
- **REST API** (FastAPI, portas 8000-8009 por símbolo)
- **Telegram Bot** (Alerts críticos e comandos)
- **Dashboard Web** (Estadual de posições, P&L, métricas)
- **WebSocket** (Push updates em tempo real)

### **Camada 2: Application (Orchestration)**

Orquestração de componentes:
- **main.py:** Entry point, event loop principal
- **agent_orchestrator.py:** Coordena strategy + risk + execution
- **config management:** Symbol universe, leverage limits, thresholds
- **health checks:** API connectivity, database status, memory usage

### **Camada 3: Business Logic**

Regras de negócio:
- **SMC Signal Generation:** Ordem blocks, break of structure
- **Risk Gating:** Circuit breaker, liquidation alerts
- **Position Management:** Entry/exit logic, trailing stop
- **ML Model Inference:** PPO policy evaluation

### **Camada 4: Data Access**

Gerenciamento de dados:
- **Database** (PostgreSQL): Trades, positions, risk events
- **Parquet Cache:** OHLCV históricos (Binance)
- **API Clients:** Binance REST/WebSocket wrappers
- **File System:** Logs estruturados, audit trail

---

## Padrões de Design

### 🔐 **Pattern 1: Guardian (Risk-First)**

Toda a lógica de risco é **inviolável**, centralizada, e **nega por padrão**:

```python
# Nunca fazer: riscar = True; if market_ok: execute()
# Sempre fazer:
def execute_order(signal):
    if not riskgate_ok():  # Default: DENY
        return "BLOCKED_BY_RISKGATE"
    if not validators_ok(signal):
        return "BLOCKED_BY_VALIDATORS"
    # Só aqui:
    place_order(signal)
```

### 🎯 **Pattern 2: Circuit Breaker**

Limite duro inviolável em drawdown:
```
IF cumulative_loss > -3% per week:
    HALT_ALL_TRADING()
    ALERT(Telegram: "CIRCUIT BREAKER TRIGGERED")
    WAIT_FOR_MANUAL_INTERVENTION()
```

### 🔄 **Pattern 3: State Machine (Trade Lifecycle)**

Estados bem-definidos:
```
CLOSED → ENTRY_PENDING → OPEN → EXIT_PENDING → CLOSED
           ↓ (fail)  ↑                ↓ (timeout)
        CANCELLED ──────────────────────→ FORCED_EXIT
```

### 🤖 **Pattern 4: Confidence-Weighted Decision**

Combina múltiplas fontes de sinal:
```
final_signal = 
    0.6 * heuristics_signal * heuristics_confidence +
    0.4 * ml_signal * ml_confidence
    
IF final_signal > threshold:
    EXECUTE()
```

### 📊 **Pattern 5: Walk-Forward Validation**

Evita look-ahead bias em backtesting:
```
for window in rolling_windows(data):
    train_data = window[:0.8]
    test_data = window[0.8:]
    
    strategy.train(train_data)
    metrics = strategy.test(test_data)  # OOT testing
    
    if not metrics.quality_ok():
        REJECT_STRATEGY()
```

---

## Segurança e Risco

### 🛡️ **Proteções de Capital**

| Nível | Mecanismo | Limite | Ação |
|-------|-----------|--------|------|
| **1** | Circuit Breaker | -3%/semana | HALT imediato |
| **2** | Position Sizing | Max 10x leverage | REJECT ordem |
| **3** | Trailing Stop | 1.5x ATR | AUTO CLOSE |
| **4** | Liquidation Alert | 90% margin | ALERT + manual review |
| **5** | Rate Limit | 1.200 req/min | QUEUE + retry |

### 🔐 **Controle de Acesso**

- **API Keys:** Encrypted em `.env` (nunca em git)
- **Permissions:** Testnet vs Mainnet (separado)
- **Audit Trail:** Todas operações loggadas com timestamp UTC
- **Compliance:** Segue CFTC rules (US traders excluded)

### 📋 **Auditoria Contínua**

- **Daily reconciliation:** Posições vs Binance API
- **Weekly review:** P&L, drawdown, risk metrics
- **Monthly deep-dive:** Strategy performance, ML convergence
- **Audit trail:** 365 dias de retenção

---

## Performance e Escalabilidade

### ⚡ **Latency Budget**

```
Evento → Sinal (50ms) → Risk Check (10ms) → Order (30ms) → Fill (400ms)
                                                    = <500ms total
```

**Breakdown:**
- Fetch data: 40ms (cached features)
- Signal gen: 10ms (determinístico)
- Risk check: 5ms (boolean checks)
- Order API: 30ms (Binance latency)
- Fill callback: 400ms (network + Binance processing)

### 📈 **Escalabilidade**

**Horizontal:**
- 60 símbolos → 200+ símbolos (via Parquet sharding)
- 1 agent → N agents (multi-account management)
- Single-region → Multi-region (geo-distribution)

**Vertical:**
- Memory: 4GB baseline (Parquet + features cache)
- CPU: 4 cores (signal gen parallelizable)
- Storage: 200MB/mês (audit trail rotation)

### 🔄 **Throughput**

- **Signals/sec:** 60 símbolos × 1 sinal/5s = 12 sinais/sec
- **Orders/sec:** Max 5 (rate limit bound)
- **API calls/min:** 1.200/min (Binance limit respected)

---

## Deployment e Operações

### 🚀 **Deployment Stages**

| Stage | Env | Volume | Duration | Gate |
|-------|-----|--------|----------|------|
| **Canary 1** | Live | 10% | 30min | Sharpe >0.5, no errors |
| **Canary 2** | Live | 50% | 2h | Sharpe >0.8, latency OK |
| **Full Deploy** | Live | 100% | ∞ | Sharpe ≥1.0, green lights |

### 📊 **Monitoring**

Real-time dashboards:
- **System Health:** API connectivity, memory, CPU
- **Trading Health:** P&L, drawdown, positions, signal count
- **Risk Health:** Circuit breaker status, margin ratio, alerts

### 🔧 **Runbooks**

**Emergency SOP:**
1. Circuit breaker triggered? → Manual review + decision
2. API down? → Fallback to cached data, no new signals
3. Database down? → Memory-only mode, audit trail to file
4. Liquidation risk? → Close positions, alert owner

---

## Decisões Arquiteturais

### 🔴 **Decision 1: Heurísticas Primeiro, ML Depois**

**Escolha:** Layer 0 (heurísticas) vai live primeiro, PPO (Layer 1-6) em background.

**Rationale:**
- Heurísticas = determinísticas, testáveis, previsíveis
- PPO = aprendizado contínuo, mas 96h para convergir
- Híbrido = melhor segurança (fail-safe) + upside (ML)

**Trade-off:** Menos lucro no curto prazo, mais confiança operacional.

### 🟢 **Decision 2: Backtesting é Bloqueador**

**Escolha:** SMC strategy não vai live sem validação em 1Y dados históricos.

**Rationale:**
- "Dados sobre intuição" — princípio do projeto
- Walk-forward testing = evita look-ahead bias
- Sharpe ≥1.0 + MaxDD ≤15% = qualidade garantida

**Trade-off:** 48-96h de desenvolvimento pré-deployment.

### 🔵 **Decision 3: RiskGate Inviolável**

**Escolha:** -3% circuit breaker NUNCA pode ser bypassed, nem em ML.

**Rationale:**
- Proteção de capital > lucro
- "Segurança sobre lucro" — princípio do projeto
- Manual intervention preserva agency do investidor

**Trade-off:** Potencial upside perdido em crashes que recuperam rápido.

### 🟡 **Decision 4: Parquet over CSV**

**Escolha:** Cache histórico em Parquet (não CSV).

**Rationale:**
- Compressão: 200MB vs 2GB para 1Y × 60 símbolos
- Latência: <100ms read vs >500ms CSV
- Preservação de types: Datetime, float64, etc

**Trade-off:** Dependency extra (pyarrow), complexidade config.

### 🟠 **Decision 5: Confidence-Weighted Fusion**

**Escolha:** Heurísticas (60%) + PPO (40%) em confiança, não hard switch.

**Rationale:**
- Smooth transition: sem jumps em estratégia
- Aproveitando força de ambas
- Backtesting fácil (determinístico)

**Trade-off:** Mais código, lógica de confidence threshold.

---

## 📚 Referências Arquiteturais

| Conceito | Implementação | Arquivo |
|----------|---|---|
| API Integration | Binance REST + WebSocket | `data/binance_api.py` |
| Feature Pipeline | Indicators (104 features) | `indicators/*.py` |
| Signal Generation | Heurísticas + ML | `execution/heuristic_signals.py` + `agent/` |
| Risk Management | RiskGate, Circuit Breaker | `risk/circuit_breaker.py` |
| Order Execution | State machine | `execution/order_executor.py` |
| Backtesting | Walk-forward validator | `backtest/*.py` |
| Logging | Audit trail completo | `logs/`, `database` |

---

## 🎯 Princípios Arquiteturais

1. **Segurança sobre Lucro** — RiskGate inviolável
2. **Dados sobre Intuição** — Todas decisões baseadas em backtest
3. **Simplicidade de Código** — Boring, previsível, testável
4. **Rastreabilidade Completa** — Audit trail 365 dias
5. **Fail-Safe Defaults** — Nega por padrão, aprova com cautela

---

**Arquitetura validada e production-ready desde 22 FEV 2026.**  
**Última atualização:** 27 FEV 2026

