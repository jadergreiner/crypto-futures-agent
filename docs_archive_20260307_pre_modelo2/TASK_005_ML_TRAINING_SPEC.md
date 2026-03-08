# 🤖 TASK-005 ML Training Pipeline — PPO v0 Specification

**Título:** ML Training Pipeline (PPO) — S2-3 Sprint 2-3  
**Owner:** The Brain (#3) — ML/Arch  
**Timeline:** 22-25 FEV 2026  
**Deadline:** ⏰ 25 FEV 10:00 UTC (HARD CONSTRAINT)  
**Duration:** 96 hours wall-time  
**Status:** 🚀 READY TO KICKOFF (Gate 3 ✅ unblocked)  

---

## 🎯 Objetivo

Treinar modelo PPO (Proximal Policy Optimization) em histórico de trades de Sprint 1
para otimizar parametros de entrada da estratégia SMC (Order Blocks + BreakOfStructure).

**Saída esperada:** Policy treinada salva em `models/ppo_v0.pkl` com Sharpe ≥ 0.80

---

## 📋 Pré-requisitos ✅

- ✅ **Backtest Engine (S2-3 Gate 2-3):** backtest/metrics.py + tests COMPLETE
- ✅ **Sprint 1 Data:** 70 trades históricos em data/trades_history.json
- ✅ **Environment:** Python 3.9+, stable-baselines3, gymnasium (installed)
- ✅ **Risk Gate:** Risk module loaded (stop loss -3%, liquidation check)

---

## 🏃 Phase 1: Environment Setup (23 FEV 00:00-06:00 UTC)

**Owner:** The Blueprint (#7)  
**Tasks:**

### T5.1.1 — Criar CustomTrainingEnv

```python
# File: agent/rl/training_env.py

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from backtest.metrics import MetricsCalculator

class CryptoTradingEnv(gym.Env):
    """
    Gym environment para treinamento PPO.
    
    Observação: estado do mercado + posição aberta
    Ação: HOLD, LONG, SHORT (3 ações)
    Recompensa: PnL realizado + bônus Sharpe
    """
    
    def __init__(self, trade_data, initial_capital=10000):
        super().__init__()
        self.trade_data = trade_data  # list of OHLCV
        self.initial_capital = initial_capital
        self.current_step = 0
        self.equity = initial_capital
        self.position = 0  # 0=close, 1=long, -1=short
        self.entry_price = 0
        
        # Observation space: [close, volume, rsi, position, pnl]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32
        )
        
        # Action space: HOLD=0, LONG=1, SHORT=2
        self.action_space = spaces.Discrete(3)
        
        self.trades_history = []
        
    def reset(self):
        """Reset environment to start of episode."""
        self.current_step = 0
        self.equity = self.initial_capital
        self.position = 0
        self.entry_price = 0
        self.trades_history = []
        
        obs = self._get_observation()
        return obs, {}
    
    def step(self, action):
        """Execute one trading step."""
        # TODO: Implementar lógica de execução, PnL cálculo, risk gate check
        # action: 0=HOLD, 1=LONG, 2=SHORT
        
        # Calcular reward (PnL realizado + bônus)
        reward = 0  # TODO: compute from position change
        
        # Check para risk gate (max drawdown, etc)
        risk_gate_breach = False  # TODO: check
        
        obs = self._get_observation()
        terminated = risk_gate_breach or self.current_step > len(self.trade_data)
        
        self.current_step += 1
        
        return obs, reward, terminated, False, {}
    
    def _get_observation(self):
        """Retorna observação do estado do mercado + posição."""
        if self.current_step < len(self.trade_data):
            candle = self.trade_data[self.current_step]
            close = candle['close']
            volume = candle['volume']
            # TODO: Calcular RSI ou outro indicador
            rsi = 50.0  # placeholder
            
            pnl = 0.0
            if self.position != 0:
                pnl = (close - self.entry_price) * self.position
            
            obs = np.array(
                [close, volume, rsi, float(self.position), pnl],
                dtype=np.float32
            )
            return obs
        else:
            return np.zeros(5, dtype=np.float32)
```

**Checklist:**
- [ ] File created: agent/rl/training_env.py
- [ ] Environment registered with gymnasium
- [ ] Reset/step methods tested with dummy data
- [ ] Risk gate callbacks integrated

**Estimate:** 2h

---

### T5.1.2 — Carregar Trade History

```python
# File: agent/rl/data_loader.py

import json
from pathlib import Path

def load_trade_history(filepath="data/trades_history.json"):
    """Carrega histórico de trades de Sprint 1 para ambiente."""
    with open(filepath, 'r') as f:
        trades = json.load(f)
    
    # Validar: cada trade tem entry, exit, qty
    for trade in trades:
        assert 'entry' in trade and 'exit' in trade and 'qty' in trade
    
    return trades

def convert_trades_to_ohlcv(trades):
    """Converte trades para sequência OHLCV para o ambiente."""
    # TODO: Flatten trade history → OHLCV timeline
    ohlcv_list = []
    for trade in trades:
        # Simular: candle com close=entry, next candle close=exit
        ohlcv_list.append({
            'open': trade['entry'],
            'high': max(trade['entry'], trade['exit']),
            'low': min(trade['entry'], trade['exit']),
            'close': trade['exit'],
            'volume': trade.get('qty', 1) * 10,  # placeholder volume
        })
    return ohlcv_list
```

**Checklist:**
- [ ] loads trades_history.json
- [ ] Validates schema (entry, exit, qty)
- [ ] Converts to OHLCV for environment

**Estimate:** 1h

---

## 🔄 Phase 2: PPO Training Loop (23 FEV 06:00-22:00 UTC)

**Owner:** The Brain (#3)  
**Total Time:** 16h wall-time (8h of 96h)

### T5.2.1 — Initialize PPO Agent

```python
# File: agent/rl/ppo_trainer.py

from stable_baselines3 import PPO
from agent.rl.training_env import CryptoTradingEnv

def create_ppo_agent(env, learning_rate=1e-4):
    """Cria agent PPO com params otimizados para trading."""
    
    policy_kwargs = dict(
        net_arch=[256, 256],  # 2 hidden layers, 256 neurons each
        activation_fn=torch.nn.ReLU,
    )
    
    ppo_model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=256,  # batch size
        batch_size=64,
        n_epochs=4,
        gamma=0.99,  # discount factor
        gae_lambda=0.95,
        policy_kwargs=policy_kwargs,
        verbose=1,
        tensorboard_log="logs/ppo_tensorboard/"
    )
    
    return ppo_model
```

**Checklist:**
- [ ] PPO model initialized
- [ ] Network architecture validated (256x256)
- [ ] Learning rate set to 1e-4
- [ ] TensorBoard logs configured

**Estimate:** 1h

---

### T5.2.2 — Training Loop with Daily Gates

```python
# File: agent/rl/training_loop.py

import json
from datetime import datetime
from stable_baselines3 import PPO
from backtest.metrics import MetricsCalculator

def train_with_daily_gates(
    env,
    ppo_model,
    total_timesteps=960000,  # 96h ÷ 360s/step ≈ 960k steps
    checkpoint_interval=120000,  # save every 12h
    target_sharpe=1.0,
    early_stop_sharpe=1.0,
):
    """
    Treina PPO com gates diários de convergência.
    
    Daily Gates:
    - Day 1 (23 FEV): Sharpe ≥ 0.40 (ramp up)
    - Day 2 (24 FEV): Sharpe ≥ 0.70 (converging)
    - Day 3 (25 FEV): Sharpe ≥ 1.0 (target) or early stop
    """
    
    checkpoint_num = 0
    start_time = datetime.now()
    
    for timestep in range(0, total_timesteps, checkpoint_interval):
        # Train para próximo checkpoint
        ppo_model.learn(
            total_timesteps=checkpoint_interval,
            log_interval=100,
        )
        
        checkpoint_num += 1
        
        # Save checkpoint
        checkpoint_path = f"models/ppo_checkpoint_{checkpoint_num}.pkl"
        ppo_model.save(checkpoint_path)
        
        # Daily gate validation
        metrics = evaluate_policy_sharpe(ppo_model, env)
        sharpe = metrics['sharpe_ratio']
        
        elapsed_hours = (datetime.now() - start_time).total_seconds() / 3600
        
        print(f"\n[Day {elapsed_hours/24:.1f}] Checkpoint {checkpoint_num}")
        print(f"  Sharpe Ratio: {sharpe:.3f}")
        print(f"  Win Rate: {metrics['win_rate']:.1%}")
        print(f"  Max DD: {metrics['max_drawdown']:.1%}")
        
        # EARLY STOP if Sharpe ≥ 1.0
        if sharpe >= early_stop_sharpe:
            print(f"\n✅ EARLY STOP — Sharpe ≥ {early_stop_sharpe} reached!")
            ppo_model.save(f"models/ppo_v0_final.pkl")
            return ppo_model
        
        # Gate check (3 daily gates)
        day_num = int(elapsed_hours / 24) + 1
        if day_num == 1 and sharpe < 0.40:
            print("⚠️ Day 1 Gate FAIL — Sharpe < 0.40. Continuing...")
        elif day_num == 2 and sharpe < 0.70:
            print("⚠️ Day 2 Gate FAIL — Sharpe < 0.70. Continuing...")
        elif day_num == 3 and sharpe < 1.0:
            print("⚠️ Day 3 Gate FAIL — Sharpe < 1.0. Deadline approaching.")
    
    # Final save
    ppo_model.save("models/ppo_v0_final.pkl")
    return ppo_model

def evaluate_policy_sharpe(ppo_model, env, n_episodes=10):
    """Avalia policy em episódios e calcula Sharpe."""
    all_returns = []
    
    for _ in range(n_episodes):
        obs, _ = env.reset()
        episode_trades = []
        terminated = False
        
        while not terminated:
            action, _ = ppo_model.predict(obs, deterministic=True)
            obs, reward, terminated, _, _ = env.step(action)
            episode_trades.append(reward)
        
        all_returns.append(sum(episode_trades))
    
    # Calcular Sharpe dos returns
    returns_array = np.array(all_returns)
    sharpe = np.mean(returns_array) / (np.std(returns_array) + 1e-8)
    
    return {
        'sharpe_ratio': sharpe,
        'win_rate': sum(1 for r in all_returns if r > 0) / len(all_returns),
        'max_drawdown': 0.05,  # placeholder
    }
```

**Checklist:**
- [ ] Training loop implemented
- [ ] Daily gate validation (3 gates)
- [ ] Early stop @ Sharpe ≥ 1.0
- [ ] Checkpoints saved every 12h
- [ ] TensorBoard accessible at logs/

**Estimate:** 3h

---

## 🎯 Phase 3: Final Validation (25 FEV 08:00-10:00 UTC)

**Owner:** Audit (#8)  
**Last 2 hours before deadline

### T5.3.1 — Backtest Validation

```python
# File: agent/rl/final_validation.py

from backtest.metrics import MetricsCalculator

def validate_trained_policy(policy_path, trade_data):
    """
    Validação final: roda policy treinada no backtest engine
    e verifica se todos métrica gates passam.
    """
    
    ppo_model = PPO.load(policy_path)
    env = CryptoTradingEnv(trade_data)
    
    obs, _ = env.reset()
    trades = []
    
    for _ in range(len(trade_data)):
        action, _ = ppo_model.predict(obs, deterministic=True)
        obs, reward, terminated, _, _ = env.step(action)
        
        if terminated:
            break
    
    # Calcular métricas FINAIS
    calc = MetricsCalculator(
        env.trades_history,
        initial_capital=10000
    )
    
    metrics = {
        'sharpe': calc.calculate_sharpe_ratio(),
        'max_dd': calc.calculate_max_drawdown(),
        'win_rate': calc.calculate_win_rate(),
        'profit_factor': calc.calculate_profit_factor(),
        'consecutive_losses': calc.calculate_consecutive_losses(),
    }
    
    is_valid = calc.validate_against_thresholds(metrics)
    
    print("\n" + "="*50)
    print("TASK-005 FINAL VALIDATION")
    print("="*50)
    print(f"Sharpe Ratio: {metrics['sharpe']:.2f} (gate: ≥0.80)")
    print(f"Max Drawdown: {metrics['max_dd']:.1%} (gate: ≤12%)")
    print(f"Win Rate: {metrics['win_rate']:.1%} (gate: ≥45%)")
    print(f"Profit Factor: {metrics['profit_factor']:.2f} (gate: ≥1.5)")
    print(f"Max Losses: {metrics['consecutive_losses']} (gate: ≤5)")
    print("="*50)
    print(f"Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    print("="*50)
    
    return is_valid, metrics
```

**Checklist:**
- [ ] Backtest validation script tested
- [ ] All 5 metrics gates verified
- [ ] TensorBoard logs reviewed
- [ ] Model saved to models/ppo_v0_final.pkl

**Estimate:** 1h

---

## 📊 Timeline (Wall-clock)

```
23 FEV 00:00 UTC — TASK-005 KICKOFF
├─ 00:00-06:00 (6h)  — Phase 1 (Env setup)
├─ 06:00-22:00 (16h) — Phase 2 (96h training ÷ 6 ~ 16h actual compute)
└─ 22:00-24:00 (2h)  — Integration check

24 FEV 00:00-10:00 (10h) — Continued training

25 FEV 08:00-10:00 (2h) — Phase 3 (Final validation)

⏰ 25 FEV 10:00 UTC — DEADLINE (HARD)
└─ Models saved + Metrics validated ✅
```

---

## 🎁 Deliverables

| Item | Path | Owner | Status |
|------|------|-------|--------|
| Custom Env | agent/rl/training_env.py | Blueprint #7 | 📋 |
| Data Loader | agent/rl/data_loader.py | Blueprint #7 | 📋 |
| PPO Trainer | agent/rl/ppo_trainer.py | The Brain #3 | 📋 |
| Daily Gates | agent/rl/training_loop.py | The Brain #3 | 📋 |
| Final Model | models/ppo_v0_final.pkl | The Brain #3 | 📋 |
| Validation | agent/rl/final_validation.py | Audit #8 | 📋 |
| TensorBoard Logs | logs/ppo_tensorboard/ | Blueprint #7 | 📋 |

---

## 🚀 Dependencies & Blockers

**Unblocked by:**
- ✅ Gate 3 (backtest/metrics) COMPLETE
- ✅ Sprint 1 trade history available
- ✅ stable-baselines3, gymnasium installed

**Blocks:**
- 🔴 TASK-006 (Deployment) — waits for TASK-005 sign-off

---

## 🎓 Success Criteria

**All 6 must pass:**
1. ✅ Sharpe Ratio ≥ 0.80 (gate) / ≥ 1.20 (target)
2. ✅ Max Drawdown ≤ 12% (gate) / ≤ 10% (target)
3. ✅ Win Rate ≥ 45% (gate) / ≥ 55% (target)
4. ✅ Profit Factor ≥ 1.5 (gate) / ≥ 2.0 (target)
5. ✅ Consecutive Losses ≤ 5 (gate) / ≤ 3 (target)
6. ✅ Model saved: models/ppo_v0_final.pkl

**If all pass:** 🟢 **GO-LIVE APPROVED** → Production deployment ready

---

**Created:** 23 FEV 01:30 UTC  
**Owner:** The Brain (#3) + The Blueprint (#7)  
**Status:** 🚀 READY TO KICKOFF  
**Deadline:** ⏰ 25 FEV 10:00 UTC (HARD)
