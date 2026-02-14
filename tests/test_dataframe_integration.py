"""
Testes de integração para validar o fluxo completo de dados do DataFrame para o Database.

Inclui testes para:
- Fluxo completo de dados históricos (simulando collector.fetch_historical() -> db.insert_ohlcv())
- Inserção em múltiplos timeframes (D1, H4, H1)
- Validação de todas as 9 colunas obrigatórias (timestamp, symbol, open, high, low, close, volume, quote_volume, trades_count)
- Comportamento com múltiplos símbolos
"""

import pytest
import tempfile
import os
import pandas as pd
from data.database import DatabaseManager


def test_dataframe_to_database_flow():
    """Testa o fluxo completo de DataFrame para Database, como usado em main.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        
        # Simular dados retornados por collector.fetch_historical()
        # Este é o formato exato que o collector retorna
        historical_data = pd.DataFrame([
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
                'timestamp': 1609545600000,
                'symbol': 'BTCUSDT',
                'open': 29200.0,
                'high': 29800.0,
                'low': 28900.0,
                'close': 29600.0,
                'volume': 1200.0,
                'quote_volume': 35520000.0,
                'trades_count': 5800
            },
            {
                'timestamp': 1609632000000,
                'symbol': 'BTCUSDT',
                'open': 29600.0,
                'high': 30000.0,
                'low': 29400.0,
                'close': 29800.0,
                'volume': 1500.0,
                'quote_volume': 44700000.0,
                'trades_count': 6200
            }
        ])
        
        # Simular o código em main.py: collect_historical_data()
        # Linha 59-62: d1_data = collector.fetch_historical(symbol, "1d", 365)
        d1_data = historical_data  # Simula retorno do collector
        
        # Linha 60-62: if d1_data is not None and not d1_data.empty:
        if d1_data is not None and not d1_data.empty:
            # Esta linha deve funcionar agora sem erro de binding
            db.insert_ohlcv("d1", d1_data)
            
        # Verificar inserção
        retrieved_data = db.get_ohlcv("d1", "BTCUSDT")
        assert len(retrieved_data) == 3
        assert retrieved_data[0]['close'] == 29200.0
        assert retrieved_data[1]['close'] == 29600.0
        assert retrieved_data[2]['close'] == 29800.0


def test_multiple_timeframes_dataframe_insert():
    """Testa inserção de DataFrames para múltiplos timeframes (D1, H4, H1)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        
        # Dados D1
        d1_data = pd.DataFrame([
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
        
        # Dados H4
        h4_data = pd.DataFrame([
            {
                'timestamp': 1609459200000,
                'symbol': 'ETHUSDT',
                'open': 730.0,
                'high': 735.0,
                'low': 725.0,
                'close': 732.0,
                'volume': 500.0,
                'quote_volume': 366000.0,
                'trades_count': 750
            },
            {
                'timestamp': 1609473600000,
                'symbol': 'ETHUSDT',
                'open': 732.0,
                'high': 745.0,
                'low': 728.0,
                'close': 740.0,
                'volume': 600.0,
                'quote_volume': 444000.0,
                'trades_count': 800
            }
        ])
        
        # Dados H1
        h1_data = pd.DataFrame([
            {
                'timestamp': 1609459200000,
                'symbol': 'ETHUSDT',
                'open': 730.0,
                'high': 732.0,
                'low': 728.0,
                'close': 731.0,
                'volume': 100.0,
                'quote_volume': 73100.0,
                'trades_count': 150
            }
        ])
        
        # Simular main.py linhas 58-74
        if d1_data is not None and not d1_data.empty:
            db.insert_ohlcv("d1", d1_data)
            
        if h4_data is not None and not h4_data.empty:
            db.insert_ohlcv("h4", h4_data)
            
        if h1_data is not None and not h1_data.empty:
            db.insert_ohlcv("h1", h1_data)
        
        # Verificar inserções
        assert len(db.get_ohlcv("d1", "ETHUSDT")) == 1
        assert len(db.get_ohlcv("h4", "ETHUSDT")) == 2
        assert len(db.get_ohlcv("h1", "ETHUSDT")) == 1


def test_dataframe_with_all_nine_columns():
    """Verifica que todas as 9 colunas necessárias são inseridas corretamente."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        
        # DataFrame com todas as 9 colunas
        df = pd.DataFrame([
            {
                'timestamp': 1609459200000,
                'symbol': 'ADAUSDT',
                'open': 0.18,
                'high': 0.19,
                'low': 0.17,
                'close': 0.185,
                'volume': 10000000.0,
                'quote_volume': 1850000.0,
                'trades_count': 25000
            }
        ])
        
        db.insert_ohlcv("h4", df)
        
        # Recuperar e verificar todas as colunas
        data = db.get_ohlcv("h4", "ADAUSDT")
        assert len(data) == 1
        
        record = data[0]
        assert record['timestamp'] == 1609459200000
        assert record['symbol'] == 'ADAUSDT'
        assert record['open'] == 0.18
        assert record['high'] == 0.19
        assert record['low'] == 0.17
        assert record['close'] == 0.185
        assert record['volume'] == 10000000.0
        assert record['quote_volume'] == 1850000.0
        assert record['trades_count'] == 25000
