"""Model 2.0 audit snapshot runner for M2-004.2."""

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


def run_audit_snapshot(
    *,
    model2_db_path: str | Path,
    output_dir: str | Path,
    retention_days: int,
    opportunity_id: int | None,
    symbol: str | None,
    timeframe: str | None,
    start_ts: int | None,
    end_ts: int | None,
    limit: int,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as model2_conn:
        _ensure_model2_observability_schema(model2_conn)

    now_ms = _utc_now_ms()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    service = Model2ObservabilityService(str(resolved_model2_db))
    snapshot = service.refresh_audit_snapshot(
        run_id=run_id,
        snapshot_timestamp=now_ms,
        retention_days=retention_days,
        opportunity_id=opportunity_id,
        symbol=symbol,
        timeframe=timeframe,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
    )

    summary: dict[str, Any] = {
        "status": "ok",
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "model2_db_path": str(resolved_model2_db),
        "retention_days": int(retention_days),
        "filters": {
            "opportunity_id": opportunity_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "limit": int(limit),
        },
        "stored_rows": snapshot.stored_rows,
        "purged_rows": snapshot.purged_rows,
        "items": snapshot.rows,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_audit_{run_id}.json"
    output_file.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 audit snapshots")
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
        "--opportunity-id",
        type=int,
        default=None,
        help="Optional opportunity id filter.",
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Optional symbol filter.",
    )
    parser.add_argument(
        "--timeframe",
        default=None,
        help="Optional timeframe filter.",
    )
    parser.add_argument(
        "--start-ts",
        type=int,
        default=None,
        help="Optional event_timestamp lower bound (UTC ms).",
    )
    parser.add_argument(
        "--end-ts",
        type=int,
        default=None,
        help="Optional event_timestamp upper bound (UTC ms).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of transitions returned in one snapshot.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for audit run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_audit_snapshot(
        model2_db_path=args.model2_db_path,
        output_dir=args.output_dir,
        retention_days=args.retention_days,
        opportunity_id=args.opportunity_id,
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_ts=args.start_ts,
        end_ts=args.end_ts,
        limit=args.limit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
