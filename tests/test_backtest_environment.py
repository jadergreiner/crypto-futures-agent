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
            assert info1['balance'] == info2['balance']


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

        dates = pd.date_range('2023-01-01', periods=n_candles, freq='h')
        
        # Simular preço crescente com ruído
        base_price = 100.0
        prices = base_price + np.cumsum(np.random.randn(n_candles) * 0.5)
        
        return pd.DataFrame({
            'open_time': dates,
            'open': prices,
            'high': prices + np.abs(np.random.randn(n_candles)),
            'low': prices - np.abs(np.random.randn(n_candles)),
            'close': prices,
            'volume': np.random.randint(1000, 10000, n_candles),
        })
    
    def test_deterministic_reset(self, sample_data):
        """
        Testa se reset() com mesmo seed produz
        observações idênticas.
        """
        env1 = BacktestEnvironment(data_df=sample_data, seed=42)
        env2 = BacktestEnvironment(data_df=sample_data, seed=42)
        
        obs1, info1 = env1.reset()
        obs2, info2 = env2.reset()
        
        # Observações devem ser EXATAMENTE iguais
        np.testing.assert_array_equal(obs1, obs2,
                                     err_msg="ResetNão determinístico")
        
        # Prices devem ser iguais
        assert info1['current_price'] == info2['current_price']
        assert info1['balance'] == info2['balance']
    
    def test_deterministic_step_sequence(self, sample_data):
        """
        Testa se sequência completa é determinística.
        """
        # Executar 10 steps em dois ambientes com seed=42
        actions = [0, 1, 0, 0, 3, 0, 0, 0, 0, 0]  # HOLD, OPEN_LONG, etc.
        
        results1 = []
        env1 = BacktestEnvironment(data_df=sample_data, seed=42)
        env1.reset()
        for action in actions:
            obs, reward, done, trunc, info = env1.step(action)
            results1.append({
                'obs_sum': obs.sum(),
                'price': info['current_price'],
                'balance': info['balance'],
            })
        
        results2 = []
        env2 = BacktestEnvironment(data_df=sample_data, seed=42)
        env2.reset()
        for action in actions:
            obs, reward, done, trunc, info = env2.step(action)
            results2.append({
                'obs_sum': obs.sum(),
                'price': info['current_price'],
                'balance': info['balance'],
            })
        
        # Comparar resultados
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1['price'] == r2['price']
            assert r1['balance'] == r2['balance']
            np.testing.assert_almost_equal(r1['obs_sum'], r2['obs_sum'],
                                          decimal=6)
    
    def test_different_seeds_different_results(self, sample_data):
        """
        Testa que seeds diferentes produzem resultados
        diferentes (não totalmente dependentes dos dados).
        """
        env1 = BacktestEnvironment(data_df=sample_data, seed=42)
        env2 = BacktestEnvironment(data_df=sample_data, seed=999)
        
        obs1, _ = env1.reset()
        obs2, _ = env2.reset()
        
        # Não devem ser IGUAIS (exceto por coincidência)
        # (Com dados sintéticos pseudo-randômicos, a chance é baixa)
        assert not np.allclose(obs1, obs2)


class TestBacktestEnvironmentSequential:
    """Test 2: Avanço sequencial — Index aumenta corretamente."""
    
    @pytest.fixture
    def sample_data(self):
        n_candles = 500
        dates = pd.date_range('2023-01-01', periods=n_candles, freq='h')
        prices = 100.0 + np.cumsum(np.random.randn(n_candles) * 0.5)
        
        return pd.DataFrame({
            'open_time': dates,
            'open': prices,
            'high': prices + 0.5,
            'low': prices - 0.5,
            'close': prices,
            'volume': 1000,
        })
    
    def test_index_advances(self, sample_data):
        """Testa que current_index avança a cada step."""
        env = BacktestEnvironment(data_df=sample_data, seed=42)
        env.reset(start_index=100)
        
        assert env.current_index == 100
        
        # Fazer 10 steps
        for i in range(10):
            env.step(0)  # HOLD
            assert env.current_index == 100 + i + 1
    
    def test_step_prices_are_sequential(self, sample_data):
        """
        Testa que preços retornados nos steps correspondem
        aos dados séquenciais.
        """
        env = BacktestEnvironment(data_df=sample_data, seed=42)
        env.reset(start_index=50)
        
        for i in range(10):
            _, _, _, _, info = env.step(0)
            expected_price = sample_data.iloc[51 + i]['close']
            assert info['current_price'] == expected_price
    
    def test_episode_termination(self, sample_data):
        """
        Testa que episódio termina (done=True) ao
        atingir final dos dados.
        """
        short_data = sample_data.iloc[:10].copy()
        env = BacktestEnvironment(data_df=short_data, seed=42)
        env.reset(start_index=0)
        
        # Fazer steps até final
        done = False
        steps = 0
        while not done and steps < 20:
            _, _, done, _, _ = env.step(0)
            steps += 1
        
        assert done, "Episode não terminou ao atingir final"
        assert steps == len(short_data) - 1  # n_candles - 1


class TestBacktestEnvironmentBasics:
    """Test 3: Propriedades básicas de reset/step."""
    
    @pytest.fixture
    def sample_data(self):
        n_candles = 200
        dates = pd.date_range('2023-01-01', periods=n_candles, freq='h')
        prices = 50.0 + np.linspace(0, 10, n_candles)
        
        return pd.DataFrame({
            'open_time': dates,
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': 5000,
        })
    
    def test_observation_shape(self, sample_data):
        """Testa que observação sempre tem shape (104,)."""
        env = BacktestEnvironment(data_df=sample_data)
        obs, _ = env.reset()
        
        assert obs.shape == (104,), f"Shape incorreta: {obs.shape}"
        assert obs.dtype == np.float32
        
        # Verificar em alguns steps
        for _ in range(5):
            obs, _, _, _, _ = env.step(0)
            assert obs.shape == (104,)
    
    def test_action_space_validity(self, sample_data):
        """
        Testa que ações válidas (0-4) não causam erros.
        """
        env = BacktestEnvironment(data_df=sample_data)
        env.reset()
        
        for action in [0, 1, 2, 3, 4]:
            try:
                _, _, _, _, _ = env.step(action)
            except Exception as e:
                pytest.fail(f"Ação {action} causou erro: {e}")
    
    def test_capital_tracking(self, sample_data):
        """
        Testa que capital é rastreado corretamente.
        """
        initial_capital = 5000
        env = BacktestEnvironment(data_df=sample_data,
                                 initial_capital=initial_capital)
        _, _ = env.reset()
        
        # Capital deve começar igual ao inicial
        assert env.capital == initial_capital
        
        # Após steps, capital pode mudar mas não deve ser 0
        for _ in range(20):
            env.step(0)
        
        assert env.capital > 0, "Capital zerou (erro de lógica)"
    
    def test_trade_history_population(self, sample_data):
        """
        Testa que história de trades é preenchida ao
        fazer trades (OPEN_LONG, CLOSE).
        """
        env = BacktestEnvironment(data_df=sample_data)
        env.reset()
        
        # Fazer OPEN_LONG
        env.step(1)
        assert len(env.trade_history) == 1
        assert env.trade_history[0]['side'] == 'LONG'
        
        # Fazer CLOSE
        env.step(3)
        assert len(env.trade_history) == 1  # Mesma entrada, atualizada
        assert 'exit_price' in env.trade_history[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
