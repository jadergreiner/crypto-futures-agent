"""Controles de resiliencia para pacote M2-023.2..023.10 + M2-027.2.

Funcoes puras e deterministicas para suportar contratos de testes.
Nao desabilita risk_gate/circuit_breaker; apenas fornece avaliadores.
"""

from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Callable


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def evaluate_position_drift_gate(
    current_state: dict[str, float],
    observed_state: dict[str, float],
    threshold_pct: float,
    decision_id: int,
) -> dict[str, object]:
    current_qty = float(current_state.get("position_qty", 0.0))
    observed_qty = float(observed_state.get("position_qty", 0.0))
    baseline = max(abs(current_qty), 1e-9)
    drift_pct = abs(observed_qty - current_qty) / baseline
    allow = drift_pct <= float(threshold_pct)
    return {
        "allow": allow,
        "reason_code": None if allow else "position_drift_blocked",
        "decision_id": int(decision_id),
        "drift_pct": drift_pct,
    }


def evaluate_latency_degradation(
    metrics: dict[str, int],
    p95_limit_ms: int,
    p99_limit_ms: int,
) -> dict[str, object]:
    p95 = int(metrics.get("p95_ms", 0))
    p99 = int(metrics.get("p99_ms", 0))
    degraded = p95 > int(p95_limit_ms) or p99 > int(p99_limit_ms)
    return {
        "mode": "degraded" if degraded else "normal",
        "entry_reason": "latency_slo_breached" if degraded else None,
        "p95_ms": p95,
        "p99_ms": p99,
    }


def plan_restart_from_snapshot(
    snapshot: dict[str, int | str],
    has_open_order: bool,
) -> dict[str, object]:
    _ = snapshot.get("decision_id")
    _ = snapshot.get("phase")
    _ = snapshot.get("heartbeat_ms")
    return {
        "replay_mode": "idempotent_resume",
        "send_new_order": False if not has_open_order else False,
    }


def prioritize_events(events: list[dict[str, str]]) -> list[dict[str, str]]:
    priority_rank = {"CRITICAL": 0, "HIGH": 1, "WARN": 2}
    return sorted(events, key=lambda e: priority_rank.get(str(e.get("priority")), 9))


def query_risk_gate_audit_by_decision_id(
    trail: list[dict[str, object]],
    decision_id: int,
) -> list[dict[str, object]]:
    return [event for event in trail if _to_int(event.get("decision_id"), -1) == int(decision_id)]


def cross_validate_signal_context_position(
    signal: dict[str, object],
    context: dict[str, object],
    position: dict[str, object],
) -> dict[str, object]:
    _ = position.get("is_open", False)
    side = str(signal.get("side", "")).upper()
    trend = str(context.get("trend", "")).upper()
    conflict = (side == "LONG" and trend == "DOWN") or (side == "SHORT" and trend == "UP")
    return {
        "allow": not conflict,
        "reason_code": "cross_validation_conflict" if conflict else None,
    }


def execute_with_category_retry(
    fn: Callable[[], object],
    category: str,
    max_attempts: int,
) -> dict[str, object]:
    attempts = 1 if category == "permanent" else max(1, int(max_attempts))
    last_error: str | None = None
    for _ in range(attempts):
        try:
            fn()
            return {"ok": True, "error": None}
        except Exception as exc:  # noqa: BLE001 - contrato de retry
            last_error = str(exc)
    return {"ok": False, "error": last_error}


def compute_reconciliation_health_indicators(
    samples: list[dict[str, object]],
) -> dict[str, float]:
    if not samples:
        return {"drift_mean": 0.0, "confirmation_p95_ms": 0.0, "adjustment_rate": 0.0}
    drifts = [_to_float(item.get("drift")) for item in samples]
    confirms = sorted(_to_float(item.get("confirm_ms")) for item in samples)
    adjusted_count = sum(1 for item in samples if bool(item.get("adjusted", False)))
    p95_index = max(0, min(len(confirms) - 1, int((len(confirms) - 1) * 0.95)))
    return {
        "drift_mean": mean(drifts),
        "confirmation_p95_ms": confirms[p95_index],
        "adjustment_rate": adjusted_count / float(len(samples)),
    }


def validate_contingency_runbook(runbook_path: Path) -> dict[str, object]:
    if not runbook_path.exists():
        return {"ready": False, "reason_code": "runbook_missing_or_invalid"}
    try:
        content = runbook_path.read_text(encoding="utf-8").strip()
    except OSError:
        return {"ready": False, "reason_code": "runbook_missing_or_invalid"}
    if not content:
        return {"ready": False, "reason_code": "runbook_missing_or_invalid"}
    return {"ready": True, "reason_code": None}


def validate_schema_tables(
    existing_tables: set[str],
    required_tables: set[str],
) -> dict[str, object]:
    missing = sorted(required_tables - existing_tables)
    if missing:
        return {"ok": False, "reason_code": "schema_divergence", "missing_tables": missing}
    return {"ok": True, "reason_code": None, "missing_tables": []}
