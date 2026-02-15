# Pipeline de Treinamento RL - Guia de Uso

Este documento descreve como usar o pipeline de treinamento de Reinforcement Learning implementado para o agente de trading de futuros de criptomoedas.

## Visão Geral

O pipeline implementa um agente PPO (Proximal Policy Optimization) treinado em 3 fases:

1. **Fase 1: Exploração** (500k timesteps) - Alta entropia para exploração
2. **Fase 2: Refinamento** (1M timesteps) - Redução da entropia para convergência
3. **Fase 3: Validação** - Testes em dados out-of-sample

## Arquitetura

### Componentes Principais

- **`agent/data_loader.py`**: Carrega dados históricos do SQLite ou gera dados sintéticos
- **`agent/environment.py`**: Environment Gymnasium customizado para trading
- **`agent/reward.py`**: Calculadora de recompensas multi-componente
- **`agent/trainer.py`**: Gerenciador de treinamento em 3 fases
- **`agent/risk_manager.py`**: Gestão de risco com regras invioláveis
- **`backtest/backtester.py`**: Engine de backtesting
- **`backtest/walk_forward.py`**: Walk-forward optimization

### Observation Space

O environment retorna 104 features normalizadas:
- Preço e retornos (11 features)
- Indicadores técnicos (33 features) 
- SMC structures (15 features)
- Volume e liquidez (10 features)
- Sentiment (12 features)
- Macro (8 features)
- Correlação com BTC (3 features)
- Contexto D1 (2 features)
- Estado da posição (10 features)

### Action Space

5 ações discretas:
- 0: HOLD
- 1: OPEN_LONG
- 2: OPEN_SHORT
- 3: CLOSE
- 4: REDUCE_50 (reduz 50% da posição)

## Como Usar

### 1. Pré-requisitos

```bash
# Instalar dependências
pip install -r requirements.txt
```

As principais dependências RL já estão no `requirements.txt`:
- `gymnasium>=0.29.0`
- `stable-baselines3>=2.1.0`
- `torch>=2.0.0`

### 2. Treinamento

#### Opção A: Treinar com Dados Reais (requer DB populado)

```bash
# Coletar dados históricos primeiro
python main.py --collect-data

# Treinar modelo
python main.py --train
```

#### Opção B: Treinar com Dados Sintéticos

O pipeline possui fallback automático para dados sintéticos se o banco estiver vazio:

```bash
python main.py --train
```

O treinamento irá:
1. Carregar dados (reais ou sintéticos)
2. Executar Fase 1 (500k steps, ~30-60 min)
3. Executar Fase 2 (1M steps, ~60-120 min)
4. Executar Fase 3 (validação)
5. Salvar modelo final em `models/crypto_agent_ppo_final.zip`

### 3. Backtesting

```bash
python main.py --backtest --start-date 2024-01-01 --end-date 2024-12-31
```

Isso irá:
- Carregar o modelo treinado
- Executar o modelo em dados de teste
- Gerar relatório visual com gráficos
- Salvar em `backtest_report_YYYYMMDD_HHMMSS.png`

### 4. Teste Rápido

Para testar todo o pipeline rapidamente:

```bash
python test_rl_pipeline.py
```

Este script executa:
- Geração de dados sintéticos
- Teste do environment
- Mini-treinamento (10k steps)
- Backtesting com geração de relatório

## Estrutura de Dados

### Formato Esperado

O DataLoader espera dados em formato `Dict[str, Any]`:

```python
{
    'h1': pd.DataFrame,      # OHLCV H1 com indicadores
    'h4': pd.DataFrame,      # OHLCV H4 com indicadores (principal)
    'd1': pd.DataFrame,      # OHLCV D1 com indicadores
    'sentiment': Dict,       # Dados de sentiment (funding, OI, etc.)
    'macro': Dict,          # Dados macro (Fear/Greed, DXY, etc.)
    'smc': Dict            # Estruturas SMC (Order Blocks, FVGs, etc.)
}
```

