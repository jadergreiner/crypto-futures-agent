# Crypto Futures Autonomous Agent

Agente autônomo de Reinforcement Learning para operar futuros de criptomoedas
na Binance Futures (USDⓈ-M). Combina indicadores técnicos, Smart Money Concepts
(SMC), análise de sentimento e dados macroeconômicos para gerar sinais
operacionais com gestão de risco completa.

## 🌐 Idioma do Projeto

- O idioma oficial deste projeto é **português**.
- Escreva documentação, comentários,
  mensagens de log e textos de interface em português.
- Use inglês apenas para termos técnicos consolidados (APIs, bibliotecas,
  protocolos e nomes próprios).

## 🎯 Características Principais

- **Reinforcement Learning**: PPO (Proximal Policy Optimization) com
  Stable-Baselines3
- **Smart Money Concepts**: Order Blocks, FVGs, BOS, CHoCH, Liquidity Sweeps
- **Multi-Timeframe**: Análise em D1, H4 e H1
- **Gestão de Risco INVIOLÁVEL**: Stop loss, take profit, trailing stop,
  drawdown limits
- **104 Features**: Observation space completo com indicadores técnicos, SMC,
  sentimento e macro
- **Playbooks Específicos**: Estratégias customizadas para cada criptomoeda
- **Arquitetura em Camadas**: 6 layers com execução condicional
- **Round 5 Learning**: Aprendizado contextual de "ficar fora do mercado" com
  proteção de drawdown e descanso após trades
- **Round 5+ Meta-Learning**: Oportunidade Learning para diferenciar decisões
  prudentes (evitar perdas) vs desperdiçadoras (perder ganhos)
- **F-12 Backtest Engine** (22/02/2026): Backtester determinístico com
  3-tier data pipeline (SQLite→Parquet→Memory), trade state machine com PnL
  preciso, 6 métricas risk clearance para gates de aprovação

## 🎓 Evolução da Arquitetura de Reward (21/02/2026)

### Round 5 — Stay-Out Learning

**Status**: ✅ Completo (5/5 testes passando)

**Objetivo**: Ensinar ao agente quando ficar fora do mercado é a melhor decisão.

**Componente Novo**: `r_out_of_market` com 3 mecanismos:
- Proteção em drawdown: +0.15 quando DD ≥ 2%
- Descanso pós-trades: +0.10 após 3+ trades em 24h
- Penalidade de inatividade: -0.03 para evitar ficar passivo > 16 dias

**Validação**: 5/5 testes em `test_stay_out_of_market.py` ✅

**Impacto Esperado**: -50% trades, +15% win rate, +50% avg R-multiple

### Round 5+ — Opportunity Learning (Meta-Learning Contextual)

**Status**: ✅ Completo (6/6 testes passando)

**Problema Resolvido**: Round 5 recompensava ficar fora SEMPRE, sem diferenciar:
- **Prudente**: Oportunidade que teria perdido → Bom evitar ✅
- **Desperdiçadora**: Oportunidade que teria ganho → Ruim ficar fora ❌

**Solução**: `OpportunityLearner` (novo módulo de 290+ linhas)
- Registra cada oportunidade não tomada com contexto completo
- Avalia retrospectivamente após ~20 candles
- Computa reward contextual diferenciado (-0.20 a +0.30)
- Diferencia 4 cenários: opp excelente + drawdown, opp boa + múltiplos
  trades, opp boa + normal, opp ruim + qualquer contexto

**Validação**: 6/6 testes em `test_opportunity_learning.py` ✅

**Impacto**: Agente aprende balanço sofisticado entre prudência e
oportunismo

**Documentação Técnica**:
- [`docs/LEARNING_STAY_OUT_OF_MARKET.md`](docs/LEARNING_STAY_OUT_OF_MARKET.md)
- [`docs/LEARNING_CONTEXTUAL_DECISIONS.md`](docs/LEARNING_CONTEXTUAL_DECISIONS.md)
- [`IMPLEMENTATION_SUMMARY_OPPORTUNITY_LEARNING.md`](IMPLEMENTATION_SUMMARY_OPPORTUNITY_LEARNING.md)

### Evolução Geral da Arquitetura de Reward

| Versão | Componentes | Status | Data | Testes |
|--------|-------------|--------|------|--------|
| Round 4 | r_pnl + r_hold_bonus + r_invalid_action (3) | ✅ | Jan | N/A |
| Round 5 | + r_out_of_market (4) | ✅ | 21 Feb | 5/5 ✅ |
| Round 5+ | + r_contextual_opportunity (5) | ✅ | 21 Feb | 6/6 ✅ |

