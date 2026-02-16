"""
Testes para o rastreamento de flat_steps no CryptoFuturesEnv.
"""

import pytest
import numpy as np
import pandas as pd
from typing import Dict

from agent.environment import CryptoFuturesEnv


class TestFlatStepsTracking:
    """Testes para rastreamento de inatividade (flat_steps) no environment."""
    
    @pytest.fixture
    def mock_data(self):
        """Cria dados mock para o environment."""
        # Criar dados H4 simples
        h4_data = pd.DataFrame({
            'open': np.random.uniform(40000, 41000, 100),
            'high': np.random.uniform(41000, 42000, 100),
            'low': np.random.uniform(39000, 40000, 100),
            'close': np.random.uniform(40000, 41000, 100),
            'volume': np.random.uniform(1000, 2000, 100),
            'atr_14': np.random.uniform(500, 800, 100),
        })
        
        # Dados H1 e D1 vazios (não necessários para estes testes)
        h1_data = pd.DataFrame()
        d1_data = pd.DataFrame()
        
        return {
            'h1': h1_data,
            'h4': h4_data,
            'd1': d1_data,
            'symbol': 'BTCUSDT'
        }
    
    @pytest.fixture
    def env(self, mock_data):
        """Cria uma instância do environment."""
        return CryptoFuturesEnv(
            data=mock_data,
            initial_capital=10000,
            episode_length=50
        )
    
    def test_flat_steps_initialized_to_zero(self, env):
        """Testa que flat_steps é inicializado em 0."""
        assert hasattr(env, 'flat_steps'), "Environment deve ter atributo flat_steps"
        assert env.flat_steps == 0, f"flat_steps deve ser inicializado em 0, é {env.flat_steps}"
    
    def test_flat_steps_reset_to_zero_on_reset(self, env):
        """Testa que flat_steps é resetado para 0 no reset()."""
        # Simular alguma inatividade
        env.flat_steps = 15
        
        # Resetar environment
        obs, info = env.reset()
        
        # flat_steps deve ter sido resetado
        assert env.flat_steps == 0, f"flat_steps deve ser 0 após reset, é {env.flat_steps}"
    
    def test_flat_steps_increments_when_no_position(self, env):
        """Testa que flat_steps incrementa quando não há posição."""
        env.reset()
        initial_flat_steps = env.flat_steps
        
        # Executar ação HOLD sem posição
        obs, reward, terminated, truncated, info = env.step(0)  # HOLD
        
        # flat_steps deve ter incrementado
        assert env.flat_steps == initial_flat_steps + 1, \
            f"flat_steps deve ter incrementado de {initial_flat_steps} para {initial_flat_steps + 1}"
    
    def test_flat_steps_increments_multiple_holds(self, env):
        """Testa que flat_steps incrementa em múltiplos HOLDs consecutivos."""
        env.reset()
        
        # Executar vários HOLDs
        for i in range(5):
            env.step(0)  # HOLD
        
        # flat_steps deve ser 5
        assert env.flat_steps == 5, f"flat_steps deve ser 5 após 5 HOLDs, é {env.flat_steps}"
    
    def test_flat_steps_resets_when_position_opened_long(self, env):
        """Testa que flat_steps reseta quando uma posição LONG é aberta."""
        env.reset()
        
        # Incrementar flat_steps com alguns HOLDs
        for i in range(10):
            env.step(0)  # HOLD
        
        assert env.flat_steps == 10, "flat_steps deve ser 10 antes de abrir posição"
        
        # Tentar abrir posição LONG
        obs, reward, terminated, truncated, info = env.step(1)  # OPEN_LONG
        
        # Se a posição foi aberta com sucesso, flat_steps deve resetar
        if env.position is not None:
            assert env.flat_steps == 0, f"flat_steps deve resetar para 0 ao abrir posição, é {env.flat_steps}"
    
    def test_flat_steps_resets_when_position_opened_short(self, env):
        """Testa que flat_steps reseta quando uma posição SHORT é aberta."""
        env.reset()
        
        # Incrementar flat_steps
        for i in range(8):
            env.step(0)  # HOLD
        
        assert env.flat_steps == 8, "flat_steps deve ser 8 antes de abrir posição"
        
        # Tentar abrir posição SHORT
        obs, reward, terminated, truncated, info = env.step(2)  # OPEN_SHORT
        
        # Se a posição foi aberta com sucesso, flat_steps deve resetar
        if env.position is not None:
            assert env.flat_steps == 0, f"flat_steps deve resetar para 0 ao abrir posição, é {env.flat_steps}"
    
    def test_flat_steps_not_incremented_when_position_exists(self, env):
        """Testa que flat_steps não incrementa quando há posição aberta."""
        env.reset()
        
        # Abrir posição
        env.step(1)  # OPEN_LONG
        
        if env.position is not None:
            initial_flat_steps = env.flat_steps  # Deve ser 0
            
            # Executar HOLD com posição aberta
            env.step(0)  # HOLD
            
            # flat_steps não deve ter incrementado
            assert env.flat_steps == initial_flat_steps, \
                f"flat_steps não deve incrementar com posição aberta"
    
    def test_flat_steps_resumes_after_position_closes(self, env):
        """Testa que flat_steps volta a incrementar após fechar posição."""
        env.reset()
        
        # Abrir posição
        env.step(1)  # OPEN_LONG
        
        if env.position is not None:
            # Fechar posição - flat_steps deve incrementar (=1) porque posição foi fechada
            env.step(3)  # CLOSE
            assert env.flat_steps == 1, f"flat_steps deve ser 1 após fechar posição, é {env.flat_steps}"
            
            # Agora flat_steps deve continuar incrementando
            env.step(0)  # HOLD
            assert env.flat_steps == 2, f"flat_steps deve ser 2, é {env.flat_steps}"
            
            env.step(0)  # HOLD
            assert env.flat_steps == 3, f"flat_steps deve ser 3, é {env.flat_steps}"
    
    def test_flat_steps_in_position_state_when_no_position(self, env):
        """Testa que flat_steps é incluído no position_state quando não há posição."""
        env.reset()
        
        # Incrementar flat_steps
        for i in range(12):
            env.step(0)  # HOLD
        
        # Obter position_state
        position_state = env._get_position_state()
        
        # Verificar que flat_steps está presente
        assert 'flat_steps' in position_state, "flat_steps deve estar em position_state"
        assert position_state['flat_steps'] == 12, \
            f"flat_steps em position_state deve ser 12, é {position_state['flat_steps']}"
        assert position_state['has_position'] == False, "has_position deve ser False"
    
    def test_flat_steps_not_in_position_state_when_has_position(self, env):
        """Testa position_state quando há posição aberta (flat_steps não é relevante)."""
        env.reset()
        
        # Abrir posição
        env.step(1)  # OPEN_LONG
        
        if env.position is not None:
            # Obter position_state
            position_state = env._get_position_state()
            
            # Verificar estrutura do position_state com posição
            assert position_state['has_position'] == True, "has_position deve ser True"
            assert 'pnl_pct' in position_state, "pnl_pct deve estar presente"
            assert 'direction' in position_state, "direction deve estar presente"
    
    def test_flat_steps_scenario_inactive_then_trade(self, env):
        """Testa cenário completo: inatividade → trade → inatividade novamente."""
        env.reset()
        
        # Fase 1: Inatividade inicial (15 steps)
        for i in range(15):
            env.step(0)  # HOLD
        assert env.flat_steps == 15, "Fase 1: flat_steps deve ser 15"
        
        # Fase 2: Abrir posição
        env.step(1)  # OPEN_LONG
        if env.position is not None:
            assert env.flat_steps == 0, "Fase 2: flat_steps deve resetar ao abrir posição"
            
            # Fase 3: Manter posição (flat_steps não deve incrementar enquanto posição existe)
            for i in range(5):
                env.step(0)  # HOLD com posição
                # Se posição ainda existe, flat_steps deve permanecer 0
                if env.position is not None:
                    assert env.flat_steps == 0, f"Fase 3: flat_steps deve permanecer 0 com posição no step {i}"
            
            # Fase 4: Se posição ainda existe, fechar explicitamente
            if env.position is not None:
                env.step(3)  # CLOSE
                assert env.flat_steps == 1, "Fase 4: flat_steps deve ser 1 após fechar"
            
            # Fase 5: Nova inatividade (deve continuar incrementando)
            initial_flat_steps = env.flat_steps
            for i in range(8):
                env.step(0)  # HOLD
            expected_flat_steps = initial_flat_steps + 8
            assert env.flat_steps == expected_flat_steps, \
                f"Fase 5: flat_steps deve ser {expected_flat_steps}, é {env.flat_steps}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
