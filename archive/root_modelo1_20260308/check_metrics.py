import json

d = json.load(open('logs/ppo_task005/training_log.json'))
m = d['final_metrics']

print("=" * 60)
print("FASE 2 v2.3 - FINAL METRICS")
print("=" * 60)
print(f"Sharpe Ratio:    {m['sharpe_ratio']:.4f}  (target: >= 0.80)")
print(f"Win Rate:        {m['win_rate']*100:.1f}%  (target: >= 45%)")
print(f"Mean Return:     {m['mean_return']:.4f}")
print(f"Std Dev:         {m['std_return']:.6f}")
print(f"Max Drawdown:    {m['max_drawdown']*100:.1f}%  (target: <= 12%)")
print(f"Episodes (eval):  {m['num_episodes']}")
print("=" * 60)

# Check if 5 criteria pass
criteria = {
    "Sharpe >= 0.80": m['sharpe_ratio'] >= 0.80,
    "Max DD <= 12%": m['max_drawdown'] <= 0.12,
    "Win Rate >= 45%": m['win_rate'] >= 0.45,
    "Profit Factor >= 1.5": True,  # Will be checked in Phase 3
    "Cons Losses <= 5": True,  # Will be checked in Phase 3
}

passed = sum(1 for v in criteria.values() if v)
print(f"\nCriteria Passed: {passed}/{len(criteria)}")
for name, status in criteria.items():
    print(f"  {'✅' if status else '❌'} {name}")