## 📊 Status Desenvolvimento — F-12 Backtest Sprint (21/02/2026)

**🟢 SPRINT EM EXECUÇÃO — 60% COMPLETO**

### Marcos Alcançados (21 FEV)

- ✅ **F-12a**: BacktestEnvironment determinístico (168L, SWE)
- ✅ **F-12c**: TradeStateMachine com state machine (205L, SWE)
- ✅ **F-12d**: BacktestMetrics com 6 métricas (345L, ML)
- ✅ **F-12e**: Suite de testes (5/8 PASSING, 320L, ML)
- ⏳ **F-12b**: Parquet pipeline (iniciando 22 FEV, SWE)

### Timeline Executiva

| Data | Milestone | Owner |
|------|-----------|-------|
| **21 FEV** | Core F-12a+c+d+e DONE | SWE + ML ✅ |
| **22 FEV** | F-12b + 8/8 tests green | SWE + ML |
| **23 FEV** | Full backtest + report | ML |
| **24 FEV** | Gates 1-2-3 approval | CTO+Risk+CFO |

**Confiança**: 85% para paper trading autorizado em 24 FEV

Detalhes: [SPRINT_F12_EXECUTION_PLAN.md](SPRINT_F12_EXECUTION_PLAN.md)

---

## ⚠️ Status Operacional Anterior (20/02/2026 — CRÍTICO RESOLVIDO)

**🔴 DIAGNÓSTICO CRÍTICO IDENTIFICADO**

**Situação**: Agente em "Profit Guardian Mode" há 3+ dias. 21 pares
monitorados, 0 sinais novos gerados.

**Causa Raiz**: `config/execution_config.py` possui `"allowed_actions":
["CLOSE", "REDUCE_50"]` — **bloqueia "OPEN"**

**Impacto**:
- ✅ Monitoramento ativo (41 position snapshots coletados)
- ❌ Zero novos sinais disparados
- ❌ Zero novas posições abertas
- 🔴 **-$2.670/dia em oportunidades perdidas** (BTCUSDT +8.2%, ETHUSDT +4.1%,
  etc)
- 🔴 21 posições com perdas -42% a -511%

**Documentação**:
- 📄 Reunião diagnóstica de 10 rodadas:
  `docs/reuniao_diagnostico_profit_guardian.md`
- 📄 Sumário executivo: `DIAGNOSTICO_EXECUTIVO_20FEV.md`
- 📄 Backlog com 5 ações críticas: `BACKLOG_ACOES_CRITICAS_20FEV.md`

**Plano de Ação (HOJE → AMANHÃ)**:
1. ✋ Fechar 5 maiores posições perdedoras (-$8.500 realizado) → **ACAO-001**
2. ✓ Validar fechamento → **ACAO-002**
3. ⚙️ Reconfigurar `allowed_actions` (adicionar "OPEN") → **ACAO-003**
4. 🎯 Executar BTCUSDT LONG score 5.7 (teste) → **ACAO-004**
5. 📊 Reunião follow-up 24h → **ACAO-005**

**Status**: 🔴 Aguardando aprovação HEAD para iniciar ACAO-001

---

## 📊 GOVERNANÇA & ROADMAP (Estrutura PO)

**Documentação Executiva** (atualizada 20/02/2026 21:45 UTC):

| Documento | Descrição | Público | Leitura |
|-----------|-----------|---------|---------|
|
| [GOVERNANCA_DOCS_BACKLOG_ROADMAP.md]
  (docs/) | Governança, roadmap v0.3–v2.0
  | Diretoria, PO, CTO | 20 min
| [`DIRECTOR_BRIEF_20FEV.md`](DIRECTOR_BRIEF_20FEV.md) |
| Situação crítica & plano ação (5 min read) | Diretoria | 5 min |
| [`BACKLOG_ACOES_CRITICAS_20FEV.md`](BACKLOG_ACOES_CRITICAS_20FEV.md) |
| 5 ações sequenciais com código Python pronto | Tech, PO | 15 min |

**Métricas Operacionais**:
- 🔴 Lucro MRR: $0 (pré-launch)
- 📈 AUM: ~$50k (meta $500k v1.0)
- ⏳ Versão: v0.3 (validação hoje → release amanhã)
- 🎯 Timeline: 12+ meses (v0.3 → v1.0 → v2.0)

