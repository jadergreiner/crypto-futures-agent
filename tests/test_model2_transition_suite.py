import sqlite3
from pathlib import Path

import pytest

from core.model2.repository import Model2ThesisRepository
from scripts.model2.migrate import run_up


TRANSITIONS = [
    {
        "method": "transition_to_monitoring",
        "valid_from": "IDENTIFICADA",
        "to_status": "MONITORANDO",
        "already_reason": "already_monitoring",
    },
    {
        "method": "transition_to_validated",
        "valid_from": "MONITORANDO",
        "to_status": "VALIDADA",
        "already_reason": "already_validated",
    },
    {
        "method": "transition_to_invalidated",
        "valid_from": "MONITORANDO",
        "to_status": "INVALIDADA",
        "already_reason": "already_invalidated",
    },
    {
        "method": "transition_to_expired",
        "valid_from": "MONITORANDO",
        "to_status": "EXPIRADA",
        "already_reason": "already_expired",
    },
]


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def _insert_opportunity(db_path: Path, status: str) -> int:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO opportunities (
                symbol, timeframe, side, thesis_type, status,
                zone_low, zone_high, trigger_price, invalidation_price,
                created_at, updated_at, expires_at, resolved_at, resolution_reason, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "BTCUSDT",
                "H4",
                "SHORT",
                "FALHA_REGIAO_VENDA",
                status,
                100.0,
                110.0,
                97.0,
                110.0,
                1_000,
                1_000,
                90_000,
                None,
                None,
                "{}",
            ),
        )
        opportunity_id = int(cursor.lastrowid)
        conn.commit()
    return opportunity_id


def _count_events(db_path: Path, opportunity_id: int) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM opportunity_events WHERE opportunity_id = ?",
                (opportunity_id,),
            ).fetchone()[0]
        )


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_transition_valid_path_creates_single_event(
    tmp_path: Path,
    transition: dict[str, str],
) -> None:
    db_path = _prepare_db(tmp_path)
    opportunity_id = _insert_opportunity(db_path, transition["valid_from"])
    repository = Model2ThesisRepository(str(db_path))

    result = getattr(repository, transition["method"])(
        opportunity_id=opportunity_id,
        now_ms=2_000,
    )

    assert result.transitioned is True
    assert result.reason == "ok"
    assert result.previous_status == transition["valid_from"]
    assert result.current_status == transition["to_status"]
    assert _count_events(db_path, opportunity_id) == 1

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT status, from_status, to_status
            FROM opportunities o
            JOIN opportunity_events e ON e.opportunity_id = o.id
            WHERE o.id = ?
            ORDER BY e.id DESC
            LIMIT 1
            """,
            (opportunity_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == transition["to_status"]
    assert row[1] == transition["valid_from"]
    assert row[2] == transition["to_status"]


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_transition_idempotent_second_call_has_no_extra_event(
    tmp_path: Path,
    transition: dict[str, str],
) -> None:
    db_path = _prepare_db(tmp_path)
    opportunity_id = _insert_opportunity(db_path, transition["valid_from"])
    repository = Model2ThesisRepository(str(db_path))

    first = getattr(repository, transition["method"])(
        opportunity_id=opportunity_id,
        now_ms=2_000,
    )
    second = getattr(repository, transition["method"])(
        opportunity_id=opportunity_id,
        now_ms=3_000,
    )

    assert first.transitioned is True
    assert second.transitioned is False
    assert second.reason == transition["already_reason"]
    assert second.current_status == transition["to_status"]
    assert _count_events(db_path, opportunity_id) == 1


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_transition_returns_not_found_without_event(
    tmp_path: Path,
    transition: dict[str, str],
) -> None:
    db_path = _prepare_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))

    result = getattr(repository, transition["method"])(
        opportunity_id=99999,
        now_ms=2_000,
    )

    assert result.transitioned is False
    assert result.reason == "not_found"
    assert result.current_status is None

    with sqlite3.connect(db_path) as conn:
        total_events = conn.execute("SELECT COUNT(*) FROM opportunity_events").fetchone()[0]
    assert total_events == 0


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_transition_rejects_invalid_source_state_without_event(
    tmp_path: Path,
    transition: dict[str, str],
) -> None:
    invalid_sources = [
        status
        for status in ("IDENTIFICADA", "MONITORANDO", "VALIDADA", "INVALIDADA", "EXPIRADA")
        if status not in (transition["valid_from"], transition["to_status"])
    ]
    for source_status in invalid_sources:
        db_path = _prepare_db(tmp_path / source_status / transition["to_status"])
        opportunity_id = _insert_opportunity(db_path, source_status)
        repository = Model2ThesisRepository(str(db_path))

        before_events = _count_events(db_path, opportunity_id)
        result = getattr(repository, transition["method"])(
            opportunity_id=opportunity_id,
            now_ms=2_000,
        )
        after_events = _count_events(db_path, opportunity_id)

        assert result.transitioned is False
        assert result.reason == "invalid_transition"
        assert result.current_status == source_status
        assert before_events == 0
        assert after_events == 0
