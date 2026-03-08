import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATE_SCRIPT = REPO_ROOT / "scripts" / "model2" / "migrate.py"


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


def test_migration_creates_schema_indexes_and_runtime_output(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"

    result = run_migrate(db_path=db_path, output_dir=output_dir)
    payload = json.loads(result.stdout)

    assert payload["status"] == "ok"
    assert payload["applied_now"] == [1]
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

        indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(opportunities)").fetchall()
        }
        assert "idx_opportunities_status" in indexes
        assert "idx_opportunities_symbol_status" in indexes
        assert "idx_opportunities_created_at" in indexes

    run_files = list(output_dir.glob("model2_migrate_*.json"))
    assert len(run_files) == 1


def test_migration_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"

    first = json.loads(run_migrate(db_path=db_path, output_dir=output_dir).stdout)
    second = json.loads(run_migrate(db_path=db_path, output_dir=output_dir).stdout)

    assert first["applied_now"] == [1]
    assert second["applied_now"] == []
    assert second["total_applied"] == 1

    with sqlite3.connect(db_path) as conn:
        row_count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        assert row_count == 1


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
