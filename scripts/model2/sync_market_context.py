"""Sync market quotes for cycle decisions and persist snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import DB_PATH, M2_SYMBOLS
from data.binance_client import create_data_client
from data.collector import BinanceCollector
from data.database import DatabaseManager

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"
TIMEFRAME_TO_INTERVAL = {
    "D1": "1d",
    "H4": "4h",
    "H1": "1h",
    "M5": "5m",
}


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _extract_mark_price(mark_price_response: Any) -> float | None:
    data = mark_price_response
    if hasattr(data, "data"):
        data = data.data() if callable(data.data) else data.data
    if hasattr(data, "actual_instance"):
        data = data.actual_instance
    for field in ("mark_price", "markPrice", "price"):
        if hasattr(data, field):
            try:
                return float(getattr(data, field))
            except (TypeError, ValueError):
                return None
        if isinstance(data, dict) and field in data:
            try:
                return float(data[field])
            except (TypeError, ValueError):
                return None
    return None


def _extract_data(response: Any) -> Any:
    if response is None:
        return None
    if hasattr(response, "data"):
        data = response.data
        return data() if callable(data) else data
    return response


def _safe_get(obj: Any, attr: str | list[str], default: Any = None) -> Any:
    if isinstance(attr, list):
        for attr_name in attr:
            value = _safe_get(obj, attr_name, default=None)
            if value is not None:
                return value
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _get_exchange_valid_symbols(client: Any) -> tuple[set[str], str | None]:
    try:
        response = client.rest_api.exchange_information()
        data = _extract_data(response)
        symbols = None
        if isinstance(data, dict):
            symbols = data.get("symbols")
        elif hasattr(data, "symbols"):
            symbols = data.symbols

        valid: set[str] = set()
        for symbol_info in symbols or []:
            symbol = str(_safe_get(symbol_info, ["symbol"], "") or "").upper()
            status = str(_safe_get(symbol_info, ["status"], "") or "").upper()
            if symbol and status in {"TRADING", "PENDING_TRADING", "PRE_TRADING"}:
                valid.add(symbol)

        if valid:
            return valid, None
        return set(), "empty_exchange_symbol_list"
    except Exception as exc:
        return set(), str(exc)


def _filter_new_candles(db: DatabaseManager, timeframe: str, symbol: str, candles_df):
    if candles_df.empty:
        return candles_df, 0

    timestamps = [int(ts) for ts in candles_df["timestamp"].tolist()]
    placeholders = ", ".join(["?"] * len(timestamps))
    table = f"ohlcv_{timeframe.lower()}"
    query = (
        f"SELECT timestamp FROM {table} WHERE symbol = ? AND timestamp IN ({placeholders})"
    )
    with db.get_connection() as conn:
        rows = conn.execute(query, [symbol, *timestamps]).fetchall()
    existing = {int(row[0]) for row in rows}

    if not existing:
        return candles_df, 0

    filtered = candles_df[~candles_df["timestamp"].isin(existing)].copy()
    return filtered, len(existing)


def run_sync_market_context(
    *,
    source_db_path: str | Path,
    symbols: list[str],
    timeframe: str,
    candles_limit: int,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    requested_symbols = [str(s).upper() for s in (symbols if symbols else list(M2_SYMBOLS))]
    interval = TIMEFRAME_TO_INTERVAL[timeframe]

    client = create_data_client()
    collector = BinanceCollector(client)
    db = DatabaseManager(str(resolved_source_db))

    exchange_valid_symbols, exchange_error = _get_exchange_valid_symbols(client)
    eligible_symbols: list[str]
    invalid_symbols: list[str]

    if exchange_valid_symbols:
        eligible_symbols = [s for s in requested_symbols if s in exchange_valid_symbols]
        invalid_symbols = [s for s in requested_symbols if s not in exchange_valid_symbols]
    else:
        # Fallback: sem lista da exchange, mantem comportamento antigo
        eligible_symbols = list(requested_symbols)
        invalid_symbols = []

    synced_symbols = 0
    failed_symbols = 0
    synced_candles = 0
    duplicate_candles = 0
    items: list[dict[str, Any]] = []
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now_ms = _utc_now_ms()

    for symbol in invalid_symbols:
        items.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "interval": interval,
                "status": "skipped_invalid_symbol",
                "reason": "symbol_not_listed_in_exchange_information",
            }
        )

    for symbol in eligible_symbols:
        item: dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "interval": interval,
            "status": "unknown",
        }
        try:
            candles_df = collector.fetch_klines(
                symbol=symbol,
                interval=interval,
                limit=max(1, int(candles_limit)),
            )
            if candles_df.empty:
                item["status"] = "no_candles"
                failed_symbols += 1
                items.append(item)
                continue

            filtered_df, symbol_duplicates = _filter_new_candles(
                db=db,
                timeframe=timeframe,
                symbol=symbol,
                candles_df=candles_df,
            )
            duplicate_candles += int(symbol_duplicates)

            inserted = 0
            if not filtered_df.empty:
                db.insert_ohlcv(timeframe=timeframe, data=filtered_df)
                inserted = int(len(filtered_df))
                synced_candles += inserted

            latest = candles_df.iloc[-1].to_dict()
            item["status"] = "synced" if inserted > 0 else "synced_no_new_candles"
            item["candles_fetched"] = int(len(candles_df))
            item["candles_persisted"] = inserted
            item["candles_duplicated_skipped"] = int(symbol_duplicates)
            item["latest_candle"] = {
                "timestamp": int(latest["timestamp"]),
                "open": float(latest["open"]),
                "high": float(latest["high"]),
                "low": float(latest["low"]),
                "close": float(latest["close"]),
                "volume": float(latest["volume"]),
            }
            try:
                mark_price_response = client.rest_api.mark_price(symbol=symbol)
                item["mark_price"] = _extract_mark_price(mark_price_response)
            except Exception as exc:
                item["mark_price_error"] = str(exc)

            synced_symbols += 1
        except Exception as exc:
            item["status"] = "error"
            item["error"] = str(exc)
            failed_symbols += 1
        items.append(item)

    status = "ok" if failed_symbols == 0 else ("partial" if synced_symbols > 0 else "error")
    summary: dict[str, Any] = {
        "status": status,
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "source_db_path": str(resolved_source_db),
        "timeframe": timeframe,
        "interval": interval,
        "candles_limit": int(candles_limit),
        "symbols_requested": len(requested_symbols),
        "symbols_eligible": len(eligible_symbols),
        "symbols_skipped_invalid": len(invalid_symbols),
        "symbols_synced": synced_symbols,
        "symbols_failed": failed_symbols,
        "candles_persisted": synced_candles,
        "candles_duplicated_skipped": duplicate_candles,
        "exchange_symbol_filter_error": exchange_error,
        "items": items,
    }

    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_market_context_{run_id}.json"
    output_file.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync latest market context for cycle decisions")
    parser.add_argument("--source-db-path", default=DB_PATH, help="SQLite path for OHLCV persistence.")
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Symbol filter. Repeat flag for multiple symbols. Defaults to M2_SYMBOLS.",
    )
    parser.add_argument(
        "--timeframe",
        default="H4",
        choices=sorted(TIMEFRAME_TO_INTERVAL.keys()),
        help="Timeframe to sync and persist.",
    )
    parser.add_argument(
        "--candles-limit",
        type=int,
        default=4,
        help="Number of recent candles fetched per symbol.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for run summary.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_sync_market_context(
        source_db_path=args.source_db_path,
        symbols=list(args.symbol or []),
        timeframe=args.timeframe,
        candles_limit=int(args.candles_limit),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if summary["status"] in {"ok", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

