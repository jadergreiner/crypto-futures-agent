"""Model 2.0 observability dashboard runner for M2-004.1."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import MODEL2_DB_PATH
from core.model2 import Model2ObservabilityService

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _ensure_model2_observability_schema(conn: sqlite3.Connection) -> None:
    required_tables = {
        "schema_migrations",
        "opportunities",
        "opportunity_events",
        "opportunity_dashboard_snapshots",
        "opportunity_audit_snapshots",
    }
    found_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    missing = sorted(required_tables - found_tables)
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            "Model2 schema is missing required tables: "
            f"{joined}. Run 'python scripts/model2/migrate.py up' first."
        )


def run_dashboard(
    *,
    model2_db_path: str | Path,
    output_dir: str | Path,
    retention_days: int,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as model2_conn:
        _ensure_model2_observability_schema(model2_conn)

    now_ms = _utc_now_ms()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    service = Model2ObservabilityService(str(resolved_model2_db))
    snapshot = service.refresh_dashboard_snapshot(
        run_id=run_id,
        snapshot_timestamp=now_ms,
        retention_days=retention_days,
    )

    summary: dict[str, Any] = {
        "status": "ok",
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "model2_db_path": str(resolved_model2_db),
        "retention_days": int(retention_days),
        "count_by_status": snapshot.count_by_status,
        "avg_resolution_ms": snapshot.avg_resolution_ms,
        "avg_resolution_ms_by_final_status": snapshot.avg_resolution_ms_by_final_status,
        "stored_rows": snapshot.stored_rows,
        "purged_rows": snapshot.purged_rows,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_dashboard_{run_id}.json"
    output_file.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 opportunities dashboard")
    parser.add_argument(
        "--model2-db-path",
        default=MODEL2_DB_PATH,
        help="Target Model 2.0 SQLite path.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Retention window for materialized snapshots.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for dashboard run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_dashboard(
        model2_db_path=args.model2_db_path,
        output_dir=args.output_dir,
        retention_days=args.retention_days,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
