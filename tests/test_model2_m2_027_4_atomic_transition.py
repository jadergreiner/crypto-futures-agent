"""Suite RED para M2-027.4: transacao atomica CONSUMED->IN_PROGRESS em repository.py.

Testa:
- Transicao CONSUMED->IN_PROGRESS ocorre em transacao atomica
- Rollback automatico em caso de falha durante a transicao
- Nenhuma atualizacao parcial e persistida em caso de erro
"""

from __future__ import annotations

import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from core.model2.repository import Model2ThesisRepository


# ---------------------------------------------------------------------------
# Schema minimo para testes
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS technical_signals (
    id INTEGER PRIMARY KEY,
    opportunity_id INTEGER,
    symbol TEXT,
    timeframe TEXT,
    signal_side TEXT,
    entry_type TEXT,
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    status TEXT DEFAULT 'CREATED',
    signal_timestamp INTEGER,
    payload TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS signal_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER,
    status TEXT DEFAULT 'READY',
    symbol TEXT,
    signal_side TEXT,
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    created_at_ms INTEGER,
    updated_at_ms INTEGER
);

CREATE TABLE IF NOT EXISTS signal_execution_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_execution_id INTEGER,
    from_status TEXT,
    to_status TEXT,
    reason TEXT,
    ts_ms INTEGER
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY,
    symbol TEXT,
    timeframe TEXT,
    side TEXT,
    thesis_type TEXT,
    zone_low REAL,
    zone_high REAL,
    trigger_price REAL,
    invalidation_price REAL,
    status TEXT DEFAULT 'IDENTIFICADA',
    created_at_ms INTEGER,
    expires_at_ms INTEGER,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS opportunity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER,
    from_status TEXT,
    to_status TEXT,
    reason TEXT,
    ts_ms INTEGER
);
"""


@pytest.fixture
def repo() -> Model2ThesisRepository:
    """Repositorio com DB em memoria e schema completo."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(_SCHEMA)
    conn.commit()
    return Model2ThesisRepository(db_conn=conn)


@pytest.fixture
def repo_com_sinal(repo: Model2ThesisRepository) -> tuple[Model2ThesisRepository, int]:
    """Repositorio com sinal CONSUMED pre-inserido."""
    conn = repo._conn  # type: ignore[attr-defined]
    conn.execute("""
        INSERT INTO technical_signals
        (id, opportunity_id, symbol, timeframe, signal_side, entry_type, entry_price, stop_loss, take_profit, status, signal_timestamp, payload)
        VALUES (1, 10, 'BTCUSDT', '4h', 'SHORT', 'MARKET', 97000.0, 98000.0, 95000.0, 'CONSUMED', 1700000000000, '{}')
    """)
    conn.commit()
    return repo, 1


# ---------------------------------------------------------------------------
# Testes de transicao atomica
# ---------------------------------------------------------------------------

def test_atomic_transition_consumed_to_in_progress_sucesso(
    repo_com_sinal: tuple[Model2ThesisRepository, int],
) -> None:
    """Transicao CONSUMED->IN_PROGRESS deve persistir atomicamente."""
    repo, signal_id = repo_com_sinal

    # Act
    resultado = repo.atomic_transition_consumed_to_in_progress(signal_id=signal_id)

    # Assert
    assert resultado.success is True
    conn = repo._conn  # type: ignore[attr-defined]
    row = conn.execute(
        "SELECT status FROM signal_executions WHERE signal_id = ?", (signal_id,)
    ).fetchone()
    assert row is not None
    assert row[0] == "IN_PROGRESS"


def test_atomic_transition_rollback_em_falha_de_insercao(
    repo_com_sinal: tuple[Model2ThesisRepository, int],
) -> None:
    """Em caso de falha ao inserir signal_execution, nenhuma mudanca deve persistir."""
    repo, signal_id = repo_com_sinal
    conn = repo._conn  # type: ignore[attr-defined]

    # Simular falha na insercao de signal_execution
    original_execute = conn.execute

    call_count = 0

    def execute_com_falha(sql: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        if "INSERT INTO signal_executions" in sql and call_count > 0:
            raise sqlite3.OperationalError("Falha simulada de insercao")
        return original_execute(sql, *args, **kwargs)

    with patch.object(conn, "execute", side_effect=execute_com_falha):
        resultado = repo.atomic_transition_consumed_to_in_progress(signal_id=signal_id)

    # Assert: rollback deve ter ocorrido
    assert resultado.success is False
    row = conn.execute(
        "SELECT status FROM technical_signals WHERE id = ?", (signal_id,)
    ).fetchone()
    # Status original preservado
    assert row[0] == "CONSUMED"


def test_atomic_transition_rejeita_sinal_nao_consumed(
    repo: Model2ThesisRepository,
) -> None:
    """Transicao deve falhar se sinal nao estiver em status CONSUMED."""
    conn = repo._conn  # type: ignore[attr-defined]
    conn.execute("""
        INSERT INTO technical_signals
        (id, opportunity_id, symbol, timeframe, signal_side, entry_type, entry_price, stop_loss, take_profit, status, signal_timestamp, payload)
        VALUES (2, 11, 'ETHUSDT', '4h', 'SHORT', 'MARKET', 3000.0, 3100.0, 2800.0, 'CREATED', 1700000000000, '{}')
    """)
    conn.commit()

    resultado = repo.atomic_transition_consumed_to_in_progress(signal_id=2)

    assert resultado.success is False
    assert "CONSUMED" in resultado.reason


def test_atomic_transition_rejeita_sinal_inexistente(
    repo: Model2ThesisRepository,
) -> None:
    """Transicao deve falhar com sinal_id que nao existe."""
    resultado = repo.atomic_transition_consumed_to_in_progress(signal_id=9999)
    assert resultado.success is False


def test_atomic_transition_registra_evento(
    repo_com_sinal: tuple[Model2ThesisRepository, int],
) -> None:
    """Transicao bem-sucedida deve registrar evento em signal_execution_events."""
    repo, signal_id = repo_com_sinal

    repo.atomic_transition_consumed_to_in_progress(signal_id=signal_id)

    conn = repo._conn  # type: ignore[attr-defined]
    row = conn.execute(
        "SELECT from_status, to_status FROM signal_execution_events WHERE signal_execution_id IN "
        "(SELECT id FROM signal_executions WHERE signal_id = ?)",
        (signal_id,),
    ).fetchone()
    assert row is not None
    assert row[1] == "IN_PROGRESS"
