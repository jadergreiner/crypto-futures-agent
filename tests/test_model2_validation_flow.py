import sqlite3
from pathlib import Path

from core.model2.repository import M2_003_2_RULE_ID, Model2ThesisRepository
from core.model2.scanner import (
    M2_002_RULE_ID,
    M2_002_THESIS_TYPE,
    DetectionResult,
)
from scripts.model2.migrate import run_up
from scripts.model2.validate import run_validation


def _build_detection_result(rejection_ts: int = 1_700_000_000_000) -> DetectionResult:
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
        symbol="BTCUSDT",
        timeframe="H4",
        side="SHORT",
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=100.0,
        zone_high=110.0,
        trigger_price=97.0,
        invalidation_price=110.0,
        metadata=metadata,
        rule_id=M2_002_RULE_ID,
    )


def _prepare_model2_db_with_monitoring(tmp_path: Path) -> tuple[Path, int]:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)

    repository = Model2ThesisRepository(str(db_path))
    created = repository.create_initial_thesis(
        _build_detection_result(),
        now_ms=1_700_000_010_000,
    )
    repository.transition_to_monitoring(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_020_000,
    )
    return db_path, created.opportunity_id


def _prepare_source_db(tmp_path: Path) -> Path:
    source_db = tmp_path / "db" / "source.db"
    source_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_db) as conn:
        conn.execute(
            """
            CREATE TABLE ohlcv_h4 (
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quote_volume REAL NOT NULL,
                trades_count INTEGER NOT NULL,
                PRIMARY KEY (timestamp, symbol)
            )
            """
        )
        rows = [
            (1_700_000_020_000, "BTCUSDT", 98.0, 99.0, 97.5, 98.5, 100.0, 100.0, 10),
            (1_700_000_030_000, "BTCUSDT", 98.0, 99.0, 96.5, 97.0, 120.0, 120.0, 12),
        ]
        conn.executemany(
            """
            INSERT INTO ohlcv_h4 (
                timestamp, symbol, open, high, low, close, volume, quote_volume, trades_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    return source_db


def test_transition_to_validated_updates_status_and_creates_event(tmp_path: Path) -> None:
    model2_db, opportunity_id = _prepare_model2_db_with_monitoring(tmp_path)
    source_db = _prepare_source_db(tmp_path)
    output_dir = tmp_path / "results" / "model2" / "runtime"

    summary = run_validation(
        source_db_path=source_db,
        model2_db_path=model2_db,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        candles_limit=100,
        dry_run=False,
        output_dir=output_dir,
    )

    assert summary["status"] == "ok"
    assert summary["monitoring_candidates"] == 1
    assert summary["validated_now"] == 1
    assert summary["items"][0]["status"] == "VALIDATED"

    with sqlite3.connect(model2_db) as conn:
        status = conn.execute(
            "SELECT status, resolution_reason FROM opportunities WHERE id = ?",
            (opportunity_id,),
        ).fetchone()
        assert status is not None
        assert status[0] == "VALIDADA"
        assert status[1] == "validation_confirmed"

        event = conn.execute(
            """
            SELECT from_status, to_status, rule_id
            FROM opportunity_events
            WHERE opportunity_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (opportunity_id,),
        ).fetchone()
        assert event is not None
        assert event[0] == "MONITORANDO"
        assert event[1] == "VALIDADA"
        assert event[2] == M2_003_2_RULE_ID


def test_transition_to_validated_is_idempotent(tmp_path: Path) -> None:
    model2_db, opportunity_id = _prepare_model2_db_with_monitoring(tmp_path)
    repository = Model2ThesisRepository(str(model2_db))

    first = repository.transition_to_validated(
        opportunity_id=opportunity_id,
        now_ms=1_700_000_040_000,
    )
    second = repository.transition_to_validated(
        opportunity_id=opportunity_id,
        now_ms=1_700_000_050_000,
    )

    assert first.transitioned is True
    assert second.transitioned is False
    assert second.reason == "already_validated"
    with sqlite3.connect(model2_db) as conn:
        events_count = conn.execute(
            "SELECT COUNT(*) FROM opportunity_events WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()[0]
    assert events_count == 3


def test_transition_to_validated_rejects_invalid_state(tmp_path: Path) -> None:
    model2_db, opportunity_id = _prepare_model2_db_with_monitoring(tmp_path)
    repository = Model2ThesisRepository(str(model2_db))
    with sqlite3.connect(model2_db) as conn:
        conn.execute(
            "UPDATE opportunities SET status = 'IDENTIFICADA' WHERE id = ?",
            (opportunity_id,),
        )
        conn.commit()

    result = repository.transition_to_validated(
        opportunity_id=opportunity_id,
        now_ms=1_700_000_040_000,
    )
    assert result.transitioned is False
    assert result.reason == "invalid_transition"
