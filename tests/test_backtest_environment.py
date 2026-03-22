"""
Testes Unitários para BacktestEnvironment — F-12a

Validam determinismo, sequência e propriedades básicas.
"""

import pytest
import numpy as np
import pandas as pd
from backtest.backtest_environment import BacktestEnvironment


def create_sample_data():
    """Cria dicionário de dados históricos para testes."""
    n_candles_h1 = 1000
    dates_h1 = pd.date_range('2023-01-01', periods=n_candles_h1, freq='h')
    prices_h1 = 100.0 + np.cumsum(np.random.randn(n_candles_h1) * 0.5)

    h1_df = pd.DataFrame({
        'open_time': dates_h1,
        'open': prices_h1,
        'high': prices_h1 + np.abs(np.random.randn(n_candles_h1)),
        'low': prices_h1 - np.abs(np.random.randn(n_candles_h1)),
        'close': prices_h1,
        'volume': np.random.randint(1000, 10000, n_candles_h1),
    })

    # H4 (a cada 4 H1)
    h4_df = h1_df.iloc[::4].reset_index(drop=True).copy()

    # D1 (a cada 24 H1)
    d1_df = h1_df.iloc[::24].reset_index(drop=True).copy()

    return {
        'h1': h1_df,
        'h4': h4_df,
        'd1': d1_df,
        'symbol': 'BTCUSDT',
        'sentiment': {},
        'macro': {},
        'smc': {}
    }


class TestBacktestEnvironmentDeterminism:
    """Test 1: Determinismo com seed=42."""

    def test_deterministic_reset(self):
        """
        Testa se reset() com mesmo seed produz
        observações idênticas.
        """
        data = create_sample_data()

        env1 = BacktestEnvironment(data=data, seed=42)
        env2 = BacktestEnvironment(data=data, seed=42)

        obs1, info1 = env1.reset()
        obs2, info2 = env2.reset()

        # Observações devem ser EXATAMENTE iguais
        np.testing.assert_array_equal(obs1, obs2,
                                     err_msg="Reset não determinístico")

        # Capital deve ser igual
        assert env1.capital == env2.capital

    def test_deterministic_step_sequence(self):
        """
        Testa se sequência completa é determinística.
        """
        data = create_sample_data()
        actions = [0, 0, 0, 0, 0]  # Todos HOLD para teste simples

        env1 = BacktestEnvironment(data=data, seed=42)
        env1.reset()

        env2 = BacktestEnvironment(data=data, seed=42)
        env2.reset()

        for action in actions:
            obs1, _, _, _, info1 = env1.step(action)
            obs2, _, _, _, info2 = env2.step(action)

            np.testing.assert_array_almost_equal(obs1, obs2, decimal=5)
            assert info1['current_price'] == info2['current_price']


class TestBacktestEnvironmentSequential:
    """Test 2: Propriedades de sequência e terminação."""

    def test_episode_termination(self):
        """
        Testa que episódio termina (done=True) ao
        atingir final dos dados.
        """
        # Criar dados pequenos para teste rápido
        n = 20
        data = {
            'h1': pd.DataFrame({
                'open_time': pd.date_range('2023-01-01', periods=n, freq='h'),
                'open': np.ones(n) * 100,
                'high': np.ones(n) * 101,
                'low': np.ones(n) * 99,
                'close': np.ones(n) * 100,
                'volume': np.ones(n) * 1000,
            }),
            'h4': pd.DataFrame({
                'open_time': pd.date_range('2023-01-01', periods=n//4, freq='4h'),
                'open': np.ones(n//4) * 100,
                'high': np.ones(n//4) * 101,
                'low': np.ones(n//4) * 99,
                'close': np.ones(n//4) * 100,
                'volume': np.ones(n//4) * 1000,
            }),
            'd1': pd.DataFrame({
                'open_time': pd.date_range('2023-01-01', periods=1, freq='d'),
                'open': [100],
                'high': [101],
                'low': [99],
                'close': [100],
                'volume': [1000],
            }),
            'symbol': 'BTCUSDT',
            'sentiment': {},
            'macro': {},
            'smc': {}
        }

        env = BacktestEnvironment(data=data, seed=42)
        env.reset()

        # Fazer steps até done
        done = False
        steps = 0
        while not done and steps < 100:
            _, _, done, _, _ = env.step(0)  # HOLD
            steps += 1

        assert done, "Episode não terminou"


class TestBacktestEnvironmentBasics:
    """Test 3: Propriedades básicas."""

    def test_observation_shape(self):
        """Testa que observação sempre tem shape (104,)."""
        data = create_sample_data()
        env = BacktestEnvironment(data=data)
        obs, _ = env.reset()

        assert obs.shape == (104,), f"Shape incorreta: {obs.shape}, esperado (104,)"
        assert obs.dtype == np.float32

    def test_action_space_validity(self):
        """
        Testa que ações válidas (0-4) não causam erros.
        """
        data = create_sample_data()
        env = BacktestEnvironment(data=data)
        env.reset()

        for action in [0, 1, 2, 3, 4]:
            try:
                _, _, done, _, _ = env.step(action)
                if done:
                    break
            except Exception as e:
                pytest.fail(f"Ação {action} causou erro: {e}")

    def test_capital_tracking(self):
        """
        Testa que capital é rastreado corretamente.
        """
        initial_capital = 5000
        data = create_sample_data()
        env = BacktestEnvironment(data=data, initial_capital=initial_capital)
        _, _ = env.reset()

        # Capital deve começar igual ao inicial
        assert env.capital == initial_capital

        # Após steps, capital deve permanecer > 0
        for _ in range(20):
            _, _, done, _, _ = env.step(0)
            if done:
                break

        assert env.capital > 0, "Capital zerou"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
