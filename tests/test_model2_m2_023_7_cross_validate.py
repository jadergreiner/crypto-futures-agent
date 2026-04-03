"""Suite RED/GREEN para M2-023.7 - Validacao cruzada de sinais antes da ordem.

Cobre:
    RF-023.7.1  - Sinal LONG + tendencia DOWN bloqueia com reason_code
    RF-023.7.2  - Sinal SHORT + tendencia UP bloqueia com reason_code
    RF-023.7.3  - Sinal LONG + tendencia UP permite admissao
    RF-023.7.4  - Sinal SHORT + tendencia DOWN permite admissao
    RF-023.7.5  - Posicao aberta na mesma direcao bloqueia (double-exposure)
    RF-023.7.6  - Posicao aberta em direcao oposta nao bloqueia por este gate
    RF-023.7.7  - decision_id presente e auditavel no resultado
    RF-023.7.8  - Resultado deterministico: mesmas entradas, mesma saida
    RF-023.7.9  - Cobertura de fallback: campos ausentes nao causam excecao
    RF-023.7.10 - Regressao de risco: guardrails risk_gate/CB preservados
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# RF-023.7.1 - LONG + DOWN bloqueia
# ---------------------------------------------------------------------------
def test_long_tendencia_down_bloqueia_com_reason_code() -> None:
    """RF-023.7.1: sinal LONG + contexto DOWN deve bloquear admissao."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    result = cross_validate_signal_context_position(
        signal={"side": "LONG", "confidence": 0.85},
        context={"trend": "DOWN"},
        position={"is_open": False},
        decision_id=1001,
    )

    assert result["allow"] is False, "LONG + DOWN deve ser bloqueado"
    assert result["reason_code"] is not None, "reason_code deve estar presente"
    assert "conflict" in str(result["reason_code"]).lower(), (
        f"reason_code deve indicar conflito, obteve: {result['reason_code']}"
    )


# ---------------------------------------------------------------------------
# RF-023.7.2 - SHORT + UP bloqueia
# ---------------------------------------------------------------------------
def test_short_tendencia_up_bloqueia_com_reason_code() -> None:
    """RF-023.7.2: sinal SHORT + contexto UP deve bloquear admissao."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    result = cross_validate_signal_context_position(
        signal={"side": "SHORT", "confidence": 0.90},
        context={"trend": "UP"},
        position={"is_open": False},
        decision_id=1002,
    )

    assert result["allow"] is False, "SHORT + UP deve ser bloqueado"
    assert result["reason_code"] is not None


# ---------------------------------------------------------------------------
# RF-023.7.3 - LONG + UP permite
# ---------------------------------------------------------------------------
def test_long_tendencia_up_permite_admissao() -> None:
    """RF-023.7.3: sinal LONG + contexto UP deve permitir admissao."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    result = cross_validate_signal_context_position(
        signal={"side": "LONG", "confidence": 0.80},
        context={"trend": "UP"},
        position={"is_open": False},
        decision_id=1003,
    )

    assert result["allow"] is True, "LONG + UP deve ser permitido"
    assert result["reason_code"] is None, "reason_code deve ser None quando permitido"


# ---------------------------------------------------------------------------
# RF-023.7.4 - SHORT + DOWN permite
# ---------------------------------------------------------------------------
def test_short_tendencia_down_permite_admissao() -> None:
    """RF-023.7.4: sinal SHORT + contexto DOWN deve permitir admissao."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    result = cross_validate_signal_context_position(
        signal={"side": "SHORT", "confidence": 0.75},
        context={"trend": "DOWN"},
        position={"is_open": False},
        decision_id=1004,
    )

    assert result["allow"] is True, "SHORT + DOWN deve ser permitido"
    assert result["reason_code"] is None


# ---------------------------------------------------------------------------
# RF-023.7.5 - Posicao aberta mesma direcao bloqueia (double-exposure)
# ---------------------------------------------------------------------------
def test_posicao_aberta_mesma_direcao_bloqueia_double_exposure() -> None:
    """RF-023.7.5: posicao LONG ja aberta + novo sinal LONG deve bloquear."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    result = cross_validate_signal_context_position(
        signal={"side": "LONG", "confidence": 0.80},
        context={"trend": "UP"},
        position={"is_open": True, "side": "LONG"},
        decision_id=1005,
    )

    assert result["allow"] is False, (
        "Posicao LONG aberta + sinal LONG deve bloquear double-exposure"
    )
    assert result["reason_code"] == "position_already_open", (
        f"Esperado 'position_already_open', obteve: {result.get('reason_code')}"
    )


