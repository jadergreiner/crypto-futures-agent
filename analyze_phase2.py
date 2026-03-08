"""
Analytics: Phase 2 v2.3 Training Deep Dive
"""
import json
import numpy as np
from pathlib import Path

print("=" * 70)
print("PHASE 2 v2.3 — DATA ANALYSIS")
print("=" * 70)

# 1. Load training log
with open('logs/ppo_task005/training_log.json') as f:
    training_log = json.load(f)

# 2. Analyze checkpoints
print("\n[1] CHECKPOINT ANALYSIS")
print("-" * 70)
for ckpt in training_log['checkpoints']:
    m = ckpt['metrics']
    print(f"\nCheckpoint {ckpt['num']}:")
    print(f"  Timesteps:  {ckpt['timesteps']:,}")
    print(f"  Elapsed:    {ckpt['elapsed_hours']:.2f}h")
    print(f"  Sharpe:     {m['sharpe_ratio']:.4f} (mean={m['mean_return']:.4f}, std={m['std_return']:.6f})")
    print(f"  Win Rate:   {m['win_rate']*100:.1f}%")
    print(f"  Max DD:     {m['max_drawdown']*100:.1f}%")
    print(f"  Episodes:   {m['num_episodes']}")

# 3. Analyze daily gates
print("\n[2] DAILY GATES ANALYSIS")
print("-" * 70)
for day, gate_info in training_log['daily_gates'].items():
    status = "✅ PASS" if gate_info['passed'] else "❌ FAIL"
    print(f"Day {day}: {status}")
    print(f"  Threshold: {gate_info['gate_threshold']:.4f}")
    print(f"  Actual:    {gate_info['sharpe_actual']:.4f}")

# 4. Load and analyze trades data
print("\n[3] TRADES DATA ANALYSIS")
print("-" * 70)
try:
    with open('data/trades_history.json') as f:
        trades_data = json.load(f)

    # Handle both list and dict formats
    if isinstance(trades_data, list):
        trades_list = trades_data
    else:
        trades_list = trades_data.get('trades', [])

    pnls = [t['pnl'] for t in trades_list]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    print(f"Total Trades:    {len(pnls)}")
    print(f"Wins:            {len(wins)} ({len(wins)/len(pnls)*100:.1f}%)")
    print(f"Losses:          {len(losses)} ({len(losses)/len(pnls)*100:.1f}%)")
    print(f"Mean PnL:        ${np.mean(pnls):.2f}")
    print(f"Std PnL:         ${np.std(pnls):.2f}")
    print(f"Win Avg:         ${np.mean(wins):.2f}")
    print(f"Loss Avg:        ${np.mean(losses):.2f}")
    print(f"Profit Factor:   {abs(sum(wins)/sum(losses)):.2f}")

except FileNotFoundError:
    print("❌ trades_history.json not found")

# 5. Compare versions
print("\n[4] VERSION COMPARISON (v1 → v2 → v2.3)")
print("-" * 70)

versions = {
    "v1": {
        "sharpe_val": 3.79e9,
        "sharpe_val_capped": 10.0,
        "sharpe_backtest": 0.00,  # Não testado em v1
        "win_rate": 0.186,
        "duration_min": 1.37,
        "episodes": 5,
    },
    "v2": {
        "sharpe_val": 3.79e9,
        "sharpe_val_capped": 10.0,
        "sharpe_backtest": 0.00,
        "win_rate": 0.484,
        "duration_min": 2.0,
        "episodes": 5,
    },
    "v2.3": {
        "sharpe_val": 10.0,
        "sharpe_val_capped": 10.0,
        "sharpe_backtest": 0.5485,
        "win_rate": 0.510,
        "duration_min": 2.0,
        "episodes": 50,
    },
}

for ver, metrics in versions.items():
    print(f"\n{ver}:")
    print(f"  Val Sharpe (actual):  {metrics['sharpe_val']:.2e}")
    print(f"  Val Sharpe (capped):  {metrics['sharpe_val_capped']:.2f}")
    print(f"  BT Sharpe (Phase 3):  {metrics['sharpe_backtest']:.4f}")
    print(f"  Win Rate:             {metrics['win_rate']*100:.1f}%")
    print(f"  Duration:             {metrics['duration_min']:.2f} min")
    print(f"  Episodes:             {metrics['episodes']}")

# 6. Gap analysis (val vs backtest)
print("\n[5] VALIDATION vs BACKTEST GAP")
print("-" * 70)
v23_val_sharpe = versions['v2.3']['sharpe_val_capped']
v23_bt_sharpe = versions['v2.3']['sharpe_backtest']
gap = ((v23_val_sharpe - v23_bt_sharpe) / v23_val_sharpe) * 100

print(f"Validation Sharpe:  {v23_val_sharpe:.4f}")
print(f"Backtest Sharpe:    {v23_bt_sharpe:.4f}")
print(f"Gap:                {gap:.1f}% ❌ (HIGH OVERFITTING)")
print(f"\nRatio (val/bt):     {v23_val_sharpe/v23_bt_sharpe:.2f}x")

# 7. Recommendations
print("\n[6] KEY FINDINGS & RECOMMENDATIONS")
print("-" * 70)
print("\n🔍 Key Issues:")
print("  1. Sharpe metric unreliable (capped at 10.0, artificial)")
print("  2. Validation uses only 50 episodes → high std=0.0")
print("  3. Gap between validation (10.0) and backtest (0.55) = 95% ❌")
print("  4. Consecutive losses 6 > limit 5 → need safeguard")
print("\n✅ Positive Signals:")
print("  • Win rate improving: 18.6% → 48.4% → 51.0% ✅")
print("  • Max drawdown excellent: 0% → 1.1% ✅")
print("  • Profit factor strong: 4.02 ✅")
print("  • Return consistent: $38.90 ✅")
print("\n⚡ Next Steps (v2.4):")
print("  1. Increase validation episodes: 50 → 100-200")
print("  2. Add consecutive loss safeguard (max 5)")
print("  3. Review Sharpe metric (use Sortino or Calmar)")
print("  4. Increase early-stop threshold: 10.0 → 20.0+")
print("\n💡 Expected Impact:")
print("  • Sharpe val: 10.0 → ~1.5-2.5 (realistic)")
print("  • Consecutive losses: 6 → 5 (compliance)")
print("  • Phase 3 Decision: NO-GO → GO (likely)")

print("\n" + "=" * 70)
