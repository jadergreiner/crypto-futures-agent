"""
Especificação técnica para M2-016.3 - Melhorias de Features e Reward Engineering.

Documento: designs/M2_016_3_FEATURE_REWARD_IMPROVEMENTS.md
Data: 2026-03-14
Status: DRAFT - Revisão antes de execução
"""

# M2-016.3 - Melhorias de Features e Reward Engineering

## 1. VALIDAÇÃO DE EPISÓDIOS DE TREINO

### 1.1 Status Atual (2026-03-14)
- **Episódios persistidos**: 7 (todos com label='context')
- **Episódios com outcomes reais**: 0 (aguardando execuções EXITED)
- **Script de validação**: `scripts/model2/validate_training_episodes.py` ✅ PRONTO

### 1.2 Próximas Etapas
1. Aguardar ~24-48h da M2-016.2 para acumular episódios com status=EXITED
2. Executar validação de acurácia de labels (win/loss/breakeven)
3. Analisar:
   - Taxa de acurácia geral
   - Distribuição de labels (% win vs loss vs breakeven)
   - Padrões de erro (onde o label falha)
   - Correlação entre features e outcomes

### 1.3 Métrica de Sucesso
- **Meta de acurácia de labels**: >= 85% (labels corretos vs outcomes reais)
- **Taxa de cobertura**: >= 70% episódios com entrada/saída completa


## 2. ENRIQUECIMENTO DE FEATURES

### 2.1 Features Atuais (training_episodes.features)
```python
{
    "latest_candle": {           # OHLCV da vela atual
        "open", "high", "low", "close", "volume"
    },
    "signal_snapshot": {          # Estado da oportunidade
        "opportunity_id", "symbol", "status", 
        "trigger_price", "invalidation_price", "monitoring_started_at"
    },
    "gate": {                     # Validações do gate live
        "symbol", "timeframe", "execution_mode", 
        "max_daily_entries", "max_margin_per_position_usd", ...
    }
}
```

### 2.2 Features Candidatas para Enriquecimento

#### 2.2.1 Dados de Mercado (Binance API)
```python
{
    "ohlcv_context": {
        # H1, H4, D1 OHLCV para contexto multi-timeframe
        "h1_last_5_closes": [],     # Últimas 5 fechas H1
        "h4_last_10_closes": [],    # Últimas 10 fechas H4
        "d1_open_close": {},        # Open/Close do dia
        "volume_ma_20": 0.0,        # Volume médio últimas 20 velas
    },
    "volatility": {
        "atr_20": 0.0,              # ATR 20 velas (volatilidade)
        "rsi_14": 0.0,              # RSI 14 velas (momentum)
        "bb_position": 0.0,         # Posição dentro das Bandas de Bollinger
    }
}
```

#### 2.2.2 Dados de Futures (Binance Futures)
```python
{
    "futures_metrics": {
        "funding_rate": 0.0,        # Taxa de financiamento (indica pressão de longs/shorts)
        "open_interest": 0.0,       # Interesse aberto (volume total)
        "long_short_ratio": 0.0,    # Razão posições long vs short
        "mark_price": 0.0,          # Mark price (preço justo derivado)
        "basis": 0.0,               # Spot - future spread
    }
}
```

#### 2.2.3 Histórico de Sinais no Símbolo
```python
{
    "symbol_history": {
        "signals_last_7d": 0,       # Quantidade de sinais últimos 7 dias
        "win_rate_7d": 0.0,         # Taxa de vitória últimos 7 dias
        "avg_reward_7d": 0.0,       # Recompensa média últimos 7 dias
        "consecutive_losses": 0,    # Perdas consecutivas atuais
    }
}
```

### 2.3 Roadmap de Implementação

#### Fase 1 (Semana 1): Features básicas
- [ ] Adicionar volatilidade (ATR, RSI) ao `persist_training_episodes.py`
- [ ] Adicionar multi-timeframe OHLCV (H1, H4, D1)
- [ ] Testar execução do pipeline com novos dados

#### Fase 2 (Semana 2): Dados de futures
- [ ] Integrar funding_rate e open_interest via Binance API
- [ ] Adicionar mark_price e basis
- [ ] Criar cache local de dados de futures

