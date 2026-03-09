import json
import sqlite3
from pathlib import Path

from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import (
    M2_002_RULE_ID,
    M2_002_THESIS_TYPE,
    DetectionResult,
)
from scripts.model2.bridge import run_bridge
from scripts.model2.export_signals import run_export_signals
from scripts.model2.migrate import run_up
from scripts.model2.order_layer import run_order_layer
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
        "context": {"market_structure": "range", "is_non_bullish_context": True},
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
        conn.executemany(
            """
            INSERT INTO ohlcv_h4 (
                timestamp, symbol, open, high, low, close, volume, quote_volume, trades_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1_700_000_020_000, "BTCUSDT", 98.0, 99.0, 97.5, 98.5, 100.0, 100.0, 10),
                (1_700_000_030_000, "BTCUSDT", 98.0, 99.0, 96.5, 97.0, 120.0, 120.0, 12),
            ],
        )
        conn.commit()
    return source_db


def test_export_signals_dual_write_controlled_and_idempotent(tmp_path: Path) -> None:
    model2_db = tmp_path / "db" / "modelo2.db"
    legacy_db = tmp_path / "db" / "legacy.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    source_db = _prepare_source_db(tmp_path)
    run_up(db_path=model2_db, output_dir=output_dir)

    repository = Model2ThesisRepository(str(model2_db))
    created = repository.create_initial_thesis(_build_detection_result(), now_ms=1_700_000_010_000)
    repository.transition_to_monitoring(opportunity_id=created.opportunity_id, now_ms=1_700_000_020_000)
    run_validation(
        source_db_path=source_db,
        model2_db_path=model2_db,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        candles_limit=100,
        dry_run=False,
        output_dir=output_dir,
    )
    run_bridge(
        model2_db_path=model2_db,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        dry_run=False,
        output_dir=output_dir,
    )
    run_order_layer(
        model2_db_path=model2_db,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        dry_run=False,
        output_dir=output_dir,
    )

    first = run_export_signals(
        model2_db_path=model2_db,
        legacy_db_path=legacy_db,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        dry_run=False,
        output_dir=output_dir,
    )
    second = run_export_signals(
        model2_db_path=model2_db,
        legacy_db_path=legacy_db,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        dry_run=False,
        output_dir=output_dir,
    )

    assert first["consumed_candidates"] == 1
    assert first["exported_now"] == 1
    assert first["idempotent_hits_now"] == 0
    assert second["consumed_candidates"] == 1
    assert second["exported_now"] == 0
    assert second["idempotent_hits_now"] == 1

    with sqlite3.connect(legacy_db) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*), MIN(execution_mode), MIN(status), MIN(executed_at), MIN(executed_price),
                   MIN(confluence_details)
            FROM trade_signals
            """
        ).fetchone()
        assert row is not None
        assert int(row[0]) == 1
        assert row[1] == "PENDING"
        assert row[2] == "ACTIVE"
        assert row[3] is None
        assert row[4] is None
        assert '"m2_technical_signal_id"' in (row[5] or "")

    with sqlite3.connect(model2_db) as conn:
        payload_raw = conn.execute("SELECT payload_json FROM technical_signals LIMIT 1").fetchone()[0]
    payload = json.loads(payload_raw or "{}")
    assert payload["adapter_export_trade_signals"]["exported"] is True
