"""
Testes unitários para o script de treinamento PPO LSTM (train_ppo_lstm.py).
"""

import sys
import pytest
import sqlite3
import json
import numpy as np
from pathlib import Path

# Adiciona repo root ao path se necessário
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.train_ppo_lstm import PPOLstmTrainer


@pytest.fixture
def dummy_db_path(tmp_path):
    """Fixture que cria banco sqlite na memória/arquivo temporario com episodes válidos."""
    db_file = tmp_path / "model2_test.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE training_episodes (
            id INTEGER PRIMARY KEY, episode_key TEXT, cycle_run_id TEXT, execution_id TEXT,
            symbol TEXT, timeframe TEXT, status TEXT, event_timestamp TEXT,
            label TEXT, reward_proxy REAL, features_json TEXT, target_json TEXT,
            created_at TEXT
        )
    """)
    
    # Criar 5 episódios fake
    for i in range(5):
        features = {
            "latest_candle": {"close": 50000 + i*100},
            "volatility": {"atr_14": 1.5},
            "funding_rates": {"sentiment": "bullish" if i % 2 == 0 else "neutral"},
            "open_interest": {"current_oi": 150000.0}
        }
        cursor.execute(
            """INSERT INTO training_episodes 
               (symbol, timeframe, label, reward_proxy, features_json, created_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                "BTCUSDT", "H4",
                "win" if i % 2 == 0 else "loss",
                1.0 if i % 2 == 0 else -0.5,
                json.dumps(features),
                f"2026-03-01T12:00:0{i}Z"
            )
        )
    conn.commit()
    conn.close()
    return db_file


def test_trainer_initializes_and_loads(dummy_db_path, tmp_path):
    """Testa carregamento básico do trainer com política mlp."""
    checkpoints = tmp_path / "checkpoints"
    trainer = PPOLstmTrainer(
        model2_db_path=dummy_db_path,
        checkpoint_dir=checkpoints,
        policy_type="mlp"
    )
    result = trainer.load_episodes_from_db()
    
    assert result["status"] != "error"
    assert result["total_episodes"] == 5
    assert trainer.episodes_data is not None
    assert len(trainer.episodes_data) == 5

    data_result = trainer.episodes_to_training_dataset()
    assert data_result["status"] == "ok"
    assert len(trainer.obs_data) == 5
    assert len(trainer.rewards_data) == 5


def test_trainer_train_lstm_smoke(dummy_db_path, tmp_path):
    """Testa sanidade de treinamento LSTM com apenas 1 timestep para checar formato."""
    checkpoints = tmp_path / "checkpoints"
    trainer = PPOLstmTrainer(
        model2_db_path=dummy_db_path,
        checkpoint_dir=checkpoints,
        policy_type="lstm"
    )
    trainer.load_episodes_from_db()
    trainer.episodes_to_training_dataset()
    
    # Roda apenas 1 época/passo virtual para validarmos se LSTMSignalEnvironment não quebra
    res = trainer.train(timesteps=5)
    
    assert res["status"] == "ok"
    assert res["policy"] == "lstm"
    
    model_file = checkpoints / "lstm" / "ppo_model_lstm.zip"
    assert model_file.exists()
