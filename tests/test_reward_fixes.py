"""
Testes para as correções de reward: hold bonus assimétrico e r_exit_quality.
Testa os ajustes feitos para corrigir o comportamento de cortar lucros cedo e deixar perdas correrem.
"""

import pytest
from typing import Dict, Any

from agent.reward import RewardCalculator, INACTIVITY_THRESHOLD, INACTIVITY_PENALTY_RATE


class TestRewardFixes:
    """Testes para as correções de reward implementadas."""
    
    @pytest.fixture
    def reward_calc(self):
        """Cria uma instância de RewardCalculator."""
        return RewardCalculator()
    
    def test_hold_bonus_asymmetric_positive_profit(self, reward_calc):
        """Testa que hold bonus é forte para posições lucrativas."""
        position_state = {
            'has_position': True,
            'pnl_pct': 2.0  # 2% de lucro
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_hold_bonus deve ser: 0.05 + 2.0 * 0.1 = 0.25
        expected = 0.05 + 2.0 * 0.1
        assert result['r_hold_bonus'] == pytest.approx(expected, abs=0.001), \
            f"Esperado r_hold_bonus={expected} para pnl_pct=2.0%, recebeu {result['r_hold_bonus']}"
    
    def test_hold_bonus_asymmetric_small_loss(self, reward_calc):
        """Testa que hold bonus não penaliza perdas pequenas (<-0.5%)."""
        position_state = {
            'has_position': True,
            'pnl_pct': -0.3  # -0.3% de perda (pequena)
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_hold_bonus deve ser 0.0 (sem penalidade para perdas pequenas)
        assert result['r_hold_bonus'] == 0.0, \
            f"Esperado r_hold_bonus=0.0 para pnl_pct=-0.3%, recebeu {result['r_hold_bonus']}"
    
    def test_hold_bonus_asymmetric_significant_loss(self, reward_calc):
        """Testa que hold bonus penaliza fortemente posições perdedoras significativas."""
        position_state = {
            'has_position': True,
            'pnl_pct': -1.5  # -1.5% de perda
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_hold_bonus deve ser: -0.02 * abs(-1.5) = -0.03
        expected = -0.02 * abs(-1.5)
        assert result['r_hold_bonus'] == pytest.approx(expected, abs=0.001), \
            f"Esperado r_hold_bonus={expected} para pnl_pct=-1.5%, recebeu {result['r_hold_bonus']}"
    
    def test_hold_bonus_weight_is_08(self, reward_calc):
        """Testa que o peso de r_hold_bonus é 0.8 (alto)."""
        assert reward_calc.weights['r_hold_bonus'] == 0.8, \
            f"Peso de r_hold_bonus deve ser 0.8, recebeu {reward_calc.weights['r_hold_bonus']}"
    
    def test_exit_quality_good_rmultiple(self, reward_calc):
        """Testa que r_exit_quality recompensa R-multiple >= 1.0."""
        trade_result = {
            'pnl': 200.0,
            'pnl_pct': 2.0,
            'r_multiple': 2.0,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_exit_quality deve ser: min(2.0 * 0.5, 3.0) = 1.0
        expected = 2.0 * 0.5
        assert result['r_exit_quality'] == pytest.approx(expected, abs=0.001), \
            f"Esperado r_exit_quality={expected} para R=2.0, recebeu {result['r_exit_quality']}"
    
    def test_exit_quality_excellent_rmultiple(self, reward_calc):
        """Testa que r_exit_quality tem cap em 3.0 para R-multiples muito altos."""
        trade_result = {
            'pnl': 800.0,
            'pnl_pct': 8.0,
            'r_multiple': 8.0,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_exit_quality deve ser cappado em 3.0
        assert result['r_exit_quality'] == pytest.approx(3.0, abs=0.001), \
            f"Esperado r_exit_quality=3.0 (cap), recebeu {result['r_exit_quality']}"
    
    def test_exit_quality_manual_close_negative(self, reward_calc):
        """Testa que r_exit_quality penaliza manual_close com R negativo."""
        trade_result = {
            'pnl': -100.0,
            'pnl_pct': -1.0,
            'r_multiple': -1.0,
            'exit_reason': 'manual_close'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_exit_quality deve ser: -1.0 * 0.3 = -0.3
        expected = -1.0 * 0.3
        assert result['r_exit_quality'] == pytest.approx(expected, abs=0.001), \
            f"Esperado r_exit_quality={expected} para manual_close R=-1.0, recebeu {result['r_exit_quality']}"
    
    def test_exit_quality_stop_loss_not_penalized(self, reward_calc):
        """Testa que r_exit_quality NÃO penaliza stop_loss (gestão de risco correta)."""
        trade_result = {
            'pnl': -50.0,
            'pnl_pct': -0.5,
            'r_multiple': -0.5,
            'exit_reason': 'stop_loss'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_exit_quality deve ser 0.0 (sem penalidade para stop_loss)
        assert result['r_exit_quality'] == 0.0, \
            f"Esperado r_exit_quality=0.0 para stop_loss, recebeu {result['r_exit_quality']}"
    
    def test_exit_quality_weight_is_10(self, reward_calc):
        """Testa que o peso de r_exit_quality é 1.0."""
        assert reward_calc.weights['r_exit_quality'] == 1.0, \
            f"Peso de r_exit_quality deve ser 1.0, recebeu {reward_calc.weights['r_exit_quality']}"
    
    def test_inactivity_threshold_is_15(self, reward_calc):
        """Testa que INACTIVITY_THRESHOLD foi ajustado para 15."""
        assert INACTIVITY_THRESHOLD == 15, \
            f"INACTIVITY_THRESHOLD deve ser 15, recebeu {INACTIVITY_THRESHOLD}"
    
    def test_inactivity_penalty_rate_is_0015(self, reward_calc):
        """Testa que INACTIVITY_PENALTY_RATE foi ajustado para 0.015."""
        assert INACTIVITY_PENALTY_RATE == 0.015, \
            f"INACTIVITY_PENALTY_RATE deve ser 0.015, recebeu {INACTIVITY_PENALTY_RATE}"
    
    def test_inactivity_weight_is_03(self, reward_calc):
        """Testa que o peso de r_inactivity foi reduzido para 0.3."""
        assert reward_calc.weights['r_inactivity'] == 0.3, \
            f"Peso de r_inactivity deve ser 0.3, recebeu {reward_calc.weights['r_inactivity']}"
    
    def test_components_contains_exit_quality(self, reward_calc):
        """Testa que r_exit_quality está presente nos componentes retornados."""
        result = reward_calc.calculate(
            trade_result=None,
            position_state=None,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        assert 'r_exit_quality' in result, \
            "r_exit_quality deve estar presente no resultado"
    
    def test_total_reward_within_bounds(self, reward_calc):
        """Testa que o reward total está sempre dentro de [-10, +10]."""
        # Teste com valores extremos
        trade_result = {
            'pnl': 1000.0,
            'pnl_pct': 10.0,
            'r_multiple': 10.0,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True, 'pnl_pct': 10.0},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        assert -10.0 <= result['total'] <= 10.0, \
            f"Reward total deve estar em [-10, +10], recebeu {result['total']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
