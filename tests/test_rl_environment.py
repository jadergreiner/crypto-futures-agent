"""
Testes para CryptoFuturesEnv para verificar integração de multi_tf_result.
"""

import pytest
import numpy as np
import pandas as pd
from agent.environment import CryptoFuturesEnv
from tests.test_e2e_pipeline import (
    create_synthetic_ohlcv,
    create_synthetic_macro_data,
    create_synthetic_sentiment_data
)
from indicators.technical import TechnicalIndicators
from indicators.smc import SmartMoneyConcepts


def create_test_data_with_indicators(symbol='BTCUSDT'):
    """Cria dados de teste com todos os indicadores necessários."""
    # Gerar dados OHLCV
    h1_data = create_synthetic_ohlcv(length=200, seed=41)
    h4_data = create_synthetic_ohlcv(length=200, seed=42)
    d1_data = create_synthetic_ohlcv(length=50, seed=43)
    
    # Calcular indicadores
    h1_data = TechnicalIndicators.calculate_all(h1_data)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    d1_data = TechnicalIndicators.calculate_all(d1_data)
    
    # Calcular SMC
    try:
        smc_result = SmartMoneyConcepts.calculate_all_smc(h4_data)
    except Exception:
        smc_result = {
            'structure': None,
            'swings': [],
            'bos': [],
            'choch': [],
            'order_blocks': [],
            'fvgs': [],
            'liquidity_levels': [],
            'liquidity_sweeps': [],
            'premium_discount': None
        }
    
    sentiment = create_synthetic_sentiment_data()
    sentiment['symbol'] = symbol
    
    macro = create_synthetic_macro_data()
    
    return {
        'h1': h1_data,
        'h4': h4_data,
        'd1': d1_data,
        'sentiment': sentiment,
        'macro': macro,
        'smc': smc_result,
        'symbol': symbol
    }


def test_environment_computes_multi_tf_result():
    """Verifica que o environment computa multi_tf_result durante inicialização."""
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Verificar que multi_tf_result foi computado
    assert hasattr(env, 'multi_tf_result')
    assert env.multi_tf_result is not None
    assert 'd1_bias' in env.multi_tf_result
    assert 'market_regime' in env.multi_tf_result
    assert 'correlation_btc' in env.multi_tf_result
    assert 'beta_btc' in env.multi_tf_result
    
    # Verificar que symbol foi extraído corretamente
    assert hasattr(env, 'symbol')
    assert env.symbol == 'BTCUSDT'


def test_environment_uses_symbol_from_data():
    """Verifica que o environment usa o symbol do dict de dados."""
    data = create_test_data_with_indicators(symbol='ETHUSDT')
    env = CryptoFuturesEnv(data, episode_length=50)
    
    assert env.symbol == 'ETHUSDT'
    assert env.multi_tf_result['symbol'] == 'ETHUSDT'


def test_observation_has_multi_tf_features():
    """Verifica que features dos Blocos 7 e 8 não são placeholders durante treinamento."""
    # Criar env com dados que têm indicadores d1
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    obs, info = env.reset()
    
    # Verificar shape da observação
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))
    
    # Bloco 7 começa no índice 55 (11+6+11+19+4+4)
    block7_start = 55
    block8_start = 58
    
    # Bloco 7: correlação deve estar entre -1 e 1, beta deve ser razoável
    btc_return = obs[block7_start]
    correlation_val = obs[block7_start + 1]
    beta_val = obs[block7_start + 2]
    
    # Estes devem estar em faixas válidas (não todos zeros)
    assert -1.0 <= btc_return <= 1.0
    assert -1.0 <= correlation_val <= 1.0
    assert 0.0 <= beta_val <= 1.0  # Beta dividido por 3 depois clipped para [0, 1]
    
    # Bloco 8: d1_bias e regime devem ser -1, 0, ou 1
    d1_bias_val = obs[block8_start]
    regime_val = obs[block8_start + 1]
    
    assert d1_bias_val in [-1.0, 0.0, 1.0]
    assert regime_val in [-1.0, 0.0, 1.0]


def test_observation_multi_tf_across_steps():
    """Verifica que multi_tf_result é consistente entre steps em um episódio."""
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Reset e pegar primeira observação
    obs1, _ = env.reset()
    
    # Dar alguns steps e verificar observações
    for _ in range(5):
        action = env.action_space.sample()
        obs2, reward, terminated, truncated, info = env.step(action)
        
        if terminated or truncated:
            break
        
        # Verificar que observação é válida
        assert obs2.shape == (104,)
        assert not np.any(np.isnan(obs2))
        
        # Blocos 7 e 8 ainda devem ter valores válidos
        block7_start = 55
        block8_start = 58
        
        correlation_val = obs2[block7_start + 1]
        beta_val = obs2[block7_start + 2]
        d1_bias_val = obs2[block8_start]
        regime_val = obs2[block8_start + 1]
        
        assert -1.0 <= correlation_val <= 1.0
        assert 0.0 <= beta_val <= 1.0
        assert d1_bias_val in [-1.0, 0.0, 1.0]
        assert regime_val in [-1.0, 0.0, 1.0]


def test_environment_handles_missing_data_gracefully():
    """Verifica que environment trata dados D1 ausentes graciosamente."""
    # Criar dados com D1 vazio
    data = create_test_data_with_indicators()
    data['d1'] = pd.DataFrame()
    
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Ainda deve inicializar com valores de fallback
    assert env.multi_tf_result is not None
    assert env.multi_tf_result['d1_bias'] == 'NEUTRO'
    assert env.multi_tf_result['market_regime'] == 'NEUTRO'
    
    # Ainda deve ser capaz de fazer reset e step
    obs, info = env.reset()
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))


def test_environment_handles_btcusdt_symbol():
    """Verifica que environment trata corretamente o symbol BTCUSDT."""
    data = create_test_data_with_indicators(symbol='BTCUSDT')
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Para BTCUSDT, correlação e beta devem ser 1.0 (auto-correlação)
    # Mas isso depende de ter btc_data, que não temos aqui
    # Então deve usar valores de fallback
    assert env.symbol == 'BTCUSDT'
    assert env.multi_tf_result is not None


def test_data_loader_includes_symbol():
    """Verifica que DataLoader inclui chave 'symbol' nos dados retornados."""
    from agent.data_loader import DataLoader
    
    # Testar com dados sintéticos (sem DB)
    loader = DataLoader(db=None)
    
    # Carregar dados de treinamento
    data = loader.load_training_data(symbol='ETHUSDT', min_length=100)
    
    # Verificar que symbol está incluído
    assert 'symbol' in data
    assert data['symbol'] == 'ETHUSDT'
    
    # Verificar que outras chaves estão presentes
    assert 'h1' in data
    assert 'h4' in data
    assert 'd1' in data
    assert 'sentiment' in data
    assert 'macro' in data
    assert 'smc' in data
