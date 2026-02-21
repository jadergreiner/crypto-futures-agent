# ML Operations Checklist — Phase 4 PPO Training
## 23-27 FEV 2026 — CTO Revalidation 27 FEV 16:00 UTC

---

## PRE-TRAINING CHECKLIST (23 FEV 10:00 UTC)

### Infrastructure Validation
- [ ] `logs/ppo_training/` directory exists
- [ ] `logs/ppo_training/tensorboard/` directory ready (will be created at training start)
- [ ] `checkpoints/ppo_training/` directory exists
- [ ] `models/ppo_phase4/` directory exists
- [ ] `reports/revalidation/` directory exists
- [ ] Disk space available: ≥50GB (for logs + checkpoints)
- [ ] RAM available: ≥16GB (for training + data buffers)

### Configuration Validation
- [ ] `config/ppo_config.py` loads without error
  ```bash
  python -c "from config.ppo_config import PPOConfig; print(PPOConfig())"
  ```
- [ ] All 11 hyperparameters present:
  - [ ] learning_rate = 3e-4
  - [ ] batch_size = 64
  - [ ] n_steps = 2048
  - [ ] n_epochs = 10
  - [ ] gamma = 0.99
  - [ ] gae_lambda = 0.95
  - [ ] ent_coef = 0.001
  - [ ] clip_range = 0.2
  - [ ] vf_coef = 0.5
  - [ ] max_grad_norm = 0.5
  - [ ] total_timesteps = 500,000

### Environment Validation
- [ ] `agent/environment.py` can be imported
- [ ] `agent/reward.py` has 4 components:
  - [ ] r_pnl
  - [ ] r_hold_bonus
  - [ ] r_invalid_action
  - [ ] r_out_of_market
- [ ] Reward scaling: `reward_clip = 10.0`
- [ ] VecNormalize (obs + reward) enabled

### Data Pipeline Validation
- [ ] Training data cached and accessible
- [ ] Test data (≥500 candles) ready for revalidation
- [ ] No gaps in OHLCV data (verified during Phase 3)
- [ ] Macro indicators + sentiment data available
- [ ] SMC (Smart Money Concepts) features present

### Model Baseline
- [ ] Random baseline metrics saved (for comparison during revalidation):
  - Sharpe Ratio: 0.06
  - Max DD: 17.24%
  - Win Rate: 48.51%
  - Profit Factor: 0.75
  - Consecutive Losses: 5
  - Calmar Ratio: 0.10

**STATUS:** _____.  (✅ READY / ⚠️ FIX / ❌ BLOCKED)

---

## DAILY CHECKS (23-26 FEV)

### Schedule
| Time (UTC) | Check | Status | Notes |
|-----------|-------|--------|-------|
| 10:00 | Morning standup (check_training_progress.py) | | |
| 14:00 | Mid-day convergence review | | |
| 18:00 | End-of-day metrics snapshot | | |
| 22:00 | Evening checkpoint validation | | |

### Daily Check-in Tool
```bash
# Run every 10:00 UTC
python scripts/check_training_progress.py

# Expected output:
# ✅ Overall Status: OK
# ✅ Log Files: All present
# 📈 Convergence: Reward growing, KL < 0.05
# 💾 Checkpoints: N saved, latest < 12h ago
# 🔔 Alerts: No critical issues
```

### Convergence Indicators to Monitor
- **Reward Trend**: Should be ≥0 (ideally +0.0001 per step)
- **KL Divergence**: Must stay < 0.05 (policy changing moderately)
- **Episode Rewards**: Should increase over time (first 100k steps volatile)
- **Value Function Loss**: Should stabilize around epoch 5-10
- **Policy Entropy**: Should decrease gradually (less exploration over time)

### Alert Thresholds
| Alert | Threshold | Action |
|-------|-----------|--------|
| Negative reward trend | < -0.001/step for 5k steps | Check reward function |
| KL divergence spike | > 0.1 | Reduce learning rate, check data |
| No improvement | < 0.0001 reward increase for 50k steps | Might be converged early |
| Checkpoint age | > 24h without save | Check if training hung |
| GPU memory error | OOM | Reduce batch_size or n_steps |
| Gradient explosion | nan or inf loss | Reduce learning_rate, increase clip_range |

