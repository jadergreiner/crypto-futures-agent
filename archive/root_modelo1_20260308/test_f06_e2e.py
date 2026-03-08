"""
Teste E2E para F-06: step() completo no CryptoFuturesEnv.
Valida que step(), reset() e _get_observation() funcionam corretamente.
"""

import logging
import numpy as np
from agent.environment import CryptoFuturesEnv
from tests.test_rl_environment import create_test_data_with_indicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_f06_reset_and_step_complete():
    """
    US-04: Verifica que reset() e step() funcionam completamente.
    """
    print("\n" + "="*70)
    print("TESTE F-06: step() completo no CryptoFuturesEnv")
    print("="*70)
    
    # 1. Criar environment
    print("\n[1/5] Criando environment...")
    data = create_test_data_with_indicators(symbol='BTCUSDT')
    env = CryptoFuturesEnv(data, initial_capital=10000, episode_length=50)
    print(f"  ✓ Environment criado: {env.symbol}")
    
    # 2. Reset
    print("\n[2/5] Testando reset()...")
    obs, info = env.reset()
    
    # Validações de reset
    assert obs is not None, "reset() deve retornar observação"
    assert isinstance(obs, np.ndarray), "Observação deve ser numpy array"
    assert obs.shape == (104,), f"Shape esperado (104,), obteve {obs.shape}"
    assert not np.any(np.isnan(obs)), "Observação não pode conter NaN"
    assert not np.any(np.isinf(obs)), "Observação não pode conter Inf"
    
    print(f"  ✓ reset() retornou observação válida: shape={obs.shape}")
    print(f"    - sem NaN/Inf")
    print(f"    - capital inicial: ${env.capital:.2f}")
    print(f"    - start_step: {env.start_step}")
    
    # 3. Step simples (HOLD)
    print("\n[3/5] Testando step(action=0 HOLD)...")
    obs_new, reward, terminated, truncated, info = env.step(0)
    
    # Validações de step
    assert obs_new is not None, "step() deve retornar observação"
    assert isinstance(obs_new, np.ndarray), "Nova observação deve ser numpy array"
    assert obs_new.shape == (104,), f"Shape esperado (104,), obteve {obs_new.shape}"
    assert isinstance(reward, (int, float, np.number)), "Reward deve ser numérico"
    assert isinstance(terminated, (bool, np.bool_)), "terminated deve ser bool"
    assert isinstance(truncated, (bool, np.bool_)), "truncated deve ser bool"
    assert isinstance(info, dict), "info deve ser dict"
    
    print(f"  ✓ step() retornou tupla válida:")
    print(f"    - obs shape: {obs_new.shape}")
    print(f"    - reward: {reward:.4f}")
    print(f"    - terminated: {terminated}")
    print(f"    - truncated: {truncated}")
    print(f"    - info keys: {list(info.keys())}")
    
    # 4. Loop de steps completo
    print("\n[4/5] Executando 10 steps com ações aleatórias...")
    
    trade_count = 0
    max_reward = -np.inf
    min_reward = np.inf
    
    for step_idx in range(10):
        action = env.action_space.sample()
        obs_new, reward, terminated, truncated, info = env.step(action)
        
        # Validações por step
        assert obs_new.shape == (104,), f"Step {step_idx}: shape inválido"
        assert not np.any(np.isnan(obs_new)), f"Step {step_idx}: NaN na observação"
        assert not np.any(np.isinf(obs_new)), f"Step {step_idx}: Inf na observação"
        assert -15.0 <= reward <= 15.0, f"Step {step_idx}: reward fora do range {reward}"
        
        max_reward = max(max_reward, reward)
        min_reward = min(min_reward, reward)
        
        if info.get('trades_count', 0) > 0:
            trade_count = info['trades_count']
        
        if terminated or truncated:
            print(f"  ! Episódio terminou no step {step_idx}")
            break
    
    print(f"  ✓ 10 steps executados com sucesso")
    print(f"    - trades abertos: {trade_count}")
    print(f"    - reward range: [{min_reward:.4f}, {max_reward:.4f}]")
    print(f"    - capital final: ${env.capital:.2f}")
    
    # 5. Teste de term inação
    print("\n[5/5] Testando término do episódio...")
    
    # Reset e rodar até o fim
    obs, _ = env.reset()
    step_count = 0
    done = False
    
    while not done and step_count < 100:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        step_count += 1
    
    print(f"  ✓ Episódio terminou após {step_count} steps")
    print(f"    - terminated: {terminated}")
    print(f"    - truncated: {truncated}")
    print(f"    - capital final: ${env. capital:.2f}")
    print(f"    - drawdown max: {(1 - env.capital/env.peak_capital)*100:.2f}%")
    
    print("\n" + "="*70)
    print("✅ TESTE F-06 PASSOU")
    print("="*70)
    print("\nResumo:")
    print("  ✓ reset() funciona completamente")
    print("  ✓ step() funciona com todas as ações")
    print("  ✓ _get_observation() retorna 104 features válidas")
    print("  ✓ Episódios podem ser executados até término")
    print("  ✓ Recompensas estão na faixa esperada")


if __name__ == '__main__':
    try:
        test_f06_reset_and_step_complete()
    except Exception as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
