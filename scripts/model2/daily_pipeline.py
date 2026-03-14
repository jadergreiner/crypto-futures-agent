"""Model 2.0 daily orchestration runner for end-to-end operational pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.bridge import run_bridge
from scripts.model2.export_dashboard import run_export_dashboard
from scripts.model2.export_signals import run_export_signals
from scripts.model2.migrate import run_up
from scripts.model2.order_layer import run_order_layer
from scripts.model2.resolve import run_resolution
from scripts.model2.scan import run_scan
from scripts.model2.track import run_tracking
from scripts.model2.validate import run_validation
from scripts.model2.rl_signal_generation_wrapper import run_rl_signal_generation

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"

try:
    from config.settings import DB_PATH, M2_SYMBOLS, MODEL2_DB_PATH
except Exception:
    DB_PATH = "db/crypto_agent.db"
    MODEL2_DB_PATH = "db/modelo2.db"
    M2_SYMBOLS = ("BTCUSDT",)

DEFAULT_SYMBOLS = list(M2_SYMBOLS) if M2_SYMBOLS else ["BTCUSDT"]


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _single_symbol_or_none(symbols: list[str]) -> str | None:
    return symbols[0] if len(symbols) == 1 else None


def _run_stage(
    *,
    stage_name: str,
    stage_callable: Callable[..., dict[str, Any]],
    stage_kwargs: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    started = perf_counter()
    try:
        result = stage_callable(**stage_kwargs)
    except Exception as exc:
        elapsed_ms = int((perf_counter() - started) * 1000)
        return None, {
            "stage": stage_name,
            "error": str(exc),
            "elapsed_ms": elapsed_ms,
        }
    elapsed_ms = int((perf_counter() - started) * 1000)
    result_copy = dict(result)
    result_copy["stage_elapsed_ms"] = elapsed_ms
    return result_copy, None


def run_daily_pipeline(
    *,
    source_db_path: str | Path,
    model2_db_path: str | Path,
    legacy_db_path: str | Path,
    symbols: list[str],
    timeframe: str,
    scan_candles_limit: int,
    validation_candles_limit: int,
    resolution_candles_limit: int,
    limit: int,
    dry_run: bool,
    continue_on_error: bool,
    retention_days: int,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_legacy_db = _resolve_repo_path(legacy_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    symbols_to_use = list(symbols) if symbols else list(DEFAULT_SYMBOLS)
    optional_symbol_filter = _single_symbol_or_none(symbols_to_use)

    stage_summaries: dict[str, dict[str, Any]] = {}
    stage_errors: list[dict[str, Any]] = []

    stage_definitions: list[tuple[str, Callable[..., dict[str, Any]], dict[str, Any]]] = [
        (
            "migrate",
            run_up,
            {
                "db_path": resolved_model2_db,
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "scan",
            run_scan,
            {
                "source_db_path": resolved_source_db,
                "model2_db_path": resolved_model2_db,
                "symbols": symbols_to_use,
                "timeframe": timeframe,
                "candles_limit": int(scan_candles_limit),
                "dry_run": bool(dry_run),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "track",
            run_tracking,
            {
                "model2_db_path": resolved_model2_db,
                "symbol": optional_symbol_filter,
                "timeframe": timeframe,
                "limit": int(limit),
                "dry_run": bool(dry_run),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "validate",
            run_validation,
            {
                "source_db_path": resolved_source_db,
                "model2_db_path": resolved_model2_db,
                "symbol": optional_symbol_filter,
                "timeframe": timeframe,
                "limit": int(limit),
                "candles_limit": int(validation_candles_limit),
                "dry_run": bool(dry_run),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "resolve",
            run_resolution,
            {
                "source_db_path": resolved_source_db,
                "model2_db_path": resolved_model2_db,
                "symbol": optional_symbol_filter,
                "timeframe": timeframe,
                "limit": int(limit),
                "candles_limit": int(resolution_candles_limit),
                "dry_run": bool(dry_run),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "bridge",
            run_bridge,
            {
                "model2_db_path": resolved_model2_db,
                "symbol": optional_symbol_filter,
                "timeframe": timeframe,
                "limit": int(limit),
                "dry_run": bool(dry_run),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "order_layer",
            run_order_layer,
            {
                "model2_db_path": resolved_model2_db,
                "symbol": optional_symbol_filter,
                "timeframe": timeframe,
                "limit": int(limit),
                "dry_run": bool(dry_run),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "export_signals",
            run_export_signals,
            {
                "model2_db_path": resolved_model2_db,
                "legacy_db_path": resolved_legacy_db,
                "symbol": optional_symbol_filter,
                "timeframe": timeframe,
                "limit": int(limit),
                "dry_run": bool(dry_run),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "rl_signal_generation",
            run_rl_signal_generation,
            {
                "model2_db_path": resolved_model2_db,
                "timeframe": timeframe,
                "symbols": symbols_to_use,
                "dry_run": bool(dry_run),
                "output_dir": resolved_output_dir,
            },
        ),
    ]

    if not dry_run:
        stage_definitions.append(
            (
                "export_dashboard",
                run_export_dashboard,
                {
                    "model2_db_path": resolved_model2_db,
                    "output_dir": resolved_output_dir,
                    "retention_days": int(retention_days),
                },
            )
        )

    pipeline_started = perf_counter()
    for stage_name, stage_callable, stage_kwargs in stage_definitions:
        summary, error = _run_stage(
            stage_name=stage_name,
            stage_callable=stage_callable,
            stage_kwargs=stage_kwargs,
        )
        if summary is not None:
            stage_summaries[stage_name] = summary
            continue

        assert error is not None
        stage_errors.append(error)
        if not continue_on_error:
            break

    if dry_run and "export_dashboard" not in stage_summaries:
        stage_summaries["export_dashboard"] = {
            "status": "skipped_dry_run",
            "stage_elapsed_ms": 0,
        }

    status = "ok" if not stage_errors else "partial"
    if stage_errors and not continue_on_error:
        status = "error"

    total_elapsed_ms = int((perf_counter() - pipeline_started) * 1000)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = {
        "status": status,
        "run_id": run_id,
        "timestamp_utc_ms": _utc_now_ms(),
        "source_db_path": str(resolved_source_db),
        "model2_db_path": str(resolved_model2_db),
        "legacy_db_path": str(resolved_legacy_db),
        "dry_run": bool(dry_run),
        "continue_on_error": bool(continue_on_error),
        "filters": {
            "symbols": symbols_to_use,
            "timeframe": timeframe,
            "limit": int(limit),
            "scan_candles_limit": int(scan_candles_limit),
            "validation_candles_limit": int(validation_candles_limit),
            "resolution_candles_limit": int(resolution_candles_limit),
        },
        "total_elapsed_ms": total_elapsed_ms,
        "stages": stage_summaries,
        "stage_errors": stage_errors,
    }

    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_daily_pipeline_{run_id}.json"
    output_file.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 daily end-to-end operational pipeline")
    parser.add_argument(
        "--source-db-path",
        default=DB_PATH,
        help="Input SQLite with OHLCV/indicators used by scan/validate/resolve.",
    )
    parser.add_argument(
        "--model2-db-path",
        default=MODEL2_DB_PATH,
        help="Target Model 2.0 SQLite path.",
    )
    parser.add_argument(
        "--legacy-db-path",
        default=DB_PATH,
        help="Legacy SQLite path for trade_signals adapter export.",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Symbol filter. Repeat to pass multiple values. Defaults to M2_SYMBOLS if omitted.",
    )
    parser.add_argument(
        "--timeframe",
        default="H4",
        choices=["D1", "H4", "H1"],
        help="Timeframe used by all pipeline stages.",
    )
    parser.add_argument(
        "--scan-candles-limit",
        type=int,
        default=120,
        help="Candle limit for scanner stage.",
    )
    parser.add_argument(
        "--validation-candles-limit",
        type=int,
        default=240,
        help="Candle limit for validator stage.",
    )
    parser.add_argument(
        "--resolution-candles-limit",
        type=int,
        default=240,
        help="Candle limit for resolver stage.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum entities/signals consumed per stage.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without mutating lifecycle states where supported.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue executing next stages after a stage error.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Retention window for export dashboard snapshots.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for pipeline run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_daily_pipeline(
        source_db_path=args.source_db_path,
        model2_db_path=args.model2_db_path,
        legacy_db_path=args.legacy_db_path,
        symbols=list(args.symbol or []),
        timeframe=args.timeframe,
        scan_candles_limit=args.scan_candles_limit,
        validation_candles_limit=args.validation_candles_limit,
        resolution_candles_limit=args.resolution_candles_limit,
        limit=args.limit,
        dry_run=bool(args.dry_run),
        continue_on_error=bool(args.continue_on_error),
        retention_days=args.retention_days,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if summary["status"] in {"ok", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

