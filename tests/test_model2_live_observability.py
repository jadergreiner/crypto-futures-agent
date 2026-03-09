import json
import sqlite3
from pathlib import Path

from core.model2.observability import Model2ObservabilityService
from scripts.model2.live_dashboard import run_live_dashboard
from scripts.model2.migrate import run_up


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def _seed_live_executions(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        rows = [
            (
                1,
                1,
                1,
                "BTCUSDT",
                "H4",
                "SHORT",
                "live",
                "READY",
                None,
                None,
                None,
                None,
                None,
                None,
                1500,
                {"signal_snapshot": {"signal_timestamp": 1000}},
            ),
            (
                2,
                1,
                1,
                "BTCUSDT",
                "H4",
                "SHORT",
                "live",
                "ENTRY_SENT",
                "ord-2",
                None,
                None,
                1500,
                None,
                None,
                1500,
                {"signal_snapshot": {"signal_timestamp": 1000}},
            ),
            (
                3,
                1,
                1,
                "BTCUSDT",
                "H4",
                "SHORT",
                "live",
                "ENTRY_FILLED",
                "ord-3",
                0.1,
                97.0,
                1500,
                1800,
                None,
                1500,
                {"signal_snapshot": {"signal_timestamp": 1000}},
            ),
            (
                4,
                1,
                1,
                "BTCUSDT",
                "H4",
                "SHORT",
                "live",
                "PROTECTED",
                "ord-4",
                0.1,
                97.0,
                1500,
                1800,
                2000,
                1500,
                {"signal_snapshot": {"signal_timestamp": 1000}},
            ),
            (
                5,
                1,
                1,
                "BTCUSDT",
                "H4",
                "SHORT",
                "live",
                "FAILED",
                "ord-5",
                0.1,
                97.0,
                1500,
                1800,
                None,
                1500,
                {"signal_snapshot": {"signal_timestamp": 1000}},
            ),
        ]
        for row in rows:
            conn.execute(
                """
                INSERT INTO opportunities (
                    id, symbol, timeframe, side, thesis_type, status, zone_low, zone_high,
                    trigger_price, invalidation_price, created_at, updated_at, expires_at,
                    resolved_at, resolution_reason, metadata_json
                ) VALUES (?, 'BTCUSDT', 'H4', 'SHORT', 'FALHA_REGIAO_VENDA', 'VALIDADA', 100, 110, 97, 110, 1000, 1000, 2000, 1000, 'validation_confirmed', '{}')
                """,
                (row[0],),
            )
            conn.execute(
                """
                INSERT INTO technical_signals (
                    id, opportunity_id, symbol, timeframe, signal_side, entry_type,
                    entry_price, stop_loss, take_profit, signal_timestamp, status,
                    rule_id, payload_json, created_at, updated_at
                ) VALUES (?, ?, 'BTCUSDT', 'H4', 'SHORT', 'MARKET', 97, 110, 84, 1000, 'CONSUMED', 'M2-006.1-RULE-STANDARD-SIGNAL', '{}', 1000, 1000)
                """,
                (row[0], row[0]),
            )
            conn.execute(
                """
                INSERT INTO signal_executions (
                    id, technical_signal_id, opportunity_id, symbol, timeframe, signal_side,
                    execution_mode, status, entry_order_type, exchange_order_id, filled_qty,
                    filled_price, entry_sent_at, entry_filled_at, protected_at, created_at,
                    updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'MARKET', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row[0],
                    row[0],
                    row[0],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    row[9],
                    row[10],
                    row[11],
                    row[12],
                    row[13],
                    row[14],
                    row[14],
                    json.dumps(row[15], ensure_ascii=True),
                ),
            )
        conn.commit()


def test_live_execution_snapshot_metrics(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    _seed_live_executions(db_path)

    snapshot = Model2ObservabilityService(str(db_path)).refresh_live_execution_snapshot(
        run_id="RUN_LIVE",
        snapshot_timestamp=80_000,
        retention_days=30,
    )

    assert snapshot.ready_count == 1
    assert snapshot.blocked_count == 0
    assert snapshot.entry_sent_count == 1
    assert snapshot.entry_filled_count == 1
    assert snapshot.protected_count == 1
    assert snapshot.failed_count == 1
    assert snapshot.unprotected_filled_count == 1
    assert snapshot.stale_entry_sent_count == 1
    assert snapshot.avg_signal_to_entry_sent_ms == 500.0
    assert snapshot.avg_entry_sent_to_filled_ms == 300.0
    assert snapshot.avg_filled_to_protected_ms == 200.0


def test_live_dashboard_runner_writes_runtime_summary(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    _seed_live_executions(db_path)

    summary = run_live_dashboard(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        retention_days=30,
    )

    assert summary["status"] == "ok"
    assert summary["ready_count"] == 1
    assert summary["entry_sent_count"] == 1
    assert summary["entry_filled_count"] == 1
    assert summary["protected_count"] == 1
    assert summary["failed_count"] == 1
    assert Path(summary["output_file"]).exists()
