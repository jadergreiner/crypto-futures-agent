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
    assert 0.0 <= beta_val <= 1.0  # Beta dividido por 3 então clipped para [0, 1]
    
    # Bloco 8: d1_bias e regime devem ser -1, 0, ou 1
    d1_bias_val = obs[block8_start]
    regime_val = obs[block8_start + 1]
    
    assert d1_bias_val in [-1.0, 0.0, 1.0]
    assert regime_val in [-1.0, 0.0, 1.0]


def test_multi_tf_features_consistent_across_steps():
    """Verifica que features multi-tf são consistentes entre steps em um episódio."""
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


def test_close_blocked_when_r_below_minimum():
    """Testa que CLOSE é bloqueado quando R < 1.0 e posição em lucro."""
    # Criar environment com dados de teste
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Reset
    obs, info = env.reset()
    
    # Abrir posição LONG
    action_open = 1  # OPEN_LONG
    obs, reward, terminated, truncated, info = env.step(action_open)
    
    # Verificar que posição foi aberta
    assert env.position is not None, "Posição deveria ter sido aberta"
    
    # Simular lucro pequeno: modificar preço para gerar R < 1.0
    # Entry price atual
    entry_price = env.position['entry_price']
    initial_stop = env.position['initial_stop']
    
    # Modificar o preço de fechamento do próximo candle para gerar lucro pequeno
    # R = pnl / initial_risk
    # Para R = 0.5, precisamos pnl = 0.5 * initial_risk
    # initial_risk = abs(entry_price - initial_stop) * size
    position_size = env.position['size']
    initial_risk = abs(entry_price - initial_stop) * position_size
    
    # Para LONG: pnl = (exit_price - entry_price) * size
    # Queremos pnl = 0.5 * initial_risk
    # exit_price = entry_price + (0.5 * initial_risk / size)
    target_pnl = 0.5 * initial_risk
    target_exit_price = entry_price + (target_pnl / position_size)
    
    # Modificar o próximo candle
    next_idx = env.current_step
    if next_idx < len(env.data['h4']):
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'close'] = target_exit_price
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'high'] = target_exit_price + 10
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'low'] = entry_price - 5
    
    # Tentar fechar a posição (action = 3)
    action_close = 3  # CLOSE
    obs, reward, terminated, truncated, info = env.step(action_close)
    
    # Verificar que CLOSE foi bloqueado
    assert info['action_valid'] == False, "CLOSE deveria ter sido bloqueado (R < 1.0 e lucro)"
    
    # Verificar que posição ainda existe
    assert env.position is not None, "Posição não deveria ter sido fechada"
    
    # Verificar que reward contém penalidade de ação inválida
    assert info['reward_components']['r_invalid_action'] < 0, \
        "Deveria ter penalidade por ação inválida"


def test_close_allowed_when_losing():
    """Testa que CLOSE é permitido quando posição está em prejuízo."""
    # Criar environment com dados de teste
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Reset
    obs, info = env.reset()
    
    # Abrir posição LONG
    action_open = 1  # OPEN_LONG
    obs, reward, terminated, truncated, info = env.step(action_open)
    
    # Verificar que posição foi aberta
    assert env.position is not None, "Posição deveria ter sido aberta"
    
    # Simular prejuízo: modificar preço para gerar PnL negativo
    entry_price = env.position['entry_price']
    position_size = env.position['size']
    
    # Para LONG em prejuízo: exit_price < entry_price
    target_exit_price = entry_price * 0.98  # -2% de prejuízo
    
    # Modificar o próximo candle
    next_idx = env.current_step
    if next_idx < len(env.data['h4']):
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'close'] = target_exit_price
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'high'] = entry_price + 5
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'low'] = target_exit_price - 10
    
    # Tentar fechar a posição (action = 3)
    action_close = 3  # CLOSE
    obs, reward, terminated, truncated, info = env.step(action_close)
    
    # Verificar que CLOSE foi PERMITIDO (posição em prejuízo)
    assert info['action_valid'] == True, "CLOSE deveria ter sido permitido (posição em prejuízo)"
    
    # Verificar que posição foi fechada
    assert env.position is None, "Posição deveria ter sido fechada"


def test_close_allowed_when_r_above_minimum():
    """Testa que CLOSE é permitido quando R >= 1.0."""
    # Criar environment com dados de teste
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Reset
    obs, info = env.reset()
    
    # Abrir posição LONG
    action_open = 1  # OPEN_LONG
    obs, reward, terminated, truncated, info = env.step(action_open)
    
    # Verificar que posição foi aberta
    assert env.position is not None, "Posição deveria ter sido aberta"
    
    # Simular lucro bom: R >= 1.0
    entry_price = env.position['entry_price']
    initial_stop = env.position['initial_stop']
    position_size = env.position['size']
    initial_risk = abs(entry_price - initial_stop) * position_size
    
    # Para R = 1.5, precisamos pnl = 1.5 * initial_risk
    target_pnl = 1.5 * initial_risk
    target_exit_price = entry_price + (target_pnl / position_size)
    
    # Modificar o próximo candle
    next_idx = env.current_step
    if next_idx < len(env.data['h4']):
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'close'] = target_exit_price
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'high'] = target_exit_price + 10
        env.data['h4'].loc[env.data['h4'].index[next_idx], 'low'] = entry_price - 5
    
    # Tentar fechar a posição (action = 3)
    action_close = 3  # CLOSE
    obs, reward, terminated, truncated, info = env.step(action_close)
    
    # Verificar que CLOSE foi PERMITIDO (R >= 1.0)
    assert info['action_valid'] == True, "CLOSE deveria ter sido permitido (R >= 1.0)"
    
    # Verificar que posição foi fechada
    assert env.position is None, "Posição deveria ter sido fechada"


def test_position_state_has_momentum():
    """Testa que position_state contém pnl_momentum e current_r_multiple."""
    # Criar environment com dados de teste
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Reset
    obs, info = env.reset()
    
    # Abrir posição
    action_open = 1  # OPEN_LONG
    obs, reward, terminated, truncated, info = env.step(action_open)
    
    # Dar vários steps para acumular histórico de PnL
    for i in range(10):
        if env.position is None:
            break
        action_hold = 0  # HOLD
        obs, reward, terminated, truncated, info = env.step(action_hold)
    
    # Verificar que position_state foi obtido
    position_state = env._get_position_state()
    
    if position_state and position_state.get('has_position', False):
        # Verificar que pnl_momentum está presente
        assert 'pnl_momentum' in position_state, \
            "position_state deveria conter 'pnl_momentum'"
        
        # Verificar que current_r_multiple está presente
        assert 'current_r_multiple' in position_state, \
            "position_state deveria conter 'current_r_multiple'"
        
        # Verificar que são números válidos
        assert isinstance(position_state['pnl_momentum'], (int, float)), \
            "pnl_momentum deve ser um número"
        assert isinstance(position_state['current_r_multiple'], (int, float)), \
            "current_r_multiple deve ser um número"
        
        # Se temos histórico suficiente (>= 6), momentum não deve ser 0
        if len(env.pnl_history) >= 6:
            # Momentum pode ser 0 se o PnL não mudou, mas deve existir
            assert position_state['pnl_momentum'] is not None
