# Crypto Futures Autonomous Agent

Agente autônomo de Reinforcement Learning para operar futuros de criptomoedas na Binance Futures (USDⓈ-M). Combina indicadores técnicos, Smart Money Concepts (SMC), análise de sentimento e dados macroeconômicos para gerar sinais operacionais com gestão de risco completa.

## 🎯 Características Principais

- **Reinforcement Learning**: PPO (Proximal Policy Optimization) com Stable-Baselines3
- **Smart Money Concepts**: Order Blocks, FVGs, BOS, CHoCH, Liquidity Sweeps
- **Multi-Timeframe**: Análise em D1, H4 e H1
- **Gestão de Risco INVIOLÁVEL**: Stop loss, take profit, trailing stop, drawdown limits
- **104 Features**: Observation space completo com indicadores técnicos, SMC, sentimento e macro
- **Playbooks Específicos**: Estratégias customizadas para cada criptomoeda
- **Arquitetura em Camadas**: 6 layers com execução condicional

## 📊 Moedas Suportadas

- **BTC (BTCUSDT)**: Líder de mercado, ciclos de halving
- **ETH (ETHUSDT)**: Segunda maior, ecossistema DeFi
- **SOL (SOLUSDT)**: High beta, amplifica movimentos
- **BNB (BNBUSDT)**: Token burns trimestrais
- **DOGE (DOGEUSDT)**: Memecoin, sentiment-driven
- **XRP (XRPUSDT)**: Sensível a regulação
- **LTC (LTCUSDT)**: Halving próprio, correlação BTC

## 🏗️ Arquitetura

### Camadas de Execução

```
LAYER 1 (Heartbeat): 1 min    - Health check (API, DB, WebSocket)
LAYER 2 (Risk):      5 min    - Gestão de risco (apenas com posições)
LAYER 3 (H1):        1 hora   - Timing de entrada (apenas com sinais/posições)
LAYER 4 (H4):        4 horas  - Decisão principal (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
LAYER 5 (D1):        00:00 UTC - Tendência e macro (ANTES da Layer 4)
LAYER 6 (Semanal/Mensal):      - Performance review e retrain
```

### Estrutura do Projeto

```
crypto-futures-agent/
├── config/              # Configurações gerais, símbolos, parâmetros de risco
├── data/                # Collectors (OHLCV, sentiment, macro) e database
├── indicators/          # Indicadores técnicos, SMC, multi-timeframe, features
├── agent/               # Environment Gymnasium, reward, risk manager, trainer
├── playbooks/           # Playbooks específicos por moeda
├── core/                # Scheduler e layer manager
├── monitoring/          # Performance tracker, logger, alertas
├── backtest/            # Backtester e walk-forward optimization
├── tests/               # Testes unitários
└── main.py              # Entry point
```

## 🚀 Quick Start

### Opção A: Windows - Script Automático (Recomendado)

```batch
# 1. Execute o setup (apenas uma vez)
setup.bat

# 2. Inicie o agente com menu interativo
iniciar.bat
```

O script `iniciar.bat` oferece um menu interativo com todas as opções:
- ✅ Verifica e ativa o ambiente virtual automaticamente
- ✅ Valida pré-requisitos (.env, banco de dados)
- ✅ Menu com 7 opções: Paper Trading, Live, Monitor, Backtest, Train, Setup, Sair
- ✅ Confirmações de segurança para modo LIVE

### Opção B: Manual (Linux/Mac ou Avançado)

#### 1. Instalação

```bash
# Clone o repositório
git clone https://github.com/jadergreiner/crypto-futures-agent.git
cd crypto-futures-agent

# Instale as dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas API keys da Binance
```

#### 2. Setup Inicial

```bash
# Inicializar database e coletar dados históricos
python main.py --setup
```

Este comando irá:
- Criar o banco de dados SQLite
- Coletar 365 dias de dados D1
- Coletar 180 dias de dados H4
- Coletar 90 dias de dados H1
- Calcular todos os indicadores técnicos

#### 3. Treinar o Modelo (Opcional)

```bash
# Treinar o agente RL (3 fases: exploração, refinamento, validação)
python main.py --train
```

#### 4. Executar

```bash
# Modo paper trading (padrão)
python main.py --mode paper

# Modo live (requer capital real)
python main.py --mode live

# Monitorar posições abertas
python main.py --monitor --monitor-symbol C98USDT --monitor-interval 300

# Cancelar ordens abertas fora da whitelist (primeiro validar com dry-run)
python scripts/cancel_non_whitelist_orders.py --mode live --dry-run
python scripts/cancel_non_whitelist_orders.py --mode live
```

