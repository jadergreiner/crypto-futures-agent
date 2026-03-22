"""
Testes unitários para EpisodeLoader (M2-019.2).

Cobre:
- Normalização individual de features
- Carregamento de episódios de banco in-memory
- Filtragem por symbol e timeframe
- Descarte de episódios pending
- Validação da lista final
- Edge cases (banco vazio, episódios < min, features inválidas, NaN)
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any

from agent.episode_loader import (
    EpisodeNormalizer,
    load_episodes,
    validate_episodes,
)


class TestEpisodeNormalizer(unittest.TestCase):
    """Testa normalização de features."""

    def test_normalize_value_in_range(self):
        """Normaliza valor dentro do intervalo."""
        # [0, 100] -> [-1, 1]
        result = EpisodeNormalizer.normalize_value(50, 0, 100)
        self.assertAlmostEqual(result, 0.0, places=5)

    def test_normalize_value_min_bound(self):
        """Normaliza valor no limite mínimo."""
        result = EpisodeNormalizer.normalize_value(0, 0, 100)
        self.assertAlmostEqual(result, -1.0, places=5)

    def test_normalize_value_max_bound(self):
        """Normaliza valor no limite máximo."""
        result = EpisodeNormalizer.normalize_value(100, 0, 100)
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_normalize_value_outside_range(self):
        """Clamps valor fora do intervalo."""
        result = EpisodeNormalizer.normalize_value(150, 0, 100)
        self.assertAlmostEqual(result, 1.0, places=5)

        result = EpisodeNormalizer.normalize_value(-50, 0, 100)
        self.assertAlmostEqual(result, -1.0, places=5)

    def test_normalize_value_nan(self):
        """NaN retorna 0."""
        result = EpisodeNormalizer.normalize_value(float('nan'), 0, 100)
        self.assertEqual(result, 0.0)

    def test_normalize_value_infinity(self):
        """Infinito retorna 0."""
        result = EpisodeNormalizer.normalize_value(float('inf'), 0, 100)
        self.assertEqual(result, 0.0)

        result = EpisodeNormalizer.normalize_value(float('-inf'), 0, 100)
        self.assertEqual(result, 0.0)

    def test_normalize_value_none(self):
        """None retorna 0."""
        result = EpisodeNormalizer.normalize_value(None, 0, 100)
        self.assertEqual(result, 0.0)

    def test_normalize_features_empty_dict(self):
        """Dict vazio retorna array de 36 zeros."""
        result = EpisodeNormalizer.normalize_features({})
        self.assertEqual(len(result), 36)
        self.assertTrue(all(f == 0.0 for f in result))

    def test_normalize_features_partial_dict(self):
        """Dict parcial é preenchido com zeros."""
        features_dict = {
            "open_norm": 0.0,
            "close_norm": 0.5,
        }
        result = EpisodeNormalizer.normalize_features(features_dict)
        self.assertEqual(len(result), 36)
        # Primeiros 4 features: open, high, low, close
        # open_norm=0.0 com bounds (-0.5, 0.5) normaliza para 0.0
        self.assertEqual(result[0], 0.0)  # open_norm=0
        # close_norm=0.5 com bounds (-0.5, 0.5) normaliza para 1.0
        self.assertAlmostEqual(result[3], 1.0, places=5)  # close_norm=0.5
        # Resto zeros
        self.assertTrue(all(f == 0.0 for f in result[4:]))

    def test_normalize_features_full_valid(self):
        """Dict completo com values válidos."""
        features_dict = {
            "open_norm": 0.0,
            "high_norm": 0.1,
            "low_norm": -0.1,
            "close_norm": 0.05,
            "volume_norm": 0.5,
            "rsi": 50.0,
            "macd_line": 0.0,
            "macd_signal": 0.0,
            "bb_upper": 0.2,
            "bb_lower": -0.2,
            "atr_norm": 0.1,
            "h1_open_norm": 0.0,
            "h1_close_norm": 0.0,
            "h1_volume_norm": 0.5,
            "h4_open_norm": 0.0,
            "h4_close_norm": 0.0,
            "h4_volume_norm": 0.5,
            "d1_open_norm": 0.0,
            "d1_close_norm": 0.0,
            "d1_volume_norm": 0.5,
            "fr_sentiment": 0.0,
            "oi_sentiment": 0.0,
            "ls_ratio": 0.5,
            "smc_zone_proximity": 0.5,
            "smc_rejection_strength": 0.5,
            "smc_direction_bias": 0.0,
        }
        result = EpisodeNormalizer.normalize_features(features_dict)
        self.assertEqual(len(result), 36)
        # Todos devem estar em [-1, 1]
        self.assertTrue(all(-1.0 <= f <= 1.0 for f in result))

    def test_normalize_features_non_dict(self):
        """Input não-dict retorna array de 36 zeros."""
        result = EpisodeNormalizer.normalize_features(None)
        self.assertEqual(len(result), 36)
        self.assertTrue(all(f == 0.0 for f in result))

        result = EpisodeNormalizer.normalize_features("invalid")
        self.assertEqual(len(result), 36)
        self.assertTrue(all(f == 0.0 for f in result))


class TestEpisodeLoader(unittest.TestCase):
    """Testa carregamento de episódios."""

    def setUp(self):
        """Cria banco SQLite in-memory para testes."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def tearDown(self):
        """Fecha conexão."""
        self.conn.close()

    def _create_schema(self):
        """Cria tabela training_episodes em bank teste."""
        self.conn.execute(
            """
            CREATE TABLE training_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_key TEXT NOT NULL UNIQUE,
                cycle_run_id TEXT NOT NULL,
                execution_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                status TEXT NOT NULL,
                event_timestamp INTEGER NOT NULL,
                label TEXT NOT NULL,
                reward_proxy REAL,
                features_json TEXT NOT NULL,
                target_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        self.conn.commit()

    def _insert_episode(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "H4",
        label: str = "win",
        reward: float = 0.5,
        features_dict: dict[str, Any] | None = None,
    ) -> int:
        """Insere episódio de teste."""
        if features_dict is None:
            features_dict = {}

        episode_key = f"{symbol}_{timeframe}_{label}_{self.conn.execute('SELECT COUNT(*) FROM training_episodes').fetchone()[0]}"
        self.conn.execute(
            """
            INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, features_json,
                target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                episode_key,
                "cycle_001",
                1,
                symbol,
                timeframe,
                "COMPLETED",
                1234567890,
                label,
                reward,
                json.dumps(features_dict),
                "{}",
                1234567890,
            ),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT last_insert_rowid() AS id"
        ).fetchone()["id"]

    def test_load_episodes_nonexistent_db(self):
        """Retorna [] para banco não existente."""
        result = load_episodes(
            "/nonexistent/path.db",
            "BTCUSDT",
            "H4",
            min_episodes=20,
        )
        self.assertEqual(result, [])

    def test_load_episodes_empty_table(self):
        """Retorna [] quando tabela vazia."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            result = load_episodes(db_path, "BTCUSDT", "H4", min_episodes=1)
            self.assertEqual(result, [])
        finally:
            Path(db_path).unlink()

    def test_load_episodes_insufficient(self):
        """Retorna [] quando episódios < min_episodes."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE training_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_key TEXT NOT NULL UNIQUE,
                    cycle_run_id TEXT NOT NULL,
                    execution_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    status TEXT NOT NULL,
                    event_timestamp INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    reward_proxy REAL,
                    features_json TEXT NOT NULL,
                    target_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            # Insere 5 episódios válidos
            for i in range(5):
                conn.execute(
                    """
                    INSERT INTO training_episodes (
                        episode_key, cycle_run_id, execution_id, symbol,
                        timeframe, status, event_timestamp, label,
                        reward_proxy, features_json, target_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"ep_{i}",
                        "cycle_001",
                        1,
                        "BTCUSDT",
                        "H4",
                        "COMPLETED",
                        1234567890,
                        "win",
                        0.5,
                        "{}",
                        "{}",
                        1234567890,
                    ),
                )
            conn.commit()
            conn.close()

            # min_episodes=20 mas só temos 5
            result = load_episodes(db_path, "BTCUSDT", "H4", min_episodes=20)
            self.assertEqual(result, [])
        finally:
            Path(db_path).unlink()

    def test_load_episodes_sufficient(self):
        """Carrega episódios quando >= min_episodes."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE training_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_key TEXT NOT NULL UNIQUE,
                    cycle_run_id TEXT NOT NULL,
                    execution_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    status TEXT NOT NULL,
                    event_timestamp INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    reward_proxy REAL,
                    features_json TEXT NOT NULL,
                    target_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            # Insere 25 episódios válidos
            for i in range(25):
                conn.execute(
                    """
                    INSERT INTO training_episodes (
                        episode_key, cycle_run_id, execution_id, symbol,
                        timeframe, status, event_timestamp, label,
                        reward_proxy, features_json, target_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"ep_{i}",
                        "cycle_001",
                        1,
                        "BTCUSDT",
                        "H4",
                        "COMPLETED",
                        1234567890 + i,
                        "win" if i % 2 == 0 else "loss",
                        0.5,
                        json.dumps({"open_norm": 0.0, "close_norm": 0.5}),
                        "{}",
                        1234567890 + i,
                    ),
                )
            conn.commit()
            conn.close()

            result = load_episodes(db_path, "BTCUSDT", "H4", min_episodes=20)
            self.assertEqual(len(result), 25)
            self.assertTrue(validate_episodes(result))
        finally:
            Path(db_path).unlink()

    def test_load_episodes_filters_pending(self):
        """Descartar episódios com label='pending'."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE training_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_key TEXT NOT NULL UNIQUE,
                    cycle_run_id TEXT NOT NULL,
                    execution_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    status TEXT NOT NULL,
                    event_timestamp INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    reward_proxy REAL,
                    features_json TEXT NOT NULL,
                    target_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            # 10 valid, 10 pending
            for i in range(10):
                conn.execute(
                    """
                    INSERT INTO training_episodes (
                        episode_key, cycle_run_id, execution_id, symbol,
                        timeframe, status, event_timestamp, label,
                        reward_proxy, features_json, target_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"ep_valid_{i}",
                        "cycle_001",
                        1,
                        "BTCUSDT",
                        "H4",
                        "COMPLETED",
                        1234567890,
                        "win",
                        0.5,
                        "{}",
                        "{}",
                        1234567890,
                    ),
                )
            for i in range(10):
                conn.execute(
                    """
                    INSERT INTO training_episodes (
                        episode_key, cycle_run_id, execution_id, symbol,
                        timeframe, status, event_timestamp, label,
                        reward_proxy, features_json, target_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"ep_pending_{i}",
                        "cycle_001",
                        1,
                        "BTCUSDT",
                        "H4",
                        "PENDING",
                        1234567890,
                        "pending",
                        None,
                        "{}",
                        "{}",
                        1234567890,
                    ),
                )
            conn.commit()
            conn.close()

            result = load_episodes(db_path, "BTCUSDT", "H4", min_episodes=5)
            # Deve retornar apenas 10 válidos (não 20)
            self.assertEqual(len(result), 10)
        finally:
            Path(db_path).unlink()

    def test_load_episodes_filters_by_symbol_and_timeframe(self):
        """Filtra corretamente por symbol e timeframe."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE training_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_key TEXT NOT NULL UNIQUE,
                    cycle_run_id TEXT NOT NULL,
                    execution_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    status TEXT NOT NULL,
                    event_timestamp INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    reward_proxy REAL,
                    features_json TEXT NOT NULL,
                    target_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            # BTCUSDT, H4: 15 episódios
            for i in range(15):
                conn.execute(
                    """
                    INSERT INTO training_episodes (
                        episode_key, cycle_run_id, execution_id, symbol,
                        timeframe, status, event_timestamp, label,
                        reward_proxy, features_json, target_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"ep_btc_h4_{i}",
                        "cycle_001",
                        1,
                        "BTCUSDT",
                        "H4",
                        "COMPLETED",
                        1234567890,
                        "win",
                        0.5,
                        "{}",
                        "{}",
                        1234567890,
                    ),
                )
            # ETHUSDT, H4: 8 episódios (insuficiente)
            for i in range(8):
                conn.execute(
                    """
                    INSERT INTO training_episodes (
                        episode_key, cycle_run_id, execution_id, symbol,
                        timeframe, status, event_timestamp, label,
                        reward_proxy, features_json, target_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"ep_eth_h4_{i}",
                        "cycle_001",
                        1,
                        "ETHUSDT",
                        "H4",
                        "COMPLETED",
                        1234567890,
                        "win",
                        0.5,
                        "{}",
                        "{}",
                        1234567890,
                    ),
                )
            # BTCUSDT, M5: 12 episódios (insuficiente)
            for i in range(12):
                conn.execute(
                    """
                    INSERT INTO training_episodes (
                        episode_key, cycle_run_id, execution_id, symbol,
                        timeframe, status, event_timestamp, label,
                        reward_proxy, features_json, target_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"ep_btc_m5_{i}",
                        "cycle_001",
                        1,
                        "BTCUSDT",
                        "M5",
                        "COMPLETED",
                        1234567890,
                        "win",
                        0.5,
                        "{}",
                        "{}",
                        1234567890,
                    ),
                )
            conn.commit()
            conn.close()

            # BTCUSDT, H4 deve retornar 15
            result = load_episodes(db_path, "BTCUSDT", "H4", min_episodes=10)
            self.assertEqual(len(result), 15)

            # ETHUSDT, H4 deve retornar []
            result = load_episodes(db_path, "ETHUSDT", "H4", min_episodes=10)
            self.assertEqual(result, [])

            # BTCUSDT, M5 deve retornar [] (min_episodes=15 > 12 disponíveis)
            result = load_episodes(db_path, "BTCUSDT", "M5", min_episodes=15)
            self.assertEqual(result, [])
        finally:
            Path(db_path).unlink()

    def test_load_episodes_normalizes_features(self):
        """Verifica normalização de features."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE training_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_key TEXT NOT NULL UNIQUE,
                    cycle_run_id TEXT NOT NULL,
                    execution_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    status TEXT NOT NULL,
                    event_timestamp INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    reward_proxy REAL,
                    features_json TEXT NOT NULL,
                    target_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            features = {
                "open_norm": 0.0,
                "close_norm": 0.5,
                "rsi": 50.0,
            }
            conn.execute(
                """
                INSERT INTO training_episodes (
                    episode_key, cycle_run_id, execution_id, symbol,
                    timeframe, status, event_timestamp, label,
                    reward_proxy, features_json, target_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "ep_1",
                    "cycle_001",
                    1,
                    "BTCUSDT",
                    "H4",
                    "COMPLETED",
                    1234567890,
                    "win",
                    0.5,
                    json.dumps(features),
                    "{}",
                    1234567890,
                ),
            )
            conn.commit()
            conn.close()

            result = load_episodes(db_path, "BTCUSDT", "H4", min_episodes=1)
            self.assertEqual(len(result), 1)

            episode = result[0]
            self.assertIn("features", episode)
            self.assertEqual(len(episode["features"]), 36)
            self.assertTrue(all(-1.0 <= f <= 1.0 for f in episode["features"]))
        finally:
            Path(db_path).unlink()


