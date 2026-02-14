"""
Testes para indicadores técnicos.
"""

import pytest
import pandas as pd
import numpy as np
from indicators.technical import TechnicalIndicators


def create_sample_data(length=100):
    """Cria dados de amostra para testes."""
    np.random.seed(42)
    base_price = 30000
    
    data = {
        'timestamp': [i * 3600000 for i in range(length)],
        'open': base_price + np.random.randn(length) * 100,
        'high': base_price + np.random.randn(length) * 100 + 50,
        'low': base_price + np.random.randn(length) * 100 - 50,
        'close': base_price + np.random.randn(length) * 100,
        'volume': np.random.rand(length) * 1000
    }
    
    return pd.DataFrame(data)


def test_calculate_ema():
    """Testa cálculo de EMA."""
    df = create_sample_data()
    ema = TechnicalIndicators.calculate_ema(df['close'], 20)
    
    assert len(ema) == len(df)
    assert not ema.iloc[-1] == np.nan


def test_calculate_rsi():
    """Testa cálculo de RSI."""
    df = create_sample_data()
    rsi = TechnicalIndicators.calculate_rsi(df['close'], 14)
    
    assert len(rsi) == len(df)
    # RSI deve estar entre 0 e 100
    valid_rsi = rsi[~rsi.isna()]
    assert all((valid_rsi >= 0) & (valid_rsi <= 100))


def test_calculate_macd():
    """Testa cálculo de MACD."""
    df = create_sample_data()
    macd_df = TechnicalIndicators.calculate_macd(df['close'])
    
    assert 'macd_line' in macd_df.columns
    assert 'macd_signal' in macd_df.columns
    assert 'macd_histogram' in macd_df.columns
    assert len(macd_df) == len(df)


def test_calculate_bollinger():
    """Testa cálculo de Bollinger Bands."""
    df = create_sample_data()
    bb_df = TechnicalIndicators.calculate_bollinger(df['close'], 20, 2.0)
    
    assert 'bb_upper' in bb_df.columns
    assert 'bb_middle' in bb_df.columns
    assert 'bb_lower' in bb_df.columns
    
    # Upper deve ser > Lower
    valid_idx = ~bb_df['bb_upper'].isna()
    assert all(bb_df.loc[valid_idx, 'bb_upper'] >= bb_df.loc[valid_idx, 'bb_lower'])


def test_calculate_atr():
    """Testa cálculo de ATR."""
    df = create_sample_data()
    atr = TechnicalIndicators.calculate_atr(df, 14)
    
    assert len(atr) == len(df)
    # ATR deve ser positivo
    valid_atr = atr[~atr.isna()]
    assert all(valid_atr >= 0)


def test_calculate_all():
    """Testa cálculo de todos os indicadores."""
    df = create_sample_data()
    result = TechnicalIndicators.calculate_all(df)
    
    # Verificar se todas as colunas foram adicionadas
    expected_cols = ['ema_17', 'ema_34', 'rsi_14', 'macd_line', 'bb_upper', 
                     'obv', 'atr_14', 'adx_14', 'ema_alignment_score']
    
    for col in expected_cols:
        assert col in result.columns
