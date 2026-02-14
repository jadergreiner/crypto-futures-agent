"""
Testes para database manager.
"""

import pytest
import tempfile
import os
import pandas as pd
from data.database import DatabaseManager


def test_database_initialization():
    """Testa inicialização do database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        assert os.path.exists(db_path)


def test_insert_ohlcv():
    """Testa inserção de dados OHLCV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        
        test_data = [{
            'timestamp': 1609459200000,
            'symbol': 'BTCUSDT',
            'open': 29000.0,
            'high': 29500.0,
            'low': 28800.0,
            'close': 29200.0,
            'volume': 1000.0,
            'quote_volume': 29200000.0,
            'trades_count': 5000
        }]
        
        db.insert_ohlcv("h4", test_data)
        
        # Recuperar dados
        data = db.get_ohlcv("h4", "BTCUSDT")
        assert len(data) == 1
        assert data[0]['close'] == 29200.0


def test_insert_indicators():
    """Testa inserção de indicadores."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        
        test_data = [{
            'timestamp': 1609459200000,
            'symbol': 'BTCUSDT',
            'timeframe': 'H4',
            'ema_17': 29000.0,
            'ema_34': 28900.0,
            'ema_72': 28800.0,
            'ema_144': 28700.0,
            'ema_305': 28600.0,
            'ema_610': 28500.0,
            'rsi_14': 55.0,
            'macd_line': 100.0,
            'macd_signal': 90.0,
            'macd_histogram': 10.0,
            'bb_upper': 30000.0,
            'bb_middle': 29000.0,
            'bb_lower': 28000.0,
            'bb_bandwidth': 0.068,
            'bb_percent_b': 0.5,
            'vp_poc': 29100.0,
            'vp_vah': 29500.0,
            'vp_val': 28700.0,
            'obv': 1000000.0,
            'atr_14': 500.0,
            'adx_14': 25.0,
            'di_plus': 20.0,
            'di_minus': 18.0
        }]
        
        db.insert_indicators(test_data)
        
        # Recuperar dados
        data = db.get_indicators("BTCUSDT", "H4")
        assert len(data) == 1
        assert data[0]['rsi_14'] == 55.0


def test_insert_ohlcv_with_dataframe():
    """Testa inserção de dados OHLCV usando DataFrame."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        
        # Criar DataFrame de teste com todas as 9 colunas necessárias
        test_df = pd.DataFrame([
            {
                'timestamp': 1609459200000,
                'symbol': 'BTCUSDT',
                'open': 29000.0,
                'high': 29500.0,
                'low': 28800.0,
                'close': 29200.0,
                'volume': 1000.0,
                'quote_volume': 29200000.0,
                'trades_count': 5000
            },
            {
                'timestamp': 1609459260000,
                'symbol': 'BTCUSDT',
                'open': 29200.0,
                'high': 29600.0,
                'low': 28900.0,
                'close': 29400.0,
                'volume': 1100.0,
                'quote_volume': 32340000.0,
                'trades_count': 5500
            }
        ])
        
        # Inserir DataFrame
        db.insert_ohlcv("h4", test_df)
        
        # Recuperar dados
        data = db.get_ohlcv("h4", "BTCUSDT")
        assert len(data) == 2
        assert data[0]['close'] == 29200.0
        assert data[1]['close'] == 29400.0


def test_insert_ohlcv_with_empty_dataframe():
    """Testa inserção de DataFrame vazio (não deve causar erro)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        
        # DataFrame vazio com colunas corretas
        empty_df = pd.DataFrame(columns=[
            'timestamp', 'symbol', 'open', 'high', 'low', 'close',
            'volume', 'quote_volume', 'trades_count'
        ])
        
        # Não deve causar erro
        db.insert_ohlcv("h4", empty_df)
        
        # Verificar que nenhum dado foi inserido
        data = db.get_ohlcv("h4", "BTCUSDT")
        assert len(data) == 0


def test_insert_ohlcv_with_multiple_symbols():
    """Testa inserção de dados OHLCV para múltiplos símbolos usando DataFrame."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        
        # DataFrame com múltiplos símbolos
        test_df = pd.DataFrame([
            {
                'timestamp': 1609459200000,
                'symbol': 'BTCUSDT',
                'open': 29000.0,
                'high': 29500.0,
                'low': 28800.0,
                'close': 29200.0,
                'volume': 1000.0,
                'quote_volume': 29200000.0,
                'trades_count': 5000
            },
            {
                'timestamp': 1609459200000,
                'symbol': 'ETHUSDT',
                'open': 730.0,
                'high': 750.0,
                'low': 720.0,
                'close': 740.0,
                'volume': 2000.0,
                'quote_volume': 1480000.0,
                'trades_count': 3000
            }
        ])
        
        db.insert_ohlcv("d1", test_df)
        
        # Verificar cada símbolo
        btc_data = db.get_ohlcv("d1", "BTCUSDT")
        eth_data = db.get_ohlcv("d1", "ETHUSDT")
        
        assert len(btc_data) == 1
        assert btc_data[0]['close'] == 29200.0
        assert len(eth_data) == 1
        assert eth_data[0]['close'] == 740.0
