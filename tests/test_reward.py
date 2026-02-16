"""
Testes unitários para RewardCalculator.
Testa a lógica de bonus de R-multiple e cálculo de reward.
"""

import pytest
from typing import Dict, Any

from agent.reward import RewardCalculator


class TestRewardCalculator:
    """Testes para a classe RewardCalculator."""
    
    @pytest.fixture
    def reward_calc(self):
        """Cria uma instância de RewardCalculator com pesos padrão."""
        return RewardCalculator()
    
    def test_calculate_basic(self, reward_calc):
        """Testa cálculo básico de reward."""
        result = reward_calc.calculate(
            trade_result=None,
            position_state=None,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        assert isinstance(result, dict), "Resultado deve ser um dicionário"
        assert 'total' in result, "Resultado deve conter chave 'total'"
        
        # Verifica que os componentes estão presentes
        expected_keys = ['r_pnl', 'r_risk', 'r_consistency', 'r_overtrading', 
                        'r_hold_bonus', 'r_invalid_action']
        for key in expected_keys:
            assert key in result, f"Faltando chave '{key}'"
    
    def test_r_multiple_greater_than_3(self, reward_calc):
        """Testa que R-multiple > 3.0 recebe bonus de 0.5 com amplificação."""
        trade_result = {
            'pnl': 350.0,
            'pnl_pct': 3.5,
            'r_multiple': 3.5,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # Verifica que o componente r_pnl recebeu amplificação × 10 + bonus de 0.5
        r_pnl = result['r_pnl']
        
        # r_pnl deve incluir: (pnl_pct × 10) + 0.5 bonus
        # (3.5 × 10) + 0.5 = 35.5
        expected_r_pnl = (3.5 * 10) + 0.5
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 3.5R com amplificação, recebeu {r_pnl}"
    
    def test_r_multiple_between_2_and_3(self, reward_calc):
        """Testa que R-multiple entre 2.0 e 3.0 recebe bonus de 0.2 com amplificação."""
        trade_result = {
            'pnl': 250.0,
            'pnl_pct': 2.5,
            'r_multiple': 2.5,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # Verifica que o componente r_pnl recebeu amplificação × 10 + bonus de 0.2
        r_pnl = result['r_pnl']
        
        # r_pnl deve incluir: (pnl_pct × 10) + 0.2 bonus
        # (2.5 × 10) + 0.2 = 25.2
        expected_r_pnl = (2.5 * 10) + 0.2
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 2.5R com amplificação, recebeu {r_pnl}"
    
    def test_r_multiple_exactly_2(self, reward_calc):
        """Testa que R-multiple exatamente 2.0 NÃO recebe bonus (> 2.0 necessário) com amplificação."""
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
        
        # Verifica que o componente r_pnl NÃO recebeu bonus (apenas amplificação)
        r_pnl = result['r_pnl']
        
        # r_pnl deve ser: pnl_pct × 10 (sem bonus)
        # 2.0 × 10 = 20.0
        expected_r_pnl = 2.0 * 10
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para exatamente 2.0R (sem bonus), recebeu {r_pnl}"
    
    def test_r_multiple_less_than_2(self, reward_calc):
        """Testa que R-multiple < 2.0 não recebe bonus com amplificação."""
        trade_result = {
            'pnl': 150.0,
            'pnl_pct': 1.5,
            'r_multiple': 1.5,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # Verifica que o componente r_pnl NÃO recebeu bonus (apenas amplificação)
        r_pnl = result['r_pnl']
        
        # r_pnl deve ser: pnl_pct × 10 (sem bonus)
        # 1.5 × 10 = 15.0
        expected_r_pnl = 1.5 * 10
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 1.5R (sem bonus), recebeu {r_pnl}"
    
    def test_r_multiple_exactly_3(self, reward_calc):
        """Testa que R-multiple exatamente 3.0 NÃO recebe bonus de 0.5 (> 3.0 necessário) com amplificação."""
        trade_result = {
            'pnl': 300.0,
            'pnl_pct': 3.0,
            'r_multiple': 3.0,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # Verifica que o componente r_pnl recebeu bonus de 0.2, não 0.5
        r_pnl = result['r_pnl']
        
        # r_pnl deve ser: (pnl_pct × 10) + 0.2 bonus (porque 3.0 > 2.0 mas não > 3.0)
        # (3.0 × 10) + 0.2 = 30.2
        expected_r_pnl = (3.0 * 10) + 0.2
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para exatamente 3.0R (bonus 0.2), recebeu {r_pnl}"
    
    def test_r_multiple_negative(self, reward_calc):
        """Testa que R-multiple negativo não recebe bonus com amplificação."""
        trade_result = {
            'pnl': -100.0,
            'pnl_pct': -1.0,
            'r_multiple': -1.0,
            'exit_reason': 'stop_loss'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # Verifica que r_pnl é negativo e sem bonus (apenas amplificação)
        r_pnl = result['r_pnl']
        
        # r_pnl deve ser: pnl_pct × 10 (sem bonus para negativo)
        # -1.0 × 10 = -10.0
        expected_r_pnl = -1.0 * 10
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para -1.0R (sem bonus), recebeu {r_pnl}"
    
    def test_r_multiple_zero(self, reward_calc):
        """Testa que R-multiple de 0 não recebe bonus."""
        trade_result = {
            'pnl': 0.0,
            'pnl_pct': 0.0,
            'r_multiple': 0.0,
            'exit_reason': 'manual'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # Verifica que r_pnl é zero (sem bonus)
        r_pnl = result['r_pnl']
        
        expected_r_pnl = 0.0
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 0.0R (sem bonus), recebeu {r_pnl}"
    
    def test_r_multiple_5_receives_5_bonus(self, reward_calc):
        """Testa que R-multiple de 5.0 recebe bonus de 0.5 (> 3.0) com amplificação."""
        trade_result = {
            'pnl': 500.0,
            'pnl_pct': 5.0,
            'r_multiple': 5.0,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # Verifica que o componente r_pnl recebeu amplificação × 10 + bonus de 0.5
        r_pnl = result['r_pnl']
        
        # r_pnl deve incluir: (pnl_pct × 10) + 0.5 bonus
        # (5.0 × 10) + 0.5 = 50.5
        expected_r_pnl = (5.0 * 10) + 0.5
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 5.0R com amplificação, recebeu {r_pnl}"
    
    def test_invalid_action_penalty(self, reward_calc):
        """Testa que ação inválida recebe penalidade."""
        result = reward_calc.calculate(
            trade_result=None,
            position_state=None,
            portfolio_state={'total_capital': 10000.0},
            action_valid=False,  # Ação inválida
            trades_recent=None
        )
        
        # Ação inválida deve ter penalidade negativa
        assert result['r_invalid_action'] < 0, \
            f"Ação inválida deve ter penalidade negativa, recebeu {result['r_invalid_action']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
