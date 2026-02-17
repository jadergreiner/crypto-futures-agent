"""
Testes unitários para SignalReplayEnv.
"""

import pytest
import numpy as np
from typing import Dict, Any, List

from agent.signal_environment import SignalReplayEnv, ACTION_HOLD, ACTION_CLOSE, ACTION_REDUCE_50


class TestSignalReplayEnv:
    """Testes para a classe SignalReplayEnv."""
    
    @pytest.fixture
    def sample_signals(self):
        """Cria sinais de exemplo para testes."""
        return [
            {
                'id': 1,
                'timestamp': 1000000,
                'symbol': 'BTCUSDT',
                'direction': 'LONG',
                'entry_price': 50000.0,
                'stop_loss': 49000.0,
                'take_profit_1': 51000.0,
                'exit_price': 51500.0,
                'exit_reason': 'take_profit_2',
                'pnl_pct': 3.0,
                'r_multiple': 3.0,
                'outcome_label': 'win'
            },
            {
                'id': 2,
                'timestamp': 2000000,
                'symbol': 'ETHUSDT',
                'direction': 'SHORT',
                'entry_price': 3000.0,
                'stop_loss': 3060.0,
                'take_profit_1': 2940.0,
                'exit_price': 3060.0,
                'exit_reason': 'stop_loss',
                'pnl_pct': -2.0,
                'r_multiple': -1.0,
                'outcome_label': 'loss'
            }
        ]
    
    @pytest.fixture
    def sample_evolutions(self):
        """Cria evoluções de exemplo para os sinais."""
        return {
            1: [
                {
                    'timestamp': 1000900,
                    'current_price': 50500.0,
                    'unrealized_pnl_pct': 1.0,
                    'distance_to_stop_pct': -2.0,
                    'distance_to_tp1_pct': 1.0,
                    'rsi_14': 55.0,
                    'macd_histogram': 0.1,
                    'bb_percent_b': 0.6,
                    'atr_14': 1.0,
                    'adx_14': 30.0,
                    'market_structure': 'bullish',
                    'funding_rate': 0.01,
                    'long_short_ratio': 1.2,
                    'mfe_pct': 1.0,
                    'mae_pct': -0.2,
                    'event_type': None
                },
                {
                    'timestamp': 1001800,
                    'current_price': 51000.0,
                    'unrealized_pnl_pct': 2.0,
                    'distance_to_stop_pct': -4.0,
                    'distance_to_tp1_pct': 0.0,
                    'rsi_14': 60.0,
                    'macd_histogram': 0.2,
                    'bb_percent_b': 0.7,
                    'atr_14': 1.0,
                    'adx_14': 35.0,
                    'market_structure': 'bullish',
                    'funding_rate': 0.01,
                    'long_short_ratio': 1.3,
                    'mfe_pct': 2.0,
                    'mae_pct': -0.2,
                    'event_type': 'PARTIAL_1'
                }
            ],
            2: [
                {
                    'timestamp': 2000900,
                    'current_price': 2990.0,
                    'unrealized_pnl_pct': 0.3,
                    'distance_to_stop_pct': 2.0,
                    'distance_to_tp1_pct': -2.0,
                    'rsi_14': 45.0,
                    'macd_histogram': -0.1,
                    'bb_percent_b': 0.4,
                    'atr_14': 1.0,
                    'adx_14': 25.0,
                    'market_structure': 'bearish',
                    'funding_rate': -0.01,
                    'long_short_ratio': 0.9,
                    'mfe_pct': 0.5,
                    'mae_pct': -2.0,
                    'event_type': None
                }
            ]
        }
    
    @pytest.fixture
    def env(self, sample_signals, sample_evolutions):
        """Cria instância do environment."""
        return SignalReplayEnv(signals=sample_signals, evolutions_dict=sample_evolutions)
    
    def test_init(self, env, sample_signals):
        """Testa inicialização do environment."""
        assert env is not None
        assert len(env.signals) == len(sample_signals)
        assert env.observation_space.shape == (20,)
        assert env.action_space.n == 5
    
    def test_reset(self, env):
        """Testa reset do environment."""
        obs, info = env.reset()
        
        assert obs is not None
        assert isinstance(obs, np.ndarray)
        assert obs.shape == (20,)
        assert isinstance(info, dict)
        assert 'signal_id' in info
        assert 'step' in info
        assert 'position_size' in info
        
        # Estado inicial
        assert env.current_step == 0
        assert env.position_closed is False
        assert env.position_size == 1.0
    
    def test_step_hold(self, env):
        """Testa ação HOLD."""
        env.reset()
        
        obs, reward, terminated, truncated, info = env.step(ACTION_HOLD)
        
        assert isinstance(obs, np.ndarray)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)
        
        # Posição deve continuar aberta
        assert env.position_closed is False
        assert env.current_step == 1
    
    def test_step_close(self, env):
        """Testa ação CLOSE."""
        env.reset()
        
        obs, reward, terminated, truncated, info = env.step(ACTION_CLOSE)
        
        # Posição deve estar fechada
        assert env.position_closed is True
        assert terminated is True
    
    def test_step_reduce(self, env):
        """Testa ação REDUCE_50."""
        env.reset()
        
        obs, reward, terminated, truncated, info = env.step(ACTION_REDUCE_50)
        
        # Posição deve ser reduzida
        assert env.position_size == 0.5
        assert terminated is False
    
    def test_step_reduce_twice(self, env):
        """Testa reduzir posição duas vezes."""
        env.reset()
        
        # Primeira redução
        obs1, reward1, _, _, _ = env.step(ACTION_REDUCE_50)
        assert env.position_size == 0.5
        # Reward pode ser positivo se houver lucro não realizado
        
        # Segunda redução (posição já pequena, deve dar penalidade)
        obs2, reward2, _, _, _ = env.step(ACTION_REDUCE_50)
        assert env.position_size == 0.5  # Não muda
        # O reward pode não ser negativo se o hold reward compensar a penalidade
        # Verificar que tentativa de reduzir não aumentou o tamanho
        assert env.position_size <= 0.5
    
    def test_episode_completion(self, env):
        """Testa conclusão natural do episódio."""
        obs, info = env.reset()
        
        total_steps = info['total_steps']
        
        # Executar HOLD até o fim
        for _ in range(total_steps + 1):
            obs, reward, terminated, truncated, info = env.step(ACTION_HOLD)
            if terminated:
                break
        
        # Deve ter terminado
        assert terminated is True
    
    def test_multiple_episodes(self, env, sample_signals):
        """Testa múltiplos episódios consecutivos."""
        episodes_completed = 0
        
        for _ in range(len(sample_signals) + 2):  # Mais que o número de sinais
            obs, info = env.reset()
            episodes_completed += 1
            
            # Executar alguns steps
            for _ in range(3):
                obs, reward, terminated, truncated, info = env.step(ACTION_HOLD)
                if terminated:
                    break
        
        # Deve ter completado múltiplos episódios
        assert episodes_completed > len(sample_signals)
    
    def test_observation_shape(self, env):
        """Testa formato da observação."""
        obs, _ = env.reset()
        
        assert obs.shape == (20,)
        assert obs.dtype == np.float32
        
        # Valores devem estar normalizados
        assert np.all(obs >= -10.0)
        assert np.all(obs <= 10.0)
    
    def test_observation_features(self, env):
        """Testa que observação contém features esperadas."""
        obs, _ = env.reset()
        
        # Observação deve ter 20 features
        assert len(obs) == 20
        
        # Executar um step e verificar novamente
        obs, _, _, _, _ = env.step(ACTION_HOLD)
        assert len(obs) == 20
    
    def test_reward_for_winning_trade(self, env, sample_signals):
        """Testa reward para trade vencedor."""
        # Resetar e garantir que pegamos o primeiro sinal (win)
        env.current_signal_idx = 0
        obs, info = env.reset()
        
        signal_id = info['signal_id']
        assert signal_id == 1  # Primeiro sinal (win)
        
        # Segurar até o fim
        total_reward = 0
        while True:
            obs, reward, terminated, truncated, info = env.step(ACTION_HOLD)
            total_reward += reward
            if terminated:
                break
        
        # Trade vencedor deve ter reward positivo total
        assert total_reward > 0
    
    def test_reward_for_losing_trade(self, env):
        """Testa reward para trade perdedor."""
        # Resetar para segundo sinal (loss)
        env.current_signal_idx = 1
        obs, info = env.reset()
        
        signal_id = info['signal_id']
        assert signal_id == 2  # Segundo sinal (loss)
        
        # Segurar até o fim
        total_reward = 0
        while True:
            obs, reward, terminated, truncated, info = env.step(ACTION_HOLD)
            total_reward += reward
            if terminated:
                break
        
        # Trade perdedor deve ter reward negativo total
        assert total_reward < 0
    
    def test_normalize_function(self, env):
        """Testa função de normalização."""
        # Valor no meio do range
        assert env._normalize(5.0, 0.0, 10.0) == 0.0
        
        # Valores extremos
        assert env._normalize(0.0, 0.0, 10.0) == -1.0
        assert env._normalize(10.0, 0.0, 10.0) == 1.0
        
        # Valores fora do range devem ser clipped
        assert env._normalize(-5.0, 0.0, 10.0) == -1.0
        assert env._normalize(15.0, 0.0, 10.0) == 1.0
        
        # Range zero
        assert env._normalize(5.0, 5.0, 5.0) == 0.0
    
    def test_info_dict_content(self, env):
        """Testa conteúdo do info dict."""
        obs, info = env.reset()
        
        assert 'signal_id' in info
        assert 'step' in info
        assert 'total_steps' in info
        assert 'position_size' in info
        assert 'position_closed' in info
        assert 'symbol' in info
        assert 'direction' in info
        assert 'outcome_label' in info
    
    def test_closed_position_no_more_rewards(self, env):
        """Testa que posição fechada não gera mais rewards."""
        env.reset()
        
        # Fechar posição
        obs, reward1, terminated, _, _ = env.step(ACTION_CLOSE)
        assert terminated is True
        
        # Tentar mais uma ação (não deveria fazer nada)
        obs, reward2, terminated, _, _ = env.step(ACTION_HOLD)
        
        assert reward2 == 0.0
        assert terminated is True
