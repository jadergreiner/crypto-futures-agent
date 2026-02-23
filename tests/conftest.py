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


# ============================================================================
# FIXTURES: Klines Cache Manager (S2-0 Data Pipeline)
# ============================================================================
# Adicionadas para testes de data/scripts/klines_cache_manager.py

import sqlite3
from datetime import datetime, timedelta


@pytest.fixture
def temp_db_klines():
    """Cria database temporário para testes de klines (SQLite em memória)."""
    try:
        from data.scripts.klines_cache_manager import DB_SCHEMA_SQL
    except ImportError:
        # Fallback se import falhar
        DB_SCHEMA_SQL = """
        CREATE TABLE IF NOT EXISTS klines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            open_time INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            close_time INTEGER NOT NULL,
            quote_volume REAL NOT NULL,
            trades INTEGER,
            taker_buy_volume REAL,
            taker_buy_quote_volume REAL,
            is_validated BOOLEAN DEFAULT 0,
            sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, open_time),
            CHECK (low <= open AND low <= close AND high >= open AND high >= close)
        );
        CREATE INDEX IF NOT EXISTS idx_symbol_time ON klines(symbol, open_time);
        CREATE INDEX IF NOT EXISTS idx_validated ON klines(is_validated);
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            sync_type TEXT NOT NULL,
            rows_inserted INTEGER,
            rows_updated INTEGER,
            start_time INTEGER,
            end_time INTEGER,
            duration_seconds REAL,
            status TEXT,
            error_message TEXT,
            sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_sync_symbol ON sync_log(symbol);
        """
    
    conn = sqlite3.connect(":memory:")
    conn.executescript(DB_SCHEMA_SQL)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def valid_kline_array_klines():
    """Um candle Binance válido [array format] para testes de klines."""
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    return [
        now_ms,                    # open_time
        50000.0,                   # open
        51000.0,                   # high
        49000.0,                   # low
        50500.0,                   # close
        123.45,                    # volume
        now_ms + 4 * 3600 * 1000,  # close_time (4h depois)
        6234567.89,                # quote_volume
        1234,                      # trades
        61.725,                    # taker_buy_volume
        3117283.945                # taker_buy_quote_volume
    ]


@pytest.fixture
def valid_kline_dict_klines():
    """Um candle em formato dicionário para validação de klines."""
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    return {
        "open_time": now_ms,
        "open": 50000.0,
        "high": 51000.0,
        "low": 49000.0,
        "close": 50500.0,
        "volume": 123.45,
        "close_time": now_ms + 4 * 3600 * 1000,
        "quote_volume": 6234567.89,
        "trades": 1234
    }


@pytest.fixture
def mock_symbol_list_klines():
    """60 símbolos Binance válidos para testes."""
    return [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT",
        "XRPUSDT", "MATICUSDT", "LINKUSDT", "DOTUSDT", "UNIUSDT",
        "LTCUSDT", "BCUSDT", "SOLUSDT", "AVAXUSDT", "TRXUSDT",
        "FTMUSDT", "XLMUSDT", "XTZUSDT", "ATOMUSDT", "NEOUSDT",
        "VETUSDT", "EGLDUSDT", "THETAUSDT", "ALGOUSDT", "ZILUSDT",
        "ONTUSDT", "CRVUSDT", "KSMAUSDT", "COTIUSDT", "MIDUSDT",
        "SKLUSDT", "AAVAUSDT", "SNXUSDT", "YFIUSDT", "ZECUSDT",
        "DCRUSDT", "OMGUSDT", "ANKRUSDT", "BALANCERUSDT", "1INCHUSDT",
        "CHZUSDT", "BANDUSDT", "MITHUSDT", "YFIIUSDT", "CAKEUSDT",
        "NKNUSDT", "SCUSDT", "AUDIOUSDT", "OCEANUSDT", "SUNUSDT",
        "ROSEUSDT", "DYDXUSDT", "RAYUSDT", "GUSHUSDT", "XVALUSDT",
        "GMTUSDT", "OPSUSDT", "APUSDT", "GALUSDT", "LDOUSDT"
    ]


@pytest.fixture
def sample_klines_batch_klines(valid_kline_array_klines):
    """Cria 100 candles sequenciais para teste de batch insert."""
    batch = []
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    
    for i in range(100):
        kline = [
            now_ms - (100 - i) * 4 * 3600 * 1000,  # open_time
            50000.0 + i,                             # open
            51000.0 + i,                             # high
            49000.0 + i,                             # low
            50500.0 + i,                             # close
            100 + i * 0.5,                           # volume
            now_ms - (99 - i) * 4 * 3600 * 1000,   # close_time
            5000000 + i * 50000,                     # quote_volume
            1000 + i,                                # trades
            50 + i * 0.25,                           # taker_buy_volume
            2500000 + i * 25000                      # taker_buy_quote_volume
        ]
        batch.append(kline)
    
    return batch