#### Fase 3 (Semana 3): Histórico de símbolo
- [ ] Calcular win_rate_7d, avg_reward_7d por símbolo
- [ ] Rastrear consecutive_losses
- [ ] Persistir em `symbol_training_stats` (tabela nova)


## 3. AJUSTES NA REWARD FUNCTION

### 3.1 Reward Atual (agent/reward.py)
```python
Components:
  r_pnl: Ganho/perda realizado (base)
  r_hold_bonus: Incentivo para manter posições lucrativas
  r_invalid_action: Penalidade para ações inválidas
  r_out_of_market: Recompensa por ficar fora em condições ruins
```

### 3.2 Reward Estendida Proposta

#### 3.2.1 Componente Sharpe Ratio
```python
# Calcular empiricamente Sharpe durante episódios
sharpe_bonus = 0.5 if sharpe_ratio > 1.0 else 0.0
# Recompensa quando desempenho tem boa relação risco/retorno
```

#### 3.2.2 Componente Drawdown
```python
max_dd = (peak_capital - min_capital) / peak_capital
dd_penalty = -0.3 * max_dd if max_dd > 0.1 else 0.0
# Penaliza drawdown > 10%
```

#### 3.2.3 Componente Recovery Time
```python
recovery_steps = steps_from_trough_to_new_peak
recovery_bonus = 0.2 if recovery_steps < 20 else -0.1
# Recompensa para recuperação rápida
```

### 3.3 Nova Função de Reward (pseudocódigo)
```python
def reward_extended(
    traded: bool,
    pnl: float,
    peak_capital: float,
    trough_capital: float,
    steps: int,
    sharpe: float,
    action_valid: bool,
) -> float:
    r_pnl = pnl_scale * pnl if traded else 0
    r_hold = hold_bonus_calc(pnl) if traded else 0
    r_sharpe = 0.5 if sharpe > 1.0 else 0
    r_dd = -0.3 * (peak - trough) / peak if (peak - trough)/peak > 0.1 else 0
    r_recovery = 0.2 if recovery_fast(steps) else -0.1
    r_invalid = -0.5 if not action_valid else 0
    
    total = (r_pnl + r_hold + r_sharpe + r_dd + r_recovery + r_invalid)
    return np.clip(total, -10, 10)
```

### 3.4 Configuração Proposta
```python
# Pesos dos componentes (ajustáveis)
REWARD_WEIGHTS = {
    'r_pnl': 1.0,           # Peso base (não mude)
    'r_hold_bonus': 1.0,    # Equalizado com PnL
    'r_sharpe': 0.5,        # Metade do peso da base
    'r_drawdown': 0.7,      # Penalidade moderada
    'r_recovery': 0.3,      # Incentivo leve
    'r_invalid': 1.0,       # Full penalidade
}
```


## 4. FINE-TUNE DE HIPERPARÂMETROS PPO

### 4.1 Espaço de Busca

| Parâmetro | Valores Atuais | Candidatos a Testar | Motivo |
|-----------|----------------|-------------------|---------|
| `learning_rate` | 3e-4 | [1e-4, 3e-4, 1e-3, 3e-3] | Convergência mais rápida |
| `batch_size` | 64 | [32, 64, 128, 256] | Estabilidade vs variância |
| `n_steps` | 2048 | [512, 1024, 2048, 4096] | Tamanho do rollout buffer |
| `n_epochs` | 10 | [5, 10, 20, 30] | Iterações de otimização |
| `ent_coef` | 0.01 | [0, 0.01, 0.05, 0.1] | Exploração vs exploitação |
| `clip_range` | 0.2 | [0.1, 0.2, 0.3] | Convergência PPO |
| `gae_lambda` | 0.95 | [0.9, 0.95, 0.98, 0.99] | Bias-variance tradeoff |

### 4.2 Estratégia de Busca
1. **Grid Search (Fase 1)**: Testar combinações principais de `learning_rate` × `batch_size`
2. **Random Search (Fase 2)**: Busca aleatória em espaço reduzido
3. **Bayesian Optimization (Fase 3)**: Otimização probabilística

### 4.3 Métrica de Avaliação
```python
score = (
    0.5 * sharpe_ratio +           # Risco ajustado (principal)
    0.3 * total_return +           # Retorno absoluto
    0.1 * win_rate +               # Taxa de vitória
    0.1 * convergence_speed        # Velocidade (episódios até convergência)
)
```


