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


class TrainingStaleResult(TypedDict):
    """Resultado canonico da avaliacao de stale do treino."""

    stale: bool
    reason: str
    age_ms: int | None
    max_allowed_age_ms: int


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
            status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(triggered_at_ms),
            str(trigger_reason),
            int(episodes_count),
            (str(model_id_before) if model_id_before is not None else None),
            (str(model_id_after) if model_id_after is not None else None),
            (float(avg_reward_delta) if avg_reward_delta is not None else None),
            str(status),
        ),
    )


def evaluate_training_trigger_audit(
    *,
    pending_episodes: int,
    retrain_threshold: int,
    is_running: bool,
    now_ms: int,
    last_completed_at_ms: int | None,
) -> TrainingTriggerAuditDecision:
    """Avalia trigger incremental de treino com semantica auditavel."""
    pending_value = max(0, int(pending_episodes))
    threshold_value = int(retrain_threshold)

    if threshold_value <= 0:
        return {
            "trigger_allowed": False,
            "trigger_reason": "invalid_threshold",
            "status": "blocked",
            "pending_episodes": pending_value,
            "retrain_threshold": threshold_value,
            "now_ms": int(now_ms),
            "last_completed_at_ms": last_completed_at_ms,
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
        }

    return {
        "trigger_allowed": True,
        "trigger_reason": "threshold_reached",
        "status": "started",
        "pending_episodes": pending_value,
        "retrain_threshold": threshold_value,
        "now_ms": int(now_ms),
        "last_completed_at_ms": last_completed_at_ms,
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
