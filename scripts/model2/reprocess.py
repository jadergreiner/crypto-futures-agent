"""Model 2.0 historical replay runner for M2-005.2."""

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
from config.symbols import ALL_SYMBOLS
from core.model2 import (
    DetectorInput,
    Model2ThesisRepository,
    ResolutionInput,
    ValidationInput,
    detect_initial_short_failure,
    evaluate_monitoring_resolution,
    evaluate_monitoring_validation,
)
from core.model2.resolver import RESOLUTION_ACTION_EXPIRED, RESOLUTION_ACTION_INVALIDATED
from core.model2.thesis_state import OFFICIAL_THESIS_STATUSES
from indicators.smc import SmartMoneyConcepts
from scripts.model2.migrate import run_up

DEFAULT_REPLAY_DB_PATH = "db/modelo2_replay.db"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"
TIMEFRAME_TO_TABLE = {
    "D1": "ohlcv_d1",
    "H4": "ohlcv_h4",
    "H1": "ohlcv_h1",
}


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _load_candles_until_timestamp(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    timeframe: str,
    end_ts: int,
    limit: int,
) -> pd.DataFrame:
    table_name = TIMEFRAME_TO_TABLE[timeframe]
    query = (
        f"SELECT timestamp, open, high, low, close, volume "
        f"FROM {table_name} "
        f"WHERE symbol = ? AND timestamp <= ? "
        f"ORDER BY timestamp DESC LIMIT ?"
    )
    rows = conn.execute(query, (symbol, int(end_ts), int(limit))).fetchall()
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return frame.sort_values("timestamp").reset_index(drop=True)


