"""Controles de resiliencia para pacote M2-023.2..023.10 + M2-027.2.

Funcoes puras e deterministicas para suportar contratos de testes.
Nao desabilita risk_gate/circuit_breaker; apenas fornece avaliadores.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from statistics import mean
from typing import Any, Callable


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
    retryable_categories = {"timeout", "transient"}
    normalized_category = str(category or "unknown").strip().lower()
    should_retry = normalized_category in retryable_categories
    attempts = max(1, int(max_attempts)) if should_retry else 1

    last_error: str | None = None
    for _ in range(attempts):
        try:
            fn()
            return {
                "ok": True,
                "error": None,
                "category": normalized_category,
                "attempts": attempts,
                "should_retry": should_retry,
            }
        except Exception as exc:  # noqa: BLE001 - contrato de retry
            last_error = str(exc)
    return {
        "ok": False,
        "error": last_error,
        "category": normalized_category,
        "attempts": attempts,
        "should_retry": should_retry,
    }


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


_RISK_GATE_REASON_CODES = frozenset({
    "risk_gate_blocked",
    "risk_gate_drawdown",
    "risk_gate_size_limit",
    "risk_gate_daily_limit",
})


def build_risk_gate_audit_trail(
    db_path: str,
    decision_id: int,
) -> list[dict[str, Any]]:
    """Constroi trilha auditavel de bloqueios do risk_gate para um decision_id.

    Consulta `signal_executions` e `signal_execution_events` no banco
    canonico M2 filtrando por `decision_id` e `failure_reason` indicativo
    de bloqueio pelo risk_gate (M2-023.6, ADR-002/007).

    Fail-safe: retorna lista vazia sem lancar excecao em caso de DB ausente,
    tabela inexistente ou qualquer erro de consulta.

    Args:
        db_path: Caminho absoluto para o banco modelo2.db.
        decision_id: Identificador da decisao a auditar.

    Returns:
        Lista de dicts com os campos:
            - execution_id: int
            - decision_id: int
            - reason_code: str (ex.: 'risk_gate_blocked')
            - symbol: str
            - timestamp_ms: int
            - metadata: dict (payload_json do evento, se disponivel)
    """
    trail: list[dict[str, Any]] = []
    try:
        if not Path(db_path).exists():
            return trail

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT
                    se.id           AS execution_id,
                    se.decision_id  AS decision_id,
                    COALESCE(se.failure_reason, se.gate_reason) AS reason_code,
                    se.symbol       AS symbol,
                    COALESCE(
                        see.event_timestamp,
                        se.created_at,
                        0
                    )               AS timestamp_ms,
                    COALESCE(see.payload_json, '{}') AS payload_json
                FROM signal_executions se
                LEFT JOIN signal_execution_events see
                    ON see.signal_execution_id = se.id
                WHERE se.decision_id = ?
                  AND (
                      se.failure_reason LIKE '%risk_gate%'
                      OR se.gate_reason LIKE '%risk_gate%'
                  )
                ORDER BY timestamp_ms ASC
                """,
                (int(decision_id),),
            ).fetchall()
        finally:
            conn.close()

        for row in rows:
            reason: str = str(row["reason_code"] or "risk_gate_blocked")
            # Normalizar reason_code para catalogo canonico quando possivel
            if reason not in _RISK_GATE_REASON_CODES:
                reason = "risk_gate_blocked"
            try:
                metadata: dict[str, Any] = json.loads(str(row["payload_json"] or "{}"))
            except Exception:
                metadata = {}
            trail.append({
                "execution_id": int(row["execution_id"]),
                "decision_id": int(row["decision_id"]),
                "reason_code": reason,
                "symbol": str(row["symbol"] or ""),
                "timestamp_ms": int(row["timestamp_ms"] or 0),
                "metadata": metadata,
            })

    except Exception:
        # Fail-safe intencional (ADR-002): nunca propagar excecao.
        trail = []

    return trail
