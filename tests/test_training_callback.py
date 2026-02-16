"""
Teste simples para demonstrar as melhorias no TrainingCallback.
Valida que o callback captura todos os episódios e não apenas o último.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock
from collections import deque

from agent.trainer import TrainingCallback


class TestTrainingCallback:
    """Testes para o TrainingCallback corrigido."""
    
    def test_callback_initialization(self):
        """Testa que o callback inicializa com os atributos corretos."""
        callback = TrainingCallback(verbose=1, log_interval=1000)
        
        assert callback.log_interval == 1000
        assert callback.episode_rewards == []
        assert callback.episode_lengths == []
        assert callback._last_ep_info_len == 0
    
    def test_callback_captures_all_new_episodes(self):
        """Testa que o callback captura TODOS os episódios novos, não apenas o último."""
        callback = TrainingCallback(verbose=0, log_interval=1000)
        
        # Simular o modelo com um buffer de episódios
        callback.model = MagicMock()
        callback.model.ep_info_buffer = deque(maxlen=100)
        
        # Simular que nenhum episódio foi processado ainda
        callback._last_ep_info_len = 0
        
        # Adicionar 3 episódios ao buffer
        callback.model.ep_info_buffer.append({'r': 10.0, 'l': 100})
        callback.model.ep_info_buffer.append({'r': 20.0, 'l': 150})
        callback.model.ep_info_buffer.append({'r': 15.0, 'l': 120})
        
        # Chamar _on_step para capturar episódios
        callback.n_calls = 500  # Não é um intervalo de log
        callback._on_step()
        
        # Verificar que todos os 3 episódios foram capturados
        assert len(callback.episode_rewards) == 3
        assert len(callback.episode_lengths) == 3
        assert callback.episode_rewards == [10.0, 20.0, 15.0]
        assert callback.episode_lengths == [100, 150, 120]
        assert callback._last_ep_info_len == 3
    
    def test_callback_only_captures_new_episodes(self):
        """Testa que o callback não reprocessa episódios já capturados."""
        callback = TrainingCallback(verbose=0, log_interval=1000)
        
        # Simular o modelo
        callback.model = MagicMock()
        callback.model.ep_info_buffer = deque(maxlen=100)
        
        # Adicionar 2 episódios
        callback.model.ep_info_buffer.append({'r': 10.0, 'l': 100})
        callback.model.ep_info_buffer.append({'r': 20.0, 'l': 150})
        
        # Primeira captura
        callback.n_calls = 500
        callback._on_step()
        assert len(callback.episode_rewards) == 2
        
        # Adicionar mais 2 episódios
        callback.model.ep_info_buffer.append({'r': 30.0, 'l': 200})
        callback.model.ep_info_buffer.append({'r': 40.0, 'l': 180})
        
        # Segunda captura - deve capturar apenas os 2 novos
        callback.n_calls = 1000
        callback._on_step()
        
        assert len(callback.episode_rewards) == 4
        assert callback.episode_rewards == [10.0, 20.0, 30.0, 40.0]
        assert callback._last_ep_info_len == 4
    
    def test_callback_handles_empty_buffer(self):
        """Testa que o callback lida com buffer vazio."""
        callback = TrainingCallback(verbose=0, log_interval=1000)
        
        callback.model = MagicMock()
        callback.model.ep_info_buffer = deque(maxlen=100)
        
        # Chamar _on_step com buffer vazio
        callback.n_calls = 1000
        callback._on_step()
        
        assert len(callback.episode_rewards) == 0
        assert len(callback.episode_lengths) == 0
        assert callback._last_ep_info_len == 0
    
    def test_on_rollout_end_does_nothing(self):
        """Testa que _on_rollout_end não faz nada (pass)."""
        callback = TrainingCallback(verbose=0, log_interval=1000)
        
        callback.model = MagicMock()
        callback.model.ep_info_buffer = deque(maxlen=100)
        callback.model.ep_info_buffer.append({'r': 10.0, 'l': 100})
        
        initial_rewards_len = len(callback.episode_rewards)
        
        # Chamar _on_rollout_end
        callback._on_rollout_end()
        
        # Verificar que nada foi adicionado
        assert len(callback.episode_rewards) == initial_rewards_len
    
    def test_callback_computes_stats_correctly(self):
        """Testa que o callback calcula estatísticas corretamente."""
        callback = TrainingCallback(verbose=0, log_interval=1000)
        
        callback.model = MagicMock()
        callback.model.ep_info_buffer = deque(maxlen=100)
        
        # Adicionar episódios com rewards conhecidos
        for i in range(10):
            callback.model.ep_info_buffer.append({'r': float(i), 'l': 100})
        
        callback.n_calls = 500
        callback._on_step()
        
        # Calcular média manualmente
        expected_mean = np.mean([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        actual_mean = np.mean(callback.episode_rewards)
        
        assert actual_mean == pytest.approx(expected_mean, abs=0.001)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