#### 5. Backtest

```bash
# Executar backtest em período específico
python main.py --backtest --start-date 2024-01-01 --end-date 2024-12-31
```

## 📈 Features do Observation Space (104 features)

### Bloco 1: Preço (11 features)
- Retornos em múltiplos timeframes
- Range atual
- EMA alignment score

### Bloco 2: EMAs (6 features)
- Distância do preço para cada EMA (17, 34, 72, 144, 305, 610)

### Bloco 3: Indicadores Técnicos (11 features)
- RSI, MACD, Bollinger Bands
- Volume Profile (POC, VAH, VAL)
- OBV, ATR, ADX, DI+/-

### Bloco 4: Smart Money Concepts (19 features)
- Estrutura de mercado (bullish/bearish/range)
- BOS e CHoCH
- Order Blocks (contagem e distância)
- Fair Value Gaps
- Liquidez e sweeps
- Premium/Discount zones

### Bloco 5: Sentimento (4 features)
- Long/Short Ratio
- Open Interest change
- Funding Rate
- Liquidation imbalance

### Bloco 6: Macro (4 features)
- DXY change
- Fear & Greed Index
- BTC Dominance
- Stablecoin flows

### Bloco 7: Correlação (3 features)
- BTC return
- Correlação com BTC
- Beta

### Bloco 8: Contexto D1 (2 features)
- Bias D1 (bullish/bearish/neutro)
- Regime de mercado (risk_on/risk_off/neutro)

### Bloco 9: Posição (5 features)
- Direção da posição
- PnL %
- Tempo na posição
- Distância do stop
- Distância do take profit

## 🛡️ Gestão de Risco

### Parâmetros INVIOLÁVEIS

```python
max_risk_per_trade: 2% do capital
max_simultaneous_risk: 6% do capital
max_daily_drawdown: 5% → fecha tudo, bloqueia 24h
max_total_drawdown: 15% → PAUSA agente
max_simultaneous_positions: 3
max_leverage: 5x (isolada)
stop_loss_atr_multiplier: 1.5x ATR
take_profit_atr_multiplier: 3.0x ATR
trailing_stop_activation: 1.5R
confluence_min_score: 8/14 para abrir posição
```

## 🧪 Smart Money Concepts

### Conceitos Implementados

1. **Swing Points**: Detecção algorítmica de Higher Highs/Lows e Lower Highs/Lows
2. **Market Structure**: Classificação automática (bullish/bearish/range)
3. **BOS (Break of Structure)**: Quebra de estrutura confirmando tendência
4. **CHoCH (Change of Character)**: Mudança de caráter sinalizando reversão
5. **Order Blocks**: Zonas institucionais de demanda/oferta
6. **Fair Value Gaps (FVG)**: Ineficiências de preço a serem preenchidas
7. **Breaker Blocks**: Order Blocks que falharam e inverteram polaridade
8. **Liquidity Levels**: BSL e SSL em swing highs/lows iguais
9. **Liquidity Sweeps**: Detecção de stop hunts
10. **Premium/Discount Zones**: Classificação de zonas de valor

## 🎮 Actions Space

O agente pode executar 5 ações:

```
0: HOLD          - Manter posição atual ou aguardar
1: OPEN_LONG     - Abrir posição comprada
2: OPEN_SHORT    - Abrir posição vendida
3: CLOSE         - Fechar posição atual
4: REDUCE_50     - Reduzir posição em 50% e mover stop para breakeven
```

## 📊 Reward Function

Recompensa multi-componente com 6 componentes:

```python
R_total = r_pnl + r_risk + r_consistency + r_overtrading + r_hold_bonus + r_invalid_action

r_pnl: pnl_pct * 100 (peso 1.0)
r_risk: penalidades por violações (peso 1.0)
r_consistency: sharpe_rolling_20 * 0.1 (peso 0.5)
r_overtrading: >3 trades/24h → -0.3 per extra (peso 0.5)
r_hold_bonus: +0.01/candle para posição lucrativa (peso 0.3)
r_invalid_action: -0.1 para ações impossíveis (peso 0.2)
```

## 🔄 Training Pipeline

### Fase 1: Exploração (500k timesteps)
- Alta entropia (ent_coef=0.01)
- Aprendizado exploratório
- PPO padrão

