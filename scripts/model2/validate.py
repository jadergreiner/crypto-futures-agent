"""Model 2.0 validator runner for M2-003.2."""

from __future__ import annotations

import argparse
import importlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

pd = importlib.import_module("pandas")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import DB_PATH, MODEL2_DB_PATH
from core.model2 import (
    M2_003_2_RULE_ID,
    Model2ThesisRepository,
    ValidationInput,
    evaluate_monitoring_validation,
)
from core.model2.ohlcv_cache import OhlcvCacheProvider, build_cache_key
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


def _load_candles(conn: sqlite3.Connection, symbol: str, timeframe: str, limit: int) -> Any:
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


def _load_candles_cached(
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    limit: int,
    cache_provider: OhlcvCacheProvider,
) -> Any:
    def _loader(target_symbol: str, target_timeframe: str, target_limit: int) -> list[dict[str, Any]]:
        raw_records = _load_candles(
            conn=conn,
            symbol=target_symbol,
            timeframe=target_timeframe,
            limit=target_limit,
        ).to_dict(orient="records")
        return cast(list[dict[str, Any]], raw_records)

    key = build_cache_key(symbol=symbol, timeframe=timeframe, limit=limit)
    result = cache_provider.get_many([(symbol, timeframe, limit)], _loader)[key]
    if not result.candles:
        return pd.DataFrame()
    candles_df = pd.DataFrame(result.candles)
    if "timestamp" in candles_df.columns:
        candles_df = candles_df.sort_values("timestamp").reset_index(drop=True)
    return candles_df


def run_validation(
    *,
    source_db_path: str | Path,
    model2_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    candles_limit: int,
    dry_run: bool,
    output_dir: str | Path,
    cache_provider: OhlcvCacheProvider | None = None,
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

    validated = 0
    not_validated = 0
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

            metadata_raw = candidate.get("metadata_json")
            try:
                metadata = json.loads(metadata_raw or "{}")
            except json.JSONDecodeError:
                metadata = {}

            candles_df = _load_candles(
                conn=source_conn,
                symbol=str(candidate["symbol"]),
                timeframe=candidate_timeframe,
                limit=candles_limit,
            ) if cache_provider is None else _load_candles_cached(
                conn=source_conn,
                symbol=str(candidate["symbol"]),
                timeframe=candidate_timeframe,
                limit=candles_limit,
                cache_provider=cache_provider,
            )
            validation_input = ValidationInput(
                opportunity_id=int(candidate["id"]),
                symbol=str(candidate["symbol"]),
                timeframe=candidate_timeframe,
                side=str(candidate["side"]),
                trigger_price=float(candidate["trigger_price"]),
                zone_low=float(candidate["zone_low"]),
                monitoring_started_at=(
                    int(candidate["monitoring_started_at"])
                    if candidate.get("monitoring_started_at") is not None
                    else None
                ),
                metadata=metadata,
                candles=candles_df.to_dict(orient="records"),
                validation_timestamp=_utc_now_ms(),
            )
            decision = evaluate_monitoring_validation(validation_input)
            item["decision_reason"] = decision.reason
            if not decision.is_validated:
                item["status"] = "NOT_VALIDATED"
                item["details"] = dict(decision.details)
                not_validated += 1
                items.append(item)
                continue

            if dry_run:
                item["status"] = "DRY_RUN_VALIDATED"
                item["details"] = dict(decision.details)
                validated += 1
                items.append(item)
                continue

            transition_result = repository.transition_to_validated(
                opportunity_id=int(candidate["id"]),
                now_ms=_utc_now_ms(),
                rule_id=M2_003_2_RULE_ID,
                payload=decision.details,
            )
            item["status"] = "VALIDATED" if transition_result.transitioned else "SKIPPED"
            item["to_status"] = transition_result.current_status
            item["transition_reason"] = transition_result.reason
            item["details"] = dict(decision.details)
            items.append(item)

            if transition_result.transitioned:
                validated += 1
            else:
                skipped += 1
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
        "validated_now": validated,
        "not_validated_now": not_validated,
        "skipped_now": skipped,
        "items": items,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_validate_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 thesis validator")
    parser.add_argument(
        "--source-db-path",
        default=DB_PATH,
        help="Input SQLite with OHLCV candles used for validation rules.",
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
        help="Number of latest candles loaded per opportunity during validation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate rules without persisting status transitions.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for validator run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_validation(
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
