"""Test Phase D.4: Simulação de dados para validar análise de correlação.

Cria dados sintéticos realistas com correlação entre funding rates e performance.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import MODEL2_DB_PATH


def create_synthetic_episodes(db_path: Path | str, n_episodes: int = 100):
    """Cria episodes sintéticos com correlação realista."""
    import numpy as np

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Limpar episodes antigos (apenas de teste)
    conn.execute("DELETE FROM training_episodes WHERE episode_key LIKE 'synthetic:%'")

    np.random.seed(42)  # Reprodutibilidade

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    for i in range(n_episodes):
        symbol = symbols[i % len(symbols)]

        # Correlação parcial: bullish FR → maior chance de win
        fr_sentiment = np.random.choice(["bullish", "neutral", "bearish"], p=[0.33, 0.33, 0.34])
        oi_sentiment = np.random.choice(["accumulating", "neutral", "distributing"], p=[0.35, 0.30, 0.35])

        # Label correlacionado com sentimentos
        rand_val = np.random.random()
        if fr_sentiment == "bullish" and oi_sentiment == "accumulating":
            # Maior probabilidade de win
            label = "win" if rand_val < 0.65 else ("loss" if rand_val < 0.85 else "breakeven")
        elif fr_sentiment == "bearish" or oi_sentiment == "distributing":
            # Maior probabilidade de loss
            label = "loss" if rand_val < 0.65 else ("win" if rand_val < 0.20 else "breakeven")
        else:
            # Neutro
            label = "win" if rand_val < 0.45 else ("loss" if rand_val < 0.75 else "breakeven")

        # Reward correlacionado com label
        if label == "win":
            reward_proxy = np.random.uniform(0.1, 1.0)
        elif label == "loss":
            reward_proxy = np.random.uniform(-1.0, -0.1)
        else:
            reward_proxy = np.random.uniform(-0.05, 0.05)

        # Ajuste fino: FR bullish aumenta reward
        if fr_sentiment == "bullish":
            reward_proxy += 0.1
        elif fr_sentiment == "bearish":
            reward_proxy -= 0.1

        episode_key = f"synthetic:{i}:{now_ms}"
        features = {
            "latest_candle": {
                "timestamp": now_ms - (i * 60000),
                "open": 100.0 + np.random.uniform(-5, 5),
                "high": 105.0 + np.random.uniform(-5, 5),
                "low": 95.0 + np.random.uniform(-5, 5),
                "close": 100.0 + np.random.uniform(-5, 5),
                "volume": 1000000 + np.random.uniform(-100000, 100000),
            },
            "volatility": {
                "atr_14": np.random.uniform(0.5, 3.0),
                "bollinger_bands": {
                    "upper": 105.0 + np.random.uniform(-5, 5),
                    "lower": 95.0 + np.random.uniform(-5, 5),
                    "sma": 100.0 + np.random.uniform(-5, 5),
                },
            },
            "multi_timeframe": {
                "H1": {"close": 100.0 + np.random.uniform(-5, 5)},
                "H4": {"close": 100.0 + np.random.uniform(-5, 5)},
                "D1": {"close": 100.0 + np.random.uniform(-5, 5)},
            },
            "funding_rates": {
                "latest_rate": np.random.uniform(-0.001, 0.001),
                "sentiment": fr_sentiment,
                "trend": np.random.choice(["increasing", "stable", "decreasing"]),
                "avg_rate_24h": np.random.uniform(-0.0005, 0.0005),
            },
            "open_interest": {
                "current_oi": np.random.uniform(50000, 200000),
                "oi_sentiment": oi_sentiment,
                "change_direction": np.random.choice(["up", "steady", "down"]),
            },
        }

        conn.execute(
            """
            INSERT OR REPLACE INTO training_episodes (
                episode_key,
                cycle_run_id,
                execution_id,
                symbol,
                timeframe,
                status,
                event_timestamp,
                label,
                reward_proxy,
                features_json,
                target_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                episode_key,
                "synthetic_test",
                i,
                symbol,
                "H1",
                "EXECUTED",
                now_ms - (i * 60000),
                label,
                reward_proxy,
                json.dumps(features, sort_keys=True),
                json.dumps({"objective": "test"}, sort_keys=True),
                now_ms,
            ),
        )

    conn.commit()
    conn.close()

    print(f"✅ Criados {n_episodes} episodes sintéticos com correlações realistas")


if __name__ == "__main__":
    db_path = Path(MODEL2_DB_PATH)
    print(f"Criando episodes sintéticos em {db_path}...")
    create_synthetic_episodes(db_path, n_episodes=100)