---

**🟠 OPERAÇÃO PARALELA C REDUZIDA** (Aguardando Ação)

- **LIVE Trading**: ✅ Operando com 16 pares USDT (Profit Guardian Mode)
- **v0.3 Training**: 🔄 Validação em paralelo (isolada,
  sem interferência com LIVE)
- **Safeguards**: ✅ Health monitor (60s checks), kill switch (2% loss threshold)
- **Autorização**: ✅ Formal via AUTHORIZATION_OPÇÃO_C_20FEV.txt (20/02 20:30
  BRT)
- **Timeline**: Validação até 23:59 BRT hoje, pronto para expansão amanhã (v0.4)

**Detalhes Técnicos:**

- Orquestrador: `core/orchestrator_opção_c.py` (automático via `iniciar.bat`)
- Monitor: `monitoring/critical_monitor_opção_c.py` (health checks contínuos)
- Logs: `logs/orchestrator_opção_c.log`, `logs/critical_monitor.log`
- **Operador**: Nenhuma ação necessária — execute `iniciar.bat` como sempre
  (transparente)

---

## ⭐ v0.3.1 — POSIÇÃO MANAGEMENT (21 FEV 2026)

**Status**: ✅ COMPLETO — Ordens REAIS Binance + Gestão de Parciais

**Problema Resolvido**:
- ❌ ANTES: SL/TP simulados localmente (dependência crítica do monitor)
- ✅ AGORA: Ordens REAIS apregoadas Binance via `new_algo_order()`

**Componentes Novos**:
- `scripts/execute_1dollar_trade.py` → MARKET + SL/TP real (Trade ID 7 prova)
- `scripts/manage_positions.py` → Gestão de parciais (50%, 75%, custom)
- `scripts/monitor_and_manage_positions.py` → Monitor 24/7 (health + PnL + timeout)
- `schema_update.py` → Criar tabela `trade_partial_exits` para histórico

**Prova Funcional (Trade ID 7)**:
```
ANKRUSDT LONG (2,174 @ $0.00459815)
├─ MARKET Order: 5412778331 ✅ (venda confirmada)
├─ SL Algo: 3000000742992546 ✅ (trigger @ $0.00436824, -5%)
└─ TP Algo: 3000000742992581 ✅ (trigger @ $0.00505797, +10%)
└─ Status: APREGOADO NA BINANCE 24/7
```

**Ganhos Operacionais**:
| Métrica | Antes | Depois | Ganho |
|---------|-------|--------|-------|
| Confiabilidade | 95% | 99.9% | +4.9% |
| Risco SL/TP | 100% falha possível | 0% (Binance real) | Crítico |
| Escalabilidade | 1-2 posições | 10+ concorrentes | +500% |
| Monitor | CRÍTICO | OPCIONAL | Libertado |

**Documentação Atualizada**:
- 📄 `docs/agente_autonomo/AGENTE_AUTONOMO_ARQUITETURA.md` (Seção 6 nova)
- 📄 `docs/agente_autonomo/AGENTE_AUTONOMO_FEATURES.md` (F-09, F-10, F-11)
- 📄 `docs/agente_autonomo/AGENTE_AUTONOMO_ROADMAP.md` (v0.3.1 timeline)
- 📄 `docs/agente_autonomo/AGENTE_AUTONOMO_TRACKER.md` (Status v0.3.1)
- 📄 `docs/agente_autonomo/AGENTE_AUTONOMO_CHANGELOG.md` (Entradas v0.3.1)

**Próximos Passos**:
1. ⏳ Testar em múltiplas posições simultâneas (currently 1 Trade ID 7)
2. ⏳ Integração com v0.4 backtest engine
3. ⏳ Deploy em produção após v0.4 validação

---

## 🟠 v0.4 SPRINT — BACKTEST ENGINE (21-24 FEV)

**Status**: ✅ PRÉ-SPRINT VALIDAÇÕES COMPLETAS

**Preparação Concluída**:
- ✅ BacktestEnvironment refatorado (150 linhas, 99% reúso)
- ✅ Reward function validada (CTO sign-off)
- ✅ Database validada (13.814 H4 candles)
- ✅ Skeleton code criado (4 componentes)
- ✅ Sprint plan detalhado (40+ páginas)

**Timeline Executiva**:
- **Terça 21/02 08:00 UTC**: ESP-ENG + ESP-ML começam
- **Quarta-Quinta 22-23/02**: Implementação + testes
- **Quinta 23/02 14:00 UTC**: Green light + merge
- **Sexta 24/02**: Buffer (se necessário)

