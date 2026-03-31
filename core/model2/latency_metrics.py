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

_SCHEMA_LATENCY_BASELINES = """
CREATE TABLE IF NOT EXISTS m2_latency_baselines (
    stage TEXT PRIMARY KEY,
    baseline_p95_ms REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    first_recorded_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
"""

_DEFAULT_BENCHMARK_STAGES: dict[str, str] = {
    "scan": "scan",
    "track": "track",
    "validate": "validate",
    "signal_bridge": "bridge",
    "order_layer": "order_layer",
    "live_execution": "live_execution",
}


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_LATENCY_SAMPLES)
    conn.executescript(_SCHEMA_LATENCY_BASELINES)


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


def _load_stage_samples(
    conn: sqlite3.Connection,
    *,
    stage: str,
    limit: int = 500,
) -> list[float]:
    rows = conn.execute(
        "SELECT elapsed_ms FROM m2_latency_samples "
        "WHERE stage = ? ORDER BY created_at DESC LIMIT ?",
        (stage, int(limit)),
    ).fetchall()
    return [float(row[0]) for row in rows]


def summarize_stage_benchmark(
    db_path: str,
    *,
    stage: str,
    regression_multiplier: float = 2.0,
) -> dict[str, Any]:
    """Resume benchmark da etapa com baseline P95 e alerta de regressao."""
    now_ms = _utc_now_ms()

    with sqlite3.connect(db_path, timeout=5) as conn:
        _ensure_table(conn)

        samples = _load_stage_samples(conn, stage=stage)
        percentiles = compute_percentiles(samples)
        sample_count = len(samples)

        baseline_row = conn.execute(
            "SELECT baseline_p95_ms, sample_count FROM m2_latency_baselines "
            "WHERE stage = ?",
            (stage,),
        ).fetchone()

        baseline_created = False
        if baseline_row is None and sample_count > 0:
            baseline_p95_ms = float(percentiles["p95"])
            conn.execute(
                "INSERT INTO m2_latency_baselines "
                "(stage, baseline_p95_ms, sample_count, first_recorded_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    stage,
                    baseline_p95_ms,
                    sample_count,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
            baseline_created = True
        elif baseline_row is not None:
            baseline_p95_ms = float(baseline_row[0])
        else:
            baseline_p95_ms = 0.0

    p95 = float(percentiles.get("p95", 0.0))
    has_regression_alert = (
        baseline_p95_ms > 0.0 and p95 > baseline_p95_ms * float(regression_multiplier)
    )

    alert = None
    if has_regression_alert:
        alert = {
            "stage": stage,
            "metric": "p95",
            "message": (
                f"Regressao de latencia em {stage}: "
                f"p95={p95:.1f}ms > {regression_multiplier:.1f}x "
                f"baseline({baseline_p95_ms:.1f}ms)"
            ),
            "p95_ms": p95,
            "baseline_p95_ms": baseline_p95_ms,
            "regression_multiplier": float(regression_multiplier),
        }

    return {
        "stage": stage,
        "sample_count": sample_count,
        "percentiles_ms": percentiles,
        "baseline_p95_ms": round(float(baseline_p95_ms), 1),
        "baseline_created": baseline_created,
        "regression_multiplier": float(regression_multiplier),
        "has_regression_alert": has_regression_alert,
        "alert": alert,
    }


def summarize_pipeline_benchmark(
    db_path: str,
    *,
    stage_aliases: dict[str, str] | None = None,
    regression_multiplier: float = 2.0,
) -> dict[str, Any]:
    """Consolida benchmark por etapa do ciclo M2 para uso no summary."""
    aliases = stage_aliases or _DEFAULT_BENCHMARK_STAGES

    stage_summaries: dict[str, dict[str, Any]] = {}
    alerts: list[dict[str, Any]] = []

    for stage_name, sample_stage in aliases.items():
        summary = summarize_stage_benchmark(
            db_path,
            stage=sample_stage,
            regression_multiplier=regression_multiplier,
        )
        if sample_stage != stage_name:
            summary["sample_stage"] = sample_stage
        stage_summaries[stage_name] = summary
        if summary.get("alert") is not None:
            alert = dict(summary["alert"])
            alert["benchmark_stage"] = stage_name
            alerts.append(alert)

    return {
        "status": "ok",
        "regression_multiplier": float(regression_multiplier),
        "stages": stage_summaries,
        "alerts": alerts,
        "has_regression_alerts": bool(alerts),
    }
