"""
Testes para validar as correções de observações None e divisões por zero.
"""

import numpy as np
import pandas as pd
from agent.environment import CryptoFuturesEnv
from indicators.features import FeatureEngineer
from indicators.technical import TechnicalIndicators


def create_synthetic_ohlcv(
    length: int = 200,
    base_price: float = 30000.0,
    volatility: float = 100.0,
    trend: float = 0.0,
    seed: int = 42
) -> pd.DataFrame:
    """Cria dados OHLCV sintéticos."""
    np.random.seed(seed)
    
    timestamps = [1700000000000 + i * 3600000 for i in range(length)]
    
    # Gerar preços close com random walk + trend
    close_prices = [base_price]
    for i in range(1, length):
        change = np.random.randn() * volatility + trend
        new_price = close_prices[-1] + change
        close_prices.append(max(new_price, 100))  # Evitar preços negativos
    
    close_prices = np.array(close_prices)
    
    # Gerar OHLC a partir do close
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = base_price
    
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.randn(length) * volatility * 0.3)
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.randn(length) * volatility * 0.3)
    
    volumes = np.abs(np.random.randn(length) * 1000 + 5000)
    
    data = {
        'timestamp': timestamps,
        'symbol': ['BTCUSDT'] * length,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes,
        'quote_volume': volumes * close_prices,
        'trades_count': (volumes / 10).astype(int),
    }
    
    return pd.DataFrame(data)


def test_observation_with_none_sentiment():
    """Testa que observação funciona quando sentiment é None."""
    # Criar dados básicos
    h4_data = create_synthetic_ohlcv(length=100, seed=42)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    
    # Criar environment com sentiment=None
    data = {
        'h4': h4_data,
        'h1': h4_data,
        'd1': h4_data.iloc[::4],  # Simular D1
        'sentiment': None,  # None!
        'macro': {
            'fear_greed_value': 50,
            'btc_dominance': 48.0,
            'dxy_change_pct': 0.0,
            'stablecoin_exchange_flow_net': 0.0,
        },
        'smc': {
            'structure': None,
            'swings': [],
            'bos': [],
            'choch': [],
            'order_blocks': [],
            'fvgs': [],
            'liquidity_levels': [],
            'liquidity_sweeps': [],
            'premium_discount': None,
        }
    }
    
    env = CryptoFuturesEnv(
        
        data=data,
        initial_capital=1000.0,
        # max_leverage removed
    )
    
    # Reset deve funcionar sem erro
    obs, _ = env.reset()
    assert obs is not None
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))


def test_observation_with_none_macro():
    """Testa que observação funciona quando macro é None."""
    # Criar dados básicos
    h4_data = create_synthetic_ohlcv(length=100, seed=42)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    
    # Criar environment com macro=None
    data = {
        'h4': h4_data,
        'h1': h4_data,
        'd1': h4_data.iloc[::4],
        'sentiment': {
            'long_short_ratio': 1.0,
            'open_interest_change_pct': 0.0,
            'funding_rate': 0.0001,
            'liquidations_long_vol': 0.0,
            'liquidations_short_vol': 0.0,
        },
        'macro': None,  # None!
        'smc': {
            'structure': None,
            'swings': [],
            'bos': [],
            'choch': [],
            'order_blocks': [],
            'fvgs': [],
            'liquidity_levels': [],
            'liquidity_sweeps': [],
            'premium_discount': None,
        }
    }
    
    env = CryptoFuturesEnv(
        
        data=data,
        initial_capital=1000.0,
        # max_leverage removed
    )
    
    # Reset deve funcionar sem erro
    obs, _ = env.reset()
    assert obs is not None
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))


def test_observation_with_none_smc():
    """Testa que observação funciona quando smc é None."""
    # Criar dados básicos
    h4_data = create_synthetic_ohlcv(length=100, seed=42)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    
    # Criar environment com smc=None
    data = {
        'h4': h4_data,
        'h1': h4_data,
        'd1': h4_data.iloc[::4],
        'sentiment': {
            'long_short_ratio': 1.0,
            'open_interest_change_pct': 0.0,
            'funding_rate': 0.0001,
            'liquidations_long_vol': 0.0,
            'liquidations_short_vol': 0.0,
        },
        'macro': {
            'fear_greed_value': 50,
            'btc_dominance': 48.0,
            'dxy_change_pct': 0.0,
            'stablecoin_exchange_flow_net': 0.0,
        },
        'smc': None  # None!
    }
    
    env = CryptoFuturesEnv(
        
        data=data,
        initial_capital=1000.0,
        # max_leverage removed
    )
    
    # Reset deve funcionar sem erro
    obs, _ = env.reset()
    assert obs is not None
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))


def test_observation_with_all_none():
    """Testa que observação funciona quando sentiment, macro e smc são None."""
    # Criar dados básicos
    h4_data = create_synthetic_ohlcv(length=100, seed=42)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    
    # Criar environment com tudo None
    data = {
        'h4': h4_data,
        'h1': h4_data,
        'd1': h4_data.iloc[::4],
        'sentiment': None,
        'macro': None,
        'smc': None
    }
    
    env = CryptoFuturesEnv(
        
        data=data,
        initial_capital=1000.0,
        # max_leverage removed
    )
    
    # Reset deve funcionar sem erro
    obs, _ = env.reset()
    assert obs is not None
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))


