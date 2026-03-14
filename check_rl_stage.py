import json

with open('model2_daily_pipeline_20260314T041333Z.json') as f:
    data = json.load(f)
    rl_stage = data['stages'].get('rl_signal_generation', {})
    print('=== RL SIGNAL GENERATION ===')
    print(f"Status: {rl_stage.get('status')}")
    print(f"PPO Available: {rl_stage.get('ppo_available')}")
    print(f"Episodes Available: {rl_stage.get('episodes_available')}")
    print(f"Opportunities Processed: {rl_stage.get('opportunities_processed')}")
    print(f"Signals Generated: {rl_stage.get('signals_generated')}")
    print(f"With RL Enhancement: {rl_stage.get('signals_with_rl_enhancement')}")
    print(f"\nDetalhes:")
    print(json.dumps(rl_stage, indent=2))
