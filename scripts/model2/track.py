"""Model 2.0 thesis tracker runner for M2-003.1."""

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

from config.settings import M2_SHORT_ONLY, MODEL2_DB_PATH
from core.model2 import M2_003_1_RULE_ID, Model2ThesisRepository
from scripts.model2.io_utils import atomic_write_json

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _ensure_model2_schema(conn: sqlite3.Connection) -> None:
    required_tables = {"schema_migrations", "opportunities", "opportunity_events"}
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


def run_tracking(
    *,
    model2_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    dry_run: bool,
    short_only: bool = False,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    with sqlite3.connect(resolved_model2_db) as model2_conn:
        _ensure_model2_schema(model2_conn)

    repository = Model2ThesisRepository(str(resolved_model2_db))
    identified_candidates = repository.list_identified_opportunities(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )
    candidates: list[dict[str, Any]] = []
    skipped_short_only = 0

    transitioned = 0
    skipped = 0
    items: list[dict[str, Any]] = []
    for candidate in identified_candidates:
        if short_only and str(candidate.get("side") or "").upper() != "SHORT":
            skipped_short_only += 1
            items.append(
                {
                    "opportunity_id": int(candidate["id"]),
                    "symbol": candidate["symbol"],
                    "timeframe": candidate["timeframe"],
                    "from_status": candidate["status"],
                    "status": "SKIPPED_SHORT_ONLY",
                    "reason": "short_only_enforced",
                }
            )
            continue
        candidates.append(candidate)

    for candidate in candidates:
        item = {
            "opportunity_id": int(candidate["id"]),
            "symbol": candidate["symbol"],
            "timeframe": candidate["timeframe"],
            "from_status": candidate["status"],
        }
        if dry_run:
            item["status"] = "DRY_RUN_READY"
            items.append(item)
            continue

        transition_result = repository.transition_to_monitoring(
            opportunity_id=int(candidate["id"]),
            now_ms=_utc_now_ms(),
            rule_id=M2_003_1_RULE_ID,
        )
        item["status"] = "TRANSITIONED" if transition_result.transitioned else "SKIPPED"
        item["reason"] = transition_result.reason
        item["to_status"] = transition_result.current_status
        items.append(item)

        if transition_result.transitioned:
            transitioned += 1
        else:
            skipped += 1

    summary = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "model2_db_path": str(resolved_model2_db),
        "dry_run": dry_run,
        "filters": {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "short_only": bool(short_only),
        },
        "identified_candidates": len(identified_candidates),
        "eligible_candidates": len(candidates),
        "skipped_short_only": skipped_short_only,
        "transitioned_now": transitioned,
        "skipped_now": skipped,
        "items": items,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_track_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 thesis tracker")
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
        help="Maximum number of IDENTIFICADA opportunities processed in one run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list transition candidates, without updating DB.",
    )
    parser.add_argument(
        "--short-only",
        action="store_true",
        default=M2_SHORT_ONLY,
        help="Enforce SHORT-only tracking (skip LONG opportunities).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for tracker run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_tracking(
        model2_db_path=args.model2_db_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
        dry_run=bool(args.dry_run),
        short_only=bool(args.short_only),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
