"""Suite RED M2-025.5: Idempotencia de episodios por decision_id.

Objetivo: Reforcar idempotencia da gravacao de episodios para impedir
duplicidade em concorrencia ou reprocessamento.

Status: RED — testes devem falhar antes da implementacao.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def episode_db(tmp_path: Path) -> str:
    """Fixture: DB temporario com tabela training_episodes."""
    db_path = str(tmp_path / "modelo2.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE training_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_key TEXT UNIQUE NOT NULL,
                decision_id INTEGER,
                cycle_run_id TEXT,
                symbol TEXT,
                status TEXT,
                created_at INTEGER
            )
            """
        )
    return db_path


class TestEpisodeIdempotencyContract:
    """RED: Contrato de idempotencia por decision_id."""

    def test_is_episode_duplicate_returns_false_for_new(
        self, episode_db: str
    ) -> None:
        """R1: Novo decision_id nao eh duplicata."""
        from scripts.model2.persist_training_episodes import is_episode_duplicate

        result = is_episode_duplicate(
            db_path=episode_db,
            decision_id=999,
        )
        assert result is False

    def test_is_episode_duplicate_returns_true_after_insert(
        self, episode_db: str
    ) -> None:
        """R2: decision_id ja inserido retorna duplicata."""
        from scripts.model2.persist_training_episodes import is_episode_duplicate

        with sqlite3.connect(episode_db) as conn:
            conn.execute(
                "INSERT INTO training_episodes (episode_key, decision_id, symbol, status, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                ("key_999", 999, "BTCUSDT", "PENDING", 1000),
            )

        result = is_episode_duplicate(
            db_path=episode_db,
            decision_id=999,
        )
        assert result is True

    def test_is_episode_duplicate_none_decision_id_not_duplicate(
        self, episode_db: str
    ) -> None:
        """R3: decision_id=None nunca eh duplicata (legado)."""
        from scripts.model2.persist_training_episodes import is_episode_duplicate

        result = is_episode_duplicate(
            db_path=episode_db,
            decision_id=None,
        )
        assert result is False

    def test_is_episode_duplicate_does_not_raise(
        self, episode_db: str
    ) -> None:
        """Guardrail: Funcao nunca levanta excecao."""
        from scripts.model2.persist_training_episodes import is_episode_duplicate

        # Mesmo com DB invalido, nao deve levantar (fail-safe)
        result = is_episode_duplicate(
            db_path="/nao/existe/modelo2.db",
            decision_id=1,
        )
        assert isinstance(result, bool)

    def test_is_episode_duplicate_different_ids_are_independent(
        self, episode_db: str
    ) -> None:
        """R4: decision_ids diferentes sao independentes."""
        from scripts.model2.persist_training_episodes import is_episode_duplicate

        with sqlite3.connect(episode_db) as conn:
            conn.execute(
                "INSERT INTO training_episodes (episode_key, decision_id, symbol, status, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                ("key_100", 100, "BTCUSDT", "PENDING", 1000),
            )

        assert is_episode_duplicate(db_path=episode_db, decision_id=100) is True
        assert is_episode_duplicate(db_path=episode_db, decision_id=101) is False

    def test_episode_key_unique_constraint_enforced(
        self, episode_db: str
    ) -> None:
        """R5: episode_key UNIQUE enforca idempotencia no INSERT OR IGNORE."""
        with sqlite3.connect(episode_db) as conn:
            conn.execute(
                "INSERT INTO training_episodes (episode_key, decision_id, symbol, status, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                ("key_dup", 200, "ETHUSDT", "PENDING", 1000),
            )
            # Segunda insercao deve ser ignorada (IGNORE)
            conn.execute(
                "INSERT OR IGNORE INTO training_episodes (episode_key, decision_id, symbol, status, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                ("key_dup", 200, "ETHUSDT", "PENDING", 2000),
            )
            count = conn.execute(
                "SELECT COUNT(*) FROM training_episodes WHERE episode_key = 'key_dup'"
            ).fetchone()[0]

        assert count == 1
