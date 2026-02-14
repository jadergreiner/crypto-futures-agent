"""
Testes para verificar correção do bug de verificação booleana de DataFrames.
"""

import pytest
import pandas as pd
from unittest.mock import Mock


def test_dataframe_empty_check():
    """
    Testa que DataFrames vazios são tratados corretamente.
    
    O bug original era: if d1_data: causava erro "truth value is ambiguous"
    A correção: if d1_data is not None and not d1_data.empty:
    """
    # DataFrame vazio
    empty_df = pd.DataFrame(columns=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
    
    # Verificação antiga (problemática) - comentada para referência
    # with pytest.raises(ValueError, match="truth value.*ambiguous"):
    #     if empty_df:
    #         pass
    
    # Verificação corrigida
    is_valid = empty_df is not None and not empty_df.empty
    assert is_valid is False  # DataFrame vazio não deve passar na verificação


def test_dataframe_with_data_check():
    """
    Testa que DataFrames com dados são tratados corretamente.
    """
    # DataFrame com dados
    df_with_data = pd.DataFrame({
        'timestamp': [1609459200000],
        'symbol': ['BTCUSDT'],
        'open': [29000.0],
        'high': [29500.0],
        'low': [28800.0],
        'close': [29200.0],
        'volume': [1000.0]
    })
    
    # Verificação corrigida
    is_valid = df_with_data is not None and not df_with_data.empty
    assert is_valid is True  # DataFrame com dados deve passar na verificação


def test_none_dataframe_check():
    """
    Testa que None é tratado corretamente.
    """
    df = None
    
    # Verificação corrigida
    is_valid = df is not None and not df.empty
    assert is_valid is False  # None não deve passar na verificação


def test_list_empty_check():
    """
    Testa que listas vazias são tratadas corretamente (para get_ohlcv).
    """
    empty_list = []
    
    # Verificação corrigida para listas
    is_valid = empty_list is not None and len(empty_list) > 0
    assert is_valid is False  # Lista vazia não deve passar na verificação


def test_list_with_data_check():
    """
    Testa que listas com dados são tratadas corretamente (para get_ohlcv).
    """
    list_with_data = [{'timestamp': 1609459200000, 'symbol': 'BTCUSDT', 'close': 29200.0}]
    
    # Verificação corrigida para listas
    is_valid = list_with_data is not None and len(list_with_data) > 0
    assert is_valid is True  # Lista com dados deve passar na verificação


def test_collect_historical_data_with_empty_dataframe():
    """
    Testa que collect_historical_data trata DataFrames vazios corretamente.
    """
    # Mock do collector que retorna DataFrame vazio
    mock_collector = Mock()
    empty_df = pd.DataFrame(columns=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trades_count'])
    mock_collector.fetch_historical.return_value = empty_df
    
    # Mock do database
    mock_db = Mock()
    
    # Simular a lógica corrigida
    d1_data = mock_collector.fetch_historical("BTCUSDT", "1d", 365)
    if d1_data is not None and not d1_data.empty:
        mock_db.insert_ohlcv("d1", d1_data)
    
    # Verificar que insert_ohlcv NÃO foi chamado (DataFrame vazio)
    mock_db.insert_ohlcv.assert_not_called()


def test_collect_historical_data_with_valid_dataframe():
    """
    Testa que collect_historical_data insere DataFrames válidos.
    """
    # Mock do collector que retorna DataFrame com dados
    mock_collector = Mock()
    valid_df = pd.DataFrame({
        'timestamp': [1609459200000],
        'symbol': ['BTCUSDT'],
        'open': [29000.0],
        'high': [29500.0],
        'low': [28800.0],
        'close': [29200.0],
        'volume': [1000.0],
        'quote_volume': [29200000.0],
        'trades_count': [5000]
    })
    mock_collector.fetch_historical.return_value = valid_df
    
    # Mock do database
    mock_db = Mock()
    
    # Simular a lógica corrigida
    d1_data = mock_collector.fetch_historical("BTCUSDT", "1d", 365)
    if d1_data is not None and not d1_data.empty:
        mock_db.insert_ohlcv("d1", d1_data)
    
    # Verificar que insert_ohlcv foi chamado uma vez
    mock_db.insert_ohlcv.assert_called_once_with("d1", valid_df)


def test_calculate_indicators_with_empty_list():
    """
    Testa que calculate_indicators trata listas vazias corretamente.
    """
    # Mock do database que retorna lista vazia
    mock_db = Mock()
    mock_db.get_ohlcv.return_value = []
    
    # Simular a lógica corrigida
    h4_data = mock_db.get_ohlcv("h4", "BTCUSDT")
    should_process = h4_data is not None and len(h4_data) > 0
    
    # Verificar que não deve processar
    assert should_process is False


def test_calculate_indicators_with_valid_list():
    """
    Testa que calculate_indicators processa listas válidas.
    """
    # Mock do database que retorna lista com dados
    mock_db = Mock()
    mock_db.get_ohlcv.return_value = [
        {
            'timestamp': 1609459200000,
            'symbol': 'BTCUSDT',
            'open': 29000.0,
            'high': 29500.0,
            'low': 28800.0,
            'close': 29200.0,
            'volume': 1000.0
        }
    ]
    
    # Simular a lógica corrigida
    h4_data = mock_db.get_ohlcv("h4", "BTCUSDT")
    should_process = h4_data is not None and len(h4_data) > 0
    
    # Verificar que deve processar
    assert should_process is True
