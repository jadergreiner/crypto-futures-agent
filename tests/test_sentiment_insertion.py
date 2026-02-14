"""
Testes para inserção de dados de sentimento do mercado.
Valida que campos ausentes são preenchidos com None corretamente.
"""

import pytest
from data.database import DatabaseManager


def test_insert_sentiment_com_campos_completos(tmp_path):
    """Testa inserção de sentimento com todos os campos preenchidos."""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    
    # Dados completos
    dados_completos = [{
        'timestamp': 1707952800000,
        'symbol': 'BTCUSDT',
        'long_short_ratio': 1.5,
        'open_interest': 1000000.0,
        'open_interest_change_pct': 5.2,
        'funding_rate': 0.0001,
        'liquidations_long_vol': 50000.0,
        'liquidations_short_vol': 30000.0,
        'liquidations_total_vol': 80000.0,
    }]
    
    # Deve inserir sem erros
    db.insert_sentiment(dados_completos)
    
    # Verificar inserção
    result = db.get_sentiment('BTCUSDT')
    assert len(result) == 1
    assert result[0]['symbol'] == 'BTCUSDT'
    assert result[0]['long_short_ratio'] == 1.5


def test_insert_sentiment_com_campos_ausentes(tmp_path):
    """Testa inserção de sentimento com campos ausentes (API real)."""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    
    # Dados retornados pelo SentimentCollector.fetch_all_sentiment()
    # Faltam: open_interest_change_pct, liquidations_long_vol, liquidations_short_vol, liquidations_total_vol
    dados_api = [{
        'timestamp': 1707952800000,
        'symbol': 'BTCUSDT',
        'long_short_ratio': 1.5,
        'long_account': 0.6,
        'short_account': 0.4,
        'top_long_short_ratio': 1.8,
        'top_long_account': 0.65,
        'top_short_account': 0.35,
        'open_interest': 1000000.0,
        'funding_rate': 0.0001,
        'funding_time': 1707952800000,
        'buy_sell_ratio': 1.2,
        'buy_vol': 600000.0,
        'sell_vol': 500000.0,
    }]
    
    # Deve inserir sem erros, preenchendo campos ausentes com None
    db.insert_sentiment(dados_api)
    
    # Verificar inserção
    result = db.get_sentiment('BTCUSDT')
    assert len(result) == 1
    assert result[0]['symbol'] == 'BTCUSDT'
    assert result[0]['long_short_ratio'] == 1.5
    assert result[0]['open_interest'] == 1000000.0
    assert result[0]['funding_rate'] == 0.0001
    # Campos ausentes devem ser None
    assert result[0]['open_interest_change_pct'] is None
    assert result[0]['liquidations_long_vol'] is None
    assert result[0]['liquidations_short_vol'] is None
    assert result[0]['liquidations_total_vol'] is None


def test_insert_sentiment_multiplos_simbolos(tmp_path):
    """Testa inserção de sentimento para múltiplos símbolos."""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    
    # Dados para múltiplos símbolos com campos ausentes
    dados_multiplos = [
        {
            'timestamp': 1707952800000,
            'symbol': 'BTCUSDT',
            'long_short_ratio': 1.5,
            'open_interest': 1000000.0,
            'funding_rate': 0.0001,
        },
        {
            'timestamp': 1707952800000,
            'symbol': 'ETHUSDT',
            'long_short_ratio': 1.3,
            'open_interest': 500000.0,
            'funding_rate': 0.00015,
        },
    ]
    
    # Deve inserir sem erros
    db.insert_sentiment(dados_multiplos)
    
    # Verificar inserção para cada símbolo
    result_btc = db.get_sentiment('BTCUSDT')
    assert len(result_btc) == 1
    assert result_btc[0]['symbol'] == 'BTCUSDT'
    
    result_eth = db.get_sentiment('ETHUSDT')
    assert len(result_eth) == 1
    assert result_eth[0]['symbol'] == 'ETHUSDT'


def test_insert_sentiment_vazio(tmp_path):
    """Testa inserção de sentimento com lista vazia."""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    
    # Lista vazia não deve causar erro
    db.insert_sentiment([])
    
    # Não deve haver registros
    result = db.get_sentiment('BTCUSDT')
    assert len(result) == 0
