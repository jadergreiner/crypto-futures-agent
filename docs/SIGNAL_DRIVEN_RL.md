# Signal-Driven RL - Documentação

## Visão Geral

A arquitetura **Signal-Driven RL** representa uma evolução fundamental na forma como o agente aprende. Em vez de treinar em um environment simulado com dados históricos, o modelo agora aprende com **outcomes reais** de trades executados, criando um ciclo de feedback direto entre execução e aprendizado.

## Conceito

### Problema da Abordagem Anterior
- O agente treinava em um "jogo sintético" com dados históricos
- Convergência difícil (Win Rate ~48%, Profit Factor 0.66)
- Aprende a otimizar o environment simulado, não o mercado real

### Nova Abordagem: Signal-Driven RL
```
Modelo gera sinal → Execução (autotrade/manual) → Persistência rica de detalhes →
Acompanhamento a cada 15 min → Outcomes reais (parcial/stop/TP) →
Aprendizagem devolvida ao modelo
```

### Especialização por Símbolo
Cada símbolo tem seu próprio **sub-agente** especializado. Nem tudo que funciona para BTC funciona para ETH. Os sub-agentes aprendem padrões específicos de cada ativo.

## Arquitetura

### 1. Banco de Dados

#### Tabela `trade_signals`
Armazena sinais com **riqueza completa de detalhes** do momento da geração:

**Campos principais:**
- **Sinal**: direction, entry_price, stop_loss, take_profit_1/2/3
- **Risco**: position_size_suggested, risk_pct, risk_reward_ratio, leverage_suggested
- **Confluência**: confluence_score, confluence_details (JSON)
- **Contexto técnico**: RSI, EMAs, MACD, BB, ATR, ADX, etc.
- **Contexto SMC**: market_structure, BOS/CHOCH, order blocks, FVGs, liquidity
- **Sentimento**: funding_rate, long_short_ratio, open_interest, fear_greed
- **Multi-timeframe**: d1_bias, h4_trend, h1_trend, market_regime
- **Execução**: execution_mode, executed_at, executed_price, slippage
- **Resultado**: exit_price, pnl_usdt, pnl_pct, r_multiple, MFE, MAE, duration
- **RL**: reward_calculated, outcome_label (win/loss/breakeven)

#### Tabela `signal_evolution`
Snapshots a cada **15 minutos** enquanto posição está ativa:

**Campos:**
- Preço atual e PnL não-realizado
- Distância ao stop e TPs
- Indicadores no momento (RSI, MACD, BB, ATR, ADX)
- SMC (market_structure)
- Sentimento (funding_rate, long_short_ratio)
- **MFE/MAE acumulado** até o ponto
- Eventos: PARTIAL_1/2, STOP_MOVED, TRAILING_ACTIVATED

### 2. Módulos Principais

#### `agent/signal_reward.py` - SignalRewardCalculator
Calcula reward **rico e multidimensional** baseado em outcomes reais:

**Componentes:**
1. **r_pnl**: Reward por PnL realizado (proporcional ao R-multiple)
   - Bonus progressivo: R>3 (+2.0), R>2 (+1.0), R>1 (+0.5)
2. **r_partial_bonus**: Bonus por parciais executadas no momento certo
   - Bonus extra se parcial próxima ao MFE
3. **r_stop_penalty**: Penalidade proporcional por stop loss
   - Maior penalidade se trade esteve muito no lucro antes
4. **r_quality**: Reward por qualidade (ratio MFE/MAE)
   - Alto ratio = sinal foi fortemente a favor vs. contra
5. **r_timing**: Reward por timing de entrada
   - Compara entry_price vs melhor preço na janela
6. **r_management**: Reward por gestão (trailing stop, parciais)

**Exemplo:**
```python
from agent.signal_reward import SignalRewardCalculator

calc = SignalRewardCalculator()
reward = calc.calculate_signal_reward(signal, evolutions)
# {
#   'total': 4.2,
#   'r_pnl': 3.5,
#   'r_partial_bonus': 0.8,
#   'r_quality': 0.75,
#   'r_timing': 0.3,
#   'r_management': 0.4
# }
```