## 5. EXPERIMENTAÇÃO COM LSTM

### 5.1 Motivação
Adicionar memória de estado ao modelo PPO para capturar:
- Padrões sequenciais de preço
- Histórico de decisões recentes
- Dinâmica de momentum

### 5.2 Arquitetura Proposta
```python
Policy = MLPLSTMPolicy(
    features_dim=... (after flatten),
    net_arch=[256, 256],           # 2 camadas MLP
    lstm_hidden_size=128,          # Célula LSTM
    n_lstm_layers=1,               # 1 camada LSTM
    device='cpu'|'cuda'
)
```

### 5.3 Modificações Necessárias
- [ ] Criar nova classe `LSTMPolicy` em `agent/environment.py`
- [ ] Adaptar `signal_environment.py` para suportar `env.observation_space` > 1D
- [ ] Testar treinamento com `PPO(..., policy='LSTMPolicy')`

### 5.4 Benchmark
- Comparar Sharpe ratio do LSTM vs MLP após 500k timesteps
- Meta: LSTM >= MLP (capturar state dependence)


## 6. TIMELINE DE EXECUÇÃO

### Fase A1 (Dia 1-2): Validação de dados
- [x] Criar `validate_training_episodes.py`
- [ ] Executar validação quando episódios com outcomes estiverem disponíveis
- [ ] Gerar relatório de acurácia

### Fase B (Dia 3-7): Enriquecimento Features (Fase 1)
- [ ] Adicionar volatilidade (ATR, RSI) ao persist_training_episodes
- [ ] Adicionar multi-timeframe OHLCV
- [ ] Testar pipeline e coleta de dados

### Fase C (Dia 8-14): Ajuste Reward Function
- [ ] Implementar reward estendida com Sharpe + Drawdown + Recovery
- [ ] Treinar novo modelo PPO com reward estendida
- [ ] Comparar convergência vs baseline

### Fase D (Dia 15-21): Fine-tune de Hiperparâmetros
- [ ] Grid search: learning_rate × batch_size
- [ ] Avaliar Sharpe ratio para cada combo
- [ ] Selecionar melhores hiperparâmetros

### Fase E (Dia 22-28): LSTM Experimentation
- [ ] Implementar LSTMPolicy
- [ ] Treinar PPO com LSTM
- [ ] Comparar com MLP baseline


## 7. CHECKPOINTS E VALIDAÇÃO

### Checkpoint 1: Validação de Dados
- **Quando**: Após 24-48h de M2-016.2
- **Critério de sucesso**: >= 85% acurácia de labels, >= 70% cobertura
- **Ação se falhar**: Revisar lógica de labels em persist_training_episodes.py

### Checkpoint 2: Features implementadas
- **Quando**: Final do Dia 7
- **Critério de sucesso**: Pipeline roda com novos dados, sem erros
- **Ação se falhar**: Debug do código de enriquecimento

### Checkpoint 3: Reward Estendida
- **Quando**: Final do Dia 14
- **Critério de sucesso**: Sharpe ratio >= 1.2 em validação
- **Ação se falhar**: Ajustar pesos de reward

### Checkpoint 4: Fine-tune concluído
- **Quando**: Final do Dia 21
- **Critério de sucesso**: Sharpe ratio >= 1.5 (melhoria >= 25% vs baseline)
- **Ação se falhar**: Expandir grid search

### Checkpoint 5: LSTM pronto
- **Quando**: Final do Dia 28
- **Critério de sucesso**: LSTM Sharpe >= MLP Sharpe
- **Ação se falhar**: Revisão de arquitetura LSTM


## 8. DOCUMENTAÇÃO DE SAÍDA

Ao concluir M2-016.3, produzir:
1. `docs/RL_FEATURE_VALIDATION_REPORT.md` - Análise de labels e acurácia
2. `docs/RL_FEATURE_IMPROVEMENTS.md` - Detalhes de features adicionadas
3. `docs/RL_REWARD_ENGINEERING.md` - Especificação reward estendida
4. `docs/RL_PPO_HYPERPARAMETER_TUNING.md` - Resultados de grid search
5. `docs/RL_LSTM_EXPERIMENTATION.md` - Análise LSTM vs MLP


---

**Próxima ação**: Aguardar 24-48h de M2-016.2 para acumular episódios com outcomes reais.
