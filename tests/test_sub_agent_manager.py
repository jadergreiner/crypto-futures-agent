"""
Testes unitários para SubAgentManager.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

from agent.sub_agent_manager import SubAgentManager


class TestSubAgentManager:
    """Testes para a classe SubAgentManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Cria diretório temporário para testes."""
        temp = tempfile.mkdtemp()
        yield temp
        # Cleanup
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Cria uma instância de SubAgentManager com diretório temporário."""
        return SubAgentManager(base_dir=temp_dir)
    
    @pytest.fixture
    def sample_signals(self):
        """Cria sinais de exemplo para testes."""
        signals = []
        for i in range(25):  # 25 sinais para ultrapassar MIN_TRADES_FOR_TRAINING
            signals.append({
                'id': i + 1,
                'timestamp': 1000000 + i * 1000,
                'symbol': 'BTCUSDT',
                'direction': 'LONG' if i % 2 == 0 else 'SHORT',
                'entry_price': 50000.0 + i * 100,
                'stop_loss': 49000.0 + i * 100,
                'take_profit_1': 51000.0 + i * 100,
                'pnl_pct': 2.0 if i % 3 != 0 else -1.0,
                'r_multiple': 2.0 if i % 3 != 0 else -1.0,
                'outcome_label': 'win' if i % 3 != 0 else 'loss'
            })
        return signals
    
    @pytest.fixture
    def sample_evolutions(self, sample_signals):
        """Cria evoluções de exemplo para os sinais."""
        evolutions = {}
        for signal in sample_signals:
            signal_id = signal['id']
            evolutions[signal_id] = [
                {
                    'signal_id': signal_id,
                    'timestamp': signal['timestamp'] + 900000,
                    'current_price': signal['entry_price'] * 1.01,
                    'unrealized_pnl_pct': 1.0,
                    'rsi_14': 55.0,
                    'event_type': None
                },
                {
                    'signal_id': signal_id,
                    'timestamp': signal['timestamp'] + 1800000,
                    'current_price': signal['entry_price'] * 1.02,
                    'unrealized_pnl_pct': 2.0,
                    'rsi_14': 60.0,
                    'event_type': None
                }
            ]
        return evolutions
    
    def test_init(self, manager, temp_dir):
        """Testa inicialização do gerenciador."""
        assert manager is not None
        assert manager.base_dir == Path(temp_dir)
        assert isinstance(manager.agents, dict)
        assert isinstance(manager.agent_stats, dict)
    
    def test_get_or_create_agent_new(self, manager):
        """Testa criação de novo sub-agente."""
        symbol = 'BTCUSDT'
        
        assert symbol not in manager.agents
        
        agent = manager.get_or_create_agent(symbol)
        
        assert agent is not None
        assert symbol in manager.agents
        assert symbol in manager.agent_stats
        assert manager.agent_stats[symbol]['trades_trained'] == 0
    
    def test_get_or_create_agent_existing(self, manager):
        """Testa recuperação de sub-agente existente."""
        symbol = 'ETHUSDT'
        
        # Criar agente
        agent1 = manager.get_or_create_agent(symbol)
        
        # Recuperar mesmo agente
        agent2 = manager.get_or_create_agent(symbol)
        
        assert agent1 is agent2
    
    def test_train_agent_insufficient_signals(self, manager):
        """Testa treino com sinais insuficientes."""
        symbol = 'BTCUSDT'
        
        # Apenas 10 sinais (menos que MIN_TRADES_FOR_TRAINING=20)
        signals = [
            {
                'id': i,
                'timestamp': 1000 + i,
                'symbol': symbol,
                'direction': 'LONG',
                'entry_price': 50000.0,
                'outcome_label': 'win'
            }
            for i in range(10)
        ]
        
        evolutions = {i: [] for i in range(10)}
        
        result = manager.train_agent(symbol, signals, evolutions)
        
        assert result['success'] is False
        assert result['reason'] == 'insufficient_trades'
        assert result['trades_available'] == 10
    
    def test_train_agent_success(self, manager, sample_signals, sample_evolutions):
        """Testa treino bem-sucedido de sub-agente."""
        symbol = 'BTCUSDT'
        
        result = manager.train_agent(
            symbol=symbol,
            signals=sample_signals,
            evolutions=sample_evolutions,
            total_timesteps=1000  # Poucos timesteps para teste rápido
        )
        
        assert result['success'] is True
        assert result['trades_trained'] == len(sample_signals)
        assert 'win_rate' in result
        assert 'avg_r_multiple' in result
        
        # Verificar que stats foram atualizados
        assert manager.agent_stats[symbol]['trades_trained'] == len(sample_signals)
        assert manager.agent_stats[symbol]['total_steps'] >= 1000
    
    def test_get_agent_stats_existing(self, manager, sample_signals, sample_evolutions):
        """Testa recuperação de stats de agente existente."""
        symbol = 'BTCUSDT'
        
        # Treinar agente
        manager.train_agent(
            symbol=symbol,
            signals=sample_signals,
            evolutions=sample_evolutions,
            total_timesteps=500
        )
        
        stats = manager.get_agent_stats(symbol)
        
        assert stats['exists'] is True
        assert stats['trades_trained'] > 0
        assert 'win_rate' in stats
        assert 'avg_r_multiple' in stats
    
    def test_get_agent_stats_non_existing(self, manager):
        """Testa recuperação de stats de agente não existente."""
        symbol = 'NONEXISTENT'
        
        stats = manager.get_agent_stats(symbol)
        
        assert stats['exists'] is False
        assert stats['trades_trained'] == 0
        assert stats['win_rate'] == 0.0
    
    def test_save_and_load_all(self, manager, sample_signals, sample_evolutions):
        """Testa salvamento e carregamento de sub-agentes."""
        symbol = 'BTCUSDT'
        
        # Treinar agente
        manager.train_agent(
            symbol=symbol,
            signals=sample_signals,
            evolutions=sample_evolutions,
            total_timesteps=500
        )
        
        # Salvar
        manager.save_all()
        
        # Verificar que arquivos foram criados
        model_path = manager.base_dir / f"{symbol}_ppo.zip"
        stats_path = manager.base_dir / f"{symbol}_stats.json"
        
        assert model_path.exists()
        assert stats_path.exists()
        
        # Criar novo gerenciador e carregar
        new_manager = SubAgentManager(base_dir=str(manager.base_dir))
        
        # Verificar que agente foi carregado
        assert symbol in new_manager.agents
        assert symbol in new_manager.agent_stats
        assert new_manager.agent_stats[symbol]['trades_trained'] > 0
    
    def test_evaluate_signal_quality_no_agent(self, manager):
        """Testa avaliação de qualidade sem agente existente."""
        symbol = 'NONEXISTENT'
        context = {'rsi_14': 50.0}
        
        score = manager.evaluate_signal_quality(symbol, context)
        
        # Deve retornar score neutro
        assert score == 0.5
    
    def test_evaluate_signal_quality_with_agent(self, manager, sample_signals, sample_evolutions):
        """Testa avaliação de qualidade com agente treinado."""
        symbol = 'BTCUSDT'
        
        # Treinar agente
        manager.train_agent(
            symbol=symbol,
            signals=sample_signals,
            evolutions=sample_evolutions,
            total_timesteps=500
        )
        
        # Avaliar novo sinal
        context = {
            'rsi_14': 55.0,
            'macd_histogram': 0.1,
            'bb_percent_b': 0.6,
            'atr_14': 1.0,
            'adx_14': 30.0,
            'funding_rate': 0.01,
            'long_short_ratio': 1.2
        }
        
        score = manager.evaluate_signal_quality(symbol, context)
        
        # Deve retornar um score entre 0 e 1
        assert 0.0 <= score <= 1.0
    
    def test_multiple_symbols(self, manager, sample_signals, sample_evolutions):
        """Testa gerenciamento de múltiplos símbolos."""
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        for symbol in symbols:
            # Criar sinais para cada símbolo
            symbol_signals = [
                {**s, 'symbol': symbol}
                for s in sample_signals
            ]
            
            # Treinar
            manager.train_agent(
                symbol=symbol,
                signals=symbol_signals,
                evolutions=sample_evolutions,
                total_timesteps=500
            )
        
        # Verificar que todos foram criados
        for symbol in symbols:
            assert symbol in manager.agents
            assert symbol in manager.agent_stats
        
        # Salvar todos
        manager.save_all()
        
        # Verificar arquivos
        for symbol in symbols:
            model_path = manager.base_dir / f"{symbol}_ppo.zip"
            assert model_path.exists()
    
    def test_build_observation_from_context(self, manager):
        """Testa construção de observação a partir de contexto."""
        context = {
            'unrealized_pnl_pct': 1.5,
            'distance_to_stop_pct': -2.0,
            'distance_to_tp1_pct': 1.0,
            'rsi_14': 60.0,
            'macd_histogram': 0.2,
            'bb_percent_b': 0.7,
            'atr_14': 1.5,
            'adx_14': 35.0,
            'funding_rate': 0.01,
            'long_short_ratio': 1.3
        }
        
        obs = manager._build_observation_from_context(context)
        
        # Deve ter 20 features
        assert len(obs) == 20
        
        # Deve ser numpy array
        import numpy as np
        assert isinstance(obs, np.ndarray)
    
    def test_normalize_value_to_score(self, manager):
        """Testa normalização de value para score."""
        # Valores extremos
        assert manager._normalize_value_to_score(-5.0) == 0.0
        assert manager._normalize_value_to_score(5.0) == 1.0
        
        # Valor médio
        score = manager._normalize_value_to_score(0.0)
        assert 0.4 <= score <= 0.6  # Próximo a 0.5
        
        # Valores fora da faixa devem ser clipped
        assert manager._normalize_value_to_score(-10.0) == 0.0
        assert manager._normalize_value_to_score(10.0) == 1.0
