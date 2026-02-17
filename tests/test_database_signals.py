"""
Testes unitários para métodos de trade_signals no DatabaseManager.
"""

import pytest
import tempfile
import os
from typing import Dict, Any

from data.database import DatabaseManager


class TestDatabaseSignals:
    """Testes para métodos de Signal-Driven RL no DatabaseManager."""
    
    @pytest.fixture
    def temp_db(self):
        """Cria banco de dados temporário para testes."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        db = DatabaseManager(db_path=path)
        
        yield db
        
        # Cleanup
        try:
            os.unlink(path)
        except:
            pass
    
    @pytest.fixture
    def sample_signal_data(self):
        """Cria dados de sinal de exemplo."""
        return {
            'timestamp': 1000000,
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 50000.0,
            'stop_loss': 49000.0,
            'take_profit_1': 51000.0,
            'take_profit_2': 52000.0,
            'take_profit_3': 53000.0,
            'position_size_suggested': 0.1,
            'risk_pct': 1.0,
            'risk_reward_ratio': 3.0,
            'leverage_suggested': 10,
            'confluence_score': 85.0,
            'confluence_details': '{"ema_alignment": 20, "rsi": 15, "smc": 25, "sentiment": 25}',
            'rsi_14': 55.0,
            'ema_17': 50100.0,
            'ema_34': 49900.0,
            'ema_72': 49800.0,
            'ema_144': 49700.0,
            'macd_line': 50.0,
            'macd_signal': 45.0,
            'macd_histogram': 5.0,
            'bb_upper': 51000.0,
            'bb_lower': 49000.0,
            'bb_percent_b': 0.6,
            'atr_14': 500.0,
            'adx_14': 30.0,
            'di_plus': 25.0,
            'di_minus': 20.0,
            'market_structure': 'bullish',
            'bos_recent': 1,
            'choch_recent': 0,
            'nearest_ob_distance_pct': 2.0,
            'nearest_fvg_distance_pct': 1.5,
            'premium_discount_zone': 'discount',
            'liquidity_above_pct': 3.0,
            'liquidity_below_pct': 1.0,
            'funding_rate': 0.01,
            'long_short_ratio': 1.2,
            'open_interest_change_pct': 5.0,
            'fear_greed_value': 65,
            'd1_bias': 'BULLISH',
            'h4_trend': 'BULLISH',
            'h1_trend': 'BULLISH',
            'market_regime': 'RISK_ON',
            'execution_mode': 'PENDING',
            'executed_at': None,
            'executed_price': None,
            'execution_slippage_pct': None,
            'status': 'ACTIVE'
        }
    
    def test_insert_trade_signal(self, temp_db, sample_signal_data):
        """Testa inserção de sinal de trade."""
        signal_id = temp_db.insert_trade_signal(sample_signal_data)
        
        assert signal_id is not None
        assert signal_id > 0
    
    def test_insert_and_retrieve_signal(self, temp_db, sample_signal_data):
        """Testa inserção e recuperação de sinal."""
        signal_id = temp_db.insert_trade_signal(sample_signal_data)
        
        # Recuperar sinal ativo
        active_signals = temp_db.get_active_signals(symbol='BTCUSDT')
        
        assert len(active_signals) == 1
        assert active_signals[0]['id'] == signal_id
        assert active_signals[0]['symbol'] == 'BTCUSDT'
        assert active_signals[0]['direction'] == 'LONG'
        assert active_signals[0]['entry_price'] == 50000.0
    
    def test_update_signal_execution(self, temp_db, sample_signal_data):
        """Testa atualização de execução de sinal."""
        signal_id = temp_db.insert_trade_signal(sample_signal_data)
        
        # Atualizar execução
        temp_db.update_signal_execution(
            signal_id=signal_id,
            executed_at=1001000,
            executed_price=50100.0,
            execution_mode='AUTOTRADE',
            execution_slippage_pct=0.2
        )
        
        # Recuperar e verificar
        signals = temp_db.get_active_signals(symbol='BTCUSDT')
        assert len(signals) == 1
        assert signals[0]['executed_at'] == 1001000
        assert signals[0]['executed_price'] == 50100.0
        assert signals[0]['execution_mode'] == 'AUTOTRADE'
        assert signals[0]['execution_slippage_pct'] == 0.2
    
    def test_update_signal_outcome(self, temp_db, sample_signal_data):
        """Testa atualização de resultado de sinal."""
        signal_id = temp_db.insert_trade_signal(sample_signal_data)
        
        # Atualizar outcome
        outcome_data = {
            'status': 'CLOSED',
            'exit_price': 51500.0,
            'exit_timestamp': 1010000,
            'exit_reason': 'take_profit_1',
            'pnl_usdt': 150.0,
            'pnl_pct': 3.0,
            'r_multiple': 1.5,
            'max_favorable_excursion_pct': 3.5,
            'max_adverse_excursion_pct': -0.5,
            'duration_minutes': 150,
            'reward_calculated': 2.5,
            'outcome_label': 'win'
        }
        
        temp_db.update_signal_outcome(signal_id=signal_id, outcome_data=outcome_data)
        
        # Verificar que sinal não está mais ativo
        active_signals = temp_db.get_active_signals(symbol='BTCUSDT')
        assert len(active_signals) == 0
        
        # Verificar que está disponível para training
        training_signals = temp_db.get_signals_for_training(symbol='BTCUSDT')
        assert len(training_signals) == 1
        assert training_signals[0]['outcome_label'] == 'win'
        assert training_signals[0]['pnl_pct'] == 3.0
        assert training_signals[0]['r_multiple'] == 1.5
    
    def test_get_active_signals_multiple(self, temp_db, sample_signal_data):
        """Testa recuperação de múltiplos sinais ativos."""
        # Inserir 3 sinais
        signal_ids = []
        for i in range(3):
            data = sample_signal_data.copy()
            data['timestamp'] = 1000000 + i * 1000
            data['entry_price'] = 50000.0 + i * 100
            signal_id = temp_db.insert_trade_signal(data)
            signal_ids.append(signal_id)
        
        # Recuperar todos
        active_signals = temp_db.get_active_signals()
        assert len(active_signals) == 3
        
        # Fechar um sinal
        temp_db.update_signal_outcome(
            signal_id=signal_ids[0],
            outcome_data={
                'status': 'CLOSED',
                'exit_price': 51000.0,
                'exit_timestamp': 2000000,
                'exit_reason': 'take_profit_1',
                'pnl_usdt': 100.0,
                'pnl_pct': 2.0,
                'r_multiple': 1.0,
                'max_favorable_excursion_pct': 2.0,
                'max_adverse_excursion_pct': -0.3,
                'duration_minutes': 60,
                'reward_calculated': 1.5,
                'outcome_label': 'win'
            }
        )
        
        # Deve ter apenas 2 ativos
        active_signals = temp_db.get_active_signals()
        assert len(active_signals) == 2
    
    def test_get_active_signals_by_symbol(self, temp_db, sample_signal_data):
        """Testa filtro por símbolo nos sinais ativos."""
        # Inserir sinais de diferentes símbolos
        data_btc = sample_signal_data.copy()
        data_btc['symbol'] = 'BTCUSDT'
        temp_db.insert_trade_signal(data_btc)
        
        data_eth = sample_signal_data.copy()
        data_eth['symbol'] = 'ETHUSDT'
        data_eth['entry_price'] = 3000.0
        temp_db.insert_trade_signal(data_eth)
        
        # Filtrar por BTC
        btc_signals = temp_db.get_active_signals(symbol='BTCUSDT')
        assert len(btc_signals) == 1
        assert btc_signals[0]['symbol'] == 'BTCUSDT'
        
        # Filtrar por ETH
        eth_signals = temp_db.get_active_signals(symbol='ETHUSDT')
        assert len(eth_signals) == 1
        assert eth_signals[0]['symbol'] == 'ETHUSDT'
    
    def test_get_signals_for_training(self, temp_db, sample_signal_data):
        """Testa recuperação de sinais para treino."""
        # Inserir sinais com e sem outcome
        # Sinal 1: com outcome
        signal_id_1 = temp_db.insert_trade_signal(sample_signal_data)
        temp_db.update_signal_outcome(
            signal_id=signal_id_1,
            outcome_data={
                'status': 'CLOSED',
                'exit_price': 51000.0,
                'exit_timestamp': 2000000,
                'exit_reason': 'take_profit_1',
                'pnl_usdt': 100.0,
                'pnl_pct': 2.0,
                'r_multiple': 1.0,
                'max_favorable_excursion_pct': 2.0,
                'max_adverse_excursion_pct': -0.3,
                'duration_minutes': 60,
                'reward_calculated': 1.5,
                'outcome_label': 'win'
            }
        )
        
        # Sinal 2: sem outcome (ainda ativo)
        data_2 = sample_signal_data.copy()
        data_2['timestamp'] = 2000000
        temp_db.insert_trade_signal(data_2)
        
        # Sinal 3: com outcome
        data_3 = sample_signal_data.copy()
        data_3['timestamp'] = 3000000
        signal_id_3 = temp_db.insert_trade_signal(data_3)
        temp_db.update_signal_outcome(
            signal_id=signal_id_3,
            outcome_data={
                'status': 'CLOSED',
                'exit_price': 49500.0,
                'exit_timestamp': 3010000,
                'exit_reason': 'stop_loss',
                'pnl_usdt': -50.0,
                'pnl_pct': -1.0,
                'r_multiple': -0.5,
                'max_favorable_excursion_pct': 0.5,
                'max_adverse_excursion_pct': -1.0,
                'duration_minutes': 60,
                'reward_calculated': -0.5,
                'outcome_label': 'loss'
            }
        )
        
        # Recuperar apenas com outcome
        training_signals = temp_db.get_signals_for_training()
        assert len(training_signals) == 2
        assert all(s['outcome_label'] is not None for s in training_signals)
    
    def test_insert_signal_evolution(self, temp_db, sample_signal_data):
        """Testa inserção de evolução de sinal."""
        signal_id = temp_db.insert_trade_signal(sample_signal_data)
        
        evolution_data = {
            'signal_id': signal_id,
            'timestamp': 1000900,
            'current_price': 50500.0,
            'unrealized_pnl_pct': 1.0,
            'distance_to_stop_pct': -2.0,
            'distance_to_tp1_pct': 1.0,
            'rsi_14': 56.0,
            'macd_histogram': 6.0,
            'bb_percent_b': 0.65,
            'atr_14': 510.0,
            'adx_14': 32.0,
            'market_structure': 'bullish',
            'funding_rate': 0.01,
            'long_short_ratio': 1.25,
            'mfe_pct': 1.0,
            'mae_pct': -0.2,
            'event_type': None,
            'event_details': None
        }
        
        evolution_id = temp_db.insert_signal_evolution(evolution_data)
        
        assert evolution_id is not None
        assert evolution_id > 0
    
    def test_get_signal_evolution(self, temp_db, sample_signal_data):
        """Testa recuperação de evoluções de um sinal."""
        signal_id = temp_db.insert_trade_signal(sample_signal_data)
        
        # Inserir 3 evoluções
        for i in range(3):
            evolution_data = {
                'signal_id': signal_id,
                'timestamp': 1000900 + i * 900000,
                'current_price': 50500.0 + i * 100,
                'unrealized_pnl_pct': 1.0 + i * 0.5,
                'distance_to_stop_pct': -2.0,
                'distance_to_tp1_pct': 1.0 - i * 0.3,
                'rsi_14': 56.0 + i,
                'macd_histogram': 6.0,
                'bb_percent_b': 0.65,
                'atr_14': 510.0,
                'adx_14': 32.0,
                'market_structure': 'bullish',
                'funding_rate': 0.01,
                'long_short_ratio': 1.25,
                'mfe_pct': 1.0 + i * 0.5,
                'mae_pct': -0.2,
                'event_type': 'PARTIAL_1' if i == 1 else None,
                'event_details': None
            }
            temp_db.insert_signal_evolution(evolution_data)
        
        # Recuperar evoluções
        evolutions = temp_db.get_signal_evolution(signal_id)
        
        assert len(evolutions) == 3
        assert evolutions[0]['current_price'] == 50500.0
        assert evolutions[1]['current_price'] == 50600.0
        assert evolutions[2]['current_price'] == 50700.0
        
        # Verificar que está ordenado por timestamp
        assert evolutions[0]['timestamp'] < evolutions[1]['timestamp']
        assert evolutions[1]['timestamp'] < evolutions[2]['timestamp']
        
        # Verificar evento
        assert evolutions[1]['event_type'] == 'PARTIAL_1'
    
    def test_complete_signal_lifecycle(self, temp_db, sample_signal_data):
        """Testa ciclo de vida completo de um sinal."""
        # 1. Inserir sinal
        signal_id = temp_db.insert_trade_signal(sample_signal_data)
        assert signal_id > 0
        
        # 2. Atualizar execução
        temp_db.update_signal_execution(
            signal_id=signal_id,
            executed_at=1001000,
            executed_price=50100.0,
            execution_mode='AUTOTRADE',
            execution_slippage_pct=0.2
        )
        
        # 3. Inserir evoluções
        for i in range(5):
            evolution_data = {
                'signal_id': signal_id,
                'timestamp': 1001900 + i * 900000,
                'current_price': 50200.0 + i * 200,
                'unrealized_pnl_pct': 0.5 + i * 0.5,
                'distance_to_stop_pct': -2.0,
                'distance_to_tp1_pct': 1.8 - i * 0.3,
                'rsi_14': 55.0,
                'macd_histogram': 5.0,
                'bb_percent_b': 0.6,
                'atr_14': 500.0,
                'adx_14': 30.0,
                'market_structure': 'bullish',
                'funding_rate': 0.01,
                'long_short_ratio': 1.2,
                'mfe_pct': 0.5 + i * 0.5,
                'mae_pct': -0.3,
                'event_type': None,
                'event_details': None
            }
            temp_db.insert_signal_evolution(evolution_data)
        
        # 4. Finalizar sinal
        outcome_data = {
            'status': 'CLOSED',
            'exit_price': 51500.0,
            'exit_timestamp': 1010000,
            'exit_reason': 'take_profit_1',
            'pnl_usdt': 150.0,
            'pnl_pct': 3.0,
            'r_multiple': 1.5,
            'max_favorable_excursion_pct': 3.0,
            'max_adverse_excursion_pct': -0.3,
            'duration_minutes': 150,
            'reward_calculated': 2.5,
            'outcome_label': 'win'
        }
        temp_db.update_signal_outcome(signal_id=signal_id, outcome_data=outcome_data)
        
        # Verificar que tudo foi persistido corretamente
        training_signals = temp_db.get_signals_for_training(symbol='BTCUSDT')
        assert len(training_signals) == 1
        
        signal = training_signals[0]
        assert signal['executed_price'] == 50100.0
        assert signal['outcome_label'] == 'win'
        assert signal['pnl_pct'] == 3.0
        
        evolutions = temp_db.get_signal_evolution(signal_id)
        assert len(evolutions) == 5