# ---------------------------------------------------------------------------
# RF-023.7.6 - Posicao aberta direcao oposta nao bloqueia por este gate
# ---------------------------------------------------------------------------
def test_posicao_aberta_direcao_oposta_nao_bloqueia_por_este_gate() -> None:
    """RF-023.7.6: posicao SHORT aberta + sinal LONG (invertendo) nao bloqueia."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    result = cross_validate_signal_context_position(
        signal={"side": "LONG", "confidence": 0.80},
        context={"trend": "UP"},
        position={"is_open": True, "side": "SHORT"},
        decision_id=1006,
    )

    # Neste gate, inversao de posicao e decisao do order_layer, nao aqui
    assert result["allow"] is True, (
        "Posicao SHORT aberta + sinal LONG (inversao) deve ser permitida por este gate"
    )


# ---------------------------------------------------------------------------
# RF-023.7.7 - decision_id presente e auditavel no resultado
# ---------------------------------------------------------------------------
def test_decision_id_presente_no_resultado() -> None:
    """RF-023.7.7: resultado deve expor decision_id para auditabilidade."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    result = cross_validate_signal_context_position(
        signal={"side": "LONG", "confidence": 0.80},
        context={"trend": "UP"},
        position={"is_open": False},
        decision_id=9999,
    )

    assert "decision_id" in result, "Campo decision_id ausente no resultado"
    assert result["decision_id"] == 9999, (
        f"decision_id deve ser 9999, obteve: {result.get('decision_id')}"
    )


# ---------------------------------------------------------------------------
# RF-023.7.8 - Resultado deterministico (mesmas entradas, mesma saida)
# ---------------------------------------------------------------------------
def test_resultado_deterministico_funcao_pura() -> None:
    """RF-023.7.8: funcao pura - mesmas entradas sempre produzem mesmo resultado."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    kwargs = dict(
        signal={"side": "SHORT", "confidence": 0.70},
        context={"trend": "UP"},
        position={"is_open": False},
        decision_id=777,
    )

    result_a = cross_validate_signal_context_position(**kwargs)
    result_b = cross_validate_signal_context_position(**kwargs)

    assert result_a == result_b, (
        "Funcao deve ser pura: mesmas entradas devem produzir mesmo resultado"
    )


# ---------------------------------------------------------------------------
# RF-023.7.9 - Fallback conservador: campos ausentes nao causam excecao
# ---------------------------------------------------------------------------
def test_campos_ausentes_nao_causam_excecao() -> None:
    """RF-023.7.9: dicts vazios nao devem gerar excecao (fail-safe)."""
    from core.model2.resilience_controls import cross_validate_signal_context_position

    try:
        result = cross_validate_signal_context_position(
            signal={},
            context={},
            position={},
            decision_id=0,
        )
        assert isinstance(result, dict), "Resultado deve ser dict mesmo com campos vazios"
        assert "allow" in result, "Campo 'allow' deve estar presente"
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"Funcao nao deve lancar excecao com campos ausentes: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# RF-023.7.10 - Regressao de risco: risk_gate e circuit_breaker preservados
# ---------------------------------------------------------------------------
def test_guardrails_risk_gate_circuit_breaker_preservados() -> None:
    """RF-023.7.10: importar e chamar funcao nao altera risk_gate nem CB."""
    from risk import risk_gate, circuit_breaker  # type: ignore[import]
    from core.model2.resilience_controls import cross_validate_signal_context_position

    rg_before = id(risk_gate)
    cb_before = id(circuit_breaker)

    cross_validate_signal_context_position(
        signal={"side": "LONG"},
        context={"trend": "DOWN"},
        position={"is_open": False},
        decision_id=42,
    )

    assert id(risk_gate) == rg_before, "risk_gate nao deve ser alterado"
    assert id(circuit_breaker) == cb_before, "circuit_breaker nao deve ser alterado"
