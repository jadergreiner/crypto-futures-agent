# Pipeline de Treinamento RL - Guia de Uso

Este documento descreve como usar o pipeline de treinamento de Reinforcement Learning implementado para o agente de trading de futuros de criptomoedas.

## Visão Geral

O pipeline implementa um agente PPO (Proximal Policy Optimization) treinado em 3 fases com **VecNormalize**:

1. **Fase 1: Exploração** (500k timesteps) - Alta entropia para exploração
   - Hiperparâmetros ajustados: `n_steps=4096`, `batch_size=128`, `ent_coef=0.03`
   - `normalize_advantage=True` para estabilidade
   - **VecNormalize** aplicado para normalização automática de observações e rewards
   - **Nota**: `ent_coef=0.03` (aumentado de 0.02) evita convergência prematura para HOLD
2. **Fase 2: Refinamento** (1M timesteps) - Redução da entropia para convergência
   - `ent_coef=0.005` para refinamento
   - Carrega estatísticas de normalização da Fase 1
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

### 2. Diagnóstico de Disponibilidade de Dados

**NOVO:** Antes de treinar, você pode verificar se há dados suficientes no banco:

```bash
python test_diagnosis_demo.py
```

O diagnóstico verifica:
- ✅ Quantidade de candles disponíveis por timeframe (H1, H4, D1)
- ✅ Quantidade necessária considerando split treino/validação (80/20) e min_length
- ✅ Se há candles suficientes para indicadores de longo prazo (ex: EMA_610 precisa de 610 dias)
- ✅ Atualização dos dados (último candle vs tempo atual)
- ✅ Recomendações claras de quantos dias coletar se houver dados insuficientes

#### Requisitos Mínimos de Dados

Para treinar com `min_length=1000` (padrão em `main.py`):
- **H4**: 1250+ candles (≈ 250 dias) antes do split 80/20
- **D1**: 730+ candles (≈ 2 anos) para suportar EMA(610) com margem
- **H1**: 5000+ candles (≈ 120 dias) recomendado

Estes valores estão configurados em `config/settings.py` no `HISTORICAL_PERIODS`.

### 3. Treinamento

#### Opção A: Treinar com Dados Reais (requer DB populado)

```bash
# Coletar dados históricos primeiro
python main.py --setup

# O comando agora faz diagnóstico automático antes de treinar
python main.py --train
```

**MUDANÇA IMPORTANTE:** O treinamento agora:
1. ✅ Executa diagnóstico automático de dados
2. ✅ Exibe relatório detalhado de disponibilidade
3. ✅ **PARA** se dados insuficientes (sem fallback silencioso)
4. ✅ Mostra recomendações claras de como resolver

Se o diagnóstico detectar dados insuficientes, você verá:
```
❌ DADOS INSUFICIENTES PARA TREINAMENTO
  H4: faltam 500 candles → Coletar mais 104 dias de dados H4
  D1: insuficiente para EMA(610) → Colete mais 245 dias

Execute: python main.py --setup
Ou aumente HISTORICAL_PERIODS em config/settings.py
```

#### Opção B: Treinar com Dados Sintéticos

Para testes rápidos sem dados reais, use o fallback manual:

```bash
# Edite agent/data_loader.py ou use flag especial (a implementar)
python main.py --train --synthetic
```

O treinamento (quando dados OK) irá:
1. Verificar disponibilidade de dados
2. Carregar dados (reais ou sintéticos)
3. Executar Fase 1 (500k steps, ~30-60 min)
4. Executar Fase 2 (1M steps, ~60-120 min)
5. Executar Fase 3 (validação)
6. Salvar modelo final em `models/crypto_agent_ppo_final.zip`

### 4. Backtesting

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

Recompensa multi-componente **normalizada** com 8 componentes:

