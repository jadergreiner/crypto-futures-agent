import json
import sqlite3
from pathlib import Path

from core.model2.observability import Model2ObservabilityService
from scripts.model2.audit import run_audit_snapshot
from scripts.model2.dashboard import run_dashboard
from scripts.model2.migrate import run_up


DAY_MS = 24 * 60 * 60 * 1000


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def _seed_opportunities_and_events(db_path: Path) -> None:
    opportunities = [
        # IDENTIFICADA
        (
            "BTCUSDT",
            "H4",
            "SHORT",
            "FALHA_REGIAO_VENDA",
            "IDENTIFICADA",
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
        # VALIDADA (1000 ms)
        (
            "ETHUSDT",
            "H4",
            "SHORT",
            "FALHA_REGIAO_VENDA",
            "VALIDADA",
            200.0,
            210.0,
            197.0,
            210.0,
            1_000,
            2_000,
            90_000,
            2_000,
            "validation_confirmed",
            "{}",
        ),
        # INVALIDADA (3000 ms)
        (
            "SOLUSDT",
            "H4",
            "SHORT",
            "FALHA_REGIAO_VENDA",
            "INVALIDADA",
            300.0,
            310.0,
            297.0,
            310.0,
            1_000,
            4_000,
            90_000,
            4_000,
            "premise_broken",
            "{}",
        ),
        # EXPIRADA (5000 ms)
        (
            "BNBUSDT",
            "H4",
            "SHORT",
            "FALHA_REGIAO_VENDA",
            "EXPIRADA",
            400.0,
            410.0,
            397.0,
            410.0,
            1_000,
            6_000,
            90_000,
            6_000,
            "time_limit_reached",
            "{}",
        ),
    ]

    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO opportunities (
                symbol, timeframe, side, thesis_type, status,
                zone_low, zone_high, trigger_price, invalidation_price,
                created_at, updated_at, expires_at, resolved_at, resolution_reason, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            opportunities,
        )

        rows = conn.execute("SELECT id, status, symbol, timeframe FROM opportunities ORDER BY id ASC").fetchall()
        events = []
        timestamp = 10_000
        for opp_id, status, symbol, timeframe in rows:
            events.append(
                (
                    opp_id,
                    "STATUS_TRANSITION",
                    None,
                    "IDENTIFICADA",
                    timestamp,
                    "M2-002.1-RULE-FAIL-SELL-REGION",
                    json.dumps({"symbol": symbol}, ensure_ascii=True),
                )
            )
            timestamp += 1
            if status != "IDENTIFICADA":
                events.append(
                    (
                        opp_id,
                        "STATUS_TRANSITION",
                        "MONITORANDO",
                        status,
                        timestamp,
                        "M2-003-X",
                        json.dumps({"timeframe": timeframe}, ensure_ascii=True),
                    )
                )
                timestamp += 1

        conn.executemany(
            """
            INSERT INTO opportunity_events (
                opportunity_id, event_type, from_status, to_status, event_timestamp, rule_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            events,
        )
        conn.commit()


def test_dashboard_materialization_counts_and_averages(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    _seed_opportunities_and_events(db_path)

    service = Model2ObservabilityService(str(db_path))
    snapshot = service.refresh_dashboard_snapshot(
        run_id="RUN_DASH",
        snapshot_timestamp=40 * DAY_MS,
        retention_days=30,
    )

    assert snapshot.count_by_status["IDENTIFICADA"] == 1
    assert snapshot.count_by_status["MONITORANDO"] == 0
    assert snapshot.count_by_status["VALIDADA"] == 1
    assert snapshot.count_by_status["INVALIDADA"] == 1
    assert snapshot.count_by_status["EXPIRADA"] == 1
    assert snapshot.avg_resolution_ms == 3000.0
    assert snapshot.avg_resolution_ms_by_final_status["VALIDADA"] == 1000.0
    assert snapshot.avg_resolution_ms_by_final_status["INVALIDADA"] == 3000.0
    assert snapshot.avg_resolution_ms_by_final_status["EXPIRADA"] == 5000.0

    with sqlite3.connect(db_path) as conn:
        stored = conn.execute(
            "SELECT COUNT(*) FROM opportunity_dashboard_snapshots WHERE run_id = 'RUN_DASH'"
        ).fetchone()[0]
    assert stored == 5


def test_audit_materialization_filters_and_retention(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    _seed_opportunities_and_events(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO opportunity_audit_snapshots (
                run_id, snapshot_timestamp, event_id, opportunity_id, symbol, timeframe,
                event_type, from_status, to_status, event_timestamp, rule_id, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "OLD",
                1,
                99999,
                1,
                "BTCUSDT",
                "H4",
                "STATUS_TRANSITION",
                "IDENTIFICADA",
                "MONITORANDO",
                1,
                "OLD-RULE",
                "{}",
                1,
            ),
        )
        conn.commit()

    summary = run_audit_snapshot(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        retention_days=30,
        opportunity_id=1,
        symbol="BTCUSDT",
        timeframe="H4",
        start_ts=None,
        end_ts=None,
        limit=100,
    )

    assert summary["status"] == "ok"
    assert summary["stored_rows"] >= 1
    assert summary["purged_rows"] >= 1
    assert all(int(item["opportunity_id"]) == 1 for item in summary["items"])
    assert all(item["symbol"] == "BTCUSDT" for item in summary["items"])
    assert Path(summary["output_file"]).exists()


def test_dashboard_runner_writes_runtime_summary(tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    _seed_opportunities_and_events(db_path)

    summary = run_dashboard(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        retention_days=30,
    )

    assert summary["status"] == "ok"
    assert "count_by_status" in summary
    assert Path(summary["output_file"]).exists()