### Indicadores Calculados Automaticamente

O DataLoader calcula automaticamente:
- EMAs (17, 34, 72, 144, 305, 610)
- RSI, MACD, Bollinger Bands
- ADX, ATR, OBV
- EMA Alignment Score

## Parâmetros de Risco (Invioláveis)

Configurados em `config/risk_params.py`:

- **Max Risk per Trade**: 2% do capital
- **Max Simultaneous Risk**: 6% do capital
- **Max Daily Drawdown**: 5% (fecha tudo e pausa 24h)
- **Max Total Drawdown**: 15% (pausa o agente)
- **Max Positions**: 3 simultâneas
- **Stop Loss**: 1.5x ATR
- **Take Profit**: 3.0x ATR (2:1 R:R mínimo)

## Reward Function

Recompensa multi-componente com 6 componentes:

1. **PnL** (peso 1.0): Baseado em % do capital + bonus para R-multiples altos
2. **Risk** (peso 1.0): Penalidade por não ter stop ou drawdown alto
3. **Consistency** (peso 0.5): Sharpe ratio rolante dos últimos 20 trades
4. **Overtrading** (peso 0.5): Penalidade por mais de 3 trades em 24h
5. **Hold Bonus** (peso 0.3): Pequeno bonus por manter posições lucrativas
6. **Invalid Action** (peso 0.2): Penalidade por ações inválidas

## Modelos Salvos

Os modelos são salvos em `models/`:

- `phase1_exploration.zip`: Modelo após fase 1
- `phase2_refinement.zip`: Modelo após fase 2
- `crypto_agent_ppo_final.zip`: Modelo final promovido (Sharpe>1.0, DD<15%)

## Walk-Forward Optimization

Para retreinamento adaptativo com janelas rolantes:

```python
from backtest.walk_forward import WalkForward
from agent.trainer import Trainer

wf = WalkForward(train_window=365, test_window=30)
trainer = Trainer()

# Executar walk-forward com janelas de 365d treino, 30d teste
results = wf.run(data=full_data, trainer=trainer)
```

## Métricas de Avaliação

O trainer calcula automaticamente:

- **Win Rate**: % de trades vencedores
- **Profit Factor**: Lucro bruto / Perda bruta
- **Sharpe Ratio**: Retorno médio / Volatilidade
- **Max Drawdown**: Maior queda desde o pico
- **Avg R-Multiple**: Média de R:R dos trades
- **Total Return**: Retorno total em %

## Troubleshooting

### Erro: "Binance SDK not found"

O treinamento funciona sem a Binance SDK usando dados sintéticos. Para usar dados reais, instale:

```bash
pip install binance-sdk-derivatives-trading-usds-futures
```

### Erro: "NaN in observations"

O environment já trata NaN substituindo por 0. Se persistir, verifique:
- Dados têm indicadores calculados?
- Warm-up period suficiente? (mínimo 30 candles)

### Performance ruim do modelo

Ajuste hiperparâmetros em `agent/trainer.py`:
- Aumentar `total_timesteps` para mais treinamento
- Ajustar `ent_coef` (entropia)
- Modificar pesos da reward function em `agent/reward.py`

## Próximos Passos

1. **Tune de Hiperparâmetros**: Experimentar diferentes configurações
2. **Feature Engineering**: Adicionar/remover features da observação
3. **Multi-Asset**: Treinar em múltiplos símbolos simultaneamente
4. **Transfer Learning**: Usar modelo pré-treinado como base

## Referências

- [Stable-Baselines3 Documentation](https://stable-baselines3.readthedocs.io/)
- [Gymnasium Documentation](https://gymnasium.farama.org/)
- [PPO Paper](https://arxiv.org/abs/1707.06347)

---

**Nota**: Este é um sistema experimental para fins educacionais. Sempre teste em modo paper antes de usar capital real.
