import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from core.model2.thesis_state import OFFICIAL_THESIS_STATUSES


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATE_SCRIPT = REPO_ROOT / "scripts" / "model2" / "migrate.py"
MIGRATIONS_DIR = REPO_ROOT / "scripts" / "model2" / "migrations"


def run_migrate(db_path: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(MIGRATE_SCRIPT),
        "up",
        "--db-path",
        str(db_path),
        "--output-dir",
        str(output_dir),
    ]
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def base_opportunity_payload() -> dict:
    return {
        "symbol": "BTCUSDT",
        "timeframe": "H4",
        "side": "LONG",
        "thesis_type": "FALHA_REGIAO",
        "status": "IDENTIFICADA",
        "zone_low": 100.0,
        "zone_high": 120.0,
        "trigger_price": 110.0,
        "invalidation_price": 99.0,
        "created_at": 1_700_000_000_000,
        "updated_at": 1_700_000_000_001,
        "expires_at": 1_700_000_001_000,
        "resolved_at": None,
        "resolution_reason": None,
        "metadata_json": "{}",
    }


def base_event_payload(opportunity_id: int) -> dict:
    return {
        "opportunity_id": opportunity_id,
        "event_type": "STATUS_TRANSITION",
        "from_status": "IDENTIFICADA",
        "to_status": "MONITORANDO",
        "event_timestamp": 1_700_000_000_050,
        "rule_id": "RN-005",
        "payload_json": "{}",
    }


def _extract_quoted_values(raw_values: str) -> set[str]:
    return set(re.findall(r"'([^']+)'", raw_values))


def _extract_status_clause(sql_text: str, column_name: str) -> set[str]:
    pattern = re.compile(rf"{column_name}\s+IN\s*\(([^)]+)\)", re.IGNORECASE)
    match = pattern.search(sql_text)
    assert match is not None, f"Status clause not found for column {column_name}"
    return _extract_quoted_values(match.group(1))


def test_migration_status_enums_follow_canonical_contract() -> None:
    official_statuses = set(OFFICIAL_THESIS_STATUSES)

    opportunities_sql = (MIGRATIONS_DIR / "0001_create_opportunities.sql").read_text(
        encoding="utf-8"
    )
    events_sql = (MIGRATIONS_DIR / "0002_create_opportunity_events.sql").read_text(
        encoding="utf-8"
    )

    assert _extract_status_clause(opportunities_sql, "status") == official_statuses
    assert _extract_status_clause(events_sql, "from_status") == official_statuses
    assert _extract_status_clause(events_sql, "to_status") == official_statuses


def test_migration_creates_schema_indexes_and_runtime_output(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"

    result = run_migrate(db_path=db_path, output_dir=output_dir)
    payload = json.loads(result.stdout)

    assert payload["status"] == "ok"
    assert payload["applied_now"] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "schema_migrations" in tables
        assert "opportunities" in tables
        assert "opportunity_events" in tables
        assert "opportunity_dashboard_snapshots" in tables
        assert "opportunity_audit_snapshots" in tables
        assert "technical_signals" in tables
        assert "model_decisions" in tables
        assert "signal_flow_snapshots" in tables
        assert "signal_executions" in tables
        assert "signal_execution_events" in tables
        assert "signal_execution_snapshots" in tables

        opportunities_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(opportunities)").fetchall()
        }
        assert "idx_opportunities_status" in opportunities_indexes
        assert "idx_opportunities_symbol_status" in opportunities_indexes
        assert "idx_opportunities_created_at" in opportunities_indexes

        events_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(opportunity_events)").fetchall()
        }
        assert "idx_events_opportunity_ts" in events_indexes
        assert "idx_events_event_type" in events_indexes

        dashboard_indexes = {
            row[1]
            for row in conn.execute("PRAGMA index_list(opportunity_dashboard_snapshots)").fetchall()
        }
        assert "idx_dashboard_run_status" in dashboard_indexes
        assert "idx_dashboard_snapshot_ts" in dashboard_indexes

        audit_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(opportunity_audit_snapshots)").fetchall()
        }
        assert "idx_audit_snapshot_run" in audit_indexes
        assert "idx_audit_snapshot_ts" in audit_indexes
        assert "idx_audit_snapshot_opportunity" in audit_indexes

        signals_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(technical_signals)").fetchall()
        }
        assert "sqlite_autoindex_technical_signals_1" in signals_indexes
        assert "idx_technical_signals_status" in signals_indexes
        assert "idx_technical_signals_symbol_timeframe" in signals_indexes
        assert "idx_technical_signals_timestamp" in signals_indexes

        signal_flow_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(signal_flow_snapshots)").fetchall()
        }
        assert "idx_signal_flow_snapshots_run" in signal_flow_indexes
        assert "idx_signal_flow_snapshots_ts" in signal_flow_indexes

        signal_execution_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(signal_executions)").fetchall()
        }
        assert "sqlite_autoindex_signal_executions_1" in signal_execution_indexes
        assert "idx_signal_executions_status" in signal_execution_indexes
        assert "idx_signal_executions_symbol_status" in signal_execution_indexes
        assert "idx_signal_executions_updated_at" in signal_execution_indexes
        assert "idx_signal_executions_mode_status" in signal_execution_indexes
        assert "idx_signal_executions_decision_id" in signal_execution_indexes

        model_decision_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(model_decisions)").fetchall()
        }
        assert "idx_model_decisions_symbol_ts" in model_decision_indexes
        assert "idx_model_decisions_model_version" in model_decision_indexes

        signal_execution_event_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(signal_execution_events)").fetchall()
        }
        assert "idx_signal_execution_events_execution_ts" in signal_execution_event_indexes
        assert "idx_signal_execution_events_type" in signal_execution_event_indexes

        signal_execution_snapshot_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(signal_execution_snapshots)").fetchall()
        }
        assert "idx_signal_execution_snapshots_run" in signal_execution_snapshot_indexes
        assert "idx_signal_execution_snapshots_ts" in signal_execution_snapshot_indexes

    run_files = list(output_dir.glob("model2_migrate_*.json"))
    assert len(run_files) == 1


