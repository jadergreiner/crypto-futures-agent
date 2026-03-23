"""Filtro RL auditavel antes da camada de ordem do Modelo 2.0."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.sub_agent_manager import SubAgentManager
from core.model2 import Model2ThesisRepository
from scripts.model2.io_utils import atomic_write_json

try:
    from config.settings import MODEL2_DB_PATH
except Exception:
    MODEL2_DB_PATH = "db/modelo2.db"

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"
DEFAULT_THRESHOLD = 0.55
ACTION_NEUTRAL = 0
ACTION_LONG = 1
ACTION_SHORT = 2


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _safe_json_dict(raw_value: Any) -> dict[str, Any]:
    try:
        payload = json.loads(raw_value or "{}")
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict):
        return payload
    return {}


def _ensure_model2_entry_filter_schema(conn: sqlite3.Connection) -> None:
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


def _signal_side_to_expected_action(signal_side: str) -> int | None:
    side = signal_side.upper().strip()
    if side == "LONG":
        return ACTION_LONG
    if side == "SHORT":
        return ACTION_SHORT
    return None


def _build_observation(signal: Mapping[str, Any]) -> list[float]:
    return [
        float(signal.get("entry_price", 0.0) or 0.0),
        float(signal.get("stop_loss", 0.0) or 0.0),
        float(signal.get("take_profit", 0.0) or 0.0),
        float(signal.get("signal_timestamp", 0) or 0),
    ]


def _build_rl_audit_payload(
    *,
    action: int,
    confidence: float,
    threshold: float,
    reason: str,
    decision_timestamp: int,
    agent_version: str,
) -> dict[str, Any]:
    return {
        "decision": int(action),
        "confidence": float(confidence),
        "threshold": float(threshold),
        "reason": str(reason),
        "agent_version": str(agent_version),
        "decision_timestamp": int(decision_timestamp),
    }


def _write_rl_audit(
    conn: sqlite3.Connection,
    *,
    signal_id: int,
    previous_status: str,
    target_status: str,
    rl_audit: Mapping[str, Any],
    payload_base: Mapping[str, Any] | None,
    now_ms: int,
) -> bool:
    merged_payload = dict(payload_base) if isinstance(payload_base, Mapping) else {}
    merged_payload["rl_entry_filter"] = dict(rl_audit)
    cursor = conn.execute(
        """
        UPDATE technical_signals
        SET status = ?, payload_json = ?, updated_at = ?
        WHERE id = ? AND status = ?
        """,
        (
            str(target_status),
            json.dumps(merged_payload, ensure_ascii=True, sort_keys=True),
            int(now_ms),
            int(signal_id),
            str(previous_status),
        ),
    )
    return int(cursor.rowcount) > 0


def run_entry_rl_filter(
    *,
    model2_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    dry_run: bool,
    output_dir: str | Path,
    threshold: float = DEFAULT_THRESHOLD,
    manager_cls: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    with sqlite3.connect(resolved_model2_db) as conn:
        _ensure_model2_entry_filter_schema(conn)

    repository = Model2ThesisRepository(str(resolved_model2_db))
    candidates = repository.list_created_technical_signals(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )

    manager_type = manager_cls or SubAgentManager
    manager = manager_type(base_dir=str(REPO_ROOT / "models" / "sub_agents"))
    if hasattr(manager, "load_all"):
        manager.load_all()

    fallback = 0
    pass_through = 0
    cancelled_neutral = 0
    cancelled_contradiction = 0
    enriched_match = 0
    erro = 0
    items: list[dict[str, Any]] = []

    with sqlite3.connect(resolved_model2_db) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")

        for candidate in candidates:
            signal_id = int(candidate["id"])
            signal_symbol = str(candidate["symbol"])
            signal_side = str(candidate["signal_side"])
            from_status = str(candidate["status"])
            observation = _build_observation(candidate)
            raw_payload = _safe_json_dict(candidate.get("payload_json"))
            expected_action = _signal_side_to_expected_action(signal_side)
            decision_timestamp = int(candidate.get("signal_timestamp") or _utc_now_ms())

            item: dict[str, Any] = {
                "signal_id": signal_id,
                "symbol": signal_symbol,
                "signal_side": signal_side,
                "from_status": from_status,
            }

            try:
                action, confidence = manager.predict_entry(signal_symbol, observation)
            except Exception as exc:
                erro += 1
                item["result"] = "error"
                item["error"] = str(exc)
                items.append(item)
                continue

            normalized_action = int(action)
            normalized_confidence = float(confidence)
            agent_version = manager.__class__.__name__

            if normalized_confidence < float(threshold):
                fallback += 1
                pass_through += 1
                reason = "rl_entry_low_confidence"
                item["result"] = "fallback"
                item["reason"] = reason
                rl_audit = _build_rl_audit_payload(
                    action=normalized_action,
                    confidence=normalized_confidence,
                    threshold=float(threshold),
                    reason=reason,
                    decision_timestamp=decision_timestamp,
                    agent_version=agent_version,
                )
                if not dry_run:
                    _write_rl_audit(
                        conn,
                        signal_id=signal_id,
                        previous_status=from_status,
                        target_status=from_status,
                        rl_audit=rl_audit,
                        payload_base=raw_payload,
                        now_ms=_utc_now_ms(),
                    )
                items.append(item)
                continue

            if normalized_action == ACTION_NEUTRAL:
                cancelled_neutral += 1
                reason = "rl_entry_neutral"
                item["result"] = "cancelled"
                item["reason"] = reason
                rl_audit = _build_rl_audit_payload(
                    action=normalized_action,
                    confidence=normalized_confidence,
                    threshold=float(threshold),
                    reason=reason,
                    decision_timestamp=decision_timestamp,
                    agent_version=agent_version,
                )
                if not dry_run:
                    _write_rl_audit(
                        conn,
                        signal_id=signal_id,
                        previous_status=from_status,
                        target_status="CANCELLED",
                        rl_audit=rl_audit,
                        payload_base=raw_payload,
                        now_ms=_utc_now_ms(),
                    )
                items.append(item)
                continue

            if expected_action is not None and normalized_action == expected_action:
                pass_through += 1
                enriched_match += 1
                reason = "rl_entry_match"
                item["result"] = "pass_through"
                item["reason"] = reason
                rl_audit = _build_rl_audit_payload(
                    action=normalized_action,
                    confidence=normalized_confidence,
                    threshold=float(threshold),
                    reason=reason,
                    decision_timestamp=decision_timestamp,
                    agent_version=agent_version,
                )
                if not dry_run:
                    _write_rl_audit(
                        conn,
                        signal_id=signal_id,
                        previous_status=from_status,
                        target_status=from_status,
                        rl_audit=rl_audit,
                        payload_base=raw_payload,
                        now_ms=_utc_now_ms(),
                    )
                items.append(item)
                continue

            cancelled_contradiction += 1
            reason = "rl_entry_contradiction"
            item["result"] = "cancelled"
            item["reason"] = reason
            rl_audit = _build_rl_audit_payload(
                action=normalized_action,
                confidence=normalized_confidence,
                threshold=float(threshold),
                reason=reason,
                decision_timestamp=decision_timestamp,
                agent_version=agent_version,
            )
            if not dry_run:
                _write_rl_audit(
                    conn,
                    signal_id=signal_id,
                    previous_status=from_status,
                    target_status="CANCELLED",
                    rl_audit=rl_audit,
                    payload_base=raw_payload,
                    now_ms=_utc_now_ms(),
                )
            items.append(item)

    summary = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "model2_db_path": str(resolved_model2_db),
        "dry_run": bool(dry_run),
        "filters": {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": int(limit),
            "threshold": float(threshold),
        },
        "eligible_created_signals": len(candidates),
        "fallback": int(fallback),
        "pass_through": int(pass_through),
        "cancelled_neutral": int(cancelled_neutral),
        "cancelled_contradiction": int(cancelled_contradiction),
        "enriched_match": int(enriched_match),
        "erro": int(erro),
        "items": items,
    }

    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_entry_rl_filter_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filtro RL de entrada do Modelo 2.0")
    parser.add_argument(
        "--model2-db-path",
        default=MODEL2_DB_PATH,
        help="Target Model 2.0 SQLite path.",
    )
    parser.add_argument("--symbol", default=None, help="Optional symbol filter.")
    parser.add_argument("--timeframe", default=None, help="Optional timeframe filter.")
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
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Confidence threshold for decisive RL actions.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for entry RL filter summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_entry_rl_filter(
        model2_db_path=args.model2_db_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=int(args.limit),
        dry_run=bool(args.dry_run),
        output_dir=args.output_dir,
        threshold=float(args.threshold),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
