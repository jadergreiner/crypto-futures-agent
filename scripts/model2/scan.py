"""Model 2.0 opportunity scanner runner (isolated from legacy flow)."""

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

from config.settings import DB_PATH, M2_SYMBOLS, MODEL2_DB_PATH
from core.model2 import DetectorInput, Model2ThesisRepository, detect_initial_short_failure
from indicators.smc import SmartMoneyConcepts
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


def _load_indicators(conn: sqlite3.Connection, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM indicadores_tecnico
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (symbol, timeframe, limit),
    ).fetchall()
    if not rows:
        return []
    return [dict(row) for row in reversed(rows)]


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


def run_scan(
    source_db_path: str | Path,
    model2_db_path: str | Path,
    symbols: list[str],
    timeframe: str,
    candles_limit: int,
    dry_run: bool,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    if timeframe not in TIMEFRAME_TO_TABLE:
        raise ValueError(f"Unsupported timeframe {timeframe}. Supported: {sorted(TIMEFRAME_TO_TABLE)}")

    with sqlite3.connect(resolved_model2_db) as model2_conn:
        _ensure_model2_schema(model2_conn)

    source_conn = sqlite3.connect(resolved_source_db)
    source_conn.row_factory = sqlite3.Row
    repository = Model2ThesisRepository(str(resolved_model2_db))

    scanned = 0
    detected = 0
    persisted = 0
    items: list[dict[str, Any]] = []

    try:
        for symbol in symbols:
            scanned += 1
            entry: dict[str, Any] = {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "NO_DETECTION",
            }

            candles_df = _load_candles(
                conn=source_conn,
                symbol=symbol,
                timeframe=timeframe,
                limit=candles_limit,
            )
            if candles_df.empty:
                entry["status"] = "SKIPPED_NO_CANDLES"
                items.append(entry)
                continue

            indicators = _load_indicators(
                conn=source_conn,
                symbol=symbol,
                timeframe=timeframe,
                limit=candles_limit,
            )
            smc = SmartMoneyConcepts.calculate_all_smc(candles_df)
            detector_input = DetectorInput(
                symbol=symbol,
                timeframe=timeframe,
                candles=candles_df.to_dict(orient="records"),
                indicators=indicators,
                smc=smc,
                scan_timestamp=_utc_now_ms(),
            )
            result = detect_initial_short_failure(detector_input)
            if result is None:
                items.append(entry)
                continue

            detected += 1
            entry["status"] = "DETECTED"
            entry["thesis_type"] = result.thesis_type
            entry["trigger_price"] = result.trigger_price
            entry["invalidation_price"] = result.invalidation_price
            if not dry_run:
                save_result = repository.create_initial_thesis(result, now_ms=_utc_now_ms())
                if save_result.created_now:
                    persisted += 1
                    entry["status"] = "PERSISTED"
                else:
                    entry["status"] = "IDEMPOTENT_HIT"
                entry["opportunity_id"] = save_result.opportunity_id

            items.append(entry)
    finally:
        source_conn.close()

    summary = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "source_db_path": str(resolved_source_db),
        "model2_db_path": str(resolved_model2_db),
        "timeframe": timeframe,
        "dry_run": dry_run,
        "symbols_scanned": scanned,
        "detections": detected,
        "persisted_now": persisted,
        "items": items,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_scan_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 opportunity scanner")
    parser.add_argument(
        "--source-db-path",
        default=DB_PATH,
        help="Input SQLite with OHLCV/indicators (legacy analytics DB)",
    )
    parser.add_argument(
        "--model2-db-path",
        default=MODEL2_DB_PATH,
        help="Target Model 2.0 SQLite path (opportunities/events)",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Symbol to scan. Repeat to pass multiple values. Defaults to M2_SYMBOLS.",
    )
    parser.add_argument(
        "--timeframe",
        default="H4",
        choices=sorted(TIMEFRAME_TO_TABLE.keys()),
        help="Decision timeframe for the pattern detector.",
    )
    parser.add_argument(
        "--candles-limit",
        type=int,
        default=120,
        help="Number of latest candles loaded per symbol.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run detection without persisting opportunities/events.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for scanner run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    symbols = args.symbol or list(M2_SYMBOLS)
    summary = run_scan(
        source_db_path=args.source_db_path,
        model2_db_path=args.model2_db_path,
        symbols=symbols,
        timeframe=args.timeframe,
        candles_limit=args.candles_limit,
        dry_run=bool(args.dry_run),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

