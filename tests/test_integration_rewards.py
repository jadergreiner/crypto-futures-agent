"""
Teste de integração para validar o funcionamento completo do sistema de rewards amplificado.
"""

import numpy as np
import pandas as pd
from agent.environment import CryptoFuturesEnv
from agent.reward import RewardCalculator


def test_reward_integration():
    """Testa integração completa: environment + reward calculator com novos componentes."""
    
    # Criar dados mock com candles OHLC válidos
    np.random.seed(42)  # Seed para reproducibilidade
    base_prices = np.linspace(40000, 41000, 100)
    
    opens = base_prices + np.random.uniform(-100, 100, 100)
    closes = base_prices + np.random.uniform(-100, 100, 100)
    
    # Garantir que high é o máximo e low é o mínimo
    highs = np.maximum(opens, closes) + np.random.uniform(50, 200, 100)
    lows = np.minimum(opens, closes) - np.random.uniform(50, 200, 100)
    
    h4_data = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': np.random.uniform(1000, 2000, 100),
        'atr_14': np.random.uniform(500, 800, 100),
    })
    
    data = {
        'h1': pd.DataFrame(),
        'h4': h4_data,
        'd1': pd.DataFrame(),
        'symbol': 'BTCUSDT'
    }
    
    # Criar environment
    env = CryptoFuturesEnv(
        data=data,
        initial_capital=10000,
        episode_length=50
    )
    
    # Reset
    obs, info = env.reset()
    
    print("\n=== Teste de Integração de Rewards Amplificados ===\n")
    
    # Cenário 1: Inatividade inicial
    print("Cenário 1: Inatividade inicial (10 steps)")
    for i in range(10):
        obs, reward, terminated, truncated, info = env.step(0)  # HOLD
        if i == 9:
            print(f"  - Após 10 HOLDs: flat_steps={env.flat_steps}")
            print(f"  - Reward no último step: {reward:.4f}")
            print(f"  - Componentes: {info.get('reward_components', {})}")
    
    # Cenário 2: Abrir posição (resetar flat_steps)
    print("\nCenário 2: Abrir posição LONG")
    obs, reward, terminated, truncated, info = env.step(1)  # OPEN_LONG
    if env.position is not None:
        print(f"  - Posição aberta com sucesso")
        print(f"  - flat_steps resetado: {env.flat_steps}")
        print(f"  - Reward ao abrir: {reward:.4f}")
    
    # Cenário 3: Manter posição com unrealized PnL
    print("\nCenário 3: Manter posição (5 steps) - r_unrealized ativo")
    for i in range(5):
        obs, reward, terminated, truncated, info = env.step(0)  # HOLD
        if i == 4 and env.position is not None:
            position_state = env._get_position_state()
            print(f"  - Após 5 steps com posição: pnl_pct={position_state.get('pnl_pct', 0):.4f}%")
            print(f"  - flat_steps durante posição: {env.flat_steps}")
            print(f"  - Reward no último step: {reward:.4f}")
            components = info.get('reward_components', {})
            print(f"  - r_unrealized: {components.get('r_unrealized', 0):.4f}")
            print(f"  - r_hold_bonus: {components.get('r_hold_bonus', 0):.4f}")
    
    # Cenário 4: Fechar posição
    print("\nCenário 4: Fechar posição")
    obs, reward, terminated, truncated, info = env.step(3)  # CLOSE
    components = info.get('reward_components', {})
    print(f"  - Posição fechada")
    print(f"  - flat_steps após fechar: {env.flat_steps}")
    print(f"  - Reward ao fechar: {reward:.4f}")
    if components.get('r_pnl', 0) != 0:
        print(f"  - r_pnl (amplificado): {components.get('r_pnl', 0):.4f}")
    
    # Cenário 5: Inatividade prolongada (> 20 steps) - r_inactivity ativo
    print("\nCenário 5: Inatividade prolongada (25 steps) - r_inactivity ativo")
    for i in range(25):
        obs, reward, terminated, truncated, info = env.step(0)  # HOLD
        if i == 24:
            components = info.get('reward_components', {})
            print(f"  - Após 25 HOLDs: flat_steps={env.flat_steps}")
            print(f"  - Reward no último step: {reward:.4f}")
            print(f"  - r_inactivity (penalidade): {components.get('r_inactivity', 0):.4f}")
    
    print("\n=== Teste Completo! ===\n")
    
    # Validações
    assert env.flat_steps > 20, "flat_steps deve ter ultrapassado 20"
    print("✓ Todas as validações passaram!")


if __name__ == "__main__":
    test_reward_integration()
