import json
import sqlite3
from pathlib import Path

import pytest

from core.model2.observability import Model2ObservabilityService
from scripts.model2.export_dashboard import run_export_dashboard
from scripts.model2.migrate import run_up


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def _seed_signal_flow(db_path: Path) -> None:
    opportunities = [
        ("BTCUSDT", "H4", "SHORT", "FALHA_REGIAO_VENDA", "VALIDADA", 100.0, 110.0, 97.0, 110.0, 1000),
        ("ETHUSDT", "H4", "SHORT", "FALHA_REGIAO_VENDA", "VALIDADA", 200.0, 210.0, 197.0, 210.0, 1000),
        ("SOLUSDT", "H4", "SHORT", "FALHA_REGIAO_VENDA", "VALIDADA", 300.0, 310.0, 297.0, 310.0, 1000),
        ("BNBUSDT", "H4", "SHORT", "FALHA_REGIAO_VENDA", "VALIDADA", 400.0, 410.0, 397.0, 410.0, 1000),
        ("ADAUSDT", "H4", "SHORT", "FALHA_REGIAO_VENDA", "VALIDADA", 500.0, 510.0, 497.0, 510.0, 1000),
    ]
    with sqlite3.connect(db_path) as conn:
        for idx, item in enumerate(opportunities, start=1):
            symbol, timeframe, side, thesis_type, status, zl, zh, trigger, invalidation, ts = item
            conn.execute(
                """
                INSERT INTO opportunities (
                    id, symbol, timeframe, side, thesis_type, status, zone_low, zone_high,
                    trigger_price, invalidation_price, created_at, updated_at, expires_at,
                    resolved_at, resolution_reason, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    idx,
                    symbol,
                    timeframe,
                    side,
                    thesis_type,
                    status,
                    zl,
                    zh,
                    trigger,
                    invalidation,
                    ts,
                    ts,
                    ts + 100000,
                    ts,
                    "validation_confirmed",
                    "{}",
                ),
            )

        signals = [
            (
                1,
                1,
                "BTCUSDT",
                "H4",
                "SHORT",
                "MARKET",
                97.0,
                110.0,
                84.0,
                1000,
                "CREATED",
                "{}",
            ),
            (
                2,
                2,
                "ETHUSDT",
                "H4",
                "SHORT",
                "MARKET",
                197.0,
                210.0,
                184.0,
                1500,
                "CONSUMED",
                json.dumps({"order_layer": {"details": {"decision_timestamp": 2000}}}, ensure_ascii=True),
            ),
            (
                3,
                3,
                "SOLUSDT",
                "H4",
                "SHORT",
                "MARKET",
                297.0,
                310.0,
                284.0,
                2500,
                "CONSUMED",
                json.dumps(
                    {
                        "order_layer": {"details": {"decision_timestamp": 3000}},
                        "adapter_export_trade_signals": {
                            "exported": True,
                            "legacy_trade_signal_id": 9001,
                            "exported_at": 4500,
                            "rule_id": "M2-007.2-RULE-TECHNICAL-TO-TRADE-SIGNAL",
                            "metadata": {},
                        },
                    },
                    ensure_ascii=True,
                ),
            ),
            (
                4,
                4,
                "BNBUSDT",
                "H4",
                "SHORT",
                "MARKET",
                397.0,
                410.0,
                384.0,
                2600,
                "CONSUMED",
                json.dumps(
                    {
                        "order_layer": {"details": {"decision_timestamp": 3200}},
                        "adapter_export_trade_signals": {
                            "exported": False,
                            "last_error": {
                                "at": 5000,
                                "rule_id": "M2-007.2-RULE-TECHNICAL-TO-TRADE-SIGNAL",
                                "message": "db locked",
                                "attempts": 1,
                            },
                        },
                    },
                    ensure_ascii=True,
                ),
            ),
            (
                5,
                5,
                "ADAUSDT",
                "H4",
                "SHORT",
                "MARKET",
                497.0,
                510.0,
                484.0,
                2700,
                "CANCELLED",
                json.dumps({"order_layer": {"details": {"decision_timestamp": 3400}}}, ensure_ascii=True),
            ),
        ]
        for signal in signals:
            conn.execute(
                """
                INSERT INTO technical_signals (
                    id, opportunity_id, symbol, timeframe, signal_side, entry_type,
                    entry_price, stop_loss, take_profit, signal_timestamp, status,
                    rule_id, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal[0],
                    signal[1],
                    signal[2],
                    signal[3],
                    signal[4],
                    signal[5],
                    signal[6],
                    signal[7],
                    signal[8],
                    signal[9],
                    signal[10],
                    "M2-006.1-RULE-STANDARD-SIGNAL",
                    signal[11],
                    signal[9],
                    signal[9],
                ),
            )
        conn.commit()


def test_signal_flow_snapshot_metrics(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    _seed_signal_flow(db_path)

    service = Model2ObservabilityService(str(db_path))
    snapshot = service.refresh_signal_flow_snapshot(
        run_id="RUN_SIGFLOW",
        snapshot_timestamp=3_000_000,
        retention_days=30,
    )

    assert snapshot.created_count == 1
    assert snapshot.consumed_count == 3
    assert snapshot.cancelled_count == 1
    assert snapshot.exported_count == 1
    assert snapshot.consumed_not_exported_count == 2
    assert snapshot.export_error_count == 1
    assert snapshot.export_rate == pytest.approx(1.0 / 3.0, rel=1e-6)
    assert snapshot.avg_created_to_consumed_ms == pytest.approx((500 + 500 + 600) / 3.0, rel=1e-6)
    assert snapshot.avg_consumed_to_exported_ms == pytest.approx(1500.0, rel=1e-6)
    assert snapshot.avg_created_to_exported_ms == pytest.approx(2000.0, rel=1e-6)

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM signal_flow_snapshots WHERE run_id = 'RUN_SIGFLOW'"
        ).fetchone()[0]
    assert count == 1


def test_signal_flow_runner_writes_runtime_summary(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    _seed_signal_flow(db_path)

    summary = run_export_dashboard(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        retention_days=30,
    )

    assert summary["status"] == "ok"
    assert summary["created_count"] == 1
    assert summary["consumed_count"] == 3
    assert summary["exported_count"] == 1
    assert summary["export_error_count"] == 1
    assert Path(summary["output_file"]).exists()
