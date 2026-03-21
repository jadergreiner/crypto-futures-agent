"""Model 2.0 live execution observability dashboard."""

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
from scripts.model2.io_utils import atomic_write_json

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _ensure_model2_live_dashboard_schema(conn: sqlite3.Connection) -> None:
    required_tables = {"schema_migrations", "signal_executions", "signal_execution_snapshots"}
    found_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    missing = sorted(required_tables - found_tables)
    if missing:
        raise RuntimeError(
            "Model2 schema is missing required tables: "
            f"{', '.join(missing)}. Run 'python scripts/model2/migrate.py up' first."
        )


def run_live_dashboard(
    *,
    model2_db_path: str | Path,
    output_dir: str | Path,
    retention_days: int,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as conn:
        _ensure_model2_live_dashboard_schema(conn)

    now_ms = _utc_now_ms()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = Model2ObservabilityService(str(resolved_model2_db)).refresh_live_execution_snapshot(
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
        "ready_count": snapshot.ready_count,
        "blocked_count": snapshot.blocked_count,
        "entry_sent_count": snapshot.entry_sent_count,
        "entry_filled_count": snapshot.entry_filled_count,
        "protected_count": snapshot.protected_count,
        "exited_count": snapshot.exited_count,
        "failed_count": snapshot.failed_count,
        "cancelled_count": snapshot.cancelled_count,
        "unprotected_filled_count": snapshot.unprotected_filled_count,
        "stale_entry_sent_count": snapshot.stale_entry_sent_count,
        "open_position_mismatches_count": snapshot.open_position_mismatches_count,
        "avg_signal_to_entry_sent_ms": snapshot.avg_signal_to_entry_sent_ms,
        "avg_entry_sent_to_filled_ms": snapshot.avg_entry_sent_to_filled_ms,
        "avg_filled_to_protected_ms": snapshot.avg_filled_to_protected_ms,
        "stored_rows": snapshot.stored_rows,
        "purged_rows": snapshot.purged_rows,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_live_dashboard_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 live execution dashboard")
    parser.add_argument("--model2-db-path", default=MODEL2_DB_PATH)
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_live_dashboard(
        model2_db_path=args.model2_db_path,
        output_dir=args.output_dir,
        retention_days=int(args.retention_days),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
