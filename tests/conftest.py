"""
Configurações de Testes e Fixtures

Fornece fixtures compartilhadas para testes de TASK-005:
- Mock do ambiente CryptoFuturesEnv (60 pares)
- Mock de dados históricos (5 anos)
- Mock de diretório de checkpoints
- Fixtures de configuração PPO
"""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np


class MockCryptoFuturesEnv:
    """Mock simplificado do CryptoFuturesEnv para testes."""

    def __init__(self, n_pairs: int = 60, state_dim: int = 1320):
        self.n_pairs = n_pairs
        self.state_dim = state_dim
        self.observation_space = type("Space", (), {"shape": (state_dim,)})()
        self.action_space = type("Space", (), {"n": 3})()  # HOLD, LONG, SHORT
        self.reset_count = 0

    def reset(self) -> np.ndarray:
        """Reset environment, retorna estado inicial."""
        self.reset_count += 1
        return np.random.randn(self.state_dim).astype(np.float32)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """Step no ambiente."""
        state = np.random.randn(self.state_dim).astype(np.float32)
        reward = np.random.randn() * 0.1  # Pequena recompensa
        done = np.random.random() < 0.01  # Raro terminar
        info = {
            "portfolio_value": 10000.0,
            "trades_executed": np.random.randint(0, 5),
        }
        return state, reward, done, info

    def close(self) -> None:
        """Fecha environment."""
        pass


@pytest.fixture
def mock_env():
    """Fixture: Mock do CryptoFuturesEnv (60 pares, 1320D)."""
    env = MockCryptoFuturesEnv(n_pairs=60, state_dim=1320)
    yield env
    env.close()


@pytest.fixture
def mock_data_5years() -> Dict[str, np.ndarray]:
    """Fixture: Mock de dados históricos (500k timesteps)."""
    # Gerar 500k timesteps x 22 features (após PCA)
    timesteps = 500000
    features = 22
    n_pairs = 60

    data = {
        "timestamps": np.arange(timesteps),
        "ohlcv": np.random.randn(timesteps, n_pairs, features).astype(np.float32),
        "returns": np.random.randn(timesteps, n_pairs).astype(np.float32),
        "symbols": [f"SYM{i}" for i in range(n_pairs)],
    }
    return data


@pytest.fixture
def mock_checkpoint_dir() -> str:
    """Fixture: Diretório temporário para checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        checkpoint_dir = Path(tmpdir) / "checkpoints"
        checkpoint_dir.mkdir()
        yield str(checkpoint_dir)


@pytest.fixture
def mock_ppo_config() -> Dict[str, Any]:
    """Fixture: Configuração PPO válida."""
    return {
        "learning_rate": 3e-4,
        "n_steps": 2048,
        "batch_size": 64,
        "n_epochs": 10,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "ent_coef": 0.001,
        "clip_range": 0.2,
        "max_grad_norm": 0.5,
    }


@pytest.fixture
def mock_checkpoint_data() -> Dict[str, Any]:
    """Fixture: Dados de un checkpoint válido."""
    return {
        "step": 50000,
        "timestamp": "2026-02-22T12:00:00",
        "model": {"type": "PPO", "policy_net": "mock"},
        "metrics": {
            "sharpe": 1.2,
            "loss": 0.05,
            "kl_div": 0.02,
            "entropy": 0.8,
            "win_rate": 0.55,
            "drawdown": 3.2,
        },
        "checkpoint_name": "ppo_step_050000_2026-02-22T120000",
    }


@pytest.fixture
def encryption_key_env(monkeypatch) -> str:
    """Fixture: Define variável de ambiente com chave Fernet válida."""
    # Gerar chave Fernet válida para testes
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PPO_CHECKPOINT_KEY", key)
    return key


class MockMetricsBuffer:
    """Buffer simplificado de métricas para testes de monitor."""

    def __init__(self):
        self.metrics = {
            "step": [],
            "episode_reward": [],
            "loss_policy": [],
            "kl_divergence": [],
            "entropy": [],
        }

    def append(self, step: int, reward: float, loss: float, kl: float, entropy: float):
        """Adiciona métrica."""
        self.metrics["step"].append(step)
        self.metrics["episode_reward"].append(reward)
        self.metrics["loss_policy"].append(loss)
        self.metrics["kl_divergence"].append(kl)
        self.metrics["entropy"].append(entropy)

    def get_latest_kl(self) -> float:
        """Retorna KL mais recente."""
        return self.metrics["kl_divergence"][-1] if self.metrics["kl_divergence"] else 0.0


@pytest.fixture
def mock_metrics_buffer() -> MockMetricsBuffer:
    """Fixture: Buffer de métricas mock."""
    return MockMetricsBuffer()