1. **PnL** (peso 1.0): Baseado em % do capital diretamente (não multiplicado por 100)
   - Amplificação × 10 para sinal mais forte
   - Bonus de **0.5** para R-multiples > 3.0
   - Bonus de **0.2** para R-multiples > 2.0
   - Clipping final em **[-10, +10]** para compatibilidade com PPO
2. **Risk** (peso 1.0): Penalidade por não ter stop ou drawdown alto
3. **Consistency** (peso 0.5): Sharpe ratio rolante dos últimos 20 trades
4. **Overtrading** (peso 0.5): Penalidade por mais de 3 trades em 24h
5. **Hold Bonus** (peso 0.5): **Proporcional ao PnL** - `0.02 + pnl_pct × 0.05` para posições lucrativas
   - Penalidade `-0.01` para PnL < -2% (incentiva sair de perdedoras)
6. **Invalid Action** (peso 0.2): Penalidade por ações inválidas
7. **Unrealized PnL** (peso 0.3): Sinal contínuo baseado em PnL não-realizado × 0.1
8. **Inactivity** (peso 0.5): Penalidade por inatividade prolongada
   - Threshold: 10 candles H4 (~40h sem operar)
   - Penalidade: -0.02 por step excedente (cap em -0.8 após 40 steps)

**⚠️ IMPORTANTE**: Os rewards foram normalizados para a faixa [-10, +10] para evitar problemas de escala com o PPO. Versões anteriores usavam `pnl_pct * 100` que gerava valores de centenas, incompatíveis com o treinamento RL.

### Mudanças Recentes (v2.0)

Para combater o **conservadorismo excessivo** do agente (HOLD demais):
- **Penalidade de inatividade** aumentada: threshold reduzido de 20→10 candles, taxa 0.01→0.02, peso 0.3→0.5
- **Hold bonus** tornado proporcional ao lucro (antes era fixo em +0.01)
- **Entropia** na Fase 1 aumentada de 0.02→0.03 para evitar convergência prematura

## Modelos Salvos

Os modelos são salvos em `models/`:

- `phase1_exploration.zip`: Modelo após fase 1
- `phase1_vec_normalize.pkl`: Estatísticas de normalização da fase 1
- `phase2_refinement.zip`: Modelo após fase 2
- `phase2_vec_normalize.pkl`: Estatísticas de normalização da fase 2
- `crypto_agent_ppo_final.zip`: Modelo final promovido (Sharpe>1.0, DD<15%)

**⚠️ IMPORTANTE**: As estatísticas de normalização (`vec_normalize.pkl`) devem ser carregadas junto com o modelo para manter a mesma escala de observações e rewards durante inferência.

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
- Ajustar `ent_coef` (entropia): 0.02 para exploração, 0.005 para refinamento
- Modificar pesos da reward function em `agent/reward.py`
- Verificar se `VecNormalize` está aplicado (obrigatório para estabilidade)

### Problemas de convergência do PPO

Se você observar nos logs do TensorBoard:
- `clip_fraction = 0.0` → Política não está sendo atualizada
- `approx_kl ≈ 0.0` → Atualizações insignificantes
- `value_loss` muito alto → Value function com escala errada
- `entropy` quase no máximo após muitos steps → Agente agindo aleatoriamente

**Solução**: As correções implementadas incluem:
1. **Rewards normalizados** para [-10, +10] via clipping
2. **VecNormalize** aplicado para normalizar observações e rewards automaticamente
3. **Hiperparâmetros ajustados**: `n_steps=4096`, `batch_size=128`, `normalize_advantage=True`
4. **Entropia aumentada** na fase 1 (`ent_coef=0.03`) para melhor exploração e evitar convergência prematura para HOLD
5. **Hold bonus proporcional** ao PnL (0.02 + pnl_pct × 0.05) para incentivar manter trades lucrativos
6. **Penalidade de inatividade agressiva** (threshold 10 candles, taxa 0.02, peso 0.5) para combater conservadorismo

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