def _load_indicators_until_timestamp(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    timeframe: str,
    end_ts: int,
    limit: int,
) -> list[dict[str, Any]]:
    table_exists = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='indicadores_tecnico'"
    ).fetchone()[0]
    if int(table_exists) == 0:
        return []

    rows = conn.execute(
        """
        SELECT *
        FROM indicadores_tecnico
        WHERE symbol = ? AND timeframe = ? AND timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (symbol, timeframe, int(end_ts), int(limit)),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def _ensure_source_table(conn: sqlite3.Connection, table_name: str) -> None:
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    if row is None or int(row[0]) == 0:
        raise RuntimeError(f"Missing source table '{table_name}' in source DB.")


def _collect_timestamps(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    symbols: list[str],
    start_ts: int | None,
    end_ts: int | None,
) -> list[int]:
    if not symbols:
        return []
    placeholders = ", ".join(["?"] * len(symbols))
    query_parts = [
        f"SELECT DISTINCT timestamp FROM {table_name}",
        f"WHERE symbol IN ({placeholders})",
    ]
    params: list[Any] = [*symbols]
    if start_ts is not None:
        query_parts.append("AND timestamp >= ?")
        params.append(int(start_ts))
    if end_ts is not None:
        query_parts.append("AND timestamp <= ?")
        params.append(int(end_ts))
    query_parts.append("ORDER BY timestamp ASC")
    rows = conn.execute(" ".join(query_parts), params).fetchall()
    return [int(row[0]) for row in rows]


def _safe_division(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _reset_replay_data(conn: sqlite3.Connection) -> None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM opportunity_audit_snapshots")
        conn.execute("DELETE FROM opportunity_dashboard_snapshots")
        conn.execute("DELETE FROM opportunity_events")
        conn.execute("DELETE FROM opportunities")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def run_reprocess(
    *,
    source_db_path: str | Path,
    replay_db_path: str | Path,
    symbols: list[str],
    timeframe: str,
    start_ts: int | None,
    end_ts: int | None,
    candles_limit: int,
    transition_limit: int,
    output_dir: str | Path,
    allow_operational_db: bool = False,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_replay_db = _resolve_repo_path(replay_db_path)
    resolved_operational_db = _resolve_repo_path(MODEL2_DB_PATH)
    resolved_output_dir = _resolve_repo_path(output_dir)

    if not allow_operational_db and resolved_replay_db == resolved_operational_db:
        raise ValueError(
            "Replay DB cannot match operational Model2 DB. "
            "Use --allow-operational-db to bypass explicitly."
        )
    if timeframe not in TIMEFRAME_TO_TABLE:
        raise ValueError(f"Unsupported timeframe {timeframe}. Supported: {sorted(TIMEFRAME_TO_TABLE)}")
    if start_ts is not None and end_ts is not None and int(start_ts) > int(end_ts):
        raise ValueError("start_ts must be <= end_ts")

    run_up(db_path=resolved_replay_db, output_dir=resolved_output_dir)
    with sqlite3.connect(resolved_replay_db) as replay_conn:
        _reset_replay_data(replay_conn)

    source_conn = sqlite3.connect(resolved_source_db)
    source_conn.row_factory = sqlite3.Row
    replay_repository = Model2ThesisRepository(str(resolved_replay_db))
    table_name = TIMEFRAME_TO_TABLE[timeframe]

    detection_created = 0
    detection_idempotent = 0
    transitioned_monitoring = 0
    validated_now = 0
    invalidated_now = 0
    expired_now = 0
    scanned_symbols = 0
    processed_timestamps = 0

    _ensure_source_table(source_conn, table_name)
    timeline = _collect_timestamps(
        source_conn,
        table_name=table_name,
        symbols=symbols,
        start_ts=start_ts,
        end_ts=end_ts,
    )

    try:
        for timestamp in timeline:
            processed_timestamps += 1
            for symbol in symbols:
                scanned_symbols += 1
                candles_df = _load_candles_until_timestamp(
                    source_conn,
                    symbol=symbol,
                    timeframe=timeframe,
                    end_ts=timestamp,
                    limit=candles_limit,
                )
                if candles_df.empty:
                    continue

                indicators = _load_indicators_until_timestamp(
                    source_conn,
                    symbol=symbol,
                    timeframe=timeframe,
                    end_ts=timestamp,
                    limit=candles_limit,
                )
                smc = SmartMoneyConcepts.calculate_all_smc(candles_df)
                detection = detect_initial_short_failure(
                    DetectorInput(
                        symbol=symbol,
                        timeframe=timeframe,
                        candles=candles_df.to_dict(orient="records"),
                        indicators=indicators,
                        smc=smc,
                        scan_timestamp=timestamp,
                    )
                )
                if detection is not None:
                    created = replay_repository.create_initial_thesis(detection, now_ms=timestamp)
                    if created.created_now:
                        detection_created += 1
                    else:
                        detection_idempotent += 1

                identified = replay_repository.list_identified_opportunities(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=transition_limit,
                )
                for candidate in identified:
                    transition = replay_repository.transition_to_monitoring(
                        opportunity_id=int(candidate["id"]),
                        now_ms=timestamp,
                    )
                    if transition.transitioned:
                        transitioned_monitoring += 1

                monitoring_for_validation = replay_repository.list_monitoring_opportunities(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=transition_limit,
                )
                for candidate in monitoring_for_validation:
                    metadata: dict[str, Any]
                    try:
                        metadata = json.loads(candidate.get("metadata_json") or "{}")
                    except json.JSONDecodeError:
                        metadata = {}

                    decision = evaluate_monitoring_validation(
                        ValidationInput(
                            opportunity_id=int(candidate["id"]),
                            symbol=str(candidate["symbol"]),
                            timeframe=str(candidate["timeframe"]),
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
                            validation_timestamp=timestamp,
                        )
                    )
                    if not decision.is_validated:
                        continue
                    transitioned = replay_repository.transition_to_validated(
                        opportunity_id=int(candidate["id"]),
                        now_ms=timestamp,
                        payload=decision.details,
                    )
                    if transitioned.transitioned:
                        validated_now += 1

                monitoring_for_resolution = replay_repository.list_monitoring_opportunities(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=transition_limit,
                )
                for candidate in monitoring_for_resolution:
                    decision = evaluate_monitoring_resolution(
                        ResolutionInput(
                            opportunity_id=int(candidate["id"]),
                            symbol=str(candidate["symbol"]),
                            timeframe=str(candidate["timeframe"]),
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
                            resolution_timestamp=timestamp,
                        )
                    )
                    if decision.action == RESOLUTION_ACTION_INVALIDATED:
                        transitioned = replay_repository.transition_to_invalidated(
                            opportunity_id=int(candidate["id"]),
                            now_ms=timestamp,
                            payload=decision.details,
                        )
                        if transitioned.transitioned:
                            invalidated_now += 1
                    elif decision.action == RESOLUTION_ACTION_EXPIRED:
                        transitioned = replay_repository.transition_to_expired(
                            opportunity_id=int(candidate["id"]),
                            now_ms=timestamp,
                            payload=decision.details,
                        )
                        if transitioned.transitioned:
                            expired_now += 1
    finally:
        source_conn.close()

    counts_by_status = {status: 0 for status in OFFICIAL_THESIS_STATUSES}
    with sqlite3.connect(resolved_replay_db) as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM opportunities
            GROUP BY status
            """
        ).fetchall()
        for row in rows:
            status = str(row[0])
            if status in counts_by_status:
                counts_by_status[status] = int(row[1])

    directional_denom = counts_by_status["VALIDADA"] + counts_by_status["INVALIDADA"]
    resolved_denom = directional_denom + counts_by_status["EXPIRADA"]

    rates = {
        "directional": {
            "validated_over_validated_plus_invalidated": _safe_division(
                counts_by_status["VALIDADA"], directional_denom
            ),
            "invalidated_over_validated_plus_invalidated": _safe_division(
                counts_by_status["INVALIDADA"], directional_denom
            ),
            "denominator": directional_denom,
        },
        "resolved": {
            "validated_over_resolved": _safe_division(
                counts_by_status["VALIDADA"], resolved_denom
            ),
            "invalidated_over_resolved": _safe_division(
                counts_by_status["INVALIDADA"], resolved_denom
            ),
            "denominator": resolved_denom,
        },
    }

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary: dict[str, Any] = {
        "status": "ok",
        "run_id": run_id,
        "timestamp_utc_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
        "source_db_path": str(resolved_source_db),
        "replay_db_path": str(resolved_replay_db),
        "timeframe": timeframe,
        "filters": {
            "symbols": symbols,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "candles_limit": candles_limit,
            "transition_limit": transition_limit,
        },
        "timeline_points": len(timeline),
        "processed_timestamps": processed_timestamps,
        "symbol_iterations": scanned_symbols,
        "detections_created_now": detection_created,
        "detections_idempotent_hits": detection_idempotent,
        "monitoring_transitions_now": transitioned_monitoring,
        "validated_now": validated_now,
        "invalidated_now": invalidated_now,
        "expired_now": expired_now,
        "final_count_by_status": counts_by_status,
        "rates": rates,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_reprocess_{run_id}.json"
    output_file.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 historical replay")
    parser.add_argument(
        "--source-db-path",
        default=DB_PATH,
        help="Input SQLite with OHLCV candles.",
    )
    parser.add_argument(
        "--replay-db-path",
        default=DEFAULT_REPLAY_DB_PATH,
        help="Replay-only Model 2.0 SQLite path.",
    )
    parser.add_argument(
        "--allow-operational-db",
        action="store_true",
        help="Allow replay against operational MODEL2_DB_PATH (disabled by default).",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Symbol to reprocess. Repeat to pass multiple values. Defaults to ALL_SYMBOLS.",
    )
    parser.add_argument(
        "--timeframe",
        default="H4",
        choices=sorted(TIMEFRAME_TO_TABLE.keys()),
        help="Replay timeframe.",
    )
    parser.add_argument(
        "--start-ts",
        type=int,
        default=None,
        help="Lower bound timestamp (UTC ms).",
    )
    parser.add_argument(
        "--end-ts",
        type=int,
        default=None,
        help="Upper bound timestamp (UTC ms).",
    )
    parser.add_argument(
        "--candles-limit",
        type=int,
        default=240,
        help="Number of candles loaded up to each replay timestamp.",
    )
    parser.add_argument(
        "--transition-limit",
        type=int,
        default=200,
        help="Maximum opportunities consumed per state transition phase per symbol/timestamp.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for replay run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    symbols = args.symbol or list(ALL_SYMBOLS)
    summary = run_reprocess(
        source_db_path=args.source_db_path,
        replay_db_path=args.replay_db_path,
        symbols=symbols,
        timeframe=args.timeframe,
        start_ts=args.start_ts,
        end_ts=args.end_ts,
        candles_limit=args.candles_limit,
        transition_limit=args.transition_limit,
        output_dir=args.output_dir,
        allow_operational_db=bool(args.allow_operational_db),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
