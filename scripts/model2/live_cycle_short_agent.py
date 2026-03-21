"""Dedicated continuous cycle runner for the isolated short-only agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import (
    DB_PATH,
    M2_CANARY_LEVERAGE,
    M2_EXECUTION_MODE,
    M2_FUNDING_RATE_MAX_FOR_SHORT,
    M2_LIVE_SYMBOLS,
    M2_MAX_DAILY_ENTRIES,
    M2_MAX_MARGIN_PER_POSITION_USD,
    M2_MAX_SIGNAL_AGE_MINUTES,
    M2_SYMBOL_COOLDOWN_MINUTES,
)
from scripts.model2.daily_pipeline import run_daily_pipeline
from scripts.model2.healthcheck_live_execution import run_live_healthcheck
from scripts.model2.io_utils import atomic_write_json
from scripts.model2.live_cycle import run_live_cycle
from scripts.model2.persist_training_episodes import run_persist_training_episodes
from scripts.model2.sync_market_context import run_sync_market_context

DEFAULT_SHORT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "FLUXUSDT")
DEFAULT_MODEL2_SHORT_DB_PATH = os.getenv("M2_SHORT_AGENT_DB_PATH", "db/modelo2_short_agent.db")
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2_short" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _normalize_symbols(symbols: list[str] | tuple[str, ...] | None) -> list[str]:
    """Normaliza simbolos e expande placeholders como M2_SYMBOLS:, M2_LIVE_SYMBOLS:, etc."""
    source = list(symbols or ())
    fallback_list = list(M2_LIVE_SYMBOLS) if M2_LIVE_SYMBOLS else list(DEFAULT_SHORT_SYMBOLS)
    placeholder_tokens = {"M2_SYMBOLS", "M2_SYMBOLS:", "M2_LIVE_SYMBOLS", "M2_LIVE_SYMBOLS:", "ALL_SYMBOLS", "ALL_SYMBOLS:"}

    normalized: list[str] = []
    for token in source:
        symbol = str(token).strip().upper()
        if not symbol:
            continue
        if symbol in placeholder_tokens:
            # Expandir placeholder com fallback
            normalized.extend([str(s).strip().upper() for s in fallback_list if str(s).strip()])
        else:
            normalized.append(symbol)

    if normalized:
        return list(dict.fromkeys(normalized))
    if M2_LIVE_SYMBOLS:
        return list(dict.fromkeys(str(symbol).strip().upper() for symbol in M2_LIVE_SYMBOLS if str(symbol).strip()))
    return list(DEFAULT_SHORT_SYMBOLS)


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
    except Exception as exc:  # pragma: no cover - guard path
        return None, {
            "stage": stage_name,
            "error": str(exc),
            "elapsed_ms": int((perf_counter() - started) * 1000),
        }
    result_copy = dict(result)
    result_copy["stage_elapsed_ms"] = int((perf_counter() - started) * 1000)
    return result_copy, None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _print_ux_cycle_summary(summary: dict[str, Any]) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cycle_index = _to_int(summary.get("cycle_index"), 0)
    status = str(summary.get("status") or "?").upper()
    mode = str(summary.get("execution_mode") or "?")
    symbols = summary.get("symbols") or []
    symbol_label = ",".join(str(symbol) for symbol in symbols) if symbols else "-"

    stages = summary.get("stages") if isinstance(summary.get("stages"), dict) else {}
    sync_primary = stages.get("sync_tf", stages.get("sync_h4", {})) if isinstance(stages, dict) else {}
    sync_m5 = stages.get("sync_m5", {}) if isinstance(stages, dict) else {}
    pipeline = stages.get("daily_pipeline", {}) if isinstance(stages, dict) else {}
    live = stages.get("live_cycle", {}) if isinstance(stages, dict) else {}
    persist = stages.get("persist_training", {}) if isinstance(stages, dict) else {}
    health = stages.get("healthcheck", {}) if isinstance(stages, dict) else {}

    sync_primary_inserted = _to_int(sync_primary.get("candles_persisted"), 0)
    sync_m5_inserted = _to_int(sync_m5.get("candles_persisted"), 0)

    pipeline_errors = pipeline.get("stage_errors") if isinstance(pipeline, dict) else []
    pipeline_error_count = len(pipeline_errors) if isinstance(pipeline_errors, list) else 0

    execute = live.get("execute") if isinstance(live, dict) else {}
    dashboard = live.get("dashboard") if isinstance(live, dict) else {}
    staged_count = len(execute.get("staged", [])) if isinstance(execute, dict) and isinstance(execute.get("staged"), list) else 0
    processed_ready_count = (
        len(execute.get("processed_ready", []))
        if isinstance(execute, dict) and isinstance(execute.get("processed_ready"), list)
        else 0
    )
    blocked_count = _to_int(dashboard.get("blocked_count"), 0) if isinstance(dashboard, dict) else 0
    failed_count = _to_int(dashboard.get("failed_count"), 0) if isinstance(dashboard, dict) else 0
    unprotected_count = _to_int(dashboard.get("unprotected_filled_count"), 0) if isinstance(dashboard, dict) else 0

    episodes_inserted = _to_int(persist.get("episodes_inserted"), 0) if isinstance(persist, dict) else 0
    health_status = str(health.get("status") or "skipped").lower() if isinstance(health, dict) else "skipped"
    health_violations = len(health.get("violations", [])) if isinstance(health, dict) and isinstance(health.get("violations"), list) else 0

    print(f"[SHORT-CYCLE] {timestamp} | cycle={cycle_index} | status={status} | mode={mode} | symbols={symbol_label}", flush=True)
    print(
        f"[STAGES] sync_tf={sync_primary_inserted} candles | sync_m5={sync_m5_inserted} candles | "
        f"pipeline_errors={pipeline_error_count} | staged={staged_count} | ready_processed={processed_ready_count}",
        flush=True,
    )
    print(
        f"[RISK] blocked={blocked_count} | failed={failed_count} | unprotected_filled={unprotected_count} | "
        f"episodes_inserted={episodes_inserted} | health={health_status}({health_violations})",
        flush=True,
    )

    stage_errors = summary.get("stage_errors")
    if isinstance(stage_errors, list) and stage_errors:
        for err in stage_errors:
            if isinstance(err, dict):
                print(f"[ERROR] stage={err.get('stage')} | error={err.get('error')}")

    output_file = summary.get("output_file")
    if output_file:
        print(f"[ARTIFACT] {output_file}", flush=True)
    print("", flush=True)


def _print_stage_update(*, cycle_index: int, stage: str, event: str, elapsed_ms: int | None = None, error: str | None = None) -> None:
    now_label = datetime.now(timezone.utc).strftime("%H:%M:%S")
    if event == "start":
        print(f"[PROGRESS] {now_label} | cycle={cycle_index} | stage={stage} | status=RUNNING", flush=True)
        return
    if event == "ok":
        elapsed = int(elapsed_ms or 0)
        print(f"[PROGRESS] {now_label} | cycle={cycle_index} | stage={stage} | status=OK | elapsed_ms={elapsed}", flush=True)
        return
    if event == "error":
        elapsed = int(elapsed_ms or 0)
        print(
            f"[PROGRESS] {now_label} | cycle={cycle_index} | stage={stage} | status=ERROR | elapsed_ms={elapsed} | error={error}",
            flush=True,
        )
        return


def run_short_agent_cycle(
    *,
    source_db_path: str | Path,
    model2_db_path: str | Path,
    output_dir: str | Path,
    symbols: list[str],
    timeframe: str,
    execution_mode: str,
    max_daily_entries: int,
    max_margin_per_position_usd: float,
    max_signal_age_minutes: int,
    symbol_cooldown_minutes: int,
    funding_rate_max_for_short: float,
    leverage: int,
    limit: int,
    sync_h4_candles_limit: int,
    sync_m5_candles_limit: int,
    scan_candles_limit: int,
    validation_candles_limit: int,
    resolution_candles_limit: int,
    retention_days: int,
    continue_on_error: bool,
    include_persist_training: bool,
    include_healthcheck: bool,
    max_health_age_hours: int,
    max_unprotected_filled: int,
    max_stale_entry_sent: int,
    max_position_mismatches: int,
    progress_callback: Callable[[str, str, int | None, str | None], None] | None = None,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    symbols_to_use = _normalize_symbols(symbols)
    optional_symbol_filter = _single_symbol_or_none(symbols_to_use)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    stage_summaries: dict[str, dict[str, Any]] = {}
    stage_errors: list[dict[str, Any]] = []

    stage_definitions: list[tuple[str, Callable[..., dict[str, Any]], dict[str, Any]]] = [
        (
            "sync_tf",
            run_sync_market_context,
            {
                "source_db_path": resolved_source_db,
                "symbols": symbols_to_use,
                "timeframe": timeframe,
                "candles_limit": int(sync_h4_candles_limit),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "sync_m5",
            run_sync_market_context,
            {
                "source_db_path": resolved_source_db,
                "symbols": symbols_to_use,
                "timeframe": "M5",
                "candles_limit": int(sync_m5_candles_limit),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "daily_pipeline",
            run_daily_pipeline,
            {
                "source_db_path": resolved_source_db,
                "model2_db_path": resolved_model2_db,
                "legacy_db_path": resolved_source_db,
                "symbols": symbols_to_use,
                "timeframe": timeframe,
                "scan_candles_limit": int(scan_candles_limit),
                "validation_candles_limit": int(validation_candles_limit),
                "resolution_candles_limit": int(resolution_candles_limit),
                "limit": int(limit),
                "dry_run": False,
                "continue_on_error": True,
                "retention_days": int(retention_days),
                "output_dir": resolved_output_dir,
            },
        ),
        (
            "live_cycle",
            run_live_cycle,
            {
                "model2_db_path": resolved_model2_db,
                "symbol": optional_symbol_filter,
                "timeframe": timeframe,
                "limit": int(limit),
                "output_dir": resolved_output_dir,
                "execution_mode": str(execution_mode).strip().lower(),
                "live_symbols": tuple(symbols_to_use),
                "max_daily_entries": int(max_daily_entries),
                "max_margin_per_position_usd": float(max_margin_per_position_usd),
                "max_signal_age_minutes": int(max_signal_age_minutes),
                "symbol_cooldown_minutes": int(symbol_cooldown_minutes),
                "short_only": True,
                "funding_rate_max_for_short": float(funding_rate_max_for_short),
                "leverage": int(leverage),
            },
        ),
    ]

    if include_persist_training:
        stage_definitions.append(
            (
                "persist_training",
                run_persist_training_episodes,
                {
                    "source_db_path": resolved_source_db,
                    "model2_db_path": resolved_model2_db,
                    "symbols": symbols_to_use,
                    "timeframe": timeframe,
                    "output_dir": resolved_output_dir,
                },
            )
        )

    if include_healthcheck:
        stage_definitions.append(
            (
                "healthcheck",
                run_live_healthcheck,
                {
                    "runtime_dir": resolved_output_dir,
                    "output_dir": resolved_output_dir,
                    "max_age_hours": int(max_health_age_hours),
                    "max_unprotected_filled": int(max_unprotected_filled),
                    "max_stale_entry_sent": int(max_stale_entry_sent),
                    "max_position_mismatches": int(max_position_mismatches),
                    "alert_command": None,
                },
            )
        )

    cycle_started = perf_counter()
    for stage_name, stage_callable, stage_kwargs in stage_definitions:
        if progress_callback is not None:
            progress_callback(stage_name, "start", None, None)
        summary, error = _run_stage(
            stage_name=stage_name,
            stage_callable=stage_callable,
            stage_kwargs=stage_kwargs,
        )
        if summary is not None:
            stage_summaries[stage_name] = summary
            if progress_callback is not None:
                progress_callback(stage_name, "ok", int(summary.get("stage_elapsed_ms", 0)), None)
            continue

        assert error is not None
        stage_errors.append(error)
        if progress_callback is not None:
            progress_callback(stage_name, "error", int(error.get("elapsed_ms", 0)), str(error.get("error")))
        if not continue_on_error:
            break

    status = "ok"
    if stage_errors:
        status = "partial" if stage_summaries else "error"

    summary: dict[str, Any] = {
        "status": status,
        "run_id": run_id,
        "timestamp_utc_ms": _utc_now_ms(),
        "cycle_elapsed_ms": int((perf_counter() - cycle_started) * 1000),
        "source_db_path": str(resolved_source_db),
        "model2_db_path": str(resolved_model2_db),
        "output_dir": str(resolved_output_dir),
        "execution_mode": str(execution_mode).strip().lower(),
        "short_only": True,
        "symbols": symbols_to_use,
        "timeframe": timeframe,
        "limit": int(limit),
        "max_daily_entries": int(max_daily_entries),
        "max_margin_per_position_usd": float(max_margin_per_position_usd),
        "max_signal_age_minutes": int(max_signal_age_minutes),
        "symbol_cooldown_minutes": int(symbol_cooldown_minutes),
        "funding_rate_max_for_short": float(funding_rate_max_for_short),
        "leverage": int(leverage),
        "stages": stage_summaries,
        "stage_errors": stage_errors,
    }

    output_file = resolved_output_dir / f"model2_short_cycle_{run_id}.json"
    summary_with_output = dict(summary)
    summary_with_output["output_file"] = str(output_file)
    atomic_write_json(output_file, summary_with_output, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dedicated continuous short-only live cycle runner.")
    parser.add_argument("--source-db-path", default=DB_PATH)
    parser.add_argument("--model2-db-path", default=DEFAULT_MODEL2_SHORT_DB_PATH)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--timeframe", default="H1", choices=("D1", "H4", "H1"))
    parser.add_argument("--execution-mode", default=M2_EXECUTION_MODE)
    parser.add_argument("--loop-seconds", type=int, default=300)
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--max-daily-entries", type=int, default=M2_MAX_DAILY_ENTRIES)
    parser.add_argument("--max-margin-per-position-usd", type=float, default=M2_MAX_MARGIN_PER_POSITION_USD)
    parser.add_argument("--max-signal-age-minutes", type=int, default=M2_MAX_SIGNAL_AGE_MINUTES)
    parser.add_argument("--symbol-cooldown-minutes", type=int, default=M2_SYMBOL_COOLDOWN_MINUTES)
    parser.add_argument("--funding-rate-max-for-short", type=float, default=M2_FUNDING_RATE_MAX_FOR_SHORT)
    parser.add_argument("--leverage", type=int, default=M2_CANARY_LEVERAGE)
    parser.add_argument("--scan-candles-limit", type=int, default=120)
    parser.add_argument("--validation-candles-limit", type=int, default=240)
    parser.add_argument("--resolution-candles-limit", type=int, default=240)
    parser.add_argument("--sync-h4-candles-limit", type=int, default=4)
    parser.add_argument("--sync-m5-candles-limit", type=int, default=4)
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--skip-persist-training", action="store_true")
    parser.add_argument("--skip-healthcheck", action="store_true")
    parser.add_argument("--max-health-age-hours", type=int, default=2)
    parser.add_argument("--max-unprotected-filled", type=int, default=0)
    parser.add_argument("--max-stale-entry-sent", type=int, default=0)
    parser.add_argument("--max-position-mismatches", type=int, default=0)
    parser.add_argument(
        "--json-stdout",
        action="store_true",
        help="Print full JSON summary to stdout instead of UX-friendly lines.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    symbols = _normalize_symbols(args.symbol)
    keep_running = not bool(args.run_once)
    max_cycles = int(args.max_cycles)
    cycle_index = 0
    last_status = "ok"

    while True:
        cycle_index += 1
        if not bool(args.json_stdout):
            now_label = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            print(
                f"[SHORT-CYCLE] {now_label} | cycle={cycle_index} | status=RUNNING | mode={args.execution_mode} | symbols={','.join(symbols)}",
                flush=True,
            )
        try:
            summary = run_short_agent_cycle(
                source_db_path=args.source_db_path,
                model2_db_path=args.model2_db_path,
                output_dir=args.output_dir,
                symbols=symbols,
                timeframe=args.timeframe,
                execution_mode=args.execution_mode,
                max_daily_entries=int(args.max_daily_entries),
                max_margin_per_position_usd=float(args.max_margin_per_position_usd),
                max_signal_age_minutes=int(args.max_signal_age_minutes),
                symbol_cooldown_minutes=int(args.symbol_cooldown_minutes),
                funding_rate_max_for_short=float(args.funding_rate_max_for_short),
                leverage=int(args.leverage),
                limit=int(args.limit),
                sync_h4_candles_limit=int(args.sync_h4_candles_limit),
                sync_m5_candles_limit=int(args.sync_m5_candles_limit),
                scan_candles_limit=int(args.scan_candles_limit),
                validation_candles_limit=int(args.validation_candles_limit),
                resolution_candles_limit=int(args.resolution_candles_limit),
                retention_days=int(args.retention_days),
                continue_on_error=not bool(args.fail_fast),
                include_persist_training=not bool(args.skip_persist_training),
                include_healthcheck=not bool(args.skip_healthcheck),
                max_health_age_hours=int(args.max_health_age_hours),
                max_unprotected_filled=int(args.max_unprotected_filled),
                max_stale_entry_sent=int(args.max_stale_entry_sent),
                max_position_mismatches=int(args.max_position_mismatches),
                progress_callback=(
                    (lambda stage, event, elapsed_ms, error: _print_stage_update(
                        cycle_index=cycle_index,
                        stage=stage,
                        event=event,
                        elapsed_ms=elapsed_ms,
                        error=error,
                    ))
                    if not bool(args.json_stdout)
                    else None
                ),
            )
        except Exception as exc:  # pragma: no cover - top-level safety
            summary = {
                "status": "error",
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "cycle_index": cycle_index,
            }

        summary["cycle_index"] = cycle_index
        if bool(args.json_stdout):
            print(json.dumps(summary, indent=2, ensure_ascii=True))
        else:
            _print_ux_cycle_summary(summary)
        last_status = str(summary.get("status") or "error")

        if not keep_running:
            break
        if max_cycles > 0 and cycle_index >= max_cycles:
            break
        time.sleep(max(1, int(args.loop_seconds)))

    return 0 if last_status in {"ok", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
