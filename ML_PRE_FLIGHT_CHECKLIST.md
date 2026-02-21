# ML Pre-Flight Checklist — 23 FEV 10:00 UTC

Checklist operacional para validação pré-treinamento PPO.
Deadline: 23 FEV 10:00 UTC (1h antes do treinamento)

---

## Pre-Training Validation (10:00 UTC, 1h antes do treino)

- [ ] **Config PPO carregado e validado**
  - Comando: `python -c "from config.ppo_config import get_ppo_config; c=get_ppo_config('phase4'); print(f'LR={c.learning_rate}, BS={c.batch_size}, Steps={c.total_timesteps:,}')"`
  - Esperado: LR=0.0003, BS=64, Steps=500,000
  - Hiperparâmetros: 11/11 presentes
    - [ ] learning_rate
    - [ ] batch_size
    - [ ] n_steps
    - [ ] n_epochs
    - [ ] gamma
    - [ ] gae_lambda
    - [ ] ent_coef
    - [ ] clip_range
    - [ ] vf_coef
    - [ ] max_grad_norm
    - [ ] total_timesteps

- [ ] **Reward function testada**
  - Comando: `python -c "from agent.reward import RewardCalculator; r=RewardCalculator(); print(r.calculate())"`
  - Esperado: 4 componentes (r_pnl, r_hold_bonus, r_invalid_action, r_out_of_market)
  - Sem erros de import

- [ ] **Dados validados (sem gaps)**
  - Verifiquer cache parquet: `backtest/cache/OGNUSDT_4h.parquet`
  - Verifiquer cache parquet: `backtest/cache/1000PEPEUSDT_4h.parquet`
  - Comando: `python scripts/check_data_availability.py`
  - Esperado: Sem gaps > 4h

- [ ] **Checkpoints dir limpo**
  - Diretório: `models/ppo_phase4/`
  - Comando: `rm -rf models/ppo_phase4/*` (se existir garbage)
  - Esperado: Dir vazio ou contém apenas estrutura padrão

- [ ] **TensorBoard dir pronto**
  - Diretório: `logs/ppo_training/tensorboard/`
  - Comando: `mkdir -p logs/ppo_training/tensorboard`
  - Esperado: Dir criado e vazio

- [ ] **BacktestEnvironment testado (1 step)**
  - Comando: `python -c "from backtest.backtest_environment import BacktestEnvironment; print('✅ ImportOK')"`
  - Esperado: Sem erro de import

- [ ] **Risk gates confirmados (6/6)**
  - Sharpe Ratio: min = 1.0
  - Max DD: max = 15.0%
  - Win Rate: min = 45.0%
  - Profit Factor: min = 1.5
  - Consecutive Losses: max = 5
  - Calmar Ratio: min = 2.0

- [ ] **Revalidation script ready**
  - Comando: `python -c "from scripts.revalidate_model import RevalidationValidator; print('✅ OK')"`
  - Esperado: Import OK, class instantiable

---

## 23 FEV 13:00 UTC — Final Validation (1 Hour Before Launch)

**Final ML Operational Validation @ 22:30 UTC on 21 FEV — RESULTADO: ✅ 100% READY**

Resultado completo em: `FINAL_ML_OPERATIONAL_VALIDATION.txt`

- [x] **PPO Config carregado e validado** ✅
  - Status: 11/11 hiperparâmetros presentes
  - LR=0.0003, BS=64, TS=500,000
  - Result: PASS

- [x] **Reward function testada** ✅
  - Status: 4/4 componentes (r_pnl, r_hold_bonus, r_invalid_action, r_out_of_market)
  - Result: PASS

- [x] **BacktestEnvironment operacional** ✅
  - Deterministic seed=42, Box(104,), Discrete(5)
  - Result: PASS

- [x] **ParquetCache pronto** ✅
  - Cache pipeline 3-tier: SQLite → Parquet → NumPy
  - Result: PASS

- [x] **Daily training check** ✅
  - Syntax check: OK
  - Result: READY

- [x] **Dashboard script** ✅
  - Syntax check: OK
  - Métricas: Reward, losses, entropy, KL, sharpe
  - Result: READY

- [x] **Logging structure** ✅
  - `logs/ppo_training/` criado
  - `logs/ppo_training/tensorboard/` pronto
  - Result: OK

- [x] **Revalidation framework** ✅
  - RevalidationValidator class instantiable
  - Result: READY

- [x] **All 6/6 risk gates implemented** ✅
  - 1. Sharpe ≥ 1.0
  - 2. Max DD ≤ 15%
  - 3. Win Rate ≥ 45%
  - 4. Profit Factor ≥ 1.5
  - 5. Consecutive Losses ≤ 5
  - 6. Calmar ≥ 2.0
  - Result: PASS

- [x] **Decision logic verified** ✅
  - gates ≥ 5 → GO
  - gates = 4 → PARTIAL-GO
  - gates < 4 → NO-GO
  - Result: CORRECT

---

## Training Launch (14:00 UTC)

- [ ] **Start training command ready**
  ```bash
  python scripts/start_ppo_training.py --symbol OGNUSDT --mode paper --tag "F12-phase4-final"
  ```

- [ ] **Monitor setup**
  ```bash
  tensorboard --logdir=logs/ppo_training/tensorboard --port=6006
  ```
  - Endpoint: http://localhost:6006

- [ ] **Log file location confirmed**
  - Primary: `logs/ppo_training/training.log`
  - Daily summaries: `logs/ppo_training/daily_summaries/`

---

## First Hour Checks (14:00-15:00 UTC)

**Check @15:00 UTC (after 1h of training):**

- [ ] **Reward > 0?**
  - Indica que política está aprendendo algo (não random)
  - Verificar tensorboard: `Reward` trend
  - Esperado: Reward médio > -10 (ou trending up)

- [ ] **Loss diminuindo?**
  - Convergência inicial da policy
  - Verificar tensorboard: `Policy Loss`, `Value Loss`
  - Esperado: Ambos tendendo down

- [ ] **No crashes?**
  - Verificar log file: `tail -50 logs/ppo_training/training.log`
  - Esperado: Sem exceções, sem OOM, sem inf/nan

- [ ] **Training speed estimated**
  - Speedometer: steps/second
  - Expected: 1000-2000 steps/sec (com GPU)
  - Cálculo: 500k steps / (1000-2000 steps/sec) / 3600 sec = 70-140 horas

---

## Critical Success Factors

**Ref: FINAL_ML_OPERATIONAL_VALIDATION.txt**

### ✅ What TO DO

1. **Monitor tensorboard EVERY HOUR** — http://localhost:6006
2. **Run daily_training_check.py** — Generates daily summaries
3. **Check logs** — `grep -i "nan\|inf" logs/ppo_training/training.log`
4. **Backup checkpoints** — Every 100k steps

### 🚫 What NOT TO DO

1. ❌ Stop training with SIGKILL (use SIGTERM)
2. ❌ Modify reward function during training
3. ❌ Increase LR > 0.001
4. ❌ Delete logs during training
5. ❌ Use new data during training

---

## Final Validation Status

**Date:** 2026-02-21 22:30 UTC
**Result:** 🟢 **ALL 10/10 ML COMPONENTS VALIDATED**

**Status:** ✅ READY FOR 23 FEV 14:00 UTC TRAINING LAUNCH
**Confidence:** 95%
**Blockers:** 0 (ZERO)
**Warnings:** 0 (ZERO)

See [FINAL_ML_OPERATIONAL_VALIDATION.txt](FINAL_ML_OPERATIONAL_VALIDATION.txt) for complete details.


