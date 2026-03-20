"""Testes para WAL mode + busy_timeout em repository._connect (R-01/M1-06)."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from core.model2.repository import Model2ThesisRepository


def _make_repo(db_path: str) -> Model2ThesisRepository:
    return Model2ThesisRepository(db_path)


def test_wal_mode_habilitado() -> None:
    """Verifica que o journal_mode e WAL apos conectar."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    repo = _make_repo(db_path)
    # Acessa _connect diretamente para inspecionar PRAGMAs
    conn = repo._connect()
    try:
        row = conn.execute("PRAGMA journal_mode").fetchone()
        assert row is not None
        assert row[0].lower() == "wal", f"journal_mode esperado 'wal', obtido '{row[0]}'"
    finally:
        conn.close()
        Path(db_path).unlink(missing_ok=True)


def test_busy_timeout_configurado() -> None:
    """Verifica que busy_timeout e maior que zero apos conectar."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    repo = _make_repo(db_path)
    conn = repo._connect()
    try:
        row = conn.execute("PRAGMA busy_timeout").fetchone()
        assert row is not None
        timeout_ms = int(row[0])
        assert timeout_ms > 0, f"busy_timeout deve ser > 0, obtido {timeout_ms}"
    finally:
        conn.close()
        Path(db_path).unlink(missing_ok=True)


def test_foreign_keys_habilitadas() -> None:
    """Verifica que foreign_keys ainda esta habilitado."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    repo = _make_repo(db_path)
    conn = repo._connect()
    try:
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert row is not None
        assert int(row[0]) == 1
    finally:
        conn.close()
        Path(db_path).unlink(missing_ok=True)
