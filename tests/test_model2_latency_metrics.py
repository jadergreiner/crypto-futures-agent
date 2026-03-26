"""Testes RED — BLID-086: metricas de latencia em decisao e execucao.

Cobre:
- record_latency persiste sample em m2_latency_samples
- compute_percentiles retorna P50/P95/P99 corretos
- detect_latency_violations detecta P95 > 2s e P99 > 5s
- record_cycle_latencies extrai elapsed_ms do summary e persiste por etapa

Todos os testes devem FALHAR (RED) antes da implementacao.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


def _make_db() -> tuple[str, sqlite3.Connection]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.commit()
    return tmp.name, conn


# ---------------------------------------------------------------------------
# Classe 1 — record_latency
# ---------------------------------------------------------------------------

class TestRecordLatency:
    """record_latency deve persistir sample em m2_latency_samples."""

    def test_record_creates_table_and_inserts_row(self) -> None:
        from core.model2.latency_metrics import record_latency

        db_path, conn = _make_db()
        conn.close()

        record_latency(db_path, stage="scan", elapsed_ms=150)

        with sqlite3.connect(db_path) as c:
            row = c.execute(
                "SELECT stage, elapsed_ms FROM m2_latency_samples ORDER BY id DESC LIMIT 1"
            ).fetchone()
        assert row is not None
        assert row[0] == "scan"
        assert row[1] == 150

    def test_record_multiple_stages(self) -> None:
        from core.model2.latency_metrics import record_latency

        db_path, conn = _make_db()
        conn.close()

        record_latency(db_path, stage="scan", elapsed_ms=100)
        record_latency(db_path, stage="validate", elapsed_ms=200)
        record_latency(db_path, stage="execute", elapsed_ms=300)

        with sqlite3.connect(db_path) as c:
            count = c.execute("SELECT COUNT(*) FROM m2_latency_samples").fetchone()[0]
        assert count == 3


# ---------------------------------------------------------------------------
# Classe 2 — compute_percentiles
# ---------------------------------------------------------------------------

class TestComputePercentiles:
    """compute_percentiles deve retornar P50/P95/P99 corretos."""

    def test_percentiles_from_known_values(self) -> None:
        from core.model2.latency_metrics import compute_percentiles

        # 10 amostras: 100, 200, ..., 1000
        samples = [i * 100 for i in range(1, 11)]

        result = compute_percentiles(samples)

        assert "p50" in result
        assert "p95" in result
        assert "p99" in result
        assert result["p50"] == pytest.approx(550, abs=50)  # mediana de 100-1000
        assert result["p95"] >= result["p50"]
        assert result["p99"] >= result["p95"]

    def test_percentiles_empty_list_returns_zeros(self) -> None:
        from core.model2.latency_metrics import compute_percentiles

        result = compute_percentiles([])

        assert result["p50"] == 0
        assert result["p95"] == 0
        assert result["p99"] == 0


# ---------------------------------------------------------------------------
# Classe 3 — detect_latency_violations
# ---------------------------------------------------------------------------

class TestDetectLatencyViolations:
    """Detectar P95 > 2000ms ou P99 > 5000ms."""

    def test_p95_violation_when_above_threshold(self) -> None:
        from core.model2.latency_metrics import detect_latency_violations

        # P95 alto
        violations = detect_latency_violations(
            {"p50": 500, "p95": 2500, "p99": 3000},
            stage="execute",
        )

        assert len(violations) >= 1
        assert any("p95" in v.get("metric", "") for v in violations)

    def test_p99_violation_when_above_threshold(self) -> None:
        from core.model2.latency_metrics import detect_latency_violations

        violations = detect_latency_violations(
            {"p50": 1000, "p95": 1500, "p99": 6000},
            stage="execute",
        )

        assert len(violations) >= 1
        assert any("p99" in v.get("metric", "") for v in violations)

    def test_no_violation_when_within_bounds(self) -> None:
        from core.model2.latency_metrics import detect_latency_violations

        violations = detect_latency_violations(
            {"p50": 100, "p95": 500, "p99": 900},
            stage="scan",
        )

        assert violations == []


# ---------------------------------------------------------------------------
# Classe 4 — record_cycle_latencies
# ---------------------------------------------------------------------------

class TestRecordCycleLatencies:
    """record_cycle_latencies deve extrair elapsed_ms do summary e persistir."""

    def test_extracts_stage_elapsed_from_summary(self) -> None:
        from core.model2.latency_metrics import record_cycle_latencies

        db_path, conn = _make_db()
        conn.close()

        summary = {
            "stages": {
                "sync_tf": {"stage_elapsed_ms": 120},
                "daily_pipeline": {"stage_elapsed_ms": 450},
                "live_cycle": {"stage_elapsed_ms": 800},
            }
        }

        record_cycle_latencies(db_path, cycle_summary=summary)

        with sqlite3.connect(db_path) as c:
            rows = c.execute(
                "SELECT stage, elapsed_ms FROM m2_latency_samples ORDER BY stage"
            ).fetchall()

        stages = {r[0]: r[1] for r in rows}
        assert "sync_tf" in stages
        assert stages["sync_tf"] == 120

    def test_missing_stages_do_not_raise(self) -> None:
        from core.model2.latency_metrics import record_cycle_latencies

        db_path, conn = _make_db()
        conn.close()

        # Summary sem stages
        record_cycle_latencies(db_path, cycle_summary={"status": "ok"})

        with sqlite3.connect(db_path) as c:
            count = c.execute("SELECT COUNT(*) FROM m2_latency_samples").fetchone()[0]
        assert count == 0
