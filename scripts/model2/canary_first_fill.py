"""Orchestrate first canary fill validation for Model 2.0 short-only live."""

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

from config.settings import (
    DB_PATH,
    M2_CANARY_DB_PATH,
    M2_CANARY_LEVERAGE,
    M2_EXECUTION_MODE,
    M2_FUNDING_RATE_MAX_FOR_SHORT,
    M2_INJECTION_ENABLED,
    M2_LIVE_SYMBOLS,
    M2_MAX_DAILY_ENTRIES,
    M2_MAX_MARGIN_PER_POSITION_USD,
    M2_MAX_SIGNAL_AGE_MINUTES,
    M2_SYMBOL_COOLDOWN_MINUTES,
)
from core.model2 import M2_002_RULE_ID, M2_002_THESIS_TYPE, DetectionResult, Model2ThesisRepository
from scripts.model2.daily_pipeline import run_daily_pipeline
from scripts.model2.io_utils import atomic_write_json
from scripts.model2.live_cycle import run_live_cycle
from scripts.model2.migrate import run_up

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


def _remove_sqlite_files(db_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{db_path}{suffix}")
        if candidate.exists():
            candidate.unlink()


def _load_reference_price_from_source_db(
    *,
    source_db_path: Path,
    symbol: str,
    timeframe: str,
) -> float | None:
    table_name = TIMEFRAME_TO_TABLE.get(str(timeframe).upper())
    if table_name is None:
        return None
    if not source_db_path.exists():
        return None
    try:
        with sqlite3.connect(source_db_path) as conn:
            row = conn.execute(
                f"SELECT close FROM {table_name} WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
                (symbol,),
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    try:
        close_price = float(row[0])
    except (TypeError, ValueError):
        return None
    if close_price <= 0:
        return None
    return close_price


def _inject_controlled_short_signal(
    *,
    model2_db_path: Path,
    source_db_path: Path,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    now_ms = _utc_now_ms()
    repo = Model2ThesisRepository(str(model2_db_path))
    reference_price = _load_reference_price_from_source_db(
        source_db_path=source_db_path,
        symbol=symbol,
        timeframe=timeframe,
    )
    entry_price = float(reference_price or 100.0)
    stop_loss = entry_price * 1.01
    take_profit = entry_price * 0.99
    trigger_price = entry_price * 0.999
    zone_low = entry_price * 0.998
    zone_high = entry_price * 1.002
    detection = DetectionResult(
        detected=True,
        symbol=symbol,
        timeframe=timeframe,
        side="SHORT",
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=float(zone_low),
        zone_high=float(zone_high),
        trigger_price=float(trigger_price),
        invalidation_price=float(stop_loss),
        metadata={
            "rule_id": M2_002_RULE_ID,
            "rule_version": "canary_injection_v1",
            "scan_timestamp": now_ms,
            "rejection_candle": {
                "timestamp": now_ms - 3_000,
                "open": float(entry_price),
                "high": float(stop_loss),
                "low": float(take_profit),
                "close": float(trigger_price),
            },
            "context": {
                "market_structure": "range",
                "is_non_bullish_context": True,
                "source": "canary_injection",
                "basis": 0.001,
                "funding_rate": -0.0001,
                "market_regime": "RISK_ON",
                "reference_price": float(entry_price),
                "reference_price_source": (
                    "source_db_latest_close" if reference_price is not None else "fallback_static"
                ),
            },
            "parameters": {
                "controlled_injection": True,
            },
        },
        rule_id=M2_002_RULE_ID,
    )
    created = repo.create_initial_thesis(detection, now_ms=now_ms - 2_000)
    repo.transition_to_monitoring(opportunity_id=created.opportunity_id, now_ms=now_ms - 1_000)
    repo.transition_to_validated(
        opportunity_id=created.opportunity_id,
        now_ms=now_ms - 500,
        payload={"source": "canary_injection"},
    )
    signal = repo.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=now_ms,
    )
    if signal.signal_id is None:
        return {
            "status": "error",
            "reason": signal.reason,
            "opportunity_id": created.opportunity_id,
            "signal_id": None,
        }

    consumed = repo.consume_created_signal_for_order_layer(
        signal_id=int(signal.signal_id),
        now_ms=now_ms + 1,
        short_only=True,
    )
    return {
        "status": "ok",
        "opportunity_id": int(created.opportunity_id),
        "signal_id": int(signal.signal_id),
        "consume_reason": consumed.reason,
        "consume_status": consumed.current_status,
    }


def _query_first_fill(db_path: Path) -> dict[str, Any] | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, opportunity_id, symbol, signal_side, execution_mode, status,
                   exchange_order_id, requested_qty, filled_price, created_at, updated_at
            FROM signal_executions
            WHERE execution_mode = 'live'
              AND signal_side = 'SHORT'
              AND status = 'ENTRY_FILLED'
              AND exchange_order_id IS NOT NULL
              AND TRIM(exchange_order_id) <> ''
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row is not None else None


def _validate_analysis_persistence(db_path: Path, opportunity_id: int) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        opportunity = conn.execute(
            "SELECT id, status, side FROM opportunities WHERE id = ?",
            (int(opportunity_id),),
        ).fetchone()
        events_count = conn.execute(
            "SELECT COUNT(*) FROM opportunity_events WHERE opportunity_id = ?",
            (int(opportunity_id),),
        ).fetchone()[0]
    return {
        "opportunity_exists": bool(opportunity),
        "opportunity_events_count": int(events_count),
    }


def run_canary_first_fill(
    *,
    source_db_path: str | Path,
    model2_canary_db_path: str | Path,
    output_dir: str | Path,
    symbols: list[str],
    timeframe: str,
    clean_db: bool,
    injection_enabled: bool,
    execution_mode: str,
    max_daily_entries: int,
    max_margin_per_position_usd: float,
    max_signal_age_minutes: int,
    symbol_cooldown_minutes: int,
    leverage: int,
    funding_rate_max_for_short: float,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_model2_db = _resolve_repo_path(model2_canary_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if clean_db:
        resolved_model2_db.parent.mkdir(parents=True, exist_ok=True)
        _remove_sqlite_files(resolved_model2_db)

    migrate_summary = run_up(db_path=resolved_model2_db, output_dir=resolved_output_dir)
    pipeline_summary = run_daily_pipeline(
        source_db_path=resolved_source_db,
        model2_db_path=resolved_model2_db,
        legacy_db_path=resolved_source_db,
        symbols=symbols,
        timeframe=timeframe,
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=False,
        continue_on_error=True,
        retention_days=30,
        output_dir=resolved_output_dir,
    )
    live_summary = run_live_cycle(
        model2_db_path=resolved_model2_db,
        symbol=None,
        timeframe=timeframe,
        limit=200,
        output_dir=resolved_output_dir,
        execution_mode=execution_mode,
        live_symbols=tuple(symbols),
        max_daily_entries=max_daily_entries,
        max_margin_per_position_usd=max_margin_per_position_usd,
        max_signal_age_minutes=max_signal_age_minutes,
        symbol_cooldown_minutes=symbol_cooldown_minutes,
        short_only=True,
        funding_rate_max_for_short=funding_rate_max_for_short,
        leverage=leverage,
    )

    fill_row = _query_first_fill(resolved_model2_db)
    injection_summary: dict[str, Any] | None = None
    if fill_row is None and injection_enabled:
        injection_summary = _inject_controlled_short_signal(
            model2_db_path=resolved_model2_db,
            source_db_path=resolved_source_db,
            symbol=symbols[0],
            timeframe=timeframe,
        )
        live_summary = run_live_cycle(
            model2_db_path=resolved_model2_db,
            symbol=symbols[0],
            timeframe=timeframe,
            limit=200,
            output_dir=resolved_output_dir,
            execution_mode=execution_mode,
            live_symbols=tuple(symbols),
            max_daily_entries=max_daily_entries,
            max_margin_per_position_usd=max_margin_per_position_usd,
            max_signal_age_minutes=max_signal_age_minutes,
            symbol_cooldown_minutes=symbol_cooldown_minutes,
            short_only=True,
            funding_rate_max_for_short=funding_rate_max_for_short,
            leverage=leverage,
        )
        fill_row = _query_first_fill(resolved_model2_db)

    analysis_checks = (
        _validate_analysis_persistence(resolved_model2_db, int(fill_row["opportunity_id"]))
        if fill_row is not None
        else {"opportunity_exists": False, "opportunity_events_count": 0}
    )
    leverage_effective = None
    leverage_ok = False
    if fill_row is not None and float(max_margin_per_position_usd) > 0:
        leverage_effective = (float(fill_row["requested_qty"] or 0.0) * float(fill_row["filled_price"] or 0.0)) / float(max_margin_per_position_usd)
        leverage_ok = abs(float(leverage_effective) - float(leverage)) <= 0.6

    success = bool(
        fill_row is not None
        and analysis_checks["opportunity_exists"]
        and int(analysis_checks["opportunity_events_count"]) > 0
        and leverage_ok
    )

    summary: dict[str, Any] = {
        "status": "ok" if success else "alert",
        "run_id": run_id,
        "timestamp_utc_ms": _utc_now_ms(),
        "source_db_path": str(resolved_source_db),
        "model2_canary_db_path": str(resolved_model2_db),
        "execution_mode": execution_mode,
        "short_only": True,
        "symbols": list(symbols),
        "timeframe": timeframe,
        "clean_db": bool(clean_db),
        "injection_enabled": bool(injection_enabled),
        "migrate_summary": migrate_summary,
        "pipeline_summary_file": pipeline_summary.get("output_file"),
        "live_summary_status": live_summary.get("status"),
        "injection_summary": injection_summary,
        "first_fill": fill_row,
        "analysis_checks": analysis_checks,
        "leverage_target": int(leverage),
        "leverage_effective": float(leverage_effective) if leverage_effective is not None else None,
        "leverage_ok": bool(leverage_ok),
        "acceptance": {
            "has_entry_filled_short_live": bool(fill_row is not None),
            "has_analysis_persisted": bool(analysis_checks["opportunity_exists"] and analysis_checks["opportunity_events_count"] > 0),
            "leverage_profile_ok": bool(leverage_ok),
        },
    }
    output_file = resolved_output_dir / f"model2_canary_first_fill_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run first short canary fill acceptance flow.")
    parser.add_argument("--source-db-path", default=DB_PATH)
    parser.add_argument("--model2-canary-db-path", default=M2_CANARY_DB_PATH)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--timeframe", default="H4", choices=["D1", "H4", "H1"])
    parser.add_argument("--clean-db", action="store_true", default=True)
    parser.add_argument("--no-clean-db", action="store_true")
    parser.add_argument("--injection-enabled", action="store_true", default=M2_INJECTION_ENABLED)
    parser.add_argument("--execution-mode", default=M2_EXECUTION_MODE)
    parser.add_argument("--max-daily-entries", type=int, default=M2_MAX_DAILY_ENTRIES)
    parser.add_argument("--max-margin-per-position-usd", type=float, default=M2_MAX_MARGIN_PER_POSITION_USD)
    parser.add_argument("--max-signal-age-minutes", type=int, default=M2_MAX_SIGNAL_AGE_MINUTES)
    parser.add_argument("--symbol-cooldown-minutes", type=int, default=M2_SYMBOL_COOLDOWN_MINUTES)
    parser.add_argument("--leverage", type=int, default=M2_CANARY_LEVERAGE)
    parser.add_argument("--funding-rate-max-for-short", type=float, default=M2_FUNDING_RATE_MAX_FOR_SHORT)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    clean_db = bool(args.clean_db) and not bool(args.no_clean_db)
    symbols = [str(item).upper() for item in (args.symbol or M2_LIVE_SYMBOLS) if str(item).strip()]
    if not symbols:
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "FLUXUSDT"]

    summary = run_canary_first_fill(
        source_db_path=args.source_db_path,
        model2_canary_db_path=args.model2_canary_db_path,
        output_dir=args.output_dir,
        symbols=symbols,
        timeframe=args.timeframe,
        clean_db=clean_db,
        injection_enabled=bool(args.injection_enabled),
        execution_mode=args.execution_mode,
        max_daily_entries=int(args.max_daily_entries),
        max_margin_per_position_usd=float(args.max_margin_per_position_usd),
        max_signal_age_minutes=int(args.max_signal_age_minutes),
        symbol_cooldown_minutes=int(args.symbol_cooldown_minutes),
        leverage=int(args.leverage),
        funding_rate_max_for_short=float(args.funding_rate_max_for_short),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
