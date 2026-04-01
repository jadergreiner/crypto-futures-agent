"""Model 2.0 live reconciliation runner."""

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
    M2_MAX_DAILY_ENTRIES,
    M2_MAX_MARGIN_PER_POSITION_USD,
    M2_MAX_SIGNAL_AGE_MINUTES,
    M2_SHORT_ONLY,
    M2_SYMBOL_COOLDOWN_MINUTES,
    MODEL2_DB_PATH,
)
from core.model2 import Model2LiveExchange, Model2LiveExecutionService, Model2ThesisRepository
from data.binance_client import create_binance_client
from scripts.model2.io_utils import atomic_write_json

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


class _NoopExchange:
    def get_open_position(self, symbol: str) -> dict[str, Any] | None:
        return None

    def get_protection_state(self, *, symbol: str, signal_side: str) -> dict[str, Any]:
        return {"has_sl": True, "has_tp": True, "sl_order_id": None, "tp_order_id": None}

    def place_protective_order(self, *, symbol: str, signal_side: str, trigger_price: float, order_type: str) -> dict[str, Any]:
        return {"algoId": None}

    def extract_order_identifier(self, order: dict[str, Any]) -> str | None:
        return None

    def is_existing_protection_error(self, error: Exception) -> bool:
        return False

    def close_position_market(self, *, symbol: str, signal_side: str, quantity: float) -> dict[str, Any]:
        return {"orderId": None}


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _resolve_managed_symbols(
    *,
    symbol_filter: str | None,
    live_symbols: tuple[str, ...],
) -> tuple[str, ...]:
    if symbol_filter:
        return (str(symbol_filter).upper(),)
    return tuple(dict.fromkeys(str(symbol).upper() for symbol in live_symbols if str(symbol).strip()))


def _collect_scope_positions(
    *,
    exchange: Any,
    managed_symbols: tuple[str, ...],
) -> list[dict[str, Any]]:
    managed_set = {symbol.upper() for symbol in managed_symbols}
    list_positions = getattr(exchange, "list_open_positions", None)
    if callable(list_positions):
        try:
            raw_positions = list_positions()
        except Exception:
            raw_positions = []
        scoped_positions: list[dict[str, Any]] = []
        for position in raw_positions or []:
            if not isinstance(position, dict):
                continue
            symbol = str(position.get("symbol") or "").upper()
            if symbol not in managed_set:
                continue
            try:
                qty = float(position.get("position_size_qty", 0) or 0)
            except (TypeError, ValueError):
                qty = 0.0
            if qty == 0:
                continue
            scoped_positions.append(dict(position))
        return scoped_positions

    fallback_positions: list[dict[str, Any]] = []
    for current_symbol in managed_symbols:
        try:
            position = exchange.get_open_position(current_symbol)
        except Exception:
            position = None
        if position is None:
            continue
        try:
            qty = float(position.get("position_size_qty", 0) or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty == 0:
            continue
        fallback_positions.append(dict(position))
    return fallback_positions


def _collect_active_scope_executions(
    *,
    repository: Model2ThesisRepository,
    execution_mode: str,
    managed_symbols: tuple[str, ...],
) -> list[dict[str, Any]]:
    active_statuses = ("READY", "ENTRY_SENT", "ENTRY_FILLED", "PROTECTED")
    executions = repository.list_signal_executions(
        statuses=active_statuses,
        execution_mode=execution_mode,
        limit=1000,
    )
    managed_set = {symbol.upper() for symbol in managed_symbols}
    return [
        execution
        for execution in executions
        if str(execution.get("symbol") or "").upper() in managed_set
    ]


def _collect_orphan_scope_positions(
    *,
    scope_positions: list[dict[str, Any]],
    active_scope_executions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    covered_symbols = {
        str(execution.get("symbol") or "").upper()
        for execution in active_scope_executions
    }
    return [
        dict(position)
        for position in scope_positions
        if str(position.get("symbol") or "").upper() not in covered_symbols
    ]


def _ensure_model2_live_reconcile_schema(conn: sqlite3.Connection) -> None:
    required_tables = {
        "schema_migrations",
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


def run_live_reconcile(
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
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    managed_symbols = _resolve_managed_symbols(symbol_filter=symbol, live_symbols=live_symbols)

    with sqlite3.connect(resolved_model2_db) as conn:
        _ensure_model2_live_reconcile_schema(conn)

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
    if exchange is None:
        if config.execution_mode == "live":
            exchange = Model2LiveExchange(create_binance_client(mode="live"))
        else:
            exchange = _NoopExchange()  # type: ignore[assignment]

    service = Model2LiveExecutionService(
        repository=Model2ThesisRepository(str(resolved_model2_db)),
        config=config,
        exchange=exchange,
    )
    active_scope_executions = _collect_active_scope_executions(
        repository=service.repository,
        execution_mode=config.execution_mode,
        managed_symbols=managed_symbols,
    )
    scope_positions = _collect_scope_positions(
        exchange=exchange,
        managed_symbols=managed_symbols,
    )
    orphan_scope_positions = _collect_orphan_scope_positions(
        scope_positions=scope_positions,
        active_scope_executions=active_scope_executions,
    )

    now_ms = _utc_now_ms()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    reconcile_result = service.run_reconcile(
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
        "managed_symbols": list(managed_symbols),
        "short_only": bool(config.short_only),
        "funding_rate_max_for_short": float(config.funding_rate_max_for_short),
        "leverage": int(config.leverage),
        "reconciled": reconcile_result["reconciled"],
        "active_scope_executions_count": len(active_scope_executions),
        "active_scope_executions": active_scope_executions,
        "scope_open_positions_count": len(scope_positions),
        "scope_open_positions": scope_positions,
        "orphan_scope_positions_count": len(orphan_scope_positions),
        "orphan_scope_positions": orphan_scope_positions,
        "managed_scope_status": "alert" if orphan_scope_positions else "ok",
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_live_reconcile_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 live reconciliation runner")
    parser.add_argument("--model2-db-path", default=MODEL2_DB_PATH, help="Target Model 2.0 SQLite path.")
    parser.add_argument("--symbol", default=None, help="Optional symbol filter.")
    parser.add_argument("--timeframe", default=None, help="Optional timeframe filter.")
    parser.add_argument("--limit", type=int, default=200, help="Maximum live executions reconciled per run.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory used for reconciliation summaries.")
    parser.add_argument("--execution-mode", default=M2_EXECUTION_MODE, help="Execution mode stored in summary context.")
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
    summary = run_live_reconcile(
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
