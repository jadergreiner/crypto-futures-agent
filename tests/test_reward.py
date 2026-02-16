"""
Testes unitários para RewardCalculator.
Testa a lógica de bonus de R-multiple e cálculo de reward - Round 4 simplificado.
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
        """Testa cálculo básico de reward com 3 componentes."""
        result = reward_calc.calculate(
            trade_result=None,
            position_state=None,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        assert isinstance(result, dict), "Resultado deve ser um dicionário"
        assert 'total' in result, "Resultado deve conter chave 'total'"
        
        # Verifica que os 3 componentes do Round 4 estão presentes
        expected_keys = ['r_pnl', 'r_hold_bonus', 'r_invalid_action']
        for key in expected_keys:
            assert key in result, f"Faltando chave '{key}'"
        
        # Verifica que componentes antigos NÃO estão presentes
        old_keys = ['r_risk', 'r_consistency', 'r_overtrading', 'r_unrealized', 
                    'r_inactivity', 'r_exit_quality']
        for key in old_keys:
            assert key not in result, f"Componente antigo '{key}' não deveria existir"
    
    def test_r_multiple_greater_than_3(self, reward_calc):
        """Testa que R-multiple > 3.0 recebe bonus de 1.0 (R_BONUS_HIGH)."""
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
        
        # Verifica que o componente r_pnl recebeu PNL_SCALE × pnl_pct + R_BONUS_HIGH
        r_pnl = result['r_pnl']
        
        # r_pnl deve incluir: (pnl_pct × 10) + 1.0 bonus
        # (3.5 × 10) + 1.0 = 36.0
        expected_r_pnl = (3.5 * 10) + 1.0
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 3.5R, recebeu {r_pnl}"
    
    def test_r_multiple_between_2_and_3(self, reward_calc):
        """Testa que R-multiple entre 2.0 e 3.0 recebe bonus de 0.5 (R_BONUS_LOW)."""
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
        
        # Verifica que o componente r_pnl recebeu PNL_SCALE × pnl_pct + R_BONUS_LOW
        r_pnl = result['r_pnl']
        
        # r_pnl deve incluir: (pnl_pct × 10) + 0.5 bonus
        # (2.5 × 10) + 0.5 = 25.5
        expected_r_pnl = (2.5 * 10) + 0.5
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 2.5R, recebeu {r_pnl}"
    
    def test_r_multiple_exactly_2(self, reward_calc):
        """Testa que R-multiple exatamente 2.0 NÃO recebe bonus (> 2.0 necessário)."""
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
        
        # Verifica que o componente r_pnl NÃO recebeu bonus (apenas PNL_SCALE)
        r_pnl = result['r_pnl']
        
        # r_pnl deve ser: pnl_pct × 10 (sem bonus)
        # 2.0 × 10 = 20.0
        expected_r_pnl = 2.0 * 10
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para exatamente 2.0R (sem bonus), recebeu {r_pnl}"
    
    def test_r_multiple_less_than_2(self, reward_calc):
        """Testa que R-multiple < 2.0 não recebe bonus."""
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
        
        # Verifica que o componente r_pnl NÃO recebeu bonus (apenas PNL_SCALE)
        r_pnl = result['r_pnl']
        
        # r_pnl deve ser: pnl_pct × 10 (sem bonus)
        # 1.5 × 10 = 15.0
        expected_r_pnl = 1.5 * 10
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 1.5R (sem bonus), recebeu {r_pnl}"
    
    def test_r_multiple_exactly_3(self, reward_calc):
        """Testa que R-multiple exatamente 3.0 NÃO recebe R_BONUS_HIGH (> 3.0 necessário)."""
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
        
        # Verifica que o componente r_pnl recebeu R_BONUS_LOW, não R_BONUS_HIGH
        r_pnl = result['r_pnl']
        
        # r_pnl deve ser: (pnl_pct × 10) + 0.5 bonus (porque 3.0 > 2.0 mas não > 3.0)
        # (3.0 × 10) + 0.5 = 30.5
        expected_r_pnl = (3.0 * 10) + 0.5
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para exatamente 3.0R (R_BONUS_LOW), recebeu {r_pnl}"
    
    def test_r_multiple_negative(self, reward_calc):
        """Testa que R-multiple negativo não recebe bonus."""
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
        
        # Verifica que r_pnl é negativo e sem bonus (apenas PNL_SCALE)
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
    
    def test_r_multiple_5_receives_high_bonus(self, reward_calc):
        """Testa que R-multiple de 5.0 recebe R_BONUS_HIGH (> 3.0)."""
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
        
        # Verifica que o componente r_pnl recebeu PNL_SCALE × pnl_pct + R_BONUS_HIGH
        r_pnl = result['r_pnl']
        
        # r_pnl deve incluir: (pnl_pct × 10) + 1.0 bonus
        # (5.0 × 10) + 1.0 = 51.0
        expected_r_pnl = (5.0 * 10) + 1.0
        assert r_pnl == pytest.approx(expected_r_pnl, abs=0.1), \
            f"Esperado r_pnl ~{expected_r_pnl} para 5.0R, recebeu {r_pnl}"
    
    def test_invalid_action_penalty(self, reward_calc):
        """Testa que ação inválida recebe penalidade de -0.5."""
        result = reward_calc.calculate(
            trade_result=None,
            position_state=None,
            portfolio_state={'total_capital': 10000.0},
            action_valid=False,  # Ação inválida
            trades_recent=None
        )
        
        # Ação inválida deve ter penalidade de -0.5 (INVALID_ACTION_PENALTY)
        assert result['r_invalid_action'] == pytest.approx(-0.5, abs=0.01), \
            f"Ação inválida deve ter penalidade -0.5, recebeu {result['r_invalid_action']}"
    
    def test_close_blocked_is_invalid(self, reward_calc):
        """Testa que CLOSE bloqueado (action_valid=False) gera penalidade."""
        # Simula CLOSE bloqueado: action_valid=False
        result = reward_calc.calculate(
            trade_result=None,
            position_state={'has_position': True, 'pnl_pct': 0.5},  # Posição lucrativa
            portfolio_state={'total_capital': 10000.0},
            action_valid=False,  # CLOSE foi bloqueado
            trades_recent=None
        )
        
        # Verifica que r_invalid_action tem penalidade
        assert result['r_invalid_action'] < 0, \
            f"CLOSE bloqueado deve ter penalidade negativa, recebeu {result['r_invalid_action']}"
        
        # E também deve receber hold_bonus positivo por ter posição lucrativa
        assert result['r_hold_bonus'] > 0, \
            f"Posição lucrativa deve ter hold_bonus positivo, recebeu {result['r_hold_bonus']}"
    
    def test_hold_bonus_with_momentum(self, reward_calc):
        """Testa que hold bonus é proporcional ao PnL e momentum positivo dá bonus extra."""
        # Caso 1: Posição lucrativa COM momentum positivo
        result1 = reward_calc.calculate(
            trade_result=None,
            position_state={
                'has_position': True, 
                'pnl_pct': 2.0,
                'pnl_momentum': 0.5  # Momentum positivo
            },
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # hold_bonus = HOLD_BASE_BONUS + pnl_pct * HOLD_SCALING + momentum * 0.05
        # = 0.05 + 2.0 * 0.1 + 0.5 * 0.05 = 0.05 + 0.2 + 0.025 = 0.275
        expected_bonus1 = 0.05 + 2.0 * 0.1 + 0.5 * 0.05
        assert result1['r_hold_bonus'] == pytest.approx(expected_bonus1, abs=0.01), \
            f"Hold bonus com momentum deve ser {expected_bonus1}, recebeu {result1['r_hold_bonus']}"
        
        # Caso 2: Posição lucrativa SEM momentum (momentum=0)
        result2 = reward_calc.calculate(
            trade_result=None,
            position_state={
                'has_position': True, 
                'pnl_pct': 2.0,
                'pnl_momentum': 0.0  # Sem momentum
            },
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # hold_bonus = HOLD_BASE_BONUS + pnl_pct * HOLD_SCALING
        # = 0.05 + 2.0 * 0.1 = 0.25
        expected_bonus2 = 0.05 + 2.0 * 0.1
        assert result2['r_hold_bonus'] == pytest.approx(expected_bonus2, abs=0.01), \
            f"Hold bonus sem momentum deve ser {expected_bonus2}, recebeu {result2['r_hold_bonus']}"
        
        # Caso 3: Posição perdedora (PnL < -2.0)
        result3 = reward_calc.calculate(
            trade_result=None,
            position_state={
                'has_position': True, 
                'pnl_pct': -2.5,
                'pnl_momentum': 0.0
            },
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # hold_bonus = HOLD_LOSS_PENALTY = -0.02
        assert result3['r_hold_bonus'] == pytest.approx(-0.02, abs=0.01), \
            f"Hold bonus de posição perdedora deve ser -0.02, recebeu {result3['r_hold_bonus']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
