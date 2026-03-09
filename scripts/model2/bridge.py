"""Model 2.0 signal bridge runner for M2-006.1."""

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
from core.model2 import Model2ThesisRepository

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _ensure_model2_bridge_schema(conn: sqlite3.Connection) -> None:
    required_tables = {"schema_migrations", "opportunities", "opportunity_events", "technical_signals"}
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


def run_bridge(
    *,
    model2_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    dry_run: bool,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as conn:
        _ensure_model2_bridge_schema(conn)

    repository = Model2ThesisRepository(str(resolved_model2_db))
    candidates = repository.list_validated_opportunities(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )

    created_now = 0
    idempotent_hits = 0
    rejected_by_rule = 0
    items: list[dict[str, Any]] = []

    for candidate in candidates:
        item: dict[str, Any] = {
            "opportunity_id": int(candidate["id"]),
            "symbol": str(candidate["symbol"]),
            "timeframe": str(candidate["timeframe"]),
            "status": str(candidate["status"]),
        }
        if dry_run:
            item["result"] = "DRY_RUN_ELIGIBLE"
            items.append(item)
            continue

        result = repository.create_standard_signal_from_validated(
            opportunity_id=int(candidate["id"]),
            now_ms=_utc_now_ms(),
        )
        item["result"] = result.reason
        item["signal_id"] = result.signal_id
        items.append(item)

        if result.created:
            created_now += 1
        elif result.reason == "already_exists":
            idempotent_hits += 1
        else:
            rejected_by_rule += 1

    summary = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "model2_db_path": str(resolved_model2_db),
        "dry_run": dry_run,
        "filters": {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
        },
        "eligible_candidates": len(candidates),
        "signals_created_now": created_now,
        "idempotent_hits_now": idempotent_hits,
        "rule_rejections_now": rejected_by_rule,
        "items": items,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_bridge_{run_id}.json"
    output_file.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 signal bridge")
    parser.add_argument(
        "--model2-db-path",
        default=MODEL2_DB_PATH,
        help="Target Model 2.0 SQLite path.",
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
        "--limit",
        type=int,
        default=200,
        help="Maximum number of VALIDADA opportunities processed in one run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate bridge candidates without persisting technical signals.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for bridge run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_bridge(
        model2_db_path=args.model2_db_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
        dry_run=bool(args.dry_run),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