def test_feature_engineer_with_none_values_in_sentiment():
    """Testa que FeatureEngineer lida com valores None dentro de sentiment."""
    # Criar dados básicos
    h4_data = create_synthetic_ohlcv(length=100, seed=42)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    
    # Sentiment com valores None
    sentiment = {
        'long_short_ratio': 1.0,
        'open_interest_change_pct': None,  # None aqui!
        'funding_rate': 0.0001,
        'liquidations_long_vol': 0.0,
        'liquidations_short_vol': 0.0,
    }
    
    macro = {
        'fear_greed_value': 50,
        'btc_dominance': 48.0,
        'dxy_change_pct': 0.0,
        'stablecoin_exchange_flow_net': 0.0,
    }
    
    smc = {
        'structure': None,
        'swings': [],
        'bos': [],
        'choch': [],
        'order_blocks': [],
        'fvgs': [],
        'liquidity_levels': [],
        'liquidity_sweeps': [],
        'premium_discount': None,
    }
    
    # Build observation não deve falhar
    obs = FeatureEngineer.build_observation(
        symbol='BTCUSDT',
        h1_data=h4_data,
        h4_data=h4_data,
        d1_data=h4_data.iloc[::4],
        sentiment=sentiment,
        macro=macro,
        smc=smc
    )
    
    assert obs is not None
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))


def test_feature_engineer_with_none_values_in_macro():
    """Testa que FeatureEngineer lida com valores None dentro de macro."""
    # Criar dados básicos
    h4_data = create_synthetic_ohlcv(length=100, seed=42)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    
    sentiment = {
        'long_short_ratio': 1.0,
        'open_interest_change_pct': 0.0,
        'funding_rate': 0.0001,
        'liquidations_long_vol': 0.0,
        'liquidations_short_vol': 0.0,
    }
    
    # Macro com valores None
    macro = {
        'fear_greed_value': None,  # None aqui!
        'btc_dominance': None,  # None aqui!
        'dxy_change_pct': None,  # None aqui!
        'stablecoin_exchange_flow_net': None,  # None aqui!
    }
    
    smc = {
        'structure': None,
        'swings': [],
        'bos': [],
        'choch': [],
        'order_blocks': [],
        'fvgs': [],
        'liquidity_levels': [],
        'liquidity_sweeps': [],
        'premium_discount': None,
    }
    
    # Build observation não deve falhar
    obs = FeatureEngineer.build_observation(
        symbol='BTCUSDT',
        h1_data=h4_data,
        h4_data=h4_data,
        d1_data=h4_data.iloc[::4],
        sentiment=sentiment,
        macro=macro,
        smc=smc
    )
    
    assert obs is not None
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))


def test_feature_engineer_with_zero_price():
    """Testa que FeatureEngineer não divide por zero quando current_price é 0."""
    # Criar dados com preço zero
    h4_data = create_synthetic_ohlcv(length=100, seed=42)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    # Forçar preço zero no último candle
    h4_data.loc[h4_data.index[-1], 'close'] = 0.0
    
    sentiment = {
        'long_short_ratio': 1.0,
        'open_interest_change_pct': 0.0,
        'funding_rate': 0.0001,
        'liquidations_long_vol': 0.0,
        'liquidations_short_vol': 0.0,
    }
    
    macro = {
        'fear_greed_value': 50,
        'btc_dominance': 48.0,
        'dxy_change_pct': 0.0,
        'stablecoin_exchange_flow_net': 0.0,
    }
    
    # SMC com order blocks e FVGs para testar divisão por current_price
    from indicators.smc import OrderBlock, FairValueGap, ZoneStatus
    
    smc = {
        'structure': None,
        'swings': [],
        'bos': [],
        'choch': [],
        'order_blocks': [
            OrderBlock(
                timestamp=1700000000000,
                type='bullish',
                zone_high=50000.0,
                zone_low=49000.0,
                index=10,
                status=ZoneStatus.FRESH,
                strength=1.0
            )
        ],
        'fvgs': [
            FairValueGap(
                timestamp=1700000000000,
                type='bullish',
                zone_high=51000.0,
                zone_low=50500.0,
                index=15,
                status=ZoneStatus.OPEN
            )
        ],
        'liquidity_levels': [],
        'liquidity_sweeps': [],
        'premium_discount': None,
    }
    
    # Build observation não deve falhar com divisão por zero
    obs = FeatureEngineer.build_observation(
        symbol='BTCUSDT',
        h1_data=h4_data,
        h4_data=h4_data,
        d1_data=h4_data.iloc[::4],
        sentiment=sentiment,
        macro=macro,
        smc=smc
    )
    
    assert obs is not None
    assert obs.shape == (104,)
    # Pode ter alguns valores extremos, mas não deve ter NaN ou inf
    assert not np.any(np.isnan(obs))
    assert not np.any(np.isinf(obs))


if __name__ == "__main__":
    # Executar testes
    print("Testando observações com None...")
    test_observation_with_none_sentiment()
    print("[OK] Test sentiment=None passou")
    
    test_observation_with_none_macro()
    print("[OK] Test macro=None passou")
    
    test_observation_with_none_smc()
    print("[OK] Test smc=None passou")
    
    test_observation_with_all_none()
    print("[OK] Test all None passou")
    
    test_feature_engineer_with_none_values_in_sentiment()
    print("[OK] Test None values in sentiment passou")
    
    test_feature_engineer_with_none_values_in_macro()
    print("[OK] Test None values in macro passou")
    
    test_feature_engineer_with_zero_price()
    print("[OK] Test divisão por zero passou")
    
    print("\n[OK] Todos os testes passaram!")
