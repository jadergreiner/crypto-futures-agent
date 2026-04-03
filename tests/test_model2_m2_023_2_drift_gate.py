"""Suite RED/GREEN para M2-023.2 - Gate de drift de posicao em tempo real.

Cobre:
    RF-023.2.1 - Drift alto bloqueia admissao com reason_code auditavel
    RF-023.2.2 - Drift abaixo do limiar permite admissao (allow=True)
    RF-023.2.3 - Drift zero (sem divergencia) nao bloqueia
    RF-023.2.4 - decision_id preservado na saida (idempotencia)
    RF-023.2.5 - drift_pct calculado e exposto na saida
    RF-023.2.6 - Reason_code None quando permitido
    RF-023.2.7 - Regressao de risco: guardrails risk_gate/CB preservados
    RF-023.2.8 - Funcao pura: chamadas repetidas produzem mesmo resultado
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# RF-023.2.1: drift alto (40%) acima de threshold (20%) -> bloqueia
def test_drift_alto_bloqueia_com_reason_code() -> None:
    """RF-023.2.1: drift 40% > threshold 20% deve bloquear admissao."""
    from core.model2.resilience_controls import evaluate_position_drift_gate

    current = {"position_qty": 1.0, "entry_price": 100.0}
    observed = {"position_qty": 1.4, "entry_price": 100.0}

    result = evaluate_position_drift_gate(
        current_state=current,
        observed_state=observed,
        threshold_pct=0.2,
        decision_id=101,
    )

    assert result["allow"] is False
    assert result["reason_code"] == "position_drift_blocked"


# RF-023.2.2: drift baixo (10%) abaixo de threshold (20%) -> permite
def test_drift_baixo_permite_admissao() -> None:
    """RF-023.2.2: drift 10% < threshold 20% deve permitir admissao."""
    from core.model2.resilience_controls import evaluate_position_drift_gate

    current = {"position_qty": 1.0, "entry_price": 100.0}
    observed = {"position_qty": 1.1, "entry_price": 100.0}

    result = evaluate_position_drift_gate(
        current_state=current,
        observed_state=observed,
        threshold_pct=0.2,
        decision_id=202,
    )

    assert result["allow"] is True


# RF-023.2.3: drift zero (estados identicos) nao bloqueia
def test_drift_zero_nao_bloqueia() -> None:
    """RF-023.2.3: estados identicos => drift zero => nao bloqueia."""
    from core.model2.resilience_controls import evaluate_position_drift_gate

    state = {"position_qty": 2.0, "entry_price": 50000.0}

    result = evaluate_position_drift_gate(
        current_state=state,
        observed_state=state,
        threshold_pct=0.05,
        decision_id=303,
    )

    assert result["allow"] is True
    assert result["drift_pct"] == 0.0


# RF-023.2.4: decision_id e preservado na saida para rastreabilidade
def test_decision_id_preservado_na_saida() -> None:
    """RF-023.2.4: decision_id deve aparecer igual na saida."""
    from core.model2.resilience_controls import evaluate_position_drift_gate

    current = {"position_qty": 1.0}
    observed = {"position_qty": 2.0}

    result = evaluate_position_drift_gate(
        current_state=current,
        observed_state=observed,
        threshold_pct=0.5,
        decision_id=999,
    )

    assert result["decision_id"] == 999


# RF-023.2.5: drift_pct calculado e exposto na saida
def test_drift_pct_calculado_e_exposto() -> None:
    """RF-023.2.5: drift_pct deve ser calculado corretamente."""
    from core.model2.resilience_controls import evaluate_position_drift_gate

    current = {"position_qty": 1.0}
    observed = {"position_qty": 1.3}

    result = evaluate_position_drift_gate(
        current_state=current,
        observed_state=observed,
        threshold_pct=0.5,
        decision_id=404,
    )

    assert "drift_pct" in result
    drift = float(result["drift_pct"])  # type: ignore[arg-type]
    assert abs(drift - 0.3) < 1e-9


# RF-023.2.6: reason_code None quando admissao permitida
def test_reason_code_none_quando_permitido() -> None:
    """RF-023.2.6: reason_code deve ser None quando allow=True."""
    from core.model2.resilience_controls import evaluate_position_drift_gate

    current = {"position_qty": 1.0}
    observed = {"position_qty": 1.05}

    result = evaluate_position_drift_gate(
        current_state=current,
        observed_state=observed,
        threshold_pct=0.2,
        decision_id=505,
    )

    assert result["allow"] is True
    assert result["reason_code"] is None


# RF-023.2.7: guardrails risk_gate/circuit_breaker preservados
def test_guardrails_preservados() -> None:
    """RF-023.2.7: importar e chamar funcao nao altera risk_gate nem CB."""
    from risk import risk_gate, circuit_breaker
    from core.model2.resilience_controls import evaluate_position_drift_gate

    evaluate_position_drift_gate(
        current_state={"position_qty": 1.0},
        observed_state={"position_qty": 1.5},
        threshold_pct=0.2,
        decision_id=606,
    )

    assert hasattr(risk_gate, "RiskGate") or hasattr(risk_gate, "evaluate")
    assert hasattr(circuit_breaker, "CircuitBreaker")


# RF-023.2.8: funcao pura - chamadas repetidas com mesmos args produzem mesmo resultado
def test_funcao_pura_idempotente() -> None:
    """RF-023.2.8: funcao pura - resultados deterministicos."""
    from core.model2.resilience_controls import evaluate_position_drift_gate

    current = {"position_qty": 1.0}
    observed = {"position_qty": 1.4}

    r1 = evaluate_position_drift_gate(
        current_state=current,
        observed_state=observed,
        threshold_pct=0.2,
        decision_id=707,
    )
    r2 = evaluate_position_drift_gate(
        current_state=current,
        observed_state=observed,
        threshold_pct=0.2,
        decision_id=707,
    )

    assert r1 == r2
