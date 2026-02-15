# 📘 Manual do Usuário — Crypto Futures Agent

## Índice
1. [Visão Geral](#1-visão-geral)
2. [Requisitos](#2-requisitos)
3. [Instalação](#3-instalação)
4. [Configuração](#4-configuração)
5. [Modos de Operação](#5-modos-de-operação)
6. [Funcionalidades](#6-funcionalidades)
7. [Arquitetura](#7-arquitetura)
8. [Referência de Comandos](#8-referência-de-comandos)
9. [Troubleshooting](#9-troubleshooting)
10. [FAQ](#10-faq)

---

## 1. Visão Geral

O **Crypto Futures Agent** é um agente autônomo de trading de futuros de criptomoedas projetado para operar na Binance Futures (USDⓈ-M). Utiliza:

- **Reinforcement Learning (PPO)** para aprendizado e tomada de decisão
- **Smart Money Concepts (SMC)** para análise de estrutura de mercado
- **Indicadores Técnicos** avançados (22+ indicadores)
- **Análise de Sentimento** (funding rate, open interest, liquidações)
- **Dados Macroeconômicos** (Fear & Greed, DXY, BTC Dominance)
- **Gestão de Risco Automática** com regras invioláveis

### Características
- ✅ Operação autônoma 24/7
- ✅ Multi-timeframe (H1, H4, D1)
- ✅ 104 features normalizadas para o modelo RL
- ✅ Gestão de risco rigorosa (stop loss, take profit, max drawdown)
- ✅ Modos Paper Trading e Live Trading
- ✅ Playbooks específicos por criptomoeda
- ✅ Arquitetura em 6 camadas com execução condicional

### Aviso Importante
⚠️ **Este software é fornecido para uso pessoal e educacional.**
- NÃO é aconselhamento financeiro
- NÃO garante lucros
- Trading de futuros envolve ALTO RISCO de perda de capital
- Use APENAS capital que você pode perder
- SEMPRE teste em paper trading antes de usar capital real

---

## 2. Requisitos

### Sistema Operacional
- **Windows 10/11** (scripts .bat incluídos)
- **Linux** (Ubuntu 20.04+, Debian, etc.)
- **macOS** (10.14+)

### Software
- **Python 3.10+** (recomendado 3.10 ou 3.11)
- **pip** (gerenciador de pacotes Python)
- **Git** (para clonar o repositório)

### Recursos de Hardware
- **CPU**: Mínimo 2 cores, recomendado 4+ cores
- **RAM**: Mínimo 2GB, recomendado 4GB+ para treinamento
- **Disco**: ~1GB de espaço livre (dados históricos + modelos)
- **Internet**: Conexão estável para comunicação com Binance API

### Conta Binance
- Conta ativa na Binance com **Futures** habilitado
- **API Key** + **Secret Key** com permissões:
  - ✅ Enable Reading
  - ✅ Enable Futures (para paper e live trading)
  - ❌ Enable Spot & Margin Trading (não necessário)
  - ❌ Enable Withdrawals (NÃO habilite por segurança)
- Recomendado: IP whitelist nas configurações de API

---

## 3. Instalação

### 3.1. Windows - Instalação Automática (Recomendado)

```batch
# 1. Clone o repositório
git clone https://github.com/jadergreiner/crypto-futures-agent.git
cd crypto-futures-agent

# 2. Execute o script de setup
setup.bat
```

O `setup.bat` irá:
- Criar ambiente virtual Python
- Instalar todas as dependências
- Configurar estrutura de diretórios

### 3.2. Linux/Mac - Instalação Manual

```bash
# 1. Clone o repositório
git clone https://github.com/jadergreiner/crypto-futures-agent.git
cd crypto-futures-agent

# 2. Crie ambiente virtual
python3 -m venv venv

# 3. Ative o ambiente virtual
# Linux/Mac:
source venv/bin/activate
# Windows (se não usar setup.bat):
# venv\Scripts\activate

# 4. Instale dependências
pip install -r requirements.txt
```

### 3.3. Verificação da Instalação

```bash
# Teste rápido - deve executar sem erros
python main.py --dry-run
```

Se ver a mensagem "Dry-run concluído com sucesso", a instalação está OK!

---

## 4. Configuração

### 4.1. Variáveis de Ambiente (`.env`)

Copie o arquivo de exemplo e configure suas credenciais:

```bash
cp .env.example .env
```

Edite `.env` com suas informações:

```ini
# Binance API Keys (OBRIGATÓRIO)
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_API_SECRET=seu_api_secret_aqui

# Modo de Trading (padrão: paper)
TRADING_MODE=paper  # Valores: paper, live

# Ambiente (padrão: testnet)
BINANCE_ENVIRONMENT=testnet  # Valores: testnet, production

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Database
DATABASE_PATH=db/crypto_futures.db
```

**Configurações Importantes:**
- `TRADING_MODE=paper`: Modo simulado, SEM risco de capital real
- `TRADING_MODE=live`: Modo real, OPERA COM CAPITAL REAL ⚠️
- `BINANCE_ENVIRONMENT=testnet`: Usa Testnet da Binance (dados simulados)
- `BINANCE_ENVIRONMENT=production`: Usa Binance real

### 4.2. Símbolos (`config/symbols.py`)

O arquivo `config/symbols.py` define quais criptomoedas o agente pode operar.

Símbolos padrão incluídos:
- BTCUSDT, ETHUSDT, SOLUSDT (principais)
- BNBUSDT, DOGEUSDT, XRPUSDT, LTCUSDT
- Símbolos high-beta: 0GUSDT, KAIAUSDT, AXLUSDT, NILUSDT, FOGOUSDT

**Para adicionar novos símbolos:**
1. Edite `config/symbols.py`
2. Adicione entrada no dicionário `SYMBOLS`
3. Crie playbook em `playbooks/` (opcional, mas recomendado)
4. Adicione ao `AUTHORIZED_SYMBOLS` em `config/execution_config.py`

### 4.3. Parâmetros de Risco (`config/risk_params.py`)

Parâmetros de gestão de risco:

```python
RISK_PARAMS = {
    # Risco por trade (% do capital)
    'max_risk_per_trade_pct': 1.0,  # 1% do capital por trade
    
    # Stop Loss e Take Profit (multiplicadores de ATR)
    'stop_loss_atr_multiplier': 2.0,
    'take_profit_atr_multiplier': 4.0,
    
    # Limites de drawdown
    'max_drawdown_pct': 10.0,  # Pausa se drawdown > 10%
    'daily_loss_limit_pct': 3.0,  # Pausa se perda diária > 3%
    
    # Limites de posições
    'max_positions': 3,  # Máximo 3 posições simultâneas
    'max_leverage': 3,  # Máximo 3x de alavancagem
    
    # Trailing stop
    'trailing_stop_activation_pct': 2.0,  # Ativa trailing em 2% lucro
    'trailing_stop_distance_pct': 1.0,  # Distância do trailing
}
```

**Recomendações:**
- **Iniciantes**: Use `max_risk_per_trade_pct = 0.5%` (mais conservador)
- **Experientes**: Até `max_risk_per_trade_pct = 2.0%` (mais agressivo)
- **Sempre**: Mantenha `max_drawdown_pct <= 15%`

---

## 5. Modos de Operação

### 5.1. Dry-Run (Validação sem API)

```bash
python main.py --dry-run
```

**O que faz:**
- Testa pipeline completo com dados sintéticos
- NÃO requer API keys
- NÃO conecta à Binance
- Valida que todo o sistema funciona corretamente

**Quando usar:**
- Após instalação inicial
- Após mudanças no código
- Para validar que tudo está funcionando

### 5.2. Setup (Coleta de Dados Históricos)

```bash
# Setup padrão
python main.py --setup

# Setup com modo específico
python main.py --setup --mode paper
```

**O que faz:**
- Inicializa banco de dados SQLite
- Coleta dados históricos da Binance:
  - D1: 365 dias
  - H4: 180 dias
  - H1: 90 dias
- Calcula todos os indicadores técnicos
- Analisa estruturas SMC

**Duração:** ~10-30 minutos dependendo da internet

**Pré-requisito:** API keys configuradas no `.env`

### 5.3. Treinamento do Modelo

```bash
python main.py --train
```

**O que faz:**
- Treina modelo PPO em 3 fases:
  1. **Fase 1 - Exploração** (500k steps): Alta exploração, aprende básico
  2. **Fase 2 - Refinamento** (1M steps): Explora menos, refina estratégia
  3. **Fase 3 - Validação**: Valida em dados não vistos

**Duração:** 
- CPU: 6-12 horas
- GPU: 2-4 horas

**Modelos salvos em:** `models/`
- `phase1_exploration.zip`
- `phase2_refinement.zip`
- `crypto_agent_ppo_final.zip`

**Status:** ⚠️ Em desenvolvimento (v0.3)

### 5.4. Backtest

```bash
# Backtest em período específico
python main.py --backtest --start-date 2025-01-01 --end-date 2025-12-31

# Backtest com modelo específico
python main.py --backtest --model-path models/crypto_agent_ppo_final.zip
```

**O que faz:**
- Executa estratégia sobre dados históricos
- Calcula métricas de performance:
  - Sharpe Ratio
  - Sortino Ratio
  - Max Drawdown
  - Win Rate
  - Profit Factor
- Gera gráfico de equity curve

**Output:** `backtest_results/`

**Status:** ⚠️ Em desenvolvimento (v0.4)

### 5.5. Paper Trading

```bash
python main.py --mode paper
```

**O que faz:**
- Operação simulada em tempo real
- Usa dados reais da Binance
- NÃO executa ordens reais
- Tracking completo de PnL simulado

**Quando usar:**
- Validar estratégia sem risco
- Testar novo modelo treinado
- Monitorar comportamento do agente

**Logs:** `logs/paper_trading_*.log`

### 5.6. Live Trading

```bash
python main.py --mode live
```

⚠️ **ATENÇÃO: OPERA COM CAPITAL REAL!**

**O que faz:**
- Operação real na Binance Futures
- Executa ordens reais
- Movimenta capital real
- Sujeito a perdas reais

**Pré-requisitos OBRIGATÓRIOS:**
1. ✅ Testado extensivamente em paper mode (mínimo 30 dias)
2. ✅ Resultados positivos em backtest
3. ✅ Capital mínimo de $200-500
4. ✅ API keys com permissão de Futures
5. ✅ Circuit breakers configurados
6. ✅ Monitoramento ativo

**Proteções ativas:**
- Stop loss automático em todas as posições
- Max drawdown diário (pausa se atingido)
- Max número de posições
- Validação dupla antes de cada ordem

### 5.7. Monitoramento de Posições

```bash
# Monitorar todas as posições
python main.py --monitor

# Monitorar símbolo específico
python main.py --monitor --monitor-symbol BTCUSDT

# Intervalo customizado (em segundos)
python main.py --monitor --monitor-interval 60
```

**O que mostra:**
- Posições abertas em tempo real
- PnL atual ($ e %)
- Distância do stop loss e take profit
- Tempo na posição
- Detalhes da entrada

**Atualização:** A cada 60 segundos (default) ou intervalo especificado

---

## 6. Funcionalidades

### 6.1. Coleta de Dados

#### OHLCV (Open, High, Low, Close, Volume)
- **Timeframes:** H1, H4, D1
- **Fonte:** Binance API via SDK oficial
- **Armazenamento:** SQLite (`db/crypto_futures.db`)
- **Atualização:** Automática via scheduler

#### Sentiment Data
- **Funding Rate:** Taxa de financiamento atual
- **Open Interest:** Volume de contratos abertos
- **Long/Short Ratio:** Proporção de posições long vs short
- **Liquidações:** Volume de liquidações long e short
- **Fonte:** Binance Futures API
- **Frequência:** A cada 1 hora

#### Macro Data
- **Fear & Greed Index:** Índice de medo/ganância do mercado
- **DXY:** Índice do dólar americano
- **BTC Dominance:** Dominância do Bitcoin no mercado
- **Stablecoin Flows:** Fluxos de stablecoins nas exchanges
- **Fonte:** APIs públicas (Alternative.me, etc.)
- **Frequência:** A cada 4 horas

### 6.2. Indicadores Técnicos

**EMAs (Exponential Moving Averages):**
- EMA 17, 34, 72, 144, 305, 610
- Alinhamento de EMAs (score de -6 a +6)

**Osciladores:**
- RSI-14 (Relative Strength Index)
- MACD (12, 26, 9)
- ADX-14 (Average Directional Index)
- DI+ / DI- (Directional Indicators)

**Volatilidade:**
- ATR-14 (Average True Range)
- Bollinger Bands (20, 2)

**Volume:**
- OBV (On-Balance Volume)
- Volume Profile (POC, VAH, VAL)

### 6.3. Smart Money Concepts (SMC)

#### Swing Points
- Identificação de HH (Higher Highs), HL (Higher Lows)
- LH (Lower Highs), LL (Lower Lows)
- Lookback period: 20 candles

#### Market Structure
- **BULLISH**: Sequência de HH e HL
- **BEARISH**: Sequência de LH e LL
- **RANGE**: Sem tendência clara

#### Break of Structure (BOS)
- Break bullish: Preço rompe HH anterior
- Break bearish: Preço rompe LL anterior
- Confirma continuação de tendência

#### Change of Character (CHoCH)
- Break contrário à tendência atual
- Sinaliza possível reversão
- Bullish CHoCH: Break de HH em tendência bear
- Bearish CHoCH: Break de LL em tendência bull

#### Order Blocks (OBs)
- Zonas de suporte/resistência institucional
- **Bullish OB**: Candle bullish antes de impulso bullish
- **Bearish OB**: Candle bearish antes de impulso bearish
- **Status**: FRESH, TESTED, MITIGATED

#### Fair Value Gaps (FVGs)
- Imbalances de preço (gaps)
- **Bullish FVG**: Gap entre baixa do candle 1 e alta do candle 3
- **Bearish FVG**: Gap entre alta do candle 1 e baixa do candle 3
- **Status**: OPEN, FILLED, PARTIALLY_FILLED

#### Breaker Blocks
- Order blocks que falharam e se tornaram resistência/suporte contrário

#### Liquidity Levels
- **BSL** (Buy-Side Liquidity): Stops de shorts acima de resistências
- **SSL** (Sell-Side Liquidity): Stops de longs abaixo de suportes
- **Sweeps**: Liquidação de stops antes de reverter

#### Premium/Discount Zones
- Baseado em Fibonacci 50%
- **DEEP_DISCOUNT**: < 25%
- **DISCOUNT**: 25-50%
- **EQUILIBRIUM**: ~50%
- **PREMIUM**: 50-75%
- **DEEP_PREMIUM**: > 75%

### 6.4. Análise Multi-Timeframe

#### D1 Bias
Determina viés diário: **BULLISH**, **BEARISH** ou **NEUTRO**

Critérios:
- EMA alignment score
- ADX > 25 (tendência forte)
- DI+ vs DI-
- RSI em zona apropriada

#### Market Regime
Determina regime de mercado: **RISK_ON**, **RISK_OFF** ou **NEUTRO**

Fatores:
- Tendência do BTC em D1
- Fear & Greed Index
- Volume de mercado
- Volatilidade

#### Correlação com BTC
- Correlação de Pearson (30 períodos em H4)
- Range: -1 (correlação negativa perfeita) a +1 (correlação positiva perfeita)

#### Beta em relação ao BTC
- Sensibilidade do ativo em relação ao BTC
- Beta < 1: Move menos que BTC
- Beta = 1: Move igual ao BTC
- Beta > 1: Move mais que BTC (high-beta)

### 6.5. Feature Engineering

**104 features normalizadas** divididas em 9 blocos:

**Bloco 1 - Preço (11 features):**
- Retornos 1H4, 4H4
- Range percentual
- EMA score
- Retorno D1

**Bloco 2 - EMAs (6 features):**
- Distância do preço para cada EMA (17, 34, 72, 144, 305, 610)

**Bloco 3 - Indicadores (11 features):**
- RSI, MACD histogram, Bollinger %B, Bollinger Width
- Volume ratio, OBV change, ATR %
- ADX, DI diff, VP position, VP spread

**Bloco 4 - SMC (19 features):**
- Estrutura (bull/bear/range)
- BOS (bull/bear)
- CHoCH (bull/bear)
- Order Blocks (contagem e distância bull/bear)
- FVGs (contagem e distância bull/bear)
- Liquidity sweeps (up/down)
- Premium/Discount (position e zone)

**Bloco 5 - Sentimento (4 features):**
- Long/Short ratio
- OI change %
- Funding rate
- Liquidation imbalance

**Bloco 6 - Macro (4 features):**
- DXY change
- Fear & Greed
- BTC dominance
- Stablecoin flow

**Bloco 7 - Correlação BTC (3 features):**
- BTC return
- Correlation
- Beta

**Bloco 8 - Contexto D1 (2 features):**
- D1 bias (BULLISH=1, BEARISH=-1, NEUTRO=0)
- Market regime (RISK_ON=1, RISK_OFF=-1, NEUTRO=0)

**Bloco 9 - Posição (5 features):**
- Direction (LONG=1, SHORT=-1, FLAT=0)
- PnL %
- Tempo na posição
- Distância do stop
- Distância do TP

**+ Padding:** 39 features de padding para completar 104

### 6.6. Agente RL (Reinforcement Learning)

#### Algoritmo: PPO (Proximal Policy Optimization)
- Framework: Stable-Baselines3
- Biblioteca: Gymnasium (gym environment)

#### Observation Space
- **Type:** Box(104,)
- **Range:** Clipped [-10, 10]
- **Dtype:** float32

#### Action Space
- **Type:** Discrete(5)
- **Actions:**
  0. HOLD - Manter posição atual (ou flat)
  1. OPEN_LONG - Abrir posição long
  2. OPEN_SHORT - Abrir posição short
  3. CLOSE - Fechar posição atual
  4. REDUCE_50 - Reduzir posição em 50%

#### Reward Function
Multi-componente com 6 fatores:

1. **r_pnl**: PnL % do trade (com bonus para R-multiple > 2.0)
2. **r_risk**: Gestão de risco (penalidade se sem stop, drawdown alto)
3. **r_consistency**: Consistência de resultados
4. **r_overtrading**: Penalidade por excesso de trades
5. **r_hold_bonus**: Pequeno bonus por segurar posição vencedora
6. **r_invalid_action**: Penalidade por ação inválida

#### Treinamento Multi-Fase
**Fase 1 - Exploração (500k steps):**
- Alta exploração (entropy coef = 0.01)
- Aprende o básico do ambiente

**Fase 2 - Refinamento (1M steps):**
- Exploração reduzida (entropy coef = 0.005)
- Refina estratégia

**Fase 3 - Validação:**
- Testa em dados não vistos
- Critérios: Sharpe > 1.0, Drawdown < 15%

**Status:** ⚠️ Em desenvolvimento (v0.3)

### 6.7. Gestão de Risco

#### Regras INVIOLÁVEIS

**1. Stop Loss Obrigatório**
- Toda posição DEVE ter stop loss
- Calculado baseado em ATR ou estruturas SMC
- Distância máxima: 3% do preço de entrada

**2. Take Profit Definido**
- Toda posição tem take profit calculado
- Baseado em ATR (risk/reward ratio)
- Alvo mínimo: 2R (2x o stop loss)

**3. Position Sizing**
- Baseado em % de risco fixo do capital
- Ajustado pelo beta do ativo
- Símbolos high-beta: position sizing reduzido

**4. Max Drawdown**
- Diário: 3% do capital (pausa operações)
- Total: 10% do capital (circuit breaker)

**5. Max Posições**
- Máximo 3 posições simultâneas
- Diversificação obrigatória (não concentrar em um setor)

**6. Restrições por Regime**
- Símbolos high-beta (beta >= 2.0): Apenas em RISK_ON
- RISK_OFF: Apenas BTC, ETH (assets mais seguros)

#### Trailing Stop
- Ativa quando PnL > 2% (configurável)
- Distância: 1% do preço atual (configurável)
- Segue preço subindo, protege lucros

#### Circuit Breaker
Pausa automática em caso de:
- Drawdown diário > 3%
- Drawdown total > 10%
- 3+ trades perdedores seguidos com perda > 5% total
- Erro crítico na API

### 6.8. Monitoramento

#### Position Monitor
Visualização em tempo real:
```
═══════════════════════════════════════
      MONITORAMENTO DE POSIÇÕES
═══════════════════════════════════════
Símbolo: BTCUSDT
Status: LONG | Quantidade: 0.05 BTC
Entrada: $45,000.00 | Atual: $46,500.00
PnL: +$75.00 (+3.33%)
Stop Loss: $44,100.00 (-2.0%)
Take Profit: $49,500.00 (+10.0%)
Tempo: 2h 35min
═══════════════════════════════════════
```

#### Logs Estruturados
Localização: `logs/`
- `app_YYYYMMDD.log`: Log geral da aplicação
- `paper_trading_YYYYMMDD.log`: Operações em paper mode
- `live_trading_YYYYMMDD.log`: Operações em live mode
- `errors_YYYYMMDD.log`: Erros e exceções

Formato:
```
2026-02-15 12:34:56 INFO [LayerManager] Layer 4 decision: OPEN_LONG BTCUSDT
2026-02-15 12:34:57 INFO [OrderExecutor] Order executed: BTCUSDT LONG 0.05 @ $45,000
2026-02-15 12:34:57 INFO [RiskManager] Stop loss set: $44,100 (-2.0%)
```

---

## 7. Arquitetura

### 7.1. Estrutura de Diretórios

```
crypto-futures-agent/
├── agent/              # Agente RL
│   ├── environment.py  # Gymnasium environment
│   ├── trainer.py      # Treinamento PPO
│   ├── reward.py       # Reward calculator
│   ├── risk_manager.py # Gestão de risco
│   └── data_loader.py  # Carregamento de dados para treino
├── backtest/           # Engine de backtesting
│   ├── backtester.py   # Backtester principal
│   └── walk_forward.py # Walk-forward optimization
├── config/             # Configurações
│   ├── settings.py     # Settings gerais
│   ├── symbols.py      # Definição de símbolos
│   ├── risk_params.py  # Parâmetros de risco
│   └── execution_config.py # Config de execução
├── core/               # Core do sistema
│   ├── scheduler.py    # Scheduler de layers
│   └── layer_manager.py # Gerenciamento de layers
├── data/               # Coleta de dados
│   ├── collector.py    # Collector OHLCV
│   ├── sentiment_collector.py # Sentiment data
│   ├── macro_collector.py # Macro data
│   └── database.py     # Interface SQLite
├── docs/               # Documentação
│   ├── ROADMAP.md
│   ├── USER_MANUAL.md
│   └── ...
├── execution/          # Execução de ordens
│   └── order_executor.py # Executor de ordens
├── indicators/         # Indicadores
│   ├── technical.py    # Indicadores técnicos
│   ├── smc.py          # Smart Money Concepts
│   ├── multi_timeframe.py # Análise multi-TF
│   └── features.py     # Feature Engineering
├── logs/               # Logs
├── models/             # Modelos treinados
├── monitoring/         # Monitoramento
│   ├── logger.py       # Logger estruturado
│   └── position_monitor.py # Monitor de posições
├── playbooks/          # Playbooks por símbolo
│   ├── btc_playbook.py
│   ├── eth_playbook.py
│   └── ...
├── tests/              # Testes unitários
│   ├── test_features.py
│   ├── test_reward.py
│   └── ...
├── main.py             # Entry point
├── requirements.txt    # Dependências
└── .env                # Variáveis de ambiente
```

### 7.2. Fluxo de Dados

```
┌─────────────────┐
│  Binance API    │
│  (OHLCV, Sent.) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Database     │
│    (SQLite)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Indicators    │
│ (Tech + SMC +   │
│  Multi-TF)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Features    │
│  (104 features) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RL Agent      │
│  (PPO Model)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Risk Manager   │
│  (Validation)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Order Executor  │
│  (Binance API)  │
└─────────────────┘
```

### 7.3. Camadas de Execução

**LAYER 1 - Heartbeat (1 minuto)**
- Health check de API, Database, WebSocket
- Verifica conectividade
- Sem decisões de trading

**LAYER 2 - Risk Management (5 minutos)**
- Gerenciamento de risco de posições abertas
- Atualiza trailing stops
- Verifica violação de limites
- Só roda se há posições

**LAYER 3 - H1 Timing (1 hora)**
- Refina timing de entrada
- Monitora níveis de entrada
- Só roda se há sinais pendentes ou posições

**LAYER 4 - H4 Main Decision (4 horas)**
- Decisão principal de trading
- Análise completa H4
- Gera sinais de entrada/saída
- Roda em: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC

**LAYER 5 - D1 Trend & Macro (00:00 UTC)**
- Análise de tendência D1
- Contexto macroeconômico
- Define bias do dia
- Market regime
- Roda ANTES da Layer 4

**LAYER 6 - Weekly/Monthly (Semanal/Mensal)**
- Performance review
- Retreinamento de modelo (futuro)
- Ajustes de parâmetros

---

## 8. Referência de Comandos

| Comando | Descrição | Requer API | Produz Output |
|---------|-----------|------------|---------------|
| `python main.py --dry-run` | Valida pipeline com dados sintéticos | ❌ Não | Console |
| `python main.py --setup` | Coleta dados históricos e inicializa DB | ✅ Sim | DB + Console |
| `python main.py --setup --mode paper` | Setup em modo paper | ✅ Sim | DB + Console |
| `python main.py --train` | Treina modelo RL em 3 fases | ✅ Sim | Models + Logs |
| `python main.py --backtest --start-date YYYY-MM-DD --end-date YYYY-MM-DD` | Executa backtest | ✅ Sim | Relatório + Gráfico |
| `python main.py --mode paper` | Paper trading em tempo real | ✅ Sim | Logs |
| `python main.py --mode live` | Live trading (⚠️ CAPITAL REAL) | ✅ Sim | Logs + Ordens |
| `python main.py --monitor` | Monitora todas as posições | ✅ Sim | Console (live) |
| `python main.py --monitor --monitor-symbol BTCUSDT` | Monitora símbolo específico | ✅ Sim | Console (live) |
| `python main.py --monitor --monitor-interval 60` | Intervalo de 60s entre atualizações | ✅ Sim | Console (live) |

### Flags Adicionais

**--dry-run**
- Executa validação do pipeline sem API
- Útil para testar após instalação/mudanças

**--setup**
- Inicializa sistema e coleta dados históricos
- Obrigatório antes do primeiro uso

**--train**
- Treina modelo de RL
- Salva checkpoints em `models/`

**--backtest**
- Testa estratégia em dados históricos
- Requer `--start-date` e `--end-date`

**--mode {paper|live}**
- Define modo de operação
- `paper`: Simulado, sem risco
- `live`: Real, com capital real ⚠️

**--monitor**
- Ativa monitoramento de posições
- Atualização em tempo real

**--monitor-symbol SYMBOL**
- Monitora apenas símbolo específico
- Exemplo: `--monitor-symbol BTCUSDT`

**--monitor-interval SECONDS**
- Intervalo entre atualizações
- Default: 60 segundos

---

## 9. Troubleshooting

### Problema: "Missing API keys"

**Causa:** API keys não configuradas no `.env`

**Solução:**
```bash
# 1. Copie .env.example
cp .env.example .env

# 2. Edite .env e adicione suas keys
nano .env  # ou use editor de texto
```

### Problema: "Database not found"

**Causa:** Banco de dados não inicializado

**Solução:**
```bash
# Execute setup para criar e popular o DB
python main.py --setup
```

### Problema: "Insufficient data"

**Causa:** Dados históricos insuficientes no DB

**Solução:**
```bash
# Re-execute setup para coletar dados
python main.py --setup

# Aguarde completar (pode levar 10-30 min)
```

### Problema: Import errors

**Causa:** Dependências não instaladas

**Solução:**
```bash
# Reinstale requirements
pip install -r requirements.txt

# Se persistir, use ambiente virtual limpo
python -m venv venv_new
source venv_new/bin/activate  # Linux/Mac
# ou venv_new\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Problema: Erros de Binance SDK

**Causa:** Versão incompatível ou permissões de API

**Solução:**
```bash
# 1. Verifique versão
pip show binance-connector

# 2. Atualize se necessário
pip install --upgrade binance-connector

# 3. Verifique permissões da API Key na Binance:
#    - ✅ Enable Reading
#    - ✅ Enable Futures
#    - ❌ NÃO habilite Withdrawals
```

### Problema: "Connection timeout"

**Causa:** Firewall, VPN ou internet instável

**Solução:**
- Desabilite VPN temporariamente
- Verifique firewall (libere porta 443)
- Teste conexão: `ping api.binance.com`
- Use internet mais estável

### Problema: Modelo não treina

**Causa:** RAM insuficiente ou dados corrompidos

**Solução:**
```bash
# 1. Verifique RAM disponível
# Linux/Mac: free -h
# Windows: Gerenciador de Tarefas

# 2. Limpe cache e retreine
rm -rf models/*
python main.py --train
```

---

## 10. FAQ

### Quanto capital preciso?

**Mínimo recomendado:**
- **Paper Trading:** $0 (simulado)
- **Live Trading:** $200-500 USD

**Ideal:**
- $1,000+ para gestão de risco adequada
- Possibilita diversificação (3 posições de ~$300 cada)

### Quais símbolos operar?

**Para iniciantes:**
- BTCUSDT (mais estável)
- ETHUSDT (segunda maior)

**Para intermediários:**
- SOLUSDT (mais volátil, high-beta)
- BNBUSDT (burns trimestrais)

**Para avançados:**
- Símbolos low-cap: 0GUSDT, KAIAUSDT, etc.
- ⚠️ Alto risco, alta volatilidade

**Recomendação:** Comece com BTC e ETH apenas.

### Como retreinar o modelo?

```bash
# Execute novamente o comando de treino
python main.py --train

# O modelo anterior será sobrescrito
# Faça backup se quiser preservar:
cp models/crypto_agent_ppo_final.zip models/backup_modelo.zip
```

**Status:** ⚠️ Em desenvolvimento (v0.3)

### É seguro operar live?

**SIM, com ressalvas:**
- ✅ Após validação extensiva em paper (30+ dias)
- ✅ Com capital que você pode perder
- ✅ Com monitoramento ativo
- ✅ Com circuit breakers configurados

**NÃO:**
- ❌ Sem testar em paper primeiro
- ❌ Com todo seu capital
- ❌ Sem entender os riscos
- ❌ Esperando "ficar rico rápido"

### Posso rodar em servidor?

**Sim!** O sistema foi projetado para rodar localmente, mas pode ser adaptado para servidor:

**Servidor Linux:**
```bash
# Use screen ou tmux para sessão persistente
screen -S trading
python main.py --mode paper

# Detach: Ctrl+A, D
# Reattach: screen -r trading
```

**Docker (em desenvolvimento):**
```bash
# Futuro suporte via Docker
docker-compose up -d
```

### O agente opera 24/7?

**Depende do modo:**

**Paper/Live Trading:**
- ✅ Sim, opera 24/7
- Scheduler roda continuamente
- Layers executam nos intervalos definidos

**Recomendação:**
- Use VPS ou servidor dedicado
- Configure monitoramento de uptime
- Tenha alertas de falha

### Quanto tempo leva o treinamento?

**Depende do hardware:**

**CPU (4 cores):**
- Fase 1: ~3h
- Fase 2: ~6h
- Total: ~9-12h

**GPU (NVIDIA):**
- Fase 1: ~1h
- Fase 2: ~2h
- Total: ~3-4h

**Nota:** Use `nohup` ou `screen` para não interromper.

### Posso usar em Spot Trading?

**Não nativamente.** O sistema foi projetado para **Futures**:
- Alavancagem
- Short positions
- Funding rate analysis

**Adaptação para Spot:**
- Requer modificações no código
- Remover lógica de funding/alavancagem
- Ajustar gestão de risco
- Não recomendado para iniciantes

### Como funciona o stop loss?

**Cálculo automático baseado em:**
1. **ATR (Average True Range)**: Volatilidade do ativo
2. **SMC Order Blocks**: Níveis estruturais
3. **Distância máxima**: 3% do preço de entrada

**Exemplo:**
```
Preço entrada: $50,000
ATR: $1,000
Stop multiplier: 2.0
Stop loss: $50,000 - ($1,000 * 2.0) = $48,000 (-4%)

Se > 3%, ajusta para 3%:
Stop loss: $50,000 - ($50,000 * 0.03) = $48,500 (-3%)
```

### O que acontece se o bot cair?

**Proteções automáticas:**

1. **Stop Loss na Exchange:**
   - Todo stop loss é registrado na Binance
   - Executa MESMO se bot offline
   - Protege capital

2. **Ao reiniciar:**
   - Bot reconecta
   - Carrega posições abertas
   - Retoma monitoramento

3. **Recomendações:**
   - Use VPS confiável
   - Configure monitoramento (UptimeRobot, etc.)
   - Tenha alertas de queda

### Posso modificar o código?

**Sim!** Licença MIT permite:
- ✅ Uso pessoal
- ✅ Modificações
- ✅ Distribuição (com créditos)
- ✅ Uso comercial

**Recomendações:**
- Fork o repositório
- Faça branch para mudanças
- Teste extensivamente
- Considere contribuir melhorias (PR)

### Onde reportar bugs?

**GitHub Issues:**
1. Acesse: https://github.com/jadergreiner/crypto-futures-agent/issues
2. Clique "New Issue"
3. Descreva:
   - Comportamento esperado
   - Comportamento atual
   - Steps para reproduzir
   - Logs relevantes
   - Ambiente (OS, Python version)

### Tem suporte comercial?

**Não oficial.** Este é um projeto pessoal/educacional:
- ❌ Sem suporte comercial pago
- ❌ Sem garantias de funcionamento
- ✅ Comunidade pode ajudar (GitHub Issues)
- ✅ Documentação extensiva disponível

---

## 📝 Notas Finais

Este manual cobre as funcionalidades da **v0.2 (Pipeline Fix)**.

**Recursos em desenvolvimento (v0.3+):**
- Treinamento RL completo
- Backtesting avançado
- Walk-forward optimization
- Dashboard web

**Mantenha-se atualizado:**
- Verifique CHANGELOG.md para mudanças
- Veja ROADMAP.md para próximas features
- Acompanhe releases no GitHub

---

**Última atualização:** 15/02/2026 (v0.2.0)

**Desenvolvido com ❤️ para a comunidade de trading algorítmico**