#### `agent/signal_environment.py` - SignalReplayEnv
Environment que **replica trades reais** como episódios para treino offline:

**Características:**
- Cada episódio = 1 trade real com snapshots de 15 em 15 min
- Observation: 20 features (PnL, distâncias, indicadores, momentum)
- Actions: HOLD, CLOSE, REDUCE_50, MOVE_STOP_BE, TIGHTEN_STOP
- Agente aprende a **gerenciar posição** durante sua vida

**Uso:**
```python
from agent.signal_environment import SignalReplayEnv

# Carregar sinais e evoluções do banco
signals = db.get_signals_for_training(symbol='BTCUSDT', limit=100)
evolutions = {s['id']: db.get_signal_evolution(s['id']) for s in signals}

# Criar environment
env = SignalReplayEnv(signals=signals, evolutions_dict=evolutions)

# Treinar agente
obs, info = env.reset()
obs, reward, done, truncated, info = env.step(action)
```

#### `agent/sub_agent_manager.py` - SubAgentManager
Gerencia **sub-agentes especializados** por símbolo:

**Funcionalidades:**
- `get_or_create_agent(symbol)`: Retorna sub-agente do símbolo
- `train_agent(symbol, signals, evolutions)`: Treina com dados reais
- `evaluate_signal_quality(symbol, context)`: Avalia novo sinal
- `get_agent_stats(symbol)`: Retorna win_rate, avg_r_multiple, etc.
- `save_all() / load_all()`: Persistência

**Uso:**
```python
from agent.sub_agent_manager import SubAgentManager

manager = SubAgentManager(base_dir='models/sub_agents')

# Treinar sub-agente de BTC com 50 trades
result = manager.train_agent(
    symbol='BTCUSDT',
    signals=signals_btc,
    evolutions=evolutions_btc,
    total_timesteps=10000
)

# Avaliar novo sinal
quality_score = manager.evaluate_signal_quality('BTCUSDT', signal_context)
```

#### `agent/trainer.py` - Método `train_from_real_signals`
Integração com Trainer existente para retreino com sinais reais:

```python
from agent.trainer import Trainer
from data.database import DatabaseManager

trainer = Trainer()
db = DatabaseManager('db/crypto_agent.db')

# Treinar sub-agente com sinais acumulados
result = trainer.train_from_real_signals(symbol='BTCUSDT', db=db)
```

### 3. Integração com PositionMonitor

**Modificações necessárias** em `monitoring/position_monitor.py`:

1. **Ao gerar sinal**: Inserir na tabela `trade_signals` com todo o contexto
2. **A cada 15 minutos**: Inserir snapshot em `signal_evolution`
3. **Ao fechar posição**: 
   - Calcular MFE/MAE/duration
   - Atualizar `trade_signals` com outcome
   - Calcular reward via `SignalRewardCalculator`
4. **Após N trades**: Retreinar sub-agente do símbolo

## Configuração

### `config/settings.py`

Novas constantes adicionadas:

```python
# Signal-Driven RL Configuration
SIGNAL_MONITORING_INTERVAL_MINUTES = 15  # Intervalo para snapshots
SIGNAL_MIN_TRADES_FOR_RETRAINING = 20    # Mínimo para retreino
SIGNAL_RETRAINING_TIMESTEPS = 10000      # Timesteps para retreino
SUB_AGENTS_BASE_DIR = "models/sub_agents"  # Diretório sub-agentes
```

## Fluxo de Uso

### 1. Geração de Sinal
```python
# Em position_monitor.py ou signal_generator.py
signal_data = {
    'timestamp': current_timestamp,
    'symbol': 'BTCUSDT',
    'direction': 'LONG',
    'entry_price': 50000.0,
    'stop_loss': 49000.0,
    'take_profit_1': 51000.0,
    # ... todos os campos de contexto ...
    'execution_mode': 'PENDING',
    'status': 'ACTIVE'
}

signal_id = db.insert_trade_signal(signal_data)
```

### 2. Execução
```python
# Após execução (autotrade ou manual)
db.update_signal_execution(
    signal_id=signal_id,
    executed_at=execution_timestamp,
    executed_price=50100.0,
    execution_mode='AUTOTRADE',
    execution_slippage_pct=0.2
)
```

