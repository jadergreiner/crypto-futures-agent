# ML Team Handoff - Phase 4 PPO Training

**Project**: Crypto Futures Agent - PPO Training Phase 4
**Version**: 1.0
**Deadline**: 2026-02-23 14:00 UTC
**Generated**: 2026-02-21T12:52:01.792435

## 📊 Data Format Specification

### Input Observation Space
- **Type**: Box(104,)
- **Range**: Normalized features [-∞, +∞] (mostly [-1, 1])
- **Features**: 104
  - Price/OHLC (8): timestamp, open, high, low, close, volume, vwap, returns
  - Technical Indicators (40): EMA, MACD, RSI, Bollinger, ATR, etc  
  - Smart Money Concepts (16): Order Blocks, FVGs, BOS, CHoCH, Liquidity Zones
  - Sentiment (10): Social media, fear/greed, funding rates
  - Macro Data (20): DXY, bond yields, BTC dominance, crypto correlation
  - Risk Metrics (10): Drawdown, volatility, Sharpe, max dd, stress level

### Action Space
- **Type**: Discrete(5)
- **Actions**:
  - 0: HOLD (no change)
  - 1: OPEN_LONG (buy)
  - 2: OPEN_SHORT (sell)
  - 3: CLOSE_POSITION (exit trade)
  - 4: REDUCE_50_PERCENT (reduce position size)

### Training Data
- **Location**: `backtest/cache/`
- **Format**: Apache Parquet (.parquet)
- **Symbols**: 
  - OGNUSDT: 1000 H4 candles (800 train / 200 validation)
  - 1000PEPEUSDT: 1000 H4 candles (800 train / 200 validation)
- **Metadata**: `data/training_datasets/dataset_info.json`

## 🔧 Environment Specification

```python
from backtest.backtest_environment import BacktestEnvironment

# Load data
data = {
    'h4': pd.read_parquet('backtest/cache/SYMBOL_4h.parquet'),
    'h1': pd.DataFrame(),  # Not required for Phase 4
    'd1': pd.DataFrame(),  # Not required for Phase 4
    'symbol': 'OGNUSDT',
    'sentiment': pd.DataFrame(),
    'macro': pd.DataFrame(),
    'smc': pd.DataFrame()
}

# Create environment
env = BacktestEnvironment(
    data=data,
    initial_capital=10000,
    episode_length=200,
    deterministic=True,
    seed=42
)

# Use with stable-baselines3
model = PPO("MlpPolicy", env=env, ...)
model.learn(total_timesteps=1_000_000)
```

## 📈 Monitoring & Logging

### CSV Metrics (per episode)
File: `logs/ppo_training/training_metrics.csv`
Columns: episode, timesteps, reward, length, win_rate, profit_factor, sharpe, max_dd, lr

### TensorBoard
Path: `logs/ppo_training/tensorboard/`
Scalars: policy_loss, value_loss, entropy, episode_reward, episode_length

### Checkpoints
Path: `checkpoints/ppo_training/`
Frequency: Every 10,000 timesteps
Keep last: 5 models

## ⚠️ Alert Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Episode reward | < -5000 | Check environment |
| Win rate | < 40% | Review reward function |
| Max drawdown | > 25% | Check risk parameters |
| Policy loss | > 1000 | Reduce learning rate |
| Value loss | > 10000 | Maybe increase gamma |

## 🎯 PPO Hyperparameters

- **Learning Rate**: 3e-4 (range: 1e-5 to 1e-3)
- **N Steps**: 2048
- **Batch Size**: 64
- **N Epochs**: 10
- **Gamma**: 0.99
- **GAE Lambda**: 0.95
- **Clip Range**: 0.2
- **Entropy Coef**: 0.01
- **Value Func Coef**: 0.5
- **Total Timesteps**: 1,000,000

**Note**: If divergence observed, try:
1. Reduce learning rate to 1e-4
2. Increase entropy coef to 0.02
3. Add gradient clipping with max_norm=0.5

## ✅ Success Criteria

### Minimum Acceptable
- Win Rate ≥ 45%
- Profit Factor ≥ 1.0
- Max Consecutive Losses ≤ 5
- Training stability (no loss explosion)

### Target Performance
- Sharpe Ratio ≥ 1.0
- Max Drawdown ≤ 15%
- Profit Factor ≥ 1.5
- Calmar Ratio ≥ 2.0

## 📋 Known Risks & Mitigations

| Risk | Mitigation | Monitor |
|------|-----------|---------|
| Model divergence | Early stopping | policy_loss per 100 steps |
| Overfitting | Increase regularization | train vs val metrics |
| Exploration/Exploitation | Entropy annealing | entropy + rewards |
| Stale data | Validate timestamps | log data range |

## 🚀 Getting Started

### 1. Load training script
```bash
python scripts/train_ppo_skeleton.py
```

### 2. Custom config (optional)
Edit `config/ml_training_config.json` before training

### 3. Monitor training
```bash
tensorboard --logdir=logs/ppo_training/tensorboard
```

### 4. Export trained model
Models saved automatically to `checkpoints/ppo_training/`

## 📞 Support

- **Data/Cache questions**: SWE - Backend
- **Environment API questions**: SWE - Backtest
- **Infrastructure issues**: SWE - DevOps
- **Deadline changes**: CTO

---

**Status**: Ready for ML Handoff ✅
**Last Updated**: 2026-02-21T12:52:01.792435