class TestValidateEpisodes(unittest.TestCase):
    """Testa validação de episódios."""

    def test_validate_episodes_empty_list(self):
        """Lista vazia não é válida."""
        self.assertFalse(validate_episodes([]))

    def test_validate_episodes_valid(self):
        """Lista válida passa validação."""
        episodes = [
            {
                "id": 1,
                "symbol": "BTCUSDT",
                "timeframe": "H4",
                "label": "win",
                "reward_proxy": 0.5,
                "features": [0.0] * 36,
                "metadata": {},
            }
        ]
        self.assertTrue(validate_episodes(episodes))

    def test_validate_episodes_bad_features_length(self):
        """Features com tamanho != 36 não é válido."""
        episodes = [
            {
                "id": 1,
                "features": [0.0] * 35,  # 35, não 36
            }
        ]
        self.assertFalse(validate_episodes(episodes))

    def test_validate_episodes_bad_feature_bounds(self):
        """Features fora de [-1, 1] não é válido."""
        episodes = [
            {
                "id": 1,
                "features": [0.0] * 35 + [2.0],  # 2.0 > 1.0
            }
        ]
        self.assertFalse(validate_episodes(episodes))

    def test_validate_episodes_nan_feature(self):
        """Features com NaN não é válido."""
        episodes = [
            {
                "id": 1,
                "features": [0.0] * 35 + [float('nan')],
            }
        ]
        self.assertFalse(validate_episodes(episodes))


if __name__ == "__main__":
    unittest.main()
