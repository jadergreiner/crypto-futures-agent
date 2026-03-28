"""Helpers de auditoria para trigger de treino incremental (M2-022.2)."""

from __future__ import annotations

import sqlite3
from typing import TypedDict


class TrainingTriggerAuditDecision(TypedDict):
    """Resultado canonico da avaliacao de trigger de treino."""

    trigger_allowed: bool
    trigger_reason: str
    status: str
    pending_episodes: int
    retrain_threshold: int
    now_ms: int
    last_completed_at_ms: int | None
    idempotency_key: str | None


class TrainingStaleResult(TypedDict):
    """Resultado canonico da avaliacao de stale do treino."""

    stale: bool
    reason: str
    age_ms: int | None
    max_allowed_age_ms: int


class TrainingAuditWindowSummary(TypedDict):
    """Resumo operacional da janela de auditoria de treino incremental."""

    total_events: int
    started_events: int
    blocked_running_events: int
    threshold_not_reached_events: int
    conclusive: bool


def ensure_rl_training_audit_schema(conn: sqlite3.Connection) -> None:
    """Garante schema minimo da trilha rl_training_audit."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rl_training_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            triggered_at_ms INTEGER NOT NULL,
            trigger_reason TEXT NOT NULL,
            episodes_count INTEGER NOT NULL,
            model_id_before TEXT,
            model_id_after TEXT,
            avg_reward_delta REAL,
            status TEXT NOT NULL,
            decision_id TEXT,
            concurrency_key TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rl_training_audit_triggered_at
        ON rl_training_audit (triggered_at_ms DESC, id DESC)
        """
    )
    columns = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(rl_training_audit)").fetchall()
    }
    if "decision_id" not in columns:
        conn.execute("ALTER TABLE rl_training_audit ADD COLUMN decision_id TEXT")
    if "concurrency_key" not in columns:
        conn.execute("ALTER TABLE rl_training_audit ADD COLUMN concurrency_key TEXT")


