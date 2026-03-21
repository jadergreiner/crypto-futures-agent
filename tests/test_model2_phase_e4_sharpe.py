"""Testes automatizados da Fase E.4: Analise Comparativa PPO"""

import json
import sqlite3
import pytest
from pathlib import Path
import numpy as np

# Adjust sys path
import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.phase_e4_sharpe_analysis import PPOEvaluator


@pytest.fixture
def mock_db(tmp_path):
    db_path = tmp_path / "test_modelo2.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE training_episodes (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            label TEXT,
            reward_proxy REAL,
            features_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Inserir alguns cenarios
    features = {
        "latest_candle": {"close": 50000},
        "volatility": {"atr_14": 100},
        "multi_timeframe": {"H4": {"close": 50000}},
        "funding_rates": {"sentiment": "bullish"},
        "open_interest": {"oi_sentiment": "bearish"}
    }
    feat_json = json.dumps(features)
    
    episodes = [
        ("BTCUSDT", "win", 1.0, feat_json),
        ("BTCUSDT", "loss", -1.0, feat_json),
        ("ETHUSDT", "win", 0.5, feat_json),
        ("ETHUSDT", "context", 0.0, feat_json)
    ]
    
    c.executemany(
        "INSERT INTO training_episodes (symbol, label, reward_proxy, features_json) VALUES (?, ?, ?, ?)",
        episodes
    )
    conn.commit()
    conn.close()
    
    return db_path

class MockModel:
    def __init__(self, fixed_action=0):
        self.fixed_action = fixed_action
        
    def predict(self, obs, deterministic=True):
        return self.fixed_action, None


def test_evaluator_loading_episodes(mock_db):
    evaluator = PPOEvaluator(model2_db_path=mock_db)
    
    episodes = evaluator.load_episodes()
    assert "BTCUSDT" in episodes
    assert "ETHUSDT" in episodes
    assert len(episodes["BTCUSDT"]) == 2
    assert len(episodes["ETHUSDT"]) == 2
    
    # Valida extracao
    assert episodes["BTCUSDT"][0]["label"] == "win"
    assert episodes["BTCUSDT"][0]["reward_proxy"] == 1.0
    
    feats = episodes["BTCUSDT"][0]["features"]
    assert len(feats) == evaluator.n_features
    # check funding rate sentiment (bullish -> 1.0, idx 14)
    # let's not hardcode exact index, just check type and sum > 0
    assert isinstance(feats, np.ndarray)
    assert np.sum(feats) > 0

def test_evaluator_simulation_mlp_vs_lstm(mock_db):
    evaluator = PPOEvaluator(model2_db_path=mock_db)
    episodes = evaluator.load_episodes()
    
    # Vamos mockar o modelo que sempre preve LONG=1
    model_always_long = MockModel(fixed_action=1)
    
    # MLP (flat)
    mlp_metrics = evaluator.simulate_policy(model_always_long, is_lstm=False, episodes_by_symbol=episodes)
    assert mlp_metrics["total_trades"] == 4  # 4 episodios * action 1
    
    # LSTM
    lstm_metrics = evaluator.simulate_policy(model_always_long, is_lstm=True, episodes_by_symbol=episodes)
    assert lstm_metrics["total_trades"] == 4
    
    # Se action=1 e base=1.0 -> trade=0.02. base=-1.0 -> trade=-0.01. base=0.5 -> 0.02. base=0.0 -> -0.01
    # Returns: BTC(0.02, -0.01), ETH(0.02, -0.01)
    # Cumulative: 0.02*2 - 0.01*2 = 0.02
    assert abs(mlp_metrics["cumulative_return"] - 0.02) < 1e-4

def test_run_analysis_with_none_model(mock_db):
    # run analysis method natively catches path/load errors, and falls back to random/missing
    evaluator = PPOEvaluator(model2_db_path=mock_db)
    res = evaluator.run_analysis()
    
    assert res["status"] == "ok"
    assert res["episodes_processed"] == 4
    assert "mlp_baseline" in res
    assert "lstm_model" in res
    assert "comparison" in res
    assert "sharpe_delta_pct" in res["comparison"]
