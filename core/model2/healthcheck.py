"""Healthcheck operacional M2 — BLID-087.

Detecta 5 categorias de anomalia com severity CRITICAL/HIGH/WARN/OK:
1. Estagnacao de episodios (nenhum episodio recente)
2. Deferred reward timeout (reward_lookup vencido sem preenchimento)
3. Permanent lock (signal_executions presas em ENTRY_SENT)
4. (reservado para extensao futura)
5. (reservado para extensao futura)

Persiste resultado em m2_healthchecks (lazy CREATE TABLE).
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

_SEVERITY_ORDER = {"OK": 0, "WARN": 1, "HIGH": 2, "CRITICAL": 3}

_SCHEMA_M2_HEALTHCHECKS = """
CREATE TABLE IF NOT EXISTS m2_healthchecks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    overall_severity TEXT NOT NULL,
    checks_json TEXT NOT NULL DEFAULT '[]',
    created_at INTEGER NOT NULL
);
"""


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _ensure_healthchecks_table(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_M2_HEALTHCHECKS)


def _severity_max(a: str, b: str) -> str:
    return a if _SEVERITY_ORDER.get(a, 0) >= _SEVERITY_ORDER.get(b, 0) else b


def check_episode_stagnation(
    db_path: str,
    *,
    stagnation_minutes: int = 30,
) -> dict[str, Any]:
    """Verifica se ha episodios recentes em training_episodes.

    Sem episodios novos em stagnation_minutes → WARN.
    Sem episodios novos em 4x stagnation_minutes → HIGH.
    Sem episodios novos em 8x stagnation_minutes → CRITICAL.
    """
    now_ms = _utc_now_ms()
    warn_threshold_ms = stagnation_minutes * 60 * 1000
    high_threshold_ms = warn_threshold_ms * 4
    critical_threshold_ms = warn_threshold_ms * 8

    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT MAX(created_at) FROM training_episodes "
                "WHERE status NOT IN ('CYCLE_CONTEXT')"
            ).fetchone()
    except sqlite3.OperationalError:
        return {
            "code": "episode_stagnation_table_missing",
            "severity": "WARN",
            "message": "training_episodes table not found",
        }

    last_ts = int(row[0]) if row and row[0] is not None else 0
    age_ms = now_ms - last_ts if last_ts > 0 else now_ms

    if age_ms >= critical_threshold_ms:
        severity = "CRITICAL"
    elif age_ms >= high_threshold_ms:
        severity = "HIGH"
    elif age_ms >= warn_threshold_ms:
        severity = "WARN"
    else:
        severity = "OK"

    return {
        "code": "episode_stagnation",
        "severity": severity,
        "age_minutes": round(age_ms / 60_000, 1),
        "threshold_minutes": stagnation_minutes,
        "message": f"Ultimo episodio ha {round(age_ms/60_000, 1)} min"
        if last_ts > 0 else "Nenhum episodio encontrado",
    }


def check_deferred_reward_timeout(
    db_path: str,
    *,
    timeout_minutes: int = 30,
) -> dict[str, Any]:
    """Verifica episodios com reward_lookup_at_ms vencido e reward NULL.

    1+ episodio vencido → HIGH.
    5+ episodios vencidos → CRITICAL.
    """
    now_ms = _utc_now_ms()
    cutoff_ms = now_ms - timeout_minutes * 60 * 1000

    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM training_episodes "
                "WHERE reward_proxy IS NULL "
                "  AND reward_lookup_at_ms IS NOT NULL "
                "  AND reward_lookup_at_ms < ?",
                (cutoff_ms,),
            ).fetchone()
    except sqlite3.OperationalError:
        return {"code": "deferred_reward_timeout", "severity": "OK",
                "message": "training_episodes table not found"}

    count = int(row[0]) if row else 0

    if count >= 5:
        severity = "CRITICAL"
    elif count >= 1:
        severity = "HIGH"
    else:
        severity = "OK"

    return {
        "code": "deferred_reward_timeout",
        "severity": severity,
        "expired_count": count,
        "timeout_minutes": timeout_minutes,
        "message": f"{count} episodios com reward vencido sem preenchimento",
    }


def check_permanent_lock(
    db_path: str,
    *,
    lock_minutes: int = 30,
) -> dict[str, Any]:
    """Verifica signal_executions presas em ENTRY_SENT.

    1+ sinal preso > lock_minutes → HIGH.
    3+ sinais presos → CRITICAL.
    """
    now_ms = _utc_now_ms()
    cutoff_ms = now_ms - lock_minutes * 60 * 1000

    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM signal_executions "
                "WHERE status = 'ENTRY_SENT' AND updated_at < ?",
                (cutoff_ms,),
            ).fetchone()
    except sqlite3.OperationalError:
        return {"code": "permanent_lock", "severity": "OK",
                "message": "signal_executions table not found"}

    count = int(row[0]) if row else 0

    if count >= 3:
        severity = "CRITICAL"
    elif count >= 1:
        severity = "HIGH"
    else:
        severity = "OK"

    return {
        "code": "permanent_lock",
        "severity": severity,
        "stuck_count": count,
        "lock_minutes": lock_minutes,
        "message": f"{count} sinais presos em ENTRY_SENT ha >{lock_minutes}min",
    }


def run_healthcheck(
    *,
    model2_db_path: str,
    stagnation_minutes: int = 60,
    lock_minutes: int = 30,
    deferred_timeout_minutes: int = 120,
) -> dict[str, Any]:
    """Executa todos os checks e persiste resultado em m2_healthchecks."""
    import json

    checks = [
        check_episode_stagnation(model2_db_path, stagnation_minutes=stagnation_minutes),
        check_deferred_reward_timeout(model2_db_path, timeout_minutes=deferred_timeout_minutes),
        check_permanent_lock(model2_db_path, lock_minutes=lock_minutes),
    ]

    overall = "OK"
    for check in checks:
        overall = _severity_max(overall, check.get("severity", "OK"))

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now_ms = _utc_now_ms()

    try:
        with sqlite3.connect(model2_db_path, timeout=5) as conn:
            _ensure_healthchecks_table(conn)
            conn.execute(
                "INSERT INTO m2_healthchecks "
                "(run_id, overall_severity, checks_json, created_at) "
                "VALUES (?, ?, ?, ?)",
                (run_id, overall, json.dumps(checks, ensure_ascii=True), now_ms),
            )
            conn.commit()
    except sqlite3.OperationalError:
        pass

    return {
        "run_id": run_id,
        "overall_severity": overall,
        "checks": checks,
        "timestamp_utc_ms": now_ms,
    }
