"""
Testes para os novos componentes de reward: amplificação, unrealized PnL e penalidade de inatividade.
"""

import pytest
from typing import Dict, Any

from agent.reward import RewardCalculator, PNL_AMPLIFICATION_FACTOR, UNREALIZED_PNL_FACTOR
from agent.reward import INACTIVITY_THRESHOLD, INACTIVITY_PENALTY_RATE, INACTIVITY_MAX_PENALTY_STEPS


class TestRewardAmplification:
    """Testes para amplificação do sinal de PnL e novos componentes."""
    
    @pytest.fixture
    def reward_calc(self):
        """Cria uma instância de RewardCalculator."""
        return RewardCalculator()
    
    def test_pnl_amplification_factor_10(self, reward_calc):
        """Testa que pnl_pct é multiplicado pelo fator de amplificação no componente r_pnl."""
        trade_result = {
            'pnl': 30.0,
            'pnl_pct': 0.3,  # 0.3%
            'r_multiple': 1.0,
            'exit_reason': 'take_profit'
        }
        
        result = reward_calc.calculate(
            trade_result=trade_result,
            position_state={'has_position': True},
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_pnl deve ser: 0.3 * PNL_AMPLIFICATION_FACTOR = 3.0 (sem bonus porque R < 2.0)
        expected_r_pnl = 0.3 * PNL_AMPLIFICATION_FACTOR
        assert result['r_pnl'] == pytest.approx(expected_r_pnl, abs=0.01), \
            f"Esperado r_pnl={expected_r_pnl} para pnl_pct=0.3%, recebeu {result['r_pnl']}"
    
    def test_pnl_amplification_with_bonus_2r(self, reward_calc):
        """Testa amplificação com bonus para R > 2.0."""
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
        
        # r_pnl deve ser: (2.5 * 10) + 0.2 = 25.2
        expected_r_pnl = (2.5 * 10) + 0.2
        assert result['r_pnl'] == pytest.approx(expected_r_pnl, abs=0.01), \
            f"Esperado r_pnl={expected_r_pnl} para pnl_pct=2.5% e R=2.5, recebeu {result['r_pnl']}"
    
    def test_pnl_amplification_with_bonus_3r(self, reward_calc):
        """Testa amplificação com bonus para R > 3.0."""
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
        
        # r_pnl deve ser: (3.5 * 10) + 0.5 = 35.5
        expected_r_pnl = (3.5 * 10) + 0.5
        assert result['r_pnl'] == pytest.approx(expected_r_pnl, abs=0.01), \
            f"Esperado r_pnl={expected_r_pnl} para pnl_pct=3.5% e R=3.5, recebeu {result['r_pnl']}"
    
    def test_pnl_amplification_negative(self, reward_calc):
        """Testa amplificação de PnL negativo."""
        trade_result = {
            'pnl': -100.0,
            'pnl_pct': -1.0,  # -1.0%
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
        
        # r_pnl deve ser: -1.0 * 10 = -10.0 (sem bonus)
        expected_r_pnl = -1.0 * 10
        assert result['r_pnl'] == pytest.approx(expected_r_pnl, abs=0.01), \
            f"Esperado r_pnl={expected_r_pnl} para pnl_pct=-1.0%, recebeu {result['r_pnl']}"
    
    def test_unrealized_pnl_component_positive(self, reward_calc):
        """Testa componente r_unrealized para posição com lucro não realizado."""
        position_state = {
            'has_position': True,
            'direction': 'LONG',
            'pnl_pct': 1.5,  # 1.5% de lucro não realizado
            'time_in_position_hours': 8.0
        }
        
        result = reward_calc.calculate(
            trade_result=None,  # Sem trade fechado
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_unrealized deve ser: 1.5 * UNREALIZED_PNL_FACTOR
        expected_r_unrealized = 1.5 * UNREALIZED_PNL_FACTOR
        assert result['r_unrealized'] == pytest.approx(expected_r_unrealized, abs=0.01), \
            f"Esperado r_unrealized={expected_r_unrealized}, recebeu {result['r_unrealized']}"
        
        # Componente deve estar presente no resultado
        assert 'r_unrealized' in result, "r_unrealized deve estar presente no resultado"
    
    def test_unrealized_pnl_component_negative(self, reward_calc):
        """Testa componente r_unrealized para posição com perda não realizada."""
        position_state = {
            'has_position': True,
            'direction': 'SHORT',
            'pnl_pct': -0.8,  # -0.8% de perda não realizada
            'time_in_position_hours': 12.0
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_unrealized deve ser: -0.8 * UNREALIZED_PNL_FACTOR
        expected_r_unrealized = -0.8 * UNREALIZED_PNL_FACTOR
        assert result['r_unrealized'] == pytest.approx(expected_r_unrealized, abs=0.01), \
            f"Esperado r_unrealized={expected_r_unrealized}, recebeu {result['r_unrealized']}"
    
    def test_unrealized_pnl_zero_when_no_position(self, reward_calc):
        """Testa que r_unrealized é zero quando não há posição."""
        position_state = {
            'has_position': False,
            'flat_steps': 5
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_unrealized deve ser 0.0 quando não há posição
        assert result['r_unrealized'] == 0.0, \
            f"r_unrealized deve ser 0.0 sem posição, recebeu {result['r_unrealized']}"
    
    def test_inactivity_penalty_below_threshold(self, reward_calc):
        """Testa que não há penalidade para flat_steps <= INACTIVITY_THRESHOLD."""
        position_state = {
            'has_position': False,
            'flat_steps': INACTIVITY_THRESHOLD  # Exatamente no limite
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_inactivity deve ser 0.0 quando flat_steps <= INACTIVITY_THRESHOLD
        assert result['r_inactivity'] == 0.0, \
            f"r_inactivity deve ser 0.0 para flat_steps={INACTIVITY_THRESHOLD}, recebeu {result['r_inactivity']}"
    
    def test_inactivity_penalty_above_threshold(self, reward_calc):
        """Testa penalidade para flat_steps > INACTIVITY_THRESHOLD."""
        flat_steps = INACTIVITY_THRESHOLD + 5  # 5 steps acima do limite
        position_state = {
            'has_position': False,
            'flat_steps': flat_steps
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_inactivity deve ser: -INACTIVITY_PENALTY_RATE * (flat_steps - INACTIVITY_THRESHOLD)
        expected_r_inactivity = -INACTIVITY_PENALTY_RATE * 5
        assert result['r_inactivity'] == pytest.approx(expected_r_inactivity, abs=0.001), \
            f"Esperado r_inactivity={expected_r_inactivity}, recebeu {result['r_inactivity']}"
    
    def test_inactivity_penalty_capped_at_max(self, reward_calc):
        """Testa que penalidade de inatividade tem cap máximo."""
        flat_steps = INACTIVITY_THRESHOLD + 100  # Muito acima do limite
        position_state = {
            'has_position': False,
            'flat_steps': flat_steps
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_inactivity deve ser: -INACTIVITY_PENALTY_RATE * INACTIVITY_MAX_PENALTY_STEPS (cap)
        expected_r_inactivity = -INACTIVITY_PENALTY_RATE * INACTIVITY_MAX_PENALTY_STEPS
        assert result['r_inactivity'] == pytest.approx(expected_r_inactivity, abs=0.001), \
            f"Esperado r_inactivity={expected_r_inactivity} (cap), recebeu {result['r_inactivity']}"
    
    def test_inactivity_zero_when_has_position(self, reward_calc):
        """Testa que não há penalidade de inatividade quando há posição."""
        position_state = {
            'has_position': True,
            'direction': 'LONG',
            'pnl_pct': 0.5
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # r_inactivity deve ser 0.0 quando há posição
        assert result['r_inactivity'] == 0.0, \
            f"r_inactivity deve ser 0.0 quando há posição, recebeu {result['r_inactivity']}"
    
    def test_new_weights_exist(self, reward_calc):
        """Testa que os novos pesos foram adicionados corretamente."""
        weights = reward_calc.get_weights()
        
        # Verificar que os novos componentes existem
        assert 'r_unrealized' in weights, "r_unrealized deve estar nos pesos"
        assert 'r_inactivity' in weights, "r_inactivity deve estar nos pesos"
        
        # Verificar valores dos pesos
        assert weights['r_unrealized'] == 0.3, f"Peso de r_unrealized deve ser 0.3, é {weights['r_unrealized']}"
        assert weights['r_inactivity'] == 0.3, f"Peso de r_inactivity deve ser 0.3, é {weights['r_inactivity']}"
    
    def test_combined_scenario_trading_with_unrealized(self, reward_calc):
        """Testa cenário combinado: posição aberta com lucro não realizado."""
        position_state = {
            'has_position': True,
            'direction': 'LONG',
            'pnl_pct': 2.0,  # 2% de lucro não realizado
            'time_in_position_hours': 16.0
        }
        
        result = reward_calc.calculate(
            trade_result=None,
            position_state=position_state,
            portfolio_state={'total_capital': 10000.0},
            action_valid=True,
            trades_recent=None
        )
        
        # Verificar que recebe tanto r_hold_bonus quanto r_unrealized
        assert result['r_hold_bonus'] > 0, "Deve receber hold bonus por lucro"
        assert result['r_unrealized'] > 0, "Deve receber unrealized reward por lucro"
        assert result['r_inactivity'] == 0.0, "Não deve ter penalidade de inatividade com posição"
        
        # Total deve ser positivo
        assert result['total'] > 0, "Reward total deve ser positivo com posição lucrativa"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
