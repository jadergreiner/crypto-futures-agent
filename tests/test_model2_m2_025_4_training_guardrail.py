"""Suite RED M2-025.4: Guardrail de treino com dados minimos.

Objetivo: Bloquear treino incremental quando dados minimos nao forem
atendidos, registrando reason_code e acao recomendada.

Status: RED — testes devem falhar antes da implementacao.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def episodes_db(tmp_path: Path) -> str:
    """Fixture: DB com training_episodes populado."""
    db_path = str(tmp_path / "modelo2.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE training_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_key TEXT UNIQUE NOT NULL,
                symbol TEXT,
                status TEXT,
                created_at INTEGER
            )
            """
        )
        # Inserir 5 episodios
        for i in range(5):
            conn.execute(
                "INSERT INTO training_episodes (episode_key, symbol, status, created_at)"
                " VALUES (?, ?, ?, ?)",
                (f"key_{i}", "BTCUSDT", "COMPLETED", 1000 + i),
            )
    return db_path


class TestTrainingDataGuardrail:
    """RED: Guardrail de dados minimos para treino."""

    def test_check_minimum_ok_when_enough_episodes(
        self, episodes_db: str
    ) -> None:
        """R1: OK quando ha episodios suficientes."""
        from scripts.model2.persist_training_episodes import (
            check_training_data_minimum,
        )

        ok, reason_code, count = check_training_data_minimum(
            db_path=episodes_db, min_episodes=3
        )

        assert ok is True
        assert reason_code == ""
        assert count == 5

    def test_check_minimum_blocked_when_insufficient(
        self, episodes_db: str
    ) -> None:
        """R2: Bloqueado quando ha menos episodios que o minimo."""
        from scripts.model2.persist_training_episodes import (
            check_training_data_minimum,
        )

        ok, reason_code, count = check_training_data_minimum(
            db_path=episodes_db, min_episodes=10
        )

        assert ok is False
        assert reason_code == "insufficient_training_data"
        assert count == 5

    def test_check_minimum_blocked_when_table_missing(
        self, tmp_path: Path
    ) -> None:
        """R3: Bloqueado (fail-safe) quando tabela nao existe."""
        from scripts.model2.persist_training_episodes import (
            check_training_data_minimum,
        )

        db_path = str(tmp_path / "empty.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE schema_migrations (version INTEGER)")

        ok, reason_code, count = check_training_data_minimum(
            db_path=db_path, min_episodes=1
        )

        assert ok is False
        assert reason_code in ("table_not_found", "insufficient_training_data")
        assert count == 0

    def test_check_minimum_does_not_raise(self, tmp_path: Path) -> None:
        """Guardrail: Funcao nunca levanta excecao."""
        from scripts.model2.persist_training_episodes import (
            check_training_data_minimum,
        )

        ok, reason_code, count = check_training_data_minimum(
            db_path="/nao/existe/db.db", min_episodes=1
        )

        assert isinstance(ok, bool)
        assert isinstance(reason_code, str)
        assert isinstance(count, int)

    def test_check_minimum_returns_tuple_of_three(
        self, episodes_db: str
    ) -> None:
        """R4: Retorna tupla (ok, reason_code, count)."""
        from scripts.model2.persist_training_episodes import (
            check_training_data_minimum,
        )

        result = check_training_data_minimum(
            db_path=episodes_db, min_episodes=1
        )

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
        assert isinstance(result[2], int)