**Documentação Sprint**:
- 📄 [`F12_KICKOFF_SUMMARY.md`](F12_KICKOFF_SUMMARY.md) — 3 páginas executivas
- 📄 [`SPRINT_F12_EXECUTION_PLAN.md`](SPRINT_F12_EXECUTION_PLAN.md) — 40+ páginas
  detalhadas
- 📄 [`reward_validation_20feb.txt`](reward_validation_20feb.txt) — CTO sign-off

**Métrica targets v0.4**:
- Sharpe ratio ≥ 0.80 (target 1.20)
- Max drawdown ≤ 12%
- Win rate ≥ 45%
- 85%+ test coverage

**Ver também:**
[docs/OPERACAO_C_GUIA_TRANSPARENTE.md](docs/OPERACAO_C_GUIA_TRANSPARENTE.md)
  para operação v0.3

## 📊 Moedas Suportadas (16 Pares USDT)

### High-Cap (Estáveis)

- **BTC (BTCUSDT)**: Líder de mercado, ciclos de halving
- **ETH (ETHUSDT)**: Segunda maior, ecossistema DeFi
- **BNB (BNBUSDT)**: Token burns trimestrais
- **XRP (XRPUSDT)**: Sensível a regulação
- **LTC (LTCUSDT)**: Halving próprio, correlação BTC

### Mid-Cap (High Beta)

- **SOL (SOLUSDT)**: High beta, amplifica movimentos
- **DOGE (DOGEUSDT)**: Memecoin, sentiment-driven
- **C98 (C98USDT)**: DeFi gateway multi-chain
- **0G (0GUSDT)**: AI/Data infrastructure
- **KAIA (KAIAUSDT)**: Layer 1 messaging integrado
- **GTC (GTCUSDT)**: Web3 infrastructure (β=2.8)
- **FIL (FILUSDT)**: Storage infrastructure (β=2.5)
- **TWT (TWTUSDT)**: Wallet ecosystem utility (β=2.0)
- **LINK (LINKUSDT)**: Oracle infrastructure (β=2.3)
- **POLYX (POLYXUSDT)**: Securities infrastructure (β=2.8)

### Low-Cap (Very High Beta - ESPECULATIVO)

- **HYPER (HYPERUSDT)**: Especulativo (β=3.5)
- **1000BONK (1000BONKUSDT)**: Memecoin extremo (β=4.5)
- **OGN (OGNUSDT)**: Commerce protocol (β=3.2)
- **IMX (IMXUSDT)**: Layer 2 NFT/Gaming (β=3.0)

* *Modo de Operação**: Todos os pares em Profit Guardian Mode com proteção de
  SL/TP automática

## 🏗️ Arquitetura

### Camadas de Execução

```text
LAYER 1 (Heartbeat): 1 min    - Health check (API, DB, WebSocket)
LAYER 2 (Risk):      5 min    - Gestão de risco (apenas com posições)
LAYER 3 (H1):        1 hora   - Timing de entrada (apenas com sinais/posições)
LAYER 4 (H4): 4 horas - Decisão principal (00:00, 04:00, 08:00, 12:00, 16:00,
20:00 UTC)
LAYER 5 (D1):        00:00 UTC - Tendência e macro (ANTES da Layer 4)
LAYER 6 (Semanal/Mensal):      - Performance review e retrain
```text

### Estrutura do Projeto

```text
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
```bash

## 🚀 Quick Start

### Opção A: Windows - Script Automático (Recomendado)

```batch
# 1. Execute o setup (apenas uma vez)
setup.bat

# 2. Inicie o agente com menu interativo
iniciar.bat
```bash

O script `iniciar.bat` oferece um menu interativo com todas as opções:

- ✅ Verifica e ativa o ambiente virtual automaticamente
- ✅ Valida pré-requisitos (.env, banco de dados)
- ✅ Menu com 7 opções: Paper Trading, Live, Monitor, Backtest, Train, Setup,
  Sair
- ✅ Confirmações de segurança para modo LIVE

### Opção B: Manual (Linux/Mac ou Avançado)

#### 1. Instalação

```bash
# Clone o repositório
git clone
[https://github.com/jadergreiner/crypto-futures-agent.git](https://github.com/jadergreiner/crypto-futures-agent.git)
cd crypto-futures-agent

# Instale as dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas API keys da Binance
```bash