def record_training_audit_event(
    conn: sqlite3.Connection,
    *,
    triggered_at_ms: int,
    trigger_reason: str,
    episodes_count: int,
    model_id_before: str | None,
    model_id_after: str | None,
    avg_reward_delta: float | None,
    status: str,
    decision_id: str | None = None,
    concurrency_key: str | None = None,
) -> None:
    """Persiste um evento de trigger de treino para auditoria."""
    ensure_rl_training_audit_schema(conn)
    conn.execute(
        """
        INSERT INTO rl_training_audit (
            triggered_at_ms,
            trigger_reason,
            episodes_count,
            model_id_before,
            model_id_after,
            avg_reward_delta,
            status,
            decision_id,
            concurrency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(triggered_at_ms),
            str(trigger_reason),
            int(episodes_count),
            (str(model_id_before) if model_id_before is not None else None),
            (str(model_id_after) if model_id_after is not None else None),
            (float(avg_reward_delta) if avg_reward_delta is not None else None),
            str(status),
            (str(decision_id) if decision_id is not None else None),
            (str(concurrency_key) if concurrency_key is not None else None),
        ),
    )


def _build_training_idempotency_key(
    *,
    decision_id: str | None,
    timeframe: str | None,
) -> str | None:
    normalized_decision = (decision_id or "").strip()
    normalized_timeframe = (timeframe or "").strip()
    if not normalized_decision:
        return None
    if normalized_timeframe:
        return f"{normalized_decision}:{normalized_timeframe}"
    return normalized_decision


def evaluate_training_trigger_audit(
    *,
    pending_episodes: int,
    retrain_threshold: int,
    is_running: bool,
    now_ms: int,
    last_completed_at_ms: int | None,
    decision_id: str | None = None,
    timeframe: str | None = None,
) -> TrainingTriggerAuditDecision:
    """Avalia trigger incremental de treino com semantica auditavel."""
    pending_value = max(0, int(pending_episodes))
    threshold_value = int(retrain_threshold)
    idempotency_key = _build_training_idempotency_key(
        decision_id=decision_id,
        timeframe=timeframe,
    )

    if threshold_value <= 0:
        return {
            "trigger_allowed": False,
            "trigger_reason": "invalid_threshold",
            "status": "blocked",
            "pending_episodes": pending_value,
            "retrain_threshold": threshold_value,
            "now_ms": int(now_ms),
            "last_completed_at_ms": last_completed_at_ms,
            "idempotency_key": idempotency_key,
        }

    if is_running:
        return {
            "trigger_allowed": False,
            "trigger_reason": "training_already_running",
            "status": "blocked",
            "pending_episodes": pending_value,
            "retrain_threshold": threshold_value,
            "now_ms": int(now_ms),
            "last_completed_at_ms": last_completed_at_ms,
            "idempotency_key": idempotency_key,
        }

    if pending_value < threshold_value:
        return {
            "trigger_allowed": False,
            "trigger_reason": "threshold_not_reached",
            "status": "blocked",
            "pending_episodes": pending_value,
            "retrain_threshold": threshold_value,
            "now_ms": int(now_ms),
            "last_completed_at_ms": last_completed_at_ms,
            "idempotency_key": idempotency_key,
        }

    return {
        "trigger_allowed": True,
        "trigger_reason": "threshold_reached",
        "status": "started",
        "pending_episodes": pending_value,
        "retrain_threshold": threshold_value,
        "now_ms": int(now_ms),
        "last_completed_at_ms": last_completed_at_ms,
        "idempotency_key": idempotency_key,
    }


def detect_training_stale(
    *,
    now_ms: int,
    last_completed_at_ms: int | None,
    max_stale_hours: int,
    operation_active: bool,
) -> TrainingStaleResult:
    """Detecta stale de treino quando operacao esta ativa."""
    max_allowed_age_ms = max(0, int(max_stale_hours)) * 60 * 60 * 1000

    if not operation_active:
        return {
            "stale": False,
            "reason": "operation_inactive",
            "age_ms": None,
            "max_allowed_age_ms": max_allowed_age_ms,
        }

    if max_allowed_age_ms <= 0:
        return {
            "stale": False,
            "reason": "stale_check_disabled",
            "age_ms": None,
            "max_allowed_age_ms": max_allowed_age_ms,
        }

    if last_completed_at_ms is None:
        return {
            "stale": True,
            "reason": "training_stale",
            "age_ms": None,
            "max_allowed_age_ms": max_allowed_age_ms,
        }

    age_ms = max(0, int(now_ms) - int(last_completed_at_ms))
    if age_ms > max_allowed_age_ms:
        return {
            "stale": True,
            "reason": "training_stale",
            "age_ms": age_ms,
            "max_allowed_age_ms": max_allowed_age_ms,
        }

    return {
        "stale": False,
        "reason": "training_recent",
        "age_ms": age_ms,
        "max_allowed_age_ms": max_allowed_age_ms,
    }


def summarize_training_audit_window(
    conn: sqlite3.Connection,
    *,
    since_ms: int,
) -> TrainingAuditWindowSummary:
    """Resume eventos de auditoria para leitura operacional objetiva."""
    ensure_rl_training_audit_schema(conn)
    rows = conn.execute(
        """
        SELECT trigger_reason, status, COUNT(*)
        FROM rl_training_audit
        WHERE triggered_at_ms >= ?
        GROUP BY trigger_reason, status
        """,
        (int(since_ms),),
    ).fetchall()

    total_events = 0
    started_events = 0
    blocked_running_events = 0
    threshold_not_reached_events = 0

    for trigger_reason, status, count in rows:
        row_count = int(count or 0)
        total_events += row_count
        reason = str(trigger_reason or "")
        state = str(status or "")
        if state == "started":
            started_events += row_count
        if reason == "training_already_running":
            blocked_running_events += row_count
        if reason == "threshold_not_reached":
            threshold_not_reached_events += row_count

    return {
        "total_events": total_events,
        "started_events": started_events,
        "blocked_running_events": blocked_running_events,
        "threshold_not_reached_events": threshold_not_reached_events,
        "conclusive": started_events > 0,
    }
