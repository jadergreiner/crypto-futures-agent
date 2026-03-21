"""Model 2.0 resolver runner for M2-003.3."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import DB_PATH, MODEL2_DB_PATH
from core.model2 import (
    M2_003_3_RULE_ID_EXPIRATION,
    M2_003_3_RULE_ID_INVALIDATION,
    Model2ThesisRepository,
    RESOLUTION_ACTION_EXPIRED,
    RESOLUTION_ACTION_INVALIDATED,
    ResolutionInput,
    evaluate_monitoring_resolution,
)
from scripts.model2.io_utils import atomic_write_json

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"
TIMEFRAME_TO_TABLE = {
    "D1": "ohlcv_d1",
    "H4": "ohlcv_h4",
    "H1": "ohlcv_h1",
}


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


def _load_candles(conn: sqlite3.Connection, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    table_name = TIMEFRAME_TO_TABLE[timeframe]
    query = (
        f"SELECT timestamp, open, high, low, close, volume "
        f"FROM {table_name} WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?"
    )
    rows = conn.execute(query, (symbol, limit)).fetchall()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df.sort_values("timestamp").reset_index(drop=True)


def run_resolution(
    *,
    source_db_path: str | Path,
    model2_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    candles_limit: int,
    dry_run: bool,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as model2_conn:
        _ensure_model2_schema(model2_conn)

    source_conn = sqlite3.connect(resolved_source_db)
    source_conn.row_factory = sqlite3.Row
    repository = Model2ThesisRepository(str(resolved_model2_db))
    candidates = repository.list_monitoring_opportunities(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )

    invalidated = 0
    expired = 0
    no_resolution = 0
    skipped = 0
    items: list[dict[str, Any]] = []

    try:
        for candidate in candidates:
            candidate_timeframe = str(candidate["timeframe"])
            item: dict[str, Any] = {
                "opportunity_id": int(candidate["id"]),
                "symbol": candidate["symbol"],
                "timeframe": candidate_timeframe,
                "from_status": candidate["status"],
            }
            if candidate_timeframe not in TIMEFRAME_TO_TABLE:
                item["status"] = "SKIPPED_UNSUPPORTED_TIMEFRAME"
                skipped += 1
                items.append(item)
                continue

            candles_df = _load_candles(
                conn=source_conn,
                symbol=str(candidate["symbol"]),
                timeframe=candidate_timeframe,
                limit=candles_limit,
            )
            decision = evaluate_monitoring_resolution(
                ResolutionInput(
                    opportunity_id=int(candidate["id"]),
                    symbol=str(candidate["symbol"]),
                    timeframe=candidate_timeframe,
                    side=str(candidate["side"]),
                    invalidation_price=float(candidate["invalidation_price"]),
                    expires_at=(
                        int(candidate["expires_at"])
                        if candidate.get("expires_at") is not None
                        else None
                    ),
                    monitoring_started_at=(
                        int(candidate["monitoring_started_at"])
                        if candidate.get("monitoring_started_at") is not None
                        else None
                    ),
                    candles=candles_df.to_dict(orient="records"),
                    resolution_timestamp=_utc_now_ms(),
                )
            )
            item["decision_reason"] = decision.reason
            item["details"] = dict(decision.details)

            if decision.action == RESOLUTION_ACTION_INVALIDATED:
                if dry_run:
                    item["status"] = "DRY_RUN_INVALIDATED"
                    invalidated += 1
                    items.append(item)
                    continue
                result = repository.transition_to_invalidated(
                    opportunity_id=int(candidate["id"]),
                    now_ms=_utc_now_ms(),
                    rule_id=M2_003_3_RULE_ID_INVALIDATION,
                    payload=decision.details,
                )
                item["status"] = "INVALIDATED" if result.transitioned else "SKIPPED"
                item["to_status"] = result.current_status
                item["transition_reason"] = result.reason
                items.append(item)
                if result.transitioned:
                    invalidated += 1
                else:
                    skipped += 1
                continue

            if decision.action == RESOLUTION_ACTION_EXPIRED:
                if dry_run:
                    item["status"] = "DRY_RUN_EXPIRED"
                    expired += 1
                    items.append(item)
                    continue
                result = repository.transition_to_expired(
                    opportunity_id=int(candidate["id"]),
                    now_ms=_utc_now_ms(),
                    rule_id=M2_003_3_RULE_ID_EXPIRATION,
                    payload=decision.details,
                )
                item["status"] = "EXPIRED" if result.transitioned else "SKIPPED"
                item["to_status"] = result.current_status
                item["transition_reason"] = result.reason
                items.append(item)
                if result.transitioned:
                    expired += 1
                else:
                    skipped += 1
                continue

            item["status"] = "NO_RESOLUTION"
            no_resolution += 1
            items.append(item)
    finally:
        source_conn.close()

    summary = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "source_db_path": str(resolved_source_db),
        "model2_db_path": str(resolved_model2_db),
        "dry_run": dry_run,
        "filters": {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "candles_limit": candles_limit,
        },
        "monitoring_candidates": len(candidates),
        "invalidated_now": invalidated,
        "expired_now": expired,
        "no_resolution_now": no_resolution,
        "skipped_now": skipped,
        "items": items,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_resolve_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 thesis resolver")
    parser.add_argument(
        "--source-db-path",
        default=DB_PATH,
        help="Input SQLite with OHLCV candles used for invalidation/expiration rules.",
    )
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
        help="Maximum number of MONITORANDO opportunities processed in one run.",
    )
    parser.add_argument(
        "--candles-limit",
        type=int,
        default=240,
        help="Number of latest candles loaded per opportunity during resolution.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate rules without persisting status transitions.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for resolver run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_resolution(
        source_db_path=args.source_db_path,
        model2_db_path=args.model2_db_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
        candles_limit=args.candles_limit,
        dry_run=bool(args.dry_run),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