### What to Check in logs/ppo_training/

#### 1. convergence_dashboard.csv
```bash
# Head of file (should have at least 100 rows by day 2)
head -20 logs/ppo_training/convergence_dashboard.csv

# Last rows (latest progress)
tail -20 logs/ppo_training/convergence_dashboard.csv

# Column structure:
# timestep,reward,kl_divergence,value_loss,policy_entropy
```

#### 2. training_metrics.csv
```bash
tail -10 logs/ppo_training/training_metrics.csv

# Columns: timestep, policy_loss, value_loss, entropy, approx_kl, clip_fraction
```

#### 3. daily_summary.log
```bash
tail -50 logs/ppo_training/daily_summary.log
```

#### 4. alerts.log
```bash
# Should be mostly empty (good sign)
cat logs/ppo_training/alerts.log
```

#### 5. TensorBoard (Real-time Dashboard)
```bash
tensorboard --logdir=logs/ppo_training/tensorboard

# Open in browser: http://localhost:6006
# Watch:
# - Reward (should increase)
# - ValueLoss (should decrease)
# - Policy/Entropy (should decrease gradually)
# - KL Divergence (should stay < 0.1)
```

---

## REVALIDATION CHECKLIST (27 FEV)

### Pre-Revalidation (27 FEV 10:00 UTC)
- [ ] Training completed (500k timesteps)
- [ ] Final model saved as `models/ppo_phase4/best_model.zip`
- [ ] Final model metrics (from training logs) extracted
- [ ] All 5 days of logs and checkpoints intact
- [ ] No errors in final logs
- [ ] Clean shutdown of training process

### Revalidation Execution (27 FEV 14:00 UTC)
```bash
# Run full revalidation
python scripts/revalidate_model.py

# Expected flow:
# [1/5] Load trained model...
# [2/5] Load backtest data (test set, 500+ candles)...
# [3/5] Run backtest with trained model...
# [4/5] Calculate 6 risk gates...
# [5/5] Generate report...
```

### Expected Outputs
- [ ] `reports/revalidation/revalidation_result.json` created
- [ ] `reports/revalidation/revalidation_result.md` created
- [ ] Decision: GO / PARTIAL-GO / NO-GO

### 6 Risk Gates Validation

| Gate | Minimum | Phase3 Random | Expected (trained) | Status |
|------|---------|---------------|-------------------|--------|
| Sharpe Ratio | ≥1.0 | 0.06 | 1.0+ | |
| Max Drawdown | ≤15% | 17.24% | <15% | |
| Win Rate | ≥45% | 48.51% | >50% | |
| Profit Factor | ≥1.5 | 0.75 | 1.5+ | |
| Consecutive Losses | ≤5 | 5 | ≤4 | |
| Calmar Ratio | ≥2.0 | 0.10 | 2.0+ | |
| **GATES PASSED** | **5-6/6** | **2/6** | **5-6/6?** | |

### Decision Logic
- **GO**: 5-6 gates passed → Immediate CTO approval + Live deployment 28 FEV
- **PARTIAL-GO**: 4 gates passed → Manual CTO review + Optional live OR retrain
- **NO-GO**: <4 gates passed → Retrain with tuned hyperparameters

---

## TROUBLESHOOTING GUIDE

### Issue: Negative Reward Trend

**Symptoms**: Reward decreasing over time, trend < -0.0001/step

**Possible Causes**:
1. Reward function not scaled correctly
2. Learning rate too high (policy changing randomly)
3. Data has shifted (distribution change)
4. Initial state bias (early rewards inflated)

**Actions**:
1. Check `agent/reward.py` — verify weights and clipping
2. Reduce learning_rate to 1e-4 (conservative)
3. Verify training data consistency in logs
4. Run `python -c "from agent.reward import RewardCalculator; print('OK')"`

---

### Issue: KL Divergence Spike (> 0.1)

**Symptoms**: KL divergence suddenly jumps, policy changing erratically

**Possible Causes**:
1. Large reward outlier (bad trade signal)
2. Learning rate still too high
3. Batch_size or n_steps mismatch

**Actions**:
1. Reduce learning_rate → 1e-4
2. Add reward clipping validation
3. Check for data errors in reward calculation
4. Consider reducing n_steps → 1024

