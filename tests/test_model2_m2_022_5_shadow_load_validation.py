"""Suite RED M2-022.5: validacao de carga shadow com 40 simbolos.

Objetivo:
- R1: validar cenario de carga em shadow sem ordem real
- R2: validar limite de latencia P95 <= 1.5x P50 baseline
- R3: validar sucesso de episodios >= 99.5%
- R4: validar drift de reconciliacao <= 0.01%
- R5: validar timeout/categoria de erro com correlacao decision_id
- R6: validar isolamento de risco por contexto operacional

Esta suite deve falhar na fase RED antes da implementacao GREEN.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _SymbolMetrics:
    symbol: str
    p50_ms: float
    p95_ms: float
    episodes_total: int
    episodes_success: int
    reconciliation_drift_pct: float


def _build_40_symbol_metrics(
    *,
    p50_ms: float = 100.0,
    p95_ms: float = 140.0,
    drift_pct: float = 0.005,
    episodes_total: int = 2000,
    episodes_success: int = 1995,
) -> list[_SymbolMetrics]:
    return [
        _SymbolMetrics(
            symbol=f"SYM{i:02d}USDT",
            p50_ms=p50_ms,
            p95_ms=p95_ms,
            episodes_total=episodes_total,
            episodes_success=episodes_success,
            reconciliation_drift_pct=drift_pct,
        )
        for i in range(40)
    ]


def test_shadow_load_40_symbols_5m_returns_shadow_only_report() -> None:
    """R1: carga com 40 simbolos/5m deve gerar relatorio em modo shadow."""
    from core.model2.shadow_load_validation import run_shadow_load_validation

    report = run_shadow_load_validation(
        symbols=[f"SYM{i:02d}USDT" for i in range(40)],
        duration_seconds=300,
        mode="shadow",
    )

    assert report["mode"] == "shadow"
    assert report["symbols_processed"] == 40
    assert report["live_orders_sent"] == 0


def test_shadow_load_p95_within_150pct_of_baseline_marks_latency_ok() -> None:
    """R2: P95 <= 1.5x P50 baseline deve marcar latencia como aderente."""
    from core.model2.shadow_load_validation import evaluate_latency_slo

    metrics = _build_40_symbol_metrics(p50_ms=100.0, p95_ms=149.9)
    result = evaluate_latency_slo(metrics=metrics, max_p95_over_p50_ratio=1.5)

    assert result["latency_ok"] is True
    assert result["max_ratio_observed"] <= 1.5


def test_shadow_load_episode_success_rate_above_995_marks_pass() -> None:
    """R3: sucesso de episodios >= 99.5% deve passar no gate."""
    from core.model2.shadow_load_validation import evaluate_episode_success_slo

    metrics = _build_40_symbol_metrics(episodes_total=2000, episodes_success=1995)
    result = evaluate_episode_success_slo(metrics=metrics, min_success_rate=0.995)

    assert result["episode_success_ok"] is True
    assert result["success_rate"] >= 0.995


def test_shadow_load_reconciliation_drift_within_001pct_marks_pass() -> None:
    """R4: drift <= 0.01% deve manter reconciliacao como aderente."""
    from core.model2.shadow_load_validation import evaluate_reconciliation_drift_slo

    metrics = _build_40_symbol_metrics(drift_pct=0.01)
    result = evaluate_reconciliation_drift_slo(metrics=metrics, max_drift_pct=0.01)

    assert result["reconciliation_ok"] is True
    assert result["max_drift_pct_observed"] <= 0.01


def test_timeout_error_is_classified_with_decision_id_context() -> None:
    """R5: timeout deve ser classificado com categoria e decision_id."""
    from core.model2.shadow_load_validation import classify_operational_error

    error = classify_operational_error(
        source="api",
        error_kind="timeout",
        decision_id=12345,
        execution_id=987,
    )

    assert error["category"] == "transient"
    assert error["reason_code"] == "timeout"
    assert error["decision_id"] == 12345


def test_context_isolation_blocks_live_keys_in_shadow_mode() -> None:
    """R6: contexto shadow nao pode aceitar credenciais live."""
    from core.model2.shadow_load_validation import validate_risk_context_isolation

    result = validate_risk_context_isolation(
        execution_mode="shadow",
        has_live_api_key=True,
        has_paper_api_key=False,
    )

    assert result["allowed"] is False
    assert result["reason_code"] == "risk_context_isolation_blocked"


def test_integration_shadow_load_builds_consolidated_report_from_metrics() -> None:
    """Integracao: consolidar latencia, episodios e drift em relatorio unico."""
    from core.model2.shadow_load_validation import build_shadow_load_report

    metrics = _build_40_symbol_metrics()
    report = build_shadow_load_report(
        metrics=metrics,
        duration_seconds=300,
        mode="shadow",
        baseline_p50_ms=100.0,
    )

    assert report["symbols_processed"] == 40
    assert "latency" in report
    assert "episodes" in report
    assert "reconciliation" in report


def test_regression_risk_guardrails_are_declared_active_in_report() -> None:
    """Regressao/risk: relatorio deve declarar guardrails ativos."""
    from core.model2.shadow_load_validation import build_shadow_load_report

    metrics = _build_40_symbol_metrics()
    report = build_shadow_load_report(
        metrics=metrics,
        duration_seconds=300,
        mode="shadow",
        baseline_p50_ms=100.0,
    )

    guardrails = report["guardrails"]
    assert guardrails["risk_gate"] == "ATIVO"
    assert guardrails["circuit_breaker"] == "ATIVO"
    assert guardrails["decision_id"] == "IDEMPOTENTE"
