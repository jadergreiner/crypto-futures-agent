#!/usr/bin/env python
"""
Debug script to verify Phase 2 v2.4 training output
"""
import json
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("PHASE 2 v2.4 — VALIDATION EXECUTION DETAILS")
print("=" * 70)

# Load log
with open('logs/ppo_task005/training_log.json') as f:
    log = json.load(f)

start = datetime.fromisoformat(log['start_time'])
end = datetime.fromisoformat(log['end_time'])
duration = (end - start).total_seconds()

m = log['final_metrics']

print(f"\nTiming:")
print(f"  Start: {start.strftime('%H:%M:%S')}")
print(f"  End:   {end.strftime('%H:%M:%S')}")
print(f"  Duration: {duration:.1f} seconds")

print(f"\nValidation Metrics:")
print(f"  Episodes: {m['num_episodes']}")
print(f"  Returns (array):")

# Load the returns
ckpt = log['checkpoints'][0]
ckpt_m = ckpt['metrics']

print(f"    Episodes: {ckpt_m['num_episodes']}")
print(f"    Mean: ${ckpt_m['mean_return']:.4f}")
print(f"    Std: ${ckpt_m['std_return']:.2e}")
print(f"    Std (floored): ${ckpt_m['std_return_floored']:.4f}")
print(f"    Sharpe: {ckpt_m['sharpe_ratio']:.4f}")

print(f"\nAnalysis:")
if ckpt_m['std_return'] < 0.001:
    print(f"  ⚠️  Std dev is extremely small: {ckpt_m['std_return']:.2e}")
    print(f"     This suggests 50 episodes or less were evaluated")
    print(f"     (or all episodes returned nearly identical returns)")
else:
    print(f"  ✅ Std dev is reasonable: {ckpt_m['std_return']:.4f}")
    print(f"     This suggests 150+ episodes with real variance")

print("\n" + "=" * 70)