---

### Issue: Training Hangs (No Checkpoint for 24h+)

**Symptoms**: Process appears running but no new checkpoints saved

**Possible Causes**:
1. Deadlock in environment or data loading
2. GPU memory exhausted (if using GPU)
3. Disk full (can't write checkpoints)

**Actions**:
1. Check disk space: `df -h`
2. Check RAM: `free -h` (Linux) or Task Manager (Windows)
3. Kill training: `pkill -f train_ppo` (graceful) or `kill -9 <pid>` (force)
4. Restart with fresh logs directory

---

### Issue: Low Win Rate (< 45%)

**Symptoms**: Model makes mostly losing trades, win_rate % is low

**Likely Cause**: Agent hasn't learned proper entry/exit logic

**Solutions** (if occurs during revalidation):
1. Train longer (add 200k more timesteps)
2. Increase r_hold_bonus weight (incentivize holding winners)
3. Review reward function—might need adjustment
4. Check if SMC features are informative

---

### Issue: High Max Drawdown (> 15%)

**Symptoms**: Equity curve has large drops, max_drawdown_pct > 15%

**Likely Cause**: Agent taking oversized positions or bad entries

**Solutions** (if occurs during revalidation):
1. Reduce allowed max position size (risk manager)
2. Tighten stop-loss parameters
3. Add r_invalid_action penalty (−0.5 for bad actions)
4. Increase r_out_of_market bonus (stay safe when unsure)

---

## DAILY STANDUP TEMPLATE (Morning 10:00 UTC)

```
DATE: 23-27 FEV 2026
TIME: 10:00 UTC
RESPONSIBLE: ML Engineer

YESTERDAYS PROGRESS:
- Training status: ___k / 500k timesteps (___%)
- Reward trend: _____ (✅ positive / ⚠️ flat / ❌ negative)
- KL divergence: _____ (✅ < 0.05 / ⚠️ 0.05-0.1 / ❌ > 0.1)
- Last checkpoint: _____ (age: ___ hours)
- Issues: None / ⚠️ (describe)

TODAYS PLAN:
- Continue training (target: ___k more steps)
- Monitor convergence every 4 hours
- Any tuning needed? No / Yes (describe)

BLOCKERS:
- None / (list)

CONFIDENCE LEVEL:
- On track for 5-6/6 gates: ✅ High / ⚠️ Medium / ❌ Low
```

---

## REVALIDATION DAY TIMELINE (27 FEV)

| Time (UTC) | Task | Owner | Notes |
|-----------|------|-------|-------|
| 14:00 | Load trained model | ML | `models/ppo_phase4/best_model.zip` |
| 14:15 | Load test data (500+ candles) | Data | Separate from training data |
| 14:30 | Run backtest (all 62 symbols) | ML | ~30-60 min depending on hardware |
| 15:45 | Calculate 6 gates | ML | Use BacktestMetrics from F-12 |
| 16:00 | Generate decision report | ML | `reports/revalidation/revalidation_result.md` |
| 16:15 | Review with SWE lead | SWE | Check metrics, decision logic |
| 16:30 | Escalate to CTO | CTO | GO / PARTIAL-GO / NO-GO decision |

---

## SIGN-OFF

| Phase | Responsible | Status | Date | Notes |
|-------|------------|--------|------|-------|
| Pre-Training Setup | ML | ☐ | | |
| Daily Monitoring | ML | ☐ | | |
| Revalidation Execution | ML | ☐ | | |
| CTO Decision | CTO | ☐ | | |
| Live Deployment (if GO) | SWE | ☐ | | |

---

## References

- **PPO Config**: `config/ppo_config.py`
- **Revalidation Script**: `scripts/revalidate_model.py`
- **Training Guide**: `GUIA_PPO_TRAINING_PHASE4.md`
- **Risk Gates**: `backtest/backtest_metrics.py`
- **Training Dashboard**: `scripts/ppo_training_dashboard.py`
- **Progress Check**: `scripts/check_training_progress.py`

---

**Version**: 1.0
**Created**: 21 FEV 2026
**Last Updated**: 21 FEV 2026
**Status**: 🔴 NOT YET STARTED (training starts 23 FEV)