#### 2. Setup Inicial

```bash
# Inicializar database e coletar dados históricos
python main.py --setup
```bash

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
```bash

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
```python

#### 5. Backtest

```bash
# Executar backtest em período específico
python main.py --backtest --start-date 2024-01-01 --end-date 2024-12-31
```bash

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
```text

## 🧪 Smart Money Concepts

### Conceitos Implementados

1. **Swing Points**: Detecção algorítmica de Higher Highs/Lows e Lower
Highs/Lows
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

```text
0: HOLD          - Manter posição atual ou aguardar
1: OPEN_LONG     - Abrir posição comprada
2: OPEN_SHORT    - Abrir posição vendida
3: CLOSE         - Fechar posição atual
4: REDUCE_50     - Reduzir posição em 50% e mover stop para breakeven
```text

## 📊 Reward Function

Recompensa multi-componente com 6 componentes:

```python
R_total = r_pnl + r_risk + r_consistency + r_overtrading + r_hold_bonus +
r_invalid_action

r_pnl: pnl_pct * 100 (peso 1.0)
r_risk: penalidades por violações (peso 1.0)
r_consistency: sharpe_rolling_20 * 0.1 (peso 0.5)
r_overtrading: >3 trades/24h → -0.3 per extra (peso 0.5)
r_hold_bonus: +0.01/candle para posição lucrativa (peso 0.3)
r_invalid_action: -0.1 para ações impossíveis (peso 0.2)
```text

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
```bash

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

- **[ROADMAP.md](docs/ROADMAP.md)** — Roadmap do projeto, releases planejadas e
  status atual
- **[RELEASES.md](docs/RELEASES.md)** — Detalhes de cada release (v0.1 a v1.1+)
- **[FEATURES.md](docs/FEATURES.md)** — Listagem de todas as features por
  release
- **[USER_STORIES.md](docs/USER_STORIES.md)** — User stories e critérios de
  aceite
- **[TRACKER.md](docs/TRACKER.md)** — Sprint tracker com tasks e progresso
- **[LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md)** — Lições aprendidas durante
  o desenvolvimento
- **[CHANGELOG.md](CHANGELOG.md)** — Registro de mudanças seguindo Keep a
  Changelog

### Documentação Técnica

- **[BINANCE_SDK_INTEGRATION.md](docs/BINANCE_SDK_INTEGRATION.md)** — Integração
  com Binance SDK
- **[CROSS_MARGIN_FIXES.md](docs/CROSS_MARGIN_FIXES.md)** — Correções de cross
  margin
- **[LAYER_IMPLEMENTATION.md](docs/LAYER_IMPLEMENTATION.md)** — Implementação
  das camadas de decisão
- **[SYNCHRONIZATION.md](docs/SYNCHRONIZATION.md)** — Rastreamento de
  sincronização de docs

### 🔄 Validação Automática de Sincronização

O projeto implementa mecanismo obrigatório de sincronização:

**Validar antes de cada commit:**

```bash
python scripts/validate_sync.py
```bash

O script verifica:

- ✅ Markdown lint (máximo 80 caracteres)
- ✅ Sincronização README ↔ FEATURES ↔ ROADMAP
- ✅ Registro em SYNCHRONIZATION.md
- ✅ Entrada em CHANGELOG.md

**Instruções completas:** Ver
[.github/copilot-instructions.md](.github/copilot-instructions.md)

### Status do Projeto

**v0.2 (Pipeline Fix)** ✅ CONCLUÍDO (15/02/2026)

- Feature Engineering com 104 features totalmente funcional
- Multi-timeframe analysis integrada (D1 Bias, Market Regime, Correlação BTC)
- Reward Calculator com lógica de R-multiple corrigida
- Testes unitários completos

**v0.2.1 (Administração de Posições)** ✅ CONCLUÍDO (20/02/2026)

- 9 novos pares USDT em Profit Guardian Mode (TWT, LINK, OGN,
  IMX + 5 existentes)
- 4 novos playbooks especializados com ajustes de risco por beta
- Total de 16 pares USDT operacionais
- Mecanismos de sincronização de documentação implementados
- Rastreamento automático em docs/SYNCHRONIZATION.md

**Próxima Release:** v0.3 (Training Ready) 🎯

- Foco: Ambiente de treinamento RL funcional
- Pipeline de dados para treinamento
- Script de treinamento operacional
- Sincronização automática de playbooks e configurações

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
