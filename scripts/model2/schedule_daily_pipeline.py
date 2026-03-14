"""Scheduled runner for Model 2.0 daily pipeline with lock and retry control."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.daily_pipeline import DEFAULT_OUTPUT_DIR, run_daily_pipeline

try:
    from config.settings import DB_PATH, MODEL2_DB_PATH
except Exception:
    DB_PATH = "db/crypto_agent.db"
    MODEL2_DB_PATH = "db/modelo2.db"

DEFAULT_LOCK_FILE = DEFAULT_OUTPUT_DIR / "model2_daily_pipeline.lock"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _read_lock_payload(lock_path: Path) -> dict[str, Any]:
    try:
        raw = lock_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def _acquire_lock(lock_path: Path, stale_seconds: int) -> tuple[bool, dict[str, Any]]:
    now_ms = _utc_now_ms()
    stale_removed = False

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            payload = _read_lock_payload(lock_path)
            acquired_at_ms = int(payload.get("acquired_at_utc_ms") or 0)
            age_ms = max(0, now_ms - acquired_at_ms) if acquired_at_ms else None
            if stale_seconds > 0 and age_ms is not None and age_ms > (stale_seconds * 1000):
                try:
                    lock_path.unlink()
                    stale_removed = True
                    continue
                except FileNotFoundError:
                    continue
            return False, {
                "lock_path": str(lock_path),
                "reason": "already_locked",
                "stale_lock_removed": stale_removed,
                "existing_lock": payload,
                "existing_lock_age_ms": age_ms,
            }

        payload = {
            "pid": os.getpid(),
            "acquired_at_utc_ms": now_ms,
            "acquired_at_iso": _utc_now_iso(),
        }
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True))
        return True, {
            "lock_path": str(lock_path),
            "reason": "acquired",
            "stale_lock_removed": stale_removed,
            "holder": payload,
        }


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return


def _pipeline_succeeded(pipeline_status: str, retry_on_partial: bool) -> bool:
    if pipeline_status == "ok":
        return True
    if pipeline_status == "partial" and not retry_on_partial:
        return True
    return False


def _write_summary(output_dir: Path, summary: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = summary["run_id"]
    output_file = output_dir / f"model2_daily_schedule_{run_id}.json"
    summary_with_output = dict(summary)
    summary_with_output["output_file"] = str(output_file)
    output_file.write_text(json.dumps(summary_with_output, indent=2, ensure_ascii=True), encoding="utf-8")
    return output_file


def run_scheduled_execution(
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
    lock_file: str | Path,
    lock_stale_seconds: int,
    max_retries: int,
    retry_delay_seconds: int,
    retry_on_partial: bool,
) -> dict[str, Any]:
    resolved_output_dir = _resolve_repo_path(output_dir)
    resolved_lock_file = _resolve_repo_path(lock_file)
    resolved_lock_file.parent.mkdir(parents=True, exist_ok=True)

    acquired, lock_info = _acquire_lock(resolved_lock_file, stale_seconds=max(0, int(lock_stale_seconds)))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not acquired:
        summary = {
            "status": "skipped_locked",
            "run_id": run_id,
            "timestamp_utc_ms": _utc_now_ms(),
            "lock": lock_info,
            "attempts": [],
            "final_pipeline_status": None,
        }
        output_file = _write_summary(resolved_output_dir, summary)
        summary["output_file"] = str(output_file)
        return summary

    attempts: list[dict[str, Any]] = []
    final_pipeline_summary: dict[str, Any] | None = None
    final_pipeline_status = "error"

    max_attempts = max(1, int(max_retries) + 1)
    try:
        for attempt_number in range(1, max_attempts + 1):
            started = perf_counter()
            attempt_record: dict[str, Any] = {
                "attempt": attempt_number,
                "timestamp_utc_ms": _utc_now_ms(),
            }
            try:
                pipeline_summary = run_daily_pipeline(
                    source_db_path=source_db_path,
                    model2_db_path=model2_db_path,
                    legacy_db_path=legacy_db_path,
                    symbols=list(symbols),
                    timeframe=timeframe,
                    scan_candles_limit=scan_candles_limit,
                    validation_candles_limit=validation_candles_limit,
                    resolution_candles_limit=resolution_candles_limit,
                    limit=limit,
                    dry_run=dry_run,
                    continue_on_error=continue_on_error,
                    retention_days=retention_days,
                    output_dir=resolved_output_dir,
                )
                pipeline_status = str(pipeline_summary.get("status", "error"))
                attempt_record["result"] = pipeline_status
                attempt_record["pipeline_output_file"] = pipeline_summary.get("output_file")
                final_pipeline_summary = pipeline_summary
                final_pipeline_status = pipeline_status
                success = _pipeline_succeeded(pipeline_status, retry_on_partial=bool(retry_on_partial))
            except Exception as exc:
                attempt_record["result"] = "exception"
                attempt_record["error"] = str(exc)
                success = False
                final_pipeline_status = "error"

            attempt_record["elapsed_ms"] = int((perf_counter() - started) * 1000)
            attempts.append(attempt_record)
            if success:
                break
            if attempt_number < max_attempts:
                time.sleep(max(0, int(retry_delay_seconds)))
    finally:
        _release_lock(resolved_lock_file)

    status = final_pipeline_status
    if final_pipeline_status not in {"ok", "partial"}:
        status = "error"

    summary = {
        "status": status,
        "run_id": run_id,
        "timestamp_utc_ms": _utc_now_ms(),
        "lock": lock_info,
        "retry_policy": {
            "max_retries": int(max_retries),
            "retry_delay_seconds": int(retry_delay_seconds),
            "retry_on_partial": bool(retry_on_partial),
        },
        "attempts": attempts,
        "final_pipeline_status": final_pipeline_status,
        "pipeline_output_file": (
            final_pipeline_summary.get("output_file") if isinstance(final_pipeline_summary, dict) else None
        ),
    }
    output_file = _write_summary(resolved_output_dir, summary)
    summary["output_file"] = str(output_file)
    return summary


def run_scheduler_loop(
    *,
    run_at: str,
    timezone_name: str,
    poll_seconds: int,
    max_cycles: int,
    execution_kwargs: dict[str, Any],
) -> list[dict[str, Any]]:
    tz = ZoneInfo(timezone_name)
    completed: list[dict[str, Any]] = []
    last_date: str | None = None

    while True:
        now = datetime.now(tz)
        today = now.date().isoformat()
        hhmm = now.strftime("%H:%M")
        if hhmm == run_at and last_date != today:
            summary = run_scheduled_execution(**execution_kwargs)
            completed.append(summary)
            print(json.dumps(summary, indent=2, ensure_ascii=True))
            last_date = today
            if max_cycles > 0 and len(completed) >= max_cycles:
                break
        time.sleep(max(1, int(poll_seconds)))
    return completed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Schedule Model 2.0 daily pipeline with lock and retry policies"
    )
    parser.add_argument("--once", action="store_true", help="Run one immediate scheduled execution and exit.")
    parser.add_argument(
        "--run-at",
        default="00:05",
        help="Daily trigger time in HH:MM for scheduler loop mode.",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="IANA timezone used by scheduler loop mode (e.g., UTC, America/Sao_Paulo).",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=30,
        help="Polling interval in seconds when running scheduler loop mode.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=0,
        help="Stop after N successful daily trigger cycles in loop mode (0 means infinite).",
    )
    parser.add_argument(
        "--lock-file",
        default=str(DEFAULT_LOCK_FILE),
        help="File used as single-run lock for scheduled execution.",
    )
    parser.add_argument(
        "--lock-stale-seconds",
        type=int,
        default=6 * 3600,
        help="If lock age exceeds this threshold, stale lock is removed.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Retries after first failed pipeline attempt (total attempts = max_retries + 1).",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=int,
        default=60,
        help="Wait time before retrying after a failed attempt.",
    )
    parser.add_argument(
        "--retry-on-partial",
        action="store_true",
        help="Treat pipeline status=partial as retriable failure.",
    )
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
        help="Directory used for schedule and pipeline run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    execution_kwargs = {
        "source_db_path": args.source_db_path,
        "model2_db_path": args.model2_db_path,
        "legacy_db_path": args.legacy_db_path,
        "symbols": list(args.symbol or []),
        "timeframe": args.timeframe,
        "scan_candles_limit": int(args.scan_candles_limit),
        "validation_candles_limit": int(args.validation_candles_limit),
        "resolution_candles_limit": int(args.resolution_candles_limit),
        "limit": int(args.limit),
        "dry_run": bool(args.dry_run),
        "continue_on_error": bool(args.continue_on_error),
        "retention_days": int(args.retention_days),
        "output_dir": args.output_dir,
        "lock_file": args.lock_file,
        "lock_stale_seconds": int(args.lock_stale_seconds),
        "max_retries": int(args.max_retries),
        "retry_delay_seconds": int(args.retry_delay_seconds),
        "retry_on_partial": bool(args.retry_on_partial),
    }

    if args.once:
        summary = run_scheduled_execution(**execution_kwargs)
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0 if summary["status"] in {"ok", "partial", "skipped_locked"} else 1

    run_scheduler_loop(
        run_at=args.run_at,
        timezone_name=args.timezone,
        poll_seconds=int(args.poll_seconds),
        max_cycles=int(args.max_cycles),
        execution_kwargs=execution_kwargs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

