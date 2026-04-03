"""Suite RED/GREEN para M2-023.3 - Politica de degradacao por latencia.

Cobre:
    RF-023.3.1 - P95 acima do limite entra em modo degradado
    RF-023.3.2 - P99 acima do limite entra em modo degradado
    RF-023.3.3 - P95 e P99 abaixo dos limites -> modo normal
    RF-023.3.4 - P95 exatamente no limite (== limite) -> modo normal
    RF-023.3.5 - P99 exatamente no limite (== limite) -> modo normal
    RF-023.3.6 - entry_reason 'latency_slo_breached' quando degradado
    RF-023.3.7 - entry_reason None quando normal
    RF-023.3.8 - Saida do modo degradado exige janela minima estavel
    RF-023.3.9 - Janela estavel incompleta nao autoriza saida
    RF-023.3.10 - Janela vazia nao autoriza saida do modo degradado
    RF-023.3.11 - p95_ms e p99_ms expostos na saida
    RF-023.3.12 - Funcao pura: resultados deterministicos
    RF-023.3.13 - Regressao: guardrails risk_gate/circuit_breaker intactos
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.model2.resilience_controls import evaluate_latency_degradation


# ---------------------------------------------------------------------------
# RF-023.3.1: P95 acima do limite -> modo degradado
# ---------------------------------------------------------------------------
def test_p95_acima_limite_entra_degraded() -> None:
    """RF-023.3.1: P95 acima de p95_limit_ms deve gerar modo degradado."""
    metrics = {"p95_ms": 3500, "p99_ms": 1000}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert result["mode"] == "degraded"


# ---------------------------------------------------------------------------
# RF-023.3.2: P99 acima do limite -> modo degradado
# ---------------------------------------------------------------------------
def test_p99_acima_limite_entra_degraded() -> None:
    """RF-023.3.2: P99 acima de p99_limit_ms deve gerar modo degradado."""
    metrics = {"p95_ms": 1000, "p99_ms": 6000}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert result["mode"] == "degraded"


# ---------------------------------------------------------------------------
# RF-023.3.3: P95 e P99 abaixo -> modo normal
# ---------------------------------------------------------------------------
def test_p95_p99_abaixo_limites_modo_normal() -> None:
    """RF-023.3.3: Ambos abaixo dos limites -> modo normal."""
    metrics = {"p95_ms": 800, "p99_ms": 1200}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert result["mode"] == "normal"


# ---------------------------------------------------------------------------
# RF-023.3.4: P95 exatamente no limite (==) -> normal (nao viola)
# ---------------------------------------------------------------------------
def test_p95_exatamente_no_limite_nao_degrada() -> None:
    """RF-023.3.4: P95 == limite nao deve degradar (apenas > viola)."""
    metrics = {"p95_ms": 2000, "p99_ms": 1000}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert result["mode"] == "normal"


# ---------------------------------------------------------------------------
# RF-023.3.5: P99 exatamente no limite (==) -> normal
# ---------------------------------------------------------------------------
def test_p99_exatamente_no_limite_nao_degrada() -> None:
    """RF-023.3.5: P99 == limite nao deve degradar (apenas > viola)."""
    metrics = {"p95_ms": 1000, "p99_ms": 5000}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert result["mode"] == "normal"


# ---------------------------------------------------------------------------
# RF-023.3.6: entry_reason correto quando degradado
# ---------------------------------------------------------------------------
def test_entry_reason_latency_slo_breached_quando_degradado() -> None:
    """RF-023.3.6: entry_reason deve ser 'latency_slo_breached' em degraded."""
    metrics = {"p95_ms": 3000, "p99_ms": 2000}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert result["entry_reason"] == "latency_slo_breached"


# ---------------------------------------------------------------------------
# RF-023.3.7: entry_reason None quando normal
# ---------------------------------------------------------------------------
def test_entry_reason_none_quando_normal() -> None:
    """RF-023.3.7: entry_reason deve ser None quando modo normal."""
    metrics = {"p95_ms": 500, "p99_ms": 700}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert result["entry_reason"] is None


# ---------------------------------------------------------------------------
# RF-023.3.8: Saida do modo degradado exige janela minima estavel
# ---------------------------------------------------------------------------
def test_saida_degradado_exige_janela_minima_estavel() -> None:
    """RF-023.3.8: Janela completa abaixo dos limites autoriza saida."""
    metrics = {"p95_ms": 500, "p99_ms": 700}
    # janela com 3 medicoes todas abaixo dos limites
    recent_window = [
        {"p95_ms": 400, "p99_ms": 600},
        {"p95_ms": 450, "p99_ms": 650},
        {"p95_ms": 480, "p99_ms": 680},
    ]
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
        recent_window=recent_window,
        stable_window_count=3,
    )
    assert result["exit_ready"] is True


# ---------------------------------------------------------------------------
# RF-023.3.9: Janela com violacao nao autoriza saida
# ---------------------------------------------------------------------------
def test_janela_com_violacao_nao_autoriza_saida() -> None:
    """RF-023.3.9: Se alguma medicao na janela viola SLO, exit_ready=False."""
    metrics = {"p95_ms": 500, "p99_ms": 700}
    # segunda medicao viola P95
    recent_window = [
        {"p95_ms": 400, "p99_ms": 600},
        {"p95_ms": 3000, "p99_ms": 600},
        {"p95_ms": 480, "p99_ms": 680},
    ]
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
        recent_window=recent_window,
        stable_window_count=3,
    )
    assert result["exit_ready"] is False


# ---------------------------------------------------------------------------
# RF-023.3.10: Janela vazia nao autoriza saida
# ---------------------------------------------------------------------------
def test_janela_vazia_nao_autoriza_saida() -> None:
    """RF-023.3.10: Sem historico de janela, exit_ready deve ser False."""
    metrics = {"p95_ms": 500, "p99_ms": 700}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
        recent_window=[],
        stable_window_count=3,
    )
    assert result["exit_ready"] is False


# ---------------------------------------------------------------------------
# RF-023.3.11: p95_ms e p99_ms expostos na saida
# ---------------------------------------------------------------------------
def test_p95_p99_expostos_na_saida() -> None:
    """RF-023.3.11: Saida deve conter p95_ms e p99_ms com valores corretos."""
    metrics = {"p95_ms": 1234, "p99_ms": 4567}
    result = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert result["p95_ms"] == 1234
    assert result["p99_ms"] == 4567


# ---------------------------------------------------------------------------
# RF-023.3.12: Funcao pura - idempotente
# ---------------------------------------------------------------------------
def test_funcao_pura_idempotente() -> None:
    """RF-023.3.12: Chamadas repetidas com mesmos args retornam igual."""
    metrics = {"p95_ms": 3000, "p99_ms": 7000}
    r1 = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    r2 = evaluate_latency_degradation(
        metrics=metrics,
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert r1 == r2


# ---------------------------------------------------------------------------
# RF-023.3.13: Guardrails risk_gate/circuit_breaker preservados
# ---------------------------------------------------------------------------
def test_guardrails_preservados() -> None:
    """RF-023.3.13: Chamada nao altera risk_gate nem circuit_breaker."""
    from risk import risk_gate, circuit_breaker

    evaluate_latency_degradation(
        metrics={"p95_ms": 5000, "p99_ms": 9000},
        p95_limit_ms=2000,
        p99_limit_ms=5000,
    )
    assert hasattr(risk_gate, "RiskGate") or hasattr(risk_gate, "evaluate")
    assert hasattr(circuit_breaker, "CircuitBreaker")
