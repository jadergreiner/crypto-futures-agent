# M2-016.3 Phase E - LSTM Policy Architecture Exploration

**Status**: EM_DESENVOLVIMENTO (2026-03-14)
**Objetivo**: Implementar política com memoria temporal (LSTM) vs baseline (MLP)

## Contexto

Fases A-D.4 completadas:
- Features enriquecidas: volatility + multi-timeframe + funding rates + OI
- Reward function estendida e validada
- PPO baseline: Sharpe=1.176, hyperparams otimizados
- Correlacoes analisadas (FR sentiment fraco positivo vs label)

**Problema**: Modelos atuais (MLP) sao stateless. Nao capturam LSTM patterns:
- Momentum de funding rate trends
- Inercia de OI accumulation
- Volatility clustering
- Regime changes de mercado

## Fases (Estimate: 14 dias)

### E.1: LSTM Environment Wrapper (2-3 dias)
- [ ] Create `agent/lstm_environment.py` wrapping signal_environment.py
- [ ] Add state buffer (rolling window last N timesteps)
- [ ] Add feature sequence output: shape (batch, seq_len, n_features)
- [ ] Test with dummy episodes

### E.2: LSTM Policy Network (3-4 dias)
- [ ] Implement `agent/lstm_policy.py` using stable-baselines3 SubclassedPolicy
- [ ] LSTM layer (64 units) + hidden layer (128) + output
- [ ] Compare vs baseline MLP
- [ ] Test forward pass shape compatibility

### E.3: Training with LSTM (4-5 dias)
- [ ] Create `scripts/model2/train_ppo_lstm.py`
- [ ] Baseline run: PPO MLP (2 signals, 100 episodes)
- [ ] LSTM run: PPO LSTM (2 signals, 100 episodes)
- [ ] Logging: loss, reward, Sharpe, win_rate

### E.4: Analysis & Comparison (2-3 dias)
- [ ] Generate `results/model2/lstm_vs_mlp_comparison.json`
- [ ] Plots: training curves, final metrics
- [ ] Statistical test: Sharpe ratio difference
- [ ] Recommendation: use LSTM if Sharpe > +5%

## Architecture

```
LSTM Policy:
  Input (batch, seq=10, features=64)
    |
  LSTM layer (64 units, 1 layer)
    |
  Dense (128 units, ReLU)
    |
  Output (action_logits, value)

vs

MLP Policy (baseline):
  Input (64 features)
    |
  Dense (128, ReLU) -> Dense (128, ReLU) -> Output
```

## Next Immediate Tasks

1. Analyze feature dimensions required
2. Design state buffer (sequence length, overlap strategy)
3. Prototype LSTM layer in isolation
4. Plan training dataset requirements

## Success Criteria

- LSTM trains without error
- Sharpe ratio >= baseline (ideally +5% better)
- Win rate improvement or stability
- No excessive overfitting (val loss tracking)
