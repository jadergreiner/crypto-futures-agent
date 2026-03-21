"""Model 2.0 native live/shadow execution runner."""

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
    M2_CANARY_LEVERAGE,
    M2_EXECUTION_MODE,
    M2_FUNDING_RATE_MAX_FOR_SHORT,
    M2_LIVE_SYMBOLS,
    M2_MAINNET_CONFIRM_TOKEN,
    M2_MAX_DAILY_ENTRIES,
    M2_MAX_MARGIN_PER_POSITION_USD,
    M2_REQUIRE_MAINNET_CONFIRM,
    M2_MAX_SIGNAL_AGE_MINUTES,
    M2_SHORT_ONLY,
    M2_SYMBOL_COOLDOWN_MINUTES,
    MODEL2_DB_PATH,
)
from core.model2 import (
    Model2LiveExchange,
    Model2LiveExecutionService,
    Model2ThesisRepository,
)
from data.binance_client import create_binance_client
from scripts.model2.io_utils import atomic_write_json

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _ensure_model2_live_execute_schema(conn: sqlite3.Connection) -> None:
    required_tables = {
        "schema_migrations",
        "technical_signals",
        "model_decisions",
        "signal_executions",
        "signal_execution_events",
    }
    found_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    missing = sorted(required_tables - found_tables)
    if missing:
        raise RuntimeError(
            "Model2 schema is missing required tables: "
            f"{', '.join(missing)}. Run 'python scripts/model2/migrate.py up' first."
        )


def run_live_execute(
    *,
    model2_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    output_dir: str | Path,
    execution_mode: str,
    live_symbols: tuple[str, ...],
    max_daily_entries: int,
    max_margin_per_position_usd: float,
    max_signal_age_minutes: int,
    symbol_cooldown_minutes: int,
    short_only: bool = False,
    funding_rate_max_for_short: float = 0.0005,
    leverage: int | None = None,
    exchange: Model2LiveExchange | None = None,
    risk_gate: Any | None = None,
    circuit_breaker: Any | None = None,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as conn:
        _ensure_model2_live_execute_schema(conn)

    config = Model2LiveExecutionService.build_config(
        execution_mode=execution_mode,
        live_symbols=live_symbols,
        short_only=bool(short_only),
        max_daily_entries=max_daily_entries,
        max_margin_per_position_usd=max_margin_per_position_usd,
        max_signal_age_ms=int(max_signal_age_minutes) * 60_000,
        symbol_cooldown_ms=int(symbol_cooldown_minutes) * 60_000,
        funding_rate_max_for_short=float(funding_rate_max_for_short),
        leverage=leverage,
    )
    if config.execution_mode == "live" and exchange is None:
        if M2_REQUIRE_MAINNET_CONFIRM and M2_MAINNET_CONFIRM_TOKEN != "YES_MAINNET":
            raise RuntimeError(
                "Mainnet confirmation token missing. Set M2_MAINNET_CONFIRM_TOKEN=YES_MAINNET to execute live."
            )
        exchange = Model2LiveExchange(create_binance_client(mode="live"))

    service = Model2LiveExecutionService(
        repository=Model2ThesisRepository(str(resolved_model2_db)),
        config=config,
        exchange=exchange,
        risk_gate=risk_gate,
        circuit_breaker=circuit_breaker,
    )

    now_ms = _utc_now_ms()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    execution_result = service.run_execute(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        now_ms=now_ms,
    )

    summary: dict[str, Any] = {
        "status": "ok",
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "model2_db_path": str(resolved_model2_db),
        "execution_mode": config.execution_mode,
        "filters": {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": int(limit),
        },
        "live_symbols": list(config.live_symbols),
        "max_daily_entries": int(config.max_daily_entries),
        "max_margin_per_position_usd": float(config.max_margin_per_position_usd),
        "max_signal_age_minutes": int(max_signal_age_minutes),
        "symbol_cooldown_minutes": int(symbol_cooldown_minutes),
        "short_only": bool(config.short_only),
        "funding_rate_max_for_short": float(config.funding_rate_max_for_short),
        "leverage": int(config.leverage),
        "staged": execution_result["staged"],
        "processed_ready": execution_result["processed_ready"],
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_live_execute_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 live/shadow execution runner")
    parser.add_argument("--model2-db-path", default=MODEL2_DB_PATH, help="Target Model 2.0 SQLite path.")
    parser.add_argument("--symbol", default=None, help="Optional symbol filter.")
    parser.add_argument("--timeframe", default=None, help="Optional timeframe filter.")
    parser.add_argument("--limit", type=int, default=200, help="Maximum consumed technical signals staged per run.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory used for live execution summaries.")
    parser.add_argument("--execution-mode", default=M2_EXECUTION_MODE, help="Execution mode: shadow or live.")
    parser.add_argument(
        "--live-symbol",
        action="append",
        default=[],
        help="Optional symbol allow-list for live execution. Repeat the flag or use M2_LIVE_SYMBOLS env.",
    )
    parser.add_argument("--max-daily-entries", type=int, default=M2_MAX_DAILY_ENTRIES)
    parser.add_argument("--max-margin-per-position-usd", type=float, default=M2_MAX_MARGIN_PER_POSITION_USD)
    parser.add_argument("--max-signal-age-minutes", type=int, default=M2_MAX_SIGNAL_AGE_MINUTES)
    parser.add_argument("--symbol-cooldown-minutes", type=int, default=M2_SYMBOL_COOLDOWN_MINUTES)
    parser.add_argument("--short-only", action="store_true", default=M2_SHORT_ONLY)
    parser.add_argument("--funding-rate-max-for-short", type=float, default=M2_FUNDING_RATE_MAX_FOR_SHORT)
    parser.add_argument("--leverage", type=int, default=M2_CANARY_LEVERAGE)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    live_symbols = tuple(symbol.upper() for symbol in (args.live_symbol or M2_LIVE_SYMBOLS) if symbol)
    summary = run_live_execute(
        model2_db_path=args.model2_db_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=int(args.limit),
        output_dir=args.output_dir,
        execution_mode=args.execution_mode,
        live_symbols=live_symbols,
        max_daily_entries=int(args.max_daily_entries),
        max_margin_per_position_usd=float(args.max_margin_per_position_usd),
        max_signal_age_minutes=int(args.max_signal_age_minutes),
        symbol_cooldown_minutes=int(args.symbol_cooldown_minutes),
        short_only=bool(args.short_only),
        funding_rate_max_for_short=float(args.funding_rate_max_for_short),
        leverage=int(args.leverage),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
