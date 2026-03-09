"""Model 2.0 adapter runner for M2-007.2 (technical_signals -> trade_signals)."""

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

from config.settings import DB_PATH, MODEL2_DB_PATH
from core.model2 import (
    ADAPTER_EXPORT_KEY,
    M2_007_2_RULE_ID,
    Model2ThesisRepository,
    SignalAdapterInput,
    build_legacy_trade_signal_payload,
)
from data.database import DatabaseManager

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _ensure_model2_adapter_schema(conn: sqlite3.Connection) -> None:
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


def _find_existing_legacy_trade_signal_id(
    legacy_db: DatabaseManager,
    *,
    technical_signal_id: int,
) -> int | None:
    patterns = [
        f'%\"m2_technical_signal_id\": {int(technical_signal_id)}%',
        f'%\"m2_technical_signal_id\":{int(technical_signal_id)}%',
        f'%\"m2_technical_signal_id\": \"{int(technical_signal_id)}\"%',
    ]
    with legacy_db.get_connection() as conn:
        for pattern in patterns:
            row = conn.execute(
                """
                SELECT id
                FROM trade_signals
                WHERE confluence_details LIKE ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (pattern,),
            ).fetchone()
            if row is not None:
                return int(row[0])
    return None


def _parse_payload(raw_payload: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_payload or "{}")
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def run_export_signals(
    *,
    model2_db_path: str | Path,
    legacy_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    dry_run: bool,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_legacy_db = _resolve_repo_path(legacy_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as conn:
        _ensure_model2_adapter_schema(conn)

    repository = Model2ThesisRepository(str(resolved_model2_db))
    legacy_db = DatabaseManager(str(resolved_legacy_db))
    candidates = repository.list_consumed_technical_signals(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )

    exported_now = 0
    idempotent_hits = 0
    skipped_now = 0
    errors_now = 0
    items: list[dict[str, Any]] = []

    for candidate in candidates:
        signal_id = int(candidate["id"])
        candidate_payload = _parse_payload(candidate.get("payload_json"))
        item: dict[str, Any] = {
            "technical_signal_id": signal_id,
            "opportunity_id": int(candidate["opportunity_id"]),
            "symbol": str(candidate["symbol"]),
            "timeframe": str(candidate["timeframe"]),
            "status": str(candidate["status"]),
        }

        export_marker = candidate_payload.get(ADAPTER_EXPORT_KEY)
        if isinstance(export_marker, dict) and export_marker.get("exported") is True:
            item["result"] = "already_marked_exported"
            item["legacy_trade_signal_id"] = export_marker.get("legacy_trade_signal_id")
            idempotent_hits += 1
            items.append(item)
            continue

        existing_legacy_signal_id = _find_existing_legacy_trade_signal_id(
            legacy_db, technical_signal_id=signal_id
        )
        if existing_legacy_signal_id is not None:
            item["result"] = "already_exported_in_legacy"
            item["legacy_trade_signal_id"] = existing_legacy_signal_id
            if not dry_run:
                repository.mark_technical_signal_exported_to_trade_signals(
                    signal_id=signal_id,
                    legacy_trade_signal_id=existing_legacy_signal_id,
                    now_ms=_utc_now_ms(),
                    rule_id=M2_007_2_RULE_ID,
                    metadata={"source": "legacy_lookup"},
                )
            idempotent_hits += 1
            items.append(item)
            continue

        adapter_result = build_legacy_trade_signal_payload(
            SignalAdapterInput(
                technical_signal_id=signal_id,
                opportunity_id=int(candidate["opportunity_id"]),
                symbol=str(candidate["symbol"]),
                timeframe=str(candidate["timeframe"]),
                signal_side=str(candidate["signal_side"]),
                entry_price=float(candidate["entry_price"]),
                stop_loss=float(candidate["stop_loss"]),
                take_profit=float(candidate["take_profit"]),
                status=str(candidate["status"]),
                signal_timestamp=int(candidate["signal_timestamp"]),
                payload=candidate_payload,
            )
        )
        if not adapter_result.exportable:
            item["result"] = adapter_result.reason
            skipped_now += 1
            items.append(item)
            continue

        if dry_run:
            item["result"] = "DRY_RUN_EXPORTABLE"
            item["legacy_execution_mode"] = adapter_result.payload.get("execution_mode")
            item["would_send_real_order"] = False
            items.append(item)
            continue

        try:
            legacy_trade_signal_id = legacy_db.insert_trade_signal(dict(adapter_result.payload))
            repository.mark_technical_signal_exported_to_trade_signals(
                signal_id=signal_id,
                legacy_trade_signal_id=int(legacy_trade_signal_id),
                now_ms=_utc_now_ms(),
                rule_id=M2_007_2_RULE_ID,
                metadata={"dual_write_controlled": True, "would_send_real_order": False},
            )
            item["result"] = "exported"
            item["legacy_trade_signal_id"] = int(legacy_trade_signal_id)
            exported_now += 1
        except Exception as exc:
            item["result"] = "error"
            item["error"] = str(exc)
            repository.mark_technical_signal_export_error(
                signal_id=signal_id,
                now_ms=_utc_now_ms(),
                rule_id=M2_007_2_RULE_ID,
                error_message=str(exc),
            )
            errors_now += 1
        items.append(item)

    summary = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "model2_db_path": str(resolved_model2_db),
        "legacy_db_path": str(resolved_legacy_db),
        "dry_run": dry_run,
        "filters": {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
        },
        "consumed_candidates": len(candidates),
        "exported_now": exported_now,
        "idempotent_hits_now": idempotent_hits,
        "skipped_now": skipped_now,
        "errors_now": errors_now,
        "items": items,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_export_signals_{run_id}.json"
    output_file.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 adapter for technical_signals to trade_signals")
    parser.add_argument(
        "--model2-db-path",
        default=MODEL2_DB_PATH,
        help="Target Model 2.0 SQLite path.",
    )
    parser.add_argument(
        "--legacy-db-path",
        default=DB_PATH,
        help="Legacy SQLite path with trade_signals table.",
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
        help="Maximum number of CONSUMED technical_signals processed in one run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate export candidates without persisting legacy trade_signals.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for export run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_export_signals(
        model2_db_path=args.model2_db_path,
        legacy_db_path=args.legacy_db_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
        dry_run=bool(args.dry_run),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
