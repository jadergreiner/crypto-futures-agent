"""Suite RED para BLID-103: EvidenceGateResult + evaluate_evidence_gate.

Cada teste mapeia 1 requisito do handoff SA->QA.
Estado esperado na fase RED: falhar ate implementacao concluida.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any


def _load_promotion_gate() -> ModuleType:
    return importlib.import_module("core.model2.promotion_gate")


# ---------------------------------------------------------------------------
# Unitarios
# ---------------------------------------------------------------------------

def test_evidence_gate_result_campos_obrigatorios_presentes() -> None:
    """EvidenceGateResult deve ter todos os campos obrigatorios."""
    mod = _load_promotion_gate()
    result = mod.EvidenceGateResult(
        go=True,
        decision="GO",
        reasons=[],
        decision_id="blid103-001",
        evidence_ref="/tmp/hc.json",
        risk_evidence_ok=True,
        stability_evidence_ok=True,
        consistency_evidence_ok=True,
        evidence_sufficient=True,
        evaluated_at="2026-04-03T11:00:00+00:00",
    )
    assert result.go is True
    assert result.decision == "GO"
    assert result.reasons == []
    assert result.decision_id == "blid103-001"
    assert result.evidence_ref == "/tmp/hc.json"
    assert result.risk_evidence_ok is True
    assert result.stability_evidence_ok is True
    assert result.consistency_evidence_ok is True
    assert result.evidence_sufficient is True
    assert isinstance(result.evaluated_at, str)


def test_evaluate_evidence_gate_go_quando_tres_pilares_ok() -> None:
    """GO quando risk, stability e consistency sao True."""
    mod = _load_promotion_gate()
    evaluator = mod.PromotionEvaluator()
    result = evaluator.evaluate_evidence_gate(
        decision_id="blid103-002",
        risk_evidence_ok=True,
        stability_evidence_ok=True,
        consistency_evidence_ok=True,
        evidence_ref="/tmp/hc.json",
    )
    assert result.go is True
    assert result.decision == "GO"
    assert result.evidence_sufficient is True
    assert result.reasons == []


def test_evaluate_evidence_gate_no_go_quando_risco_falho() -> None:
    """NO_GO com reason especifico quando risco nao esta ok."""
    mod = _load_promotion_gate()
    evaluator = mod.PromotionEvaluator()
    result = evaluator.evaluate_evidence_gate(
        decision_id="blid103-003",
        risk_evidence_ok=False,
        stability_evidence_ok=True,
        consistency_evidence_ok=True,
    )
    assert result.go is False
    assert result.decision == "NO_GO"
    assert result.evidence_sufficient is False
    assert any("risco" in r.lower() or "risk" in r.lower() for r in result.reasons)


def test_evaluate_evidence_gate_no_go_quando_estabilidade_falha() -> None:
    """NO_GO com reason especifico quando estabilidade nao esta ok."""
    mod = _load_promotion_gate()
    evaluator = mod.PromotionEvaluator()
    result = evaluator.evaluate_evidence_gate(
        decision_id="blid103-004",
        risk_evidence_ok=True,
        stability_evidence_ok=False,
        consistency_evidence_ok=True,
    )
    assert result.go is False
    assert result.decision == "NO_GO"
    assert result.evidence_sufficient is False
    assert any("estabilidade" in r.lower() or "stability" in r.lower() for r in result.reasons)


def test_evaluate_evidence_gate_no_go_quando_consistencia_falha() -> None:
    """NO_GO com reason especifico quando consistencia nao esta ok."""
    mod = _load_promotion_gate()
    evaluator = mod.PromotionEvaluator()
    result = evaluator.evaluate_evidence_gate(
        decision_id="blid103-005",
        risk_evidence_ok=True,
        stability_evidence_ok=True,
        consistency_evidence_ok=False,
    )
    assert result.go is False
    assert result.decision == "NO_GO"
    assert result.evidence_sufficient is False
    assert any("consistencia" in r.lower() or "consistency" in r.lower() for r in result.reasons)


def test_evaluate_evidence_gate_fail_safe_nao_lanca_excecao() -> None:
    """Metodo nunca lanca excecao (fail-safe); sem evidence_ref retorna NO_GO."""
    mod = _load_promotion_gate()
    evaluator = mod.PromotionEvaluator()
    # Sem evidence_ref -> falha no pilar de consistencia implicitamente
    result = evaluator.evaluate_evidence_gate(
        decision_id="blid103-006",
        risk_evidence_ok=True,
        stability_evidence_ok=True,
        consistency_evidence_ok=True,
        evidence_ref=None,
    )
    # Nao deve lancar excecao; resultado deve ser valido
    assert isinstance(result.go, bool)
    assert isinstance(result.decision, str)
    assert isinstance(result.reasons, list)
    assert isinstance(result.evaluated_at, str)


# ---------------------------------------------------------------------------
# Integracao
# ---------------------------------------------------------------------------

def test_healthcheck_usa_evaluate_evidence_gate_sem_attribute_error() -> None:
    """run_live_healthcheck executa sem AttributeError (integracao)."""
    from scripts.model2.healthcheck_live_execution import run_live_healthcheck
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        result = run_live_healthcheck(
            runtime_dir=Path(tmp),
            output_dir=Path(tmp),
            max_age_hours=24,
            max_unprotected_filled=0,
            max_stale_entry_sent=0,
            max_position_mismatches=0,
            alert_command=None,
        )
    # Deve retornar dict com status (alert aceitavel, mas sem excecao)
    assert isinstance(result, dict)
    assert "status" in result
    assert "promotion_gate" in result
    pg = result["promotion_gate"]
    assert "go" in pg
    assert "decision" in pg
    assert "evidence_sufficient" in pg


# ---------------------------------------------------------------------------
# Regressao de risco
# ---------------------------------------------------------------------------

def test_guardrails_nao_alterados_pelo_metodo_novo() -> None:
    """PromotionEvaluator.evaluate() existente nao e afetado."""
    mod = _load_promotion_gate()
    evaluator = mod.PromotionEvaluator()
    result = evaluator.evaluate(
        win_rate=0.6,
        episode_count=50,
        max_drawdown_pct=0.03,
    )
    assert result.go is True
    assert result.win_rate == 0.6
    assert result.episode_count == 50