### 3. Monitoramento (a cada 15 min)
```python
# No ciclo de monitoramento
evolution_data = {
    'signal_id': signal_id,
    'timestamp': current_timestamp,
    'current_price': current_price,
    'unrealized_pnl_pct': calculate_pnl(),
    # ... indicadores atuais ...
    'mfe_pct': max_favorable_excursion,
    'mae_pct': max_adverse_excursion,
    'event_type': 'PARTIAL_1' if partial_executed else None
}

db.insert_signal_evolution(evolution_data)
```

### 4. Finalização
```python
# Quando posição fecha
from agent.signal_reward import SignalRewardCalculator

calc = SignalRewardCalculator()
evolutions = db.get_signal_evolution(signal_id)

# Calcular reward
reward_result = calc.calculate_signal_reward(signal, evolutions)

# Atualizar outcome
outcome_data = {
    'status': 'CLOSED',
    'exit_price': 51500.0,
    'exit_timestamp': exit_timestamp,
    'exit_reason': 'take_profit_1',
    'pnl_usdt': 150.0,
    'pnl_pct': 3.0,
    'r_multiple': 1.5,
    'max_favorable_excursion_pct': 3.5,
    'max_adverse_excursion_pct': -0.5,
    'duration_minutes': 150,
    'reward_calculated': reward_result['total'],
    'outcome_label': 'win'
}

db.update_signal_outcome(signal_id, outcome_data)
```

### 5. Retreino (após acumular trades)
```python
# Verificar se há trades suficientes
from config.settings import SIGNAL_MIN_TRADES_FOR_RETRAINING

signals = db.get_signals_for_training(symbol='BTCUSDT')

if len(signals) >= SIGNAL_MIN_TRADES_FOR_RETRAINING:
    # Retreinar sub-agente
    from agent.trainer import Trainer
    
    trainer = Trainer()
    result = trainer.train_from_real_signals(symbol='BTCUSDT', db=db)
    
    if result['success']:
        logger.info(f"Sub-agente BTCUSDT retreinado: "
                   f"win_rate={result['win_rate']:.2%}")
```

## Testes

### Executar Testes
```bash
# Todos os testes
pytest tests/test_signal_*.py tests/test_sub_agent_manager.py tests/test_database_signals.py -v

# Testes individuais
pytest tests/test_signal_reward.py -v
pytest tests/test_signal_environment.py -v
pytest tests/test_sub_agent_manager.py -v
pytest tests/test_database_signals.py -v
```

### Cobertura
- `test_signal_reward.py`: 19 testes
- `test_signal_environment.py`: 15 testes
- `test_sub_agent_manager.py`: 13 testes
- `test_database_signals.py`: 10 testes
- **Total: 57 testes** ✅

## Vantagens da Nova Arquitetura

1. **Aprendizado com Dados Reais**: Modelo aprende com outcomes reais, não simulações
2. **Especialização por Símbolo**: Sub-agentes capturam padrões específicos de cada ativo
3. **Feedback Rico**: Reward multidimensional captura qualidade, timing e gestão
4. **Gestão de Posição**: Agente aprende quando reduzir, fechar ou segurar
5. **Evolução Contínua**: Sistema se adapta conforme acumula mais trades
6. **Rastreabilidade**: Todo o ciclo é persistido para análise posterior

## Próximos Passos

1. ✅ Implementar tabelas no banco
2. ✅ Criar módulos de reward, environment e sub-agentes
3. ✅ Criar testes unitários
4. ⏳ Integrar com PositionMonitor
5. ⏳ Testar em paper trading
6. ⏳ Validar com trades reais
7. ⏳ Analisar convergência e performance

## Referências

- **Round 4 Simplificado**: Sistema de reward atual do projeto
- **Gymnasium**: Framework de RL usado (atualização do OpenAI Gym)
- **Stable-Baselines3**: Biblioteca PPO usada para sub-agentes
- **SQLite**: Banco de dados para persistência

---

**Autor**: Sistema Signal-Driven RL  
**Data**: 2026-02-17  
**Versão**: 1.0
