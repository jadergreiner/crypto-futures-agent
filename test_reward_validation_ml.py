"""
Quick test: Reward calculator integração com features + backtest
ML Specialist validation — 22 FEV
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from agent.reward import RewardCalculator

def test_reward_scaling():
    """Teste 1: Validar que escalas de reward são apropriadas para PPO"""
    calc = RewardCalculator()
    
    # Teste Trade Winner
    trade_winner = {
        'pnl_pct': 3.5,
        'r_multiple': 3.5,
        'exit_reason': 'take_profit'
    }
    reward = calc.calculate(trade_result=trade_winner)
    print(f"✅ Winner (+3.5%, R=3.5): total_reward={reward['total']:.2f} (clipped to 10.0)")
    assert reward['total'] <= 10.0, "Reward should be clipped"
    
    # Teste Trade Loser
    trade_loser = {
        'pnl_pct': -1.2,
        'r_multiple': -1.2,
    }
    reward = calc.calculate(trade_result=trade_loser)
    print(f"✅ Loser (-1.2%): total_reward={reward['total']:.2f}")
    assert reward['total'] < 0, "Loser should have negative reward"
    
    # Teste Hold Bonus
    position_state = {
        'has_position': True,
        'pnl_pct': 2.5,
        'pnl_momentum': 0.1
    }
    reward = calc.calculate(position_state=position_state)
    print(f"✅ Hold (+2.5%, momentum +0.1): hold_bonus={reward['r_hold_bonus']:.3f}")
    assert reward['r_hold_bonus'] > 0, "Hold bonus should be positive for profitable position"
    
    # Teste Out-of-Market (Drawdown protection)
    portfolio_state = {
        'current_drawdown_pct': 3.0,
        'trades_24h': 1
    }
    position_state = {'has_position': False}
    reward = calc.calculate(position_state=position_state, portfolio_state=portfolio_state)
    print(f"✅ Out-of-market (DD=3%): out_of_market={reward['r_out_of_market']:.3f}")
    assert reward['r_out_of_market'] > 0, "Should reward for staying out in drawdown"
    
    print("\n✅ ALL REWARD SCALING TESTS PASSED")
    return True

def test_reward_components():
    """Teste 2: Validar que componentes estão balanced"""
    calc = RewardCalculator()
    
    # Simular trade com múltiplos componentes
    trade = {'pnl_pct': 2.0, 'r_multiple': 2.0}
    position = {'has_position': False}
    portfolio = {'current_drawdown_pct': 0.5, 'trades_24h': 0}
    
    reward = calc.calculate(
        trade_result=trade,
        position_state=position,
        portfolio_state=portfolio,
        action_valid=True
    )
    
    print(f"\nComponent breakdown:")
    print(f"  r_pnl: {reward['r_pnl']:.2f} (trade closed at +2%, R=2)")
    print(f"  r_hold_bonus: {reward['r_hold_bonus']:.3f} (no active position)")
    print(f"  r_invalid_action: {reward['r_invalid_action']:.3f} (action valid)")
    print(f"  r_out_of_market: {reward['r_out_of_market']:.3f} (no drawdown)")
    print(f"  TOTAL: {reward['total']:.2f}")
    
    # Validar que nenhum componente domina injustamente
    assert abs(reward['r_pnl']) < 30, "PnL component shouldn't explode"
    print(f"\n✅ COMPONENT BALANCE OK")
    return True

def test_invalid_action_penalty():
    """Teste 3: Validar penalidade de ação inválida"""
    calc = RewardCalculator()
    
    reward = calc.calculate(action_valid=False)
    print(f"\nInvalid action penalty: {reward['r_invalid_action']}")
    assert reward['r_invalid_action'] == -0.5, "Invalid action penalty should be -0.5"
    assert reward['total'] == -0.5, "Total should be -0.5 for just invalid action"
    
    print(f"✅ INVALID ACTION PENALTY OK (-0.5)")
    return True

if __name__ == '__main__':
    try:
        test_reward_scaling()
        test_reward_components()
        test_invalid_action_penalty()
        print("\n" + "="*70)
        print("✅ ALL ML VALIDATION TESTS PASSED")
        print("✅ REWARD FUNCTION READY FOR BACKTEST")
        print("="*70)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