def test_migration_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"

    first = json.loads(run_migrate(db_path=db_path, output_dir=output_dir).stdout)
    second = json.loads(run_migrate(db_path=db_path, output_dir=output_dir).stdout)

    assert first["applied_now"] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert second["applied_now"] == []
    assert second["total_applied"] == 8

    with sqlite3.connect(db_path) as conn:
        row_count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        assert row_count == 8


def test_constraints_reject_invalid_values(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_migrate(db_path=db_path, output_dir=output_dir)

    with sqlite3.connect(db_path) as conn:
        payload = base_opportunity_payload()
        columns = ", ".join(payload.keys())
        placeholders = ", ".join([f":{key}" for key in payload.keys()])

        conn.execute(
            f"INSERT INTO opportunities ({columns}) VALUES ({placeholders})",
            payload,
        )

        invalid_side = base_opportunity_payload()
        invalid_side["side"] = "BUY"
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO opportunities ({columns}) VALUES ({placeholders})",
                invalid_side,
            )

        invalid_zone = base_opportunity_payload()
        invalid_zone["zone_low"] = 200.0
        invalid_zone["zone_high"] = 100.0
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO opportunities ({columns}) VALUES ({placeholders})",
                invalid_zone,
            )


def test_events_constraints_and_fk_reject_invalid_values(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_migrate(db_path=db_path, output_dir=output_dir)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        opportunity_payload = base_opportunity_payload()
        opportunity_columns = ", ".join(opportunity_payload.keys())
        opportunity_placeholders = ", ".join(
            [f":{key}" for key in opportunity_payload.keys()]
        )
        cursor = conn.execute(
            f"INSERT INTO opportunities ({opportunity_columns}) VALUES ({opportunity_placeholders})",
            opportunity_payload,
        )
        opportunity_id = int(cursor.lastrowid)

        event_payload = base_event_payload(opportunity_id=opportunity_id)
        event_columns = ", ".join(event_payload.keys())
        event_placeholders = ", ".join([f":{key}" for key in event_payload.keys()])
        conn.execute(
            f"INSERT INTO opportunity_events ({event_columns}) VALUES ({event_placeholders})",
            event_payload,
        )

        invalid_fk = base_event_payload(opportunity_id=opportunity_id + 9999)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO opportunity_events ({event_columns}) VALUES ({event_placeholders})",
                invalid_fk,
            )

        invalid_status = base_event_payload(opportunity_id=opportunity_id)
        invalid_status["to_status"] = "DESCONHECIDA"
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO opportunity_events ({event_columns}) VALUES ({event_placeholders})",
                invalid_status,
            )


def test_migration_does_not_touch_legacy_db(tmp_path: Path) -> None:
    legacy_db = tmp_path / "db" / "crypto_agent.db"
    model2_db = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    legacy_db.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(legacy_db) as conn:
        conn.execute("CREATE TABLE legacy_marker (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO legacy_marker (value) VALUES ('keep')")
        conn.execute("PRAGMA user_version = 777")
        before = conn.execute("PRAGMA user_version").fetchone()[0]

    run_migrate(db_path=model2_db, output_dir=output_dir)

    with sqlite3.connect(legacy_db) as conn:
        after = conn.execute("PRAGMA user_version").fetchone()[0]
        rows = conn.execute("SELECT value FROM legacy_marker").fetchall()

    assert before == 777
    assert after == 777
    assert rows == [("keep",)]
