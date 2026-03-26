"""Metricas de latencia por etapa do ciclo M2 — BLID-086.

Persiste amostras em m2_latency_samples e computa percentis P50/P95/P99.
Detecta violacoes: P95 > 2000ms ou P99 > 5000ms.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

_P95_THRESHOLD_MS = 2_000
_P99_THRESHOLD_MS = 5_000

_SCHEMA_LATENCY_SAMPLES = """
CREATE TABLE IF NOT EXISTS m2_latency_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage TEXT NOT NULL,
    elapsed_ms INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_latency_stage ON m2_latency_samples (stage, created_at DESC);
"""


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_LATENCY_SAMPLES)


def record_latency(db_path: str, *, stage: str, elapsed_ms: int) -> None:
    """Persiste uma amostra de latencia para a etapa informada."""
    now_ms = _utc_now_ms()
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            _ensure_table(conn)
            conn.execute(
                "INSERT INTO m2_latency_samples (stage, elapsed_ms, created_at) "
                "VALUES (?, ?, ?)",
                (stage, int(elapsed_ms), now_ms),
            )
            conn.commit()
    except sqlite3.OperationalError:
        pass


def compute_percentiles(samples: list[int | float]) -> dict[str, float]:
    """Calcula P50, P95 e P99 de uma lista de amostras (ms)."""
    if not samples:
        return {"p50": 0, "p95": 0, "p99": 0}

    sorted_samples = sorted(float(x) for x in samples)
    n = len(sorted_samples)

    def _percentile(p: float) -> float:
        idx = (p / 100) * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return sorted_samples[lo] * (1 - frac) + sorted_samples[hi] * frac

    return {
        "p50": round(_percentile(50), 1),
        "p95": round(_percentile(95), 1),
        "p99": round(_percentile(99), 1),
    }


def detect_latency_violations(
    percentiles: dict[str, float],
    *,
    stage: str,
    p95_threshold_ms: int = _P95_THRESHOLD_MS,
    p99_threshold_ms: int = _P99_THRESHOLD_MS,
) -> list[dict[str, Any]]:
    """Retorna lista de violacoes quando percentis excedem limites."""
    violations: list[dict[str, Any]] = []

    p95 = float(percentiles.get("p95", 0))
    p99 = float(percentiles.get("p99", 0))

    if p95 > p95_threshold_ms:
        violations.append({
            "stage": stage,
            "metric": "p95",
            "value_ms": p95,
            "threshold_ms": p95_threshold_ms,
            "message": f"P95 latencia {stage}={p95:.0f}ms excede {p95_threshold_ms}ms",
        })

    if p99 > p99_threshold_ms:
        violations.append({
            "stage": stage,
            "metric": "p99",
            "value_ms": p99,
            "threshold_ms": p99_threshold_ms,
            "message": f"P99 latencia {stage}={p99:.0f}ms excede {p99_threshold_ms}ms",
        })

    return violations


def record_cycle_latencies(
    db_path: str,
    *,
    cycle_summary: dict[str, Any],
) -> None:
    """Extrai elapsed_ms de cada etapa do summary e persiste em m2_latency_samples."""
    # Garantir que a tabela exista mesmo sem amostras
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            _ensure_table(conn)
    except sqlite3.OperationalError:
        return

    stages = cycle_summary.get("stages")
    if not isinstance(stages, dict):
        return

    for stage_name, stage_data in stages.items():
        if not isinstance(stage_data, dict):
            continue
        elapsed = stage_data.get("stage_elapsed_ms")
        if elapsed is not None:
            record_latency(db_path, stage=stage_name, elapsed_ms=int(elapsed))
