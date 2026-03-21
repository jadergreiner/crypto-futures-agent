"""Model 2.0 order-layer consumer runner for M2-007.1."""

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

from config.settings import MODEL2_DB_PATH, M2_SHORT_ONLY
from core.model2 import (
    Model2ThesisRepository,
    OrderLayerInput,
    evaluate_signal_for_order_layer,
)
from scripts.model2.io_utils import atomic_write_json

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _ensure_model2_order_layer_schema(conn: sqlite3.Connection) -> None:
    required_tables = {"schema_migrations", "technical_signals"}
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


def _build_order_input(candidate: dict[str, Any], now_ms: int) -> OrderLayerInput:
    payload_raw = candidate.get("payload_json")
    try:
        payload = json.loads(payload_raw or "{}")
    except json.JSONDecodeError:
        payload = {}

    return OrderLayerInput(
        signal_id=int(candidate["id"]),
        opportunity_id=int(candidate["opportunity_id"]),
        symbol=str(candidate["symbol"]),
        timeframe=str(candidate["timeframe"]),
        signal_side=str(candidate["signal_side"]),
        entry_type=str(candidate["entry_type"]),
        entry_price=float(candidate["entry_price"]),
        stop_loss=float(candidate["stop_loss"]),
        take_profit=float(candidate["take_profit"]),
        status=str(candidate["status"]),
        signal_timestamp=int(candidate["signal_timestamp"]),
        payload=payload,
        decision_timestamp=now_ms,
    )


def run_order_layer(
    *,
    model2_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    dry_run: bool,
    output_dir: str | Path,
    short_only: bool = False,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as conn:
        _ensure_model2_order_layer_schema(conn)

    repository = Model2ThesisRepository(str(resolved_model2_db))
    candidates = repository.list_created_technical_signals(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )

    consumed_now = 0
    cancelled_now = 0
    skipped_now = 0
    items: list[dict[str, Any]] = []

    for candidate in candidates:
        item: dict[str, Any] = {
            "signal_id": int(candidate["id"]),
            "opportunity_id": int(candidate["opportunity_id"]),
            "symbol": str(candidate["symbol"]),
            "timeframe": str(candidate["timeframe"]),
            "from_status": str(candidate["status"]),
        }

        if dry_run:
            decision = evaluate_signal_for_order_layer(
                _build_order_input(candidate, _utc_now_ms()),
                short_only=bool(short_only),
            )
            item["result"] = "DRY_RUN"
            item["decision_reason"] = decision.reason
            item["target_status"] = decision.target_status
            items.append(item)
            continue

        result = repository.consume_created_signal_for_order_layer(
            signal_id=int(candidate["id"]),
            now_ms=_utc_now_ms(),
            short_only=bool(short_only),
        )
        item["result"] = result.reason
        item["to_status"] = result.current_status
        item["transitioned"] = result.transitioned
        items.append(item)

        if result.transitioned and result.current_status == "CONSUMED":
            consumed_now += 1
        elif result.transitioned and result.current_status == "CANCELLED":
            cancelled_now += 1
        else:
            skipped_now += 1

    summary = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "model2_db_path": str(resolved_model2_db),
        "dry_run": dry_run,
        "filters": {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "short_only": bool(short_only),
        },
        "eligible_created_signals": len(candidates),
        "consumed_now": consumed_now,
        "cancelled_now": cancelled_now,
        "skipped_now": skipped_now,
        "items": items,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_order_layer_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 order-layer signal consumer")
    parser.add_argument(
        "--model2-db-path",
        default=MODEL2_DB_PATH,
        help="Target Model 2.0 SQLite path.",
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Optional symbol filter.",
    )
    parser.add_argument(
        "--timeframe",
        default=None,
        help="Optional timeframe filter.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of CREATED technical signals processed in one run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate decisions without persisting status changes in technical_signals.",
    )
    parser.add_argument(
        "--short-only",
        action="store_true",
        default=M2_SHORT_ONLY,
        help="Force order-layer cancellation for non-SHORT signals.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for order-layer run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_order_layer(
        model2_db_path=args.model2_db_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
        dry_run=bool(args.dry_run),
        short_only=bool(args.short_only),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
