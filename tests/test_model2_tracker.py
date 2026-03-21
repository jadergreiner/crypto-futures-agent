import json
import sqlite3
from pathlib import Path

from core.model2.repository import M2_003_1_RULE_ID, Model2ThesisRepository
from core.model2.scanner import (
    M2_002_RULE_ID,
    M2_002_THESIS_TYPE,
    DetectionResult,
)
from scripts.model2.migrate import run_up
from scripts.model2.track import run_tracking


def _build_detection_result(
    rejection_ts: int = 1_700_000_000_000,
    *,
    symbol: str = "BTCUSDT",
    side: str = "SHORT",
) -> DetectionResult:
    metadata = {
        "rule_id": M2_002_RULE_ID,
        "rule_version": "1.0.0",
        "technical_zone": {
            "source": "order_block",
            "zone_id": 7,
            "timestamp": 1_699_999_999_000,
            "zone_low": 100.0,
            "zone_high": 110.0,
            "status": "FRESH",
        },
        "rejection_candle": {
            "timestamp": rejection_ts,
            "open": 100.0,
            "high": 111.0,
            "low": 97.0,
            "close": 98.0,
        },
        "context": {
            "market_structure": "range",
            "is_non_bullish_context": True,
        },
        "parameters": {
            "requires_zone_intersection": True,
            "requires_visible_rejection": True,
            "requires_trigger_break": True,
        },
    }
    return DetectionResult(
        detected=True,
        symbol=symbol,
        timeframe="H4",
        side=side,
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=100.0,
        zone_high=110.0,
        trigger_price=97.0,
        invalidation_price=110.0,
        metadata=metadata,
        rule_id=M2_002_RULE_ID,
    )


def _prepare_db_with_identified(tmp_path: Path) -> tuple[Path, int]:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    repository = Model2ThesisRepository(str(db_path))
    created = repository.create_initial_thesis(
        _build_detection_result(),
        now_ms=1_700_000_010_000,
    )
    return db_path, created.opportunity_id


def test_transition_to_monitoring_updates_status_and_creates_event(tmp_path: Path) -> None:
    db_path, opportunity_id = _prepare_db_with_identified(tmp_path)
    repository = Model2ThesisRepository(str(db_path))

    result = repository.transition_to_monitoring(
        opportunity_id=opportunity_id,
        now_ms=1_700_000_020_000,
    )

    assert result.transitioned is True
    assert result.previous_status == "IDENTIFICADA"
    assert result.current_status == "MONITORANDO"
    assert result.reason == "ok"

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT status FROM opportunities WHERE id = ?",
            (opportunity_id,),
        ).fetchone()[0]
        assert status == "MONITORANDO"

        events = conn.execute(
            """
            SELECT from_status, to_status, rule_id
            FROM opportunity_events
            WHERE opportunity_id = ?
            ORDER BY id ASC
            """,
            (opportunity_id,),
        ).fetchall()
        assert len(events) == 2
        assert events[1][0] == "IDENTIFICADA"
        assert events[1][1] == "MONITORANDO"
        assert events[1][2] == M2_003_1_RULE_ID


def test_transition_to_monitoring_is_idempotent(tmp_path: Path) -> None:
    db_path, opportunity_id = _prepare_db_with_identified(tmp_path)
    repository = Model2ThesisRepository(str(db_path))

    first = repository.transition_to_monitoring(
        opportunity_id=opportunity_id,
        now_ms=1_700_000_020_000,
    )
    second = repository.transition_to_monitoring(
        opportunity_id=opportunity_id,
        now_ms=1_700_000_030_000,
    )

    assert first.transitioned is True
    assert second.transitioned is False
    assert second.reason == "already_monitoring"
    with sqlite3.connect(db_path) as conn:
        events_count = conn.execute(
            "SELECT COUNT(*) FROM opportunity_events WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()[0]
    assert events_count == 2


def test_transition_to_monitoring_rejects_final_status(tmp_path: Path) -> None:
    db_path, opportunity_id = _prepare_db_with_identified(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE opportunities SET status = 'VALIDADA' WHERE id = ?",
            (opportunity_id,),
        )
        conn.commit()

    result = repository.transition_to_monitoring(
        opportunity_id=opportunity_id,
        now_ms=1_700_000_020_000,
    )

    assert result.transitioned is False
    assert result.reason == "invalid_transition"
    assert result.current_status == "VALIDADA"
    with sqlite3.connect(db_path) as conn:
        events_count = conn.execute(
            "SELECT COUNT(*) FROM opportunity_events WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()[0]
    assert events_count == 1


def test_track_runner_transitions_identified_candidates(tmp_path: Path) -> None:
    db_path, opportunity_id = _prepare_db_with_identified(tmp_path)
    output_dir = tmp_path / "results" / "model2" / "runtime"

    summary = run_tracking(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        dry_run=False,
        output_dir=output_dir,
    )

    assert summary["status"] == "ok"
    assert summary["identified_candidates"] == 1
    assert summary["transitioned_now"] == 1
    assert summary["items"][0]["opportunity_id"] == opportunity_id
    assert summary["items"][0]["status"] == "TRANSITIONED"
    output_file = Path(summary["output_file"])
    assert output_file.exists()
    persisted_summary = json.loads(output_file.read_text(encoding="utf-8"))
    assert persisted_summary["transitioned_now"] == 1


def test_track_runner_short_only_skips_long_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    repository = Model2ThesisRepository(str(db_path))

    short_created = repository.create_initial_thesis(
        _build_detection_result(rejection_ts=1_700_000_010_000, symbol="BTCUSDT", side="SHORT"),
        now_ms=1_700_000_020_000,
    )
    long_created = repository.create_initial_thesis(
        _build_detection_result(rejection_ts=1_700_000_011_000, symbol="ETHUSDT", side="LONG"),
        now_ms=1_700_000_021_000,
    )

    summary = run_tracking(
        model2_db_path=db_path,
        symbol=None,
        timeframe="H4",
        limit=50,
        dry_run=False,
        short_only=True,
        output_dir=output_dir,
    )

    assert summary["status"] == "ok"
    assert summary["identified_candidates"] == 2
    assert summary["eligible_candidates"] == 1
    assert summary["skipped_short_only"] == 1
    assert summary["transitioned_now"] == 1

    with sqlite3.connect(db_path) as conn:
        short_status = conn.execute(
            "SELECT status FROM opportunities WHERE id = ?",
            (short_created.opportunity_id,),
        ).fetchone()[0]
        long_status = conn.execute(
            "SELECT status FROM opportunities WHERE id = ?",
            (long_created.opportunity_id,),
        ).fetchone()[0]

    assert short_status == "MONITORANDO"
    assert long_status == "IDENTIFICADA"
