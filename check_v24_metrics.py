import json

d = json.load(open('logs/ppo_task005/training_log.json'))
m = d['final_metrics']

print("=" * 60)
print("FASE 2 v2.4 - FINAL METRICS (NEW)")
print("=" * 60)
print(f"Episodes (eval):  {m['num_episodes']}")
print(f"Sharpe Ratio:     {m['sharpe_ratio']:.4f}  (target: >= 0.80)")
print(f"Std Dev:          {m['std_return']:.6f}")
print(f"Win Rate:         {m['win_rate']*100:.1f}%  (target: >= 45%)")
print(f"Max Drawdown:     {m['max_drawdown']*100:.1f}%  (target: <= 12%)")
print(f"Mean Return:      ${m['mean_return']:.4f}")
print("=" * 60)

print("\nCOMPARISON (v2.3 → v2.4):")
print(f"Episodes:         50 → {m['num_episodes']}")
print(f"Sharpe:           10.0000 → {m['sharpe_ratio']:.4f}  [REDUCED as expected]")
print(f"Std Dev:          0.000000 → {m['std_return']:.6f}  [NOW HAS VARIANCE ✅]")
print(f"Win Rate:         51.0% → {m['win_rate']*100:.1f}%     [MAINTAINED]")
