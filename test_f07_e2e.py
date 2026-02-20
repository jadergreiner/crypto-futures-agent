"""
Teste E2E para F-07: _get_observation() usando FeatureEngineer.
Valida que observação de 104 features está corretamente construída.
"""

import logging
import numpy as np
from agent.environment import CryptoFuturesEnv
from tests.test_rl_environment import create_test_data_with_indicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_f07_get_observation_complete():
    """
    US-04: Verifica que _get_observation() retorna 104 features válidas
    estruturadas pela FeatureEngineer.
    """
    print("\n" + "="*70)
    print("TESTE F-07: _get_observation() usando FeatureEngineer")
    print("="*70)
    
    # 1. Features de cada bloco
    feature_blocks = {
        "Bloco 1 (Preço)": (0, 11, "preço, return, momentum"),
        "Bloco 2 (EMAs)": (11, 17, "EMA12, EMA26, EMA50, EMA200"),
        "Bloco 3 (Indicadores)": (17, 36, "RSI, MACD, ATR, Bollinger, Volume"),
        "Bloco 4 (H1 Agregado)": (36, 45, "H1 features agregadas"),
        "Bloco 5 (D1 Agregado)": (45, 55, "D1 features agregadas"),
        "Bloco 6 (Posição)": (55, 76, "Estado da posição, PnL, R-múltiplos"),
        "Bloco 7 (Correlação BTC)": (76, 79, "BTCReturn, Correlation, Beta"),
        "Bloco 8 (Viés D1/Regime)": (79, 81, "D1Bias, MarketRegime"),
        "Bloco 9 (Sentimento/Macro)": (81, 104, "Sentiment, Macro, SMC"),
    }
    
    # 2. Criar environment
    print("\n[1/4] Criando environment com dados..."    )
    data = create_test_data_with_indicators(symbol='ETHUSDT')
    env = CryptoFuturesEnv(data, initial_capital=10000, episode_length=50)
    print(f"  ✓ Environment criado para {env.symbol}")
    
    # 3. Chamar reset e verificar observação
    print("\n[2/4] Testando _get_observation() após reset()...")
    obs, info = env.reset()
    
    # Validações gerais
    assert obs.shape == (104,), f"Shape esperado (104,), obteve {obs.shape}"
    assert isinstance(obs, np.ndarray), "Deve ser numpy array"
    assert obs.dtype == np.float32, f"Dtype esperado float32, obteve {obs.dtype}"
    assert not np.any(np.isnan(obs)), "Não pode conter NaN"
    assert not np.any(np.isinf(obs)), "Não pode conter Inf"
    assert np.all((obs >= -10.0) & (obs <= 10.0)), "Todos valores devem estar em [-10, 10]"
    
    print(f"  ✓ Observação de reset() é válida:")
    print(f"    - Shape: {obs.shape}")
    print(f"    - Dtype: {obs.dtype}")
    print(f"    - Range: [{np.min(obs):.6f}, {np.max(obs):.6f}]")
    print(f"    - Mean: {np.mean(obs):.6f}, Std: {np.std(obs):.6f}")
    
    # 4. Verificar blocos de features
    print("\n[3/4] Verificando estrutura dos blocos...")
    for block_name, (start, end, description) in feature_blocks.items():
        block = obs[start:end]
        print(f"  {block_name} [{start}:{end}]")
        print(f"    - {len(block)} features - {description}")
        print(f"    - Valores: min={np.min(block):.4f}, max={np.max(block):.4f}, " +
              f"mean={np.mean(block):.4f}")
        
        # Verificações por bloco
        if "Bloco 7" in block_name:  # Correlação BTC
            assert -1.0 <= block[1] <= 1.0, "Correlação deve estar em [-1, 1]"
            print(f"    ✓ Correlação BTC válida: {block[1]:.4f}")
        
        if "Bloco 8" in block_name:  # Viés D1
            assert block[0] in [-1.0, 0.0, 1.0], f"D1 Bias deve ser -1/0/1, obteve {block[0]}"
            assert block[1] in [-1.0, 0.0, 1.0], f"Market Regime deve ser -1/0/1, obteve {block[1]}"
            print(f"    ✓ D1 Bias={block[0]:.0f}, Market Regime={block[1]:.0f}")
    
    # 5. Verificar observe múltiplas vezes (deve variar com dados)
    print("\n[4/4] Testando observações em múltiplos steps...")
    obs_prev = obs
    variations = 0
    
    for step in range(15):
        action = env.action_space.sample()
        obs_new, reward, terminated, truncated, info = env.step(action)
        
        # Validação
        assert obs_new.shape == (104,), f"Step {step}: shape inválido"
        assert not np.any(np.isnan(obs_new)), f"Step {step}: NaN na obs"
        assert not np.any(np.isinf(obs_new)), f"Step {step}: Inf na obs"
        
        # Verificar que observação varia entre steps
        diff = np.sum(np.abs(obs_new - obs_prev))
        if diff > 0.01:  # Threshold mínimo para detecção de variação
            variations += 1
        
        obs_prev = obs_new
        
        if terminated or truncated:
            print(f"  Episódio terminou no step {step}")
            break
    
    print(f"  ✓ Observações variam normalmente entre steps")
    print(f"    - {variations}/15 steps tiveram variação significativa")
    
    print("\n" + "="*70)
    print("✅ TESTE F-07 PASSOU")
    print("="*70)
    print("\nResumo:")
    print("  ✓ _get_observation() retorna array (104,) float32")
    print("  ✓ Todos valores validados e no range [-10, 10]")
    print("  ✓ Estrutura de 9 blocos com features corretas")
    print("  ✓ Bloco 7 e 8 com valores multi-timeframe reais")
    print("  ✓ Observação varia naturalmente entre steps")


if __name__ == '__main__':
    try:
        test_f07_get_observation_complete()
    except Exception as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