### Fase 2: Refinamento (1M timesteps)
- Carrega modelo da Fase 1
- Reduz entropia (ent_coef=0.005)
- Otimização refinada

### Fase 3: Validação
- Avaliação determinística em dados out-of-sample
- Cálculo de métricas: win rate, profit factor, sharpe, max DD

## 📝 Playbooks

Cada moeda possui um playbook customizado com:

- **Ajustes de Confluência**: Pontos extras/penalidades específicas
- **Ajustes de Risco**: Multiplicadores de tamanho e stop
- **Identificação de Ciclo**: Fase atual do ciclo próprio da moeda
- **Condições de Trading**: Quando operar ou evitar

Exemplo: **DOGE Playbook**
- Bonus +1.5 para social sentiment > 0.7
- Bonus +1.0 para Fear & Greed > 75
- Position size reduzido para 60% (beta 2.5)
- Opera apenas em risk-on

## 🔍 Monitoring & Alerts

### Métricas Rastreadas
- Win Rate
- Profit Factor
- Sharpe Ratio
- Max Drawdown
- Avg R-Multiple
- Expectancy

### Alertas Automáticos
- ⚠️ Drawdown crítico
- ⚠️ Flash crash/pump (>5% em 5 min)
- ⚠️ Funding rate extremo
- ⚠️ Cascade de liquidações
- ⚠️ Erros de sistema

## 🧪 Testing

```bash
# Executar todos os testes
pytest tests/

# Teste específico
pytest tests/test_indicators.py -v
```

## 📚 Database Schema

12 tabelas SQLite:
- `ohlcv_d1`, `ohlcv_h4`, `ohlcv_h1`
- `indicadores_tecnico`
- `sentimento_mercado`
- `dados_macro`
- `smc_market_structure`
- `smc_zones`
- `smc_liquidity`
- `trade_log`
- `eventos_websocket`
- `relatorios`

## ⚠️ Disclaimer

**Este projeto é para fins EDUCACIONAIS e de PESQUISA apenas.**

- NÃO é aconselhamento financeiro
- NÃO garante lucros
- Trading de futuros envolve ALTO RISCO de perda de capital
- Use APENAS capital que você pode perder
- O autor NÃO se responsabiliza por perdas financeiras
- SEMPRE teste em paper trading antes de usar capital real

## 📚 Documentação

Este projeto possui documentação extensiva organizada em `docs/`:

### Documentação do Projeto
- **[ROADMAP.md](docs/ROADMAP.md)** — Roadmap do projeto, releases planejadas e status atual
- **[RELEASES.md](docs/RELEASES.md)** — Detalhes de cada release (v0.1 a v1.1+)
- **[FEATURES.md](docs/FEATURES.md)** — Listagem de todas as features por release
- **[USER_STORIES.md](docs/USER_STORIES.md)** — User stories e critérios de aceite
- **[TRACKER.md](docs/TRACKER.md)** — Sprint tracker com tasks e progresso
- **[LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md)** — Lições aprendidas durante o desenvolvimento
- **[CHANGELOG.md](CHANGELOG.md)** — Registro de mudanças seguindo Keep a Changelog

### Documentação Técnica
- **[BINANCE_SDK_INTEGRATION.md](docs/BINANCE_SDK_INTEGRATION.md)** — Integração com Binance SDK
- **[CROSS_MARGIN_FIXES.md](docs/CROSS_MARGIN_FIXES.md)** — Correções de cross margin
- **[LAYER_IMPLEMENTATION.md](docs/LAYER_IMPLEMENTATION.md)** — Implementação das camadas de decisão

### Status do Projeto
**v0.2 (Pipeline Fix)** ✅ CONCLUÍDO (15/02/2026)
- Feature Engineering com 104 features totalmente funcional
- Multi-timeframe analysis integrada (D1 Bias, Market Regime, Correlação BTC)
- Reward Calculator com lógica de R-multiple corrigida
- Testes unitários completos

**Próxima Release:** v0.3 (Training Ready) 🎯
- Foco: Ambiente de treinamento RL funcional
- Pipeline de dados para treinamento
- Script de treinamento operacional

## 📄 Licença

MIT License - Veja o arquivo LICENSE para detalhes.

## 🤝 Contribuições

Contribuições são bem-vindas! Por favor:
1. Fork o repositório
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📧 Contato

Para questões e suporte, abra uma issue no GitHub.

---

**Desenvolvido com ❤️ para a comunidade de trading algorítmico**
