"""
Testes unitários para SignalRewardCalculator.
"""

import pytest
from typing import Dict, Any, List

from agent.signal_reward import SignalRewardCalculator


class TestSignalRewardCalculator:
    """Testes para a classe SignalRewardCalculator."""
    
    @pytest.fixture
    def reward_calc(self):
        """Cria uma instância de SignalRewardCalculator."""
        return SignalRewardCalculator()
    
    def test_init(self, reward_calc):
        """Testa inicialização da calculadora."""
        assert reward_calc is not None
        assert isinstance(reward_calc, SignalRewardCalculator)
    
    def test_calculate_signal_reward_win_trade(self, reward_calc):
        """Testa cálculo de reward para trade vencedor."""
        signal = {
            'id': 1,
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 50000.0,
            'exit_price': 51500.0,
            'exit_reason': 'take_profit_2',
            'pnl_pct': 3.0,
            'r_multiple': 3.0,
            'max_favorable_excursion_pct': 3.5,
            'max_adverse_excursion_pct': -0.5,
            'outcome_label': 'win'
        }
        
        evolutions = [
            {
                'timestamp': 1000,
                'current_price': 50500.0,
                'unrealized_pnl_pct': 1.0,
                'event_type': None
            },
            {
                'timestamp': 2000,
                'current_price': 51000.0,
                'unrealized_pnl_pct': 2.0,
                'event_type': 'PARTIAL_1'
            }
        ]
        
        result = reward_calc.calculate_signal_reward(signal, evolutions)
        
        assert 'total' in result
        assert 'r_pnl' in result
        assert 'r_partial_bonus' in result
        assert 'r_quality' in result
        
        # R-multiple de 3.0 deve gerar reward positivo alto
        assert result['r_pnl'] > 3.0
        
        # Parcial executada deve gerar bonus
        assert result['r_partial_bonus'] > 0
        
        # Total deve ser positivo
        assert result['total'] > 0
    
    def test_calculate_signal_reward_loss_trade(self, reward_calc):
        """Testa cálculo de reward para trade perdedor."""
        signal = {
            'id': 2,
            'symbol': 'ETHUSDT',
            'direction': 'SHORT',
            'entry_price': 3000.0,
            'exit_price': 3060.0,
            'exit_reason': 'stop_loss',
            'pnl_pct': -2.0,
            'r_multiple': -1.0,
            'max_favorable_excursion_pct': 0.5,
            'max_adverse_excursion_pct': -2.0,
            'outcome_label': 'loss'
        }
        
        evolutions = [
            {
                'timestamp': 1000,
                'current_price': 2990.0,
                'unrealized_pnl_pct': 0.3,
                'event_type': None
            }
        ]
        
        result = reward_calc.calculate_signal_reward(signal, evolutions)
        
        # Stop loss deve gerar penalidade
        assert result['r_stop_penalty'] < 0
        
        # R-multiple negativo deve gerar reward negativo
        assert result['r_pnl'] < 0
        
        # Total deve ser negativo
        assert result['total'] < 0
    
    def test_calculate_pnl_reward_high_r(self, reward_calc):
        """Testa cálculo de reward para R-multiple alto (>3)."""
        r_multiple = 3.5
        reward = reward_calc._calculate_pnl_reward(r_multiple)
        
        # Deve incluir bonus alto
        assert reward > 3.5  # Base + bonus
        assert reward >= 3.5 + 2.0  # Base + R_MULTIPLE_BONUS_HIGH
    
    def test_calculate_pnl_reward_mid_r(self, reward_calc):
        """Testa cálculo de reward para R-multiple médio (2-3)."""
        r_multiple = 2.5
        reward = reward_calc._calculate_pnl_reward(r_multiple)
        
        # Deve incluir bonus médio
        assert reward > 2.5
        assert reward >= 2.5 + 1.0  # Base + R_MULTIPLE_BONUS_MID
    
    def test_calculate_pnl_reward_low_r(self, reward_calc):
        """Testa cálculo de reward para R-multiple baixo (1-2)."""
        r_multiple = 1.5
        reward = reward_calc._calculate_pnl_reward(r_multiple)
        
        # Deve incluir bonus baixo
        assert reward > 1.5
        assert reward >= 1.5 + 0.5  # Base + R_MULTIPLE_BONUS_LOW
    
    def test_calculate_pnl_reward_negative(self, reward_calc):
        """Testa cálculo de reward para R-multiple negativo."""
        r_multiple = -1.0
        reward = reward_calc._calculate_pnl_reward(r_multiple)
        
        # Deve ser negativo, sem bonus
        assert reward < 0
        assert reward == -1.0  # Apenas base
    
    def test_calculate_partial_bonus_with_partials(self, reward_calc):
        """Testa cálculo de bonus por parciais executadas."""
        signal = {
            'max_favorable_excursion_pct': 4.0
        }
        
        evolutions = [
            {
                'event_type': 'PARTIAL_1',
                'unrealized_pnl_pct': 3.8  # Próximo ao MFE
            },
            {
                'event_type': 'PARTIAL_2',
                'unrealized_pnl_pct': 3.5
            }
        ]
        
        bonus = reward_calc._calculate_partial_bonus(signal, evolutions, 'take_profit_2')
        
        # Deve ter bonus para 2 parciais + timing
        assert bonus > 1.0  # Pelo menos 2 * 0.5
    
    def test_calculate_partial_bonus_no_partials(self, reward_calc):
        """Testa cálculo de bonus sem parciais."""
        signal = {}
        evolutions = []
        
        bonus = reward_calc._calculate_partial_bonus(signal, evolutions, 'take_profit_1')
        
        assert bonus == 0.0
    
    def test_calculate_stop_penalty_simple(self, reward_calc):
        """Testa cálculo de penalidade por stop loss simples."""
        signal = {
            'max_favorable_excursion_pct': 0.5  # Pouco no lucro
        }
        evolutions = []
        
        penalty = reward_calc._calculate_stop_penalty(signal, evolutions)
        
        # Deve ter penalidade base
        assert penalty < 0
        assert penalty <= -1.0
    
    def test_calculate_stop_penalty_from_profit(self, reward_calc):
        """Testa penalidade por stop após trade ter estado muito no lucro."""
        signal = {
            'max_favorable_excursion_pct': 5.0  # Muito no lucro antes
        }
        evolutions = []
        
        penalty = reward_calc._calculate_stop_penalty(signal, evolutions)
        
        # Deve ter penalidade maior (má gestão)
        assert penalty < -1.0
    
    def test_calculate_quality_reward_high_ratio(self, reward_calc):
        """Testa reward por qualidade com ratio MFE/MAE alto."""
        mfe = 6.0
        mae = 1.0
        
        reward = reward_calc._calculate_quality_reward(mfe, mae)
        
        # Ratio > 3, deve ter reward alto
        assert reward > 0
    
    def test_calculate_quality_reward_low_ratio(self, reward_calc):
        """Testa reward por qualidade com ratio MFE/MAE baixo."""
        mfe = 1.0
        mae = 2.0
        
        reward = reward_calc._calculate_quality_reward(mfe, mae)
        
        # Ratio < 1, deve ter penalidade
        assert reward < 0
    
    def test_calculate_quality_reward_perfect_trade(self, reward_calc):
        """Testa reward para trade perfeito (MAE = 0)."""
        mfe = 5.0
        mae = 0.0
        
        reward = reward_calc._calculate_quality_reward(mfe, mae)
        
        # Trade perfeito, reward máximo
        assert reward > 0.5
    
    def test_calculate_timing_reward_good_entry(self, reward_calc):
        """Testa reward por timing de entrada boa."""
        signal = {
            'entry_price': 50000.0,
            'direction': 'LONG'
        }
        
        evolutions = [
            {'current_price': 50100.0},  # Subiu após entrada
            {'current_price': 50200.0}
        ]
        
        reward = reward_calc._calculate_timing_reward(signal, evolutions)
        
        # Entrada no melhor momento possível
        assert reward > 0
    
    def test_calculate_timing_reward_bad_entry(self, reward_calc):
        """Testa reward por timing de entrada ruim."""
        signal = {
            'entry_price': 50000.0,
            'direction': 'LONG'
        }
        
        evolutions = [
            {'current_price': 48000.0},  # Caiu muito após entrada
            {'current_price': 49000.0}
        ]
        
        reward = reward_calc._calculate_timing_reward(signal, evolutions)
        
        # Entrada ruim, sem reward
        assert reward == 0.0
    
    def test_calculate_management_reward_with_trailing(self, reward_calc):
        """Testa reward por gestão com trailing stop."""
        signal = {
            'exit_reason': 'trailing_stop',
            'pnl_pct': 2.5
        }
        
        evolutions = [
            {'event_type': 'TRAILING_ACTIVATED'},
            {'event_type': 'STOP_MOVED'}
        ]
        
        reward = reward_calc._calculate_management_reward(signal, evolutions)
        
        # Deve ter reward por trailing stop que protegeu lucro
        assert reward > 0
    
    def test_calculate_management_reward_no_management(self, reward_calc):
        """Testa reward por gestão sem eventos de gestão."""
        signal = {}
        evolutions = []
        
        reward = reward_calc._calculate_management_reward(signal, evolutions)
        
        assert reward == 0.0
    
    def test_reward_clipping(self, reward_calc):
        """Testa que reward total é clipped para limites."""
        # Criar sinal com valores extremos
        signal = {
            'r_multiple': 10.0,  # Muito alto
            'exit_reason': 'take_profit_3',
            'max_favorable_excursion_pct': 15.0,
            'max_adverse_excursion_pct': 0.1,
            'pnl_pct': 10.0
        }
        
        evolutions = []
        
        result = reward_calc.calculate_signal_reward(signal, evolutions)
        
        # Deve estar dentro dos limites
        assert result['total'] <= 10.0
        assert result['total'] >= -10.0
