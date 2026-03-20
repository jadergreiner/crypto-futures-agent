"""Model 2.0 live operational cycle runner."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import (
    M2_EXECUTION_MODE,
    M2_LIVE_SYMBOLS,
    M2_MAX_DAILY_ENTRIES,
    M2_MAX_MARGIN_PER_POSITION_USD,
    M2_MAX_SIGNAL_AGE_MINUTES,
    M2_SYMBOL_COOLDOWN_MINUTES,
    MODEL2_DB_PATH,
)
from scripts.model2.live_dashboard import run_live_dashboard
from scripts.model2.live_execute import run_live_execute
from scripts.model2.live_reconcile import run_live_reconcile

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def run_live_cycle(
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
) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    execute_summary = run_live_execute(
        model2_db_path=model2_db_path,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        output_dir=output_dir,
        execution_mode=execution_mode,
        live_symbols=live_symbols,
        max_daily_entries=max_daily_entries,
        max_margin_per_position_usd=max_margin_per_position_usd,
        max_signal_age_minutes=max_signal_age_minutes,
        symbol_cooldown_minutes=symbol_cooldown_minutes,
    )
    reconcile_summary = run_live_reconcile(
        model2_db_path=model2_db_path,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        output_dir=output_dir,
        execution_mode=execution_mode,
        live_symbols=live_symbols,
        max_daily_entries=max_daily_entries,
        max_margin_per_position_usd=max_margin_per_position_usd,
        max_signal_age_minutes=max_signal_age_minutes,
        symbol_cooldown_minutes=symbol_cooldown_minutes,
    )
    dashboard_summary = run_live_dashboard(
        model2_db_path=model2_db_path,
        output_dir=output_dir,
        retention_days=30,
    )

    return {
        "status": "ok",
        "run_id": run_id,
        "execution_mode": execution_mode,
        "execute": execute_summary,
        "reconcile": reconcile_summary,
        "dashboard": dashboard_summary,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 live cycle runner")
    parser.add_argument("--model2-db-path", default=MODEL2_DB_PATH)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--execution-mode", default=M2_EXECUTION_MODE)
    parser.add_argument("--live-symbol", action="append", default=[])
    parser.add_argument("--max-daily-entries", type=int, default=M2_MAX_DAILY_ENTRIES)
    parser.add_argument("--max-margin-per-position-usd", type=float, default=M2_MAX_MARGIN_PER_POSITION_USD)
    parser.add_argument("--max-signal-age-minutes", type=int, default=M2_MAX_SIGNAL_AGE_MINUTES)
    parser.add_argument("--symbol-cooldown-minutes", type=int, default=M2_SYMBOL_COOLDOWN_MINUTES)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    live_symbols = tuple(symbol.upper() for symbol in (args.live_symbol or M2_LIVE_SYMBOLS) if symbol)
    try:
        summary = run_live_cycle(
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
        )
    except Exception as exc:
        tb = traceback.format_exc()
        summary = {
            "status": "error",
            "error": str(exc),
            "traceback": tb,
        }
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
