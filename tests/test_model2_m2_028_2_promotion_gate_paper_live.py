"""Suite M2-028.2: Contrato de promocao GO/NO-GO paper→live."""

from __future__ import annotations

import pytest

from core.model2.promotion_gate import (
    LivePromotionConfig,
    LivePromotionResult,
    PromotionEvaluator,
    is_preflight_compatible_for_live,
)


def test_paper_to_live_go_when_all_criteria_and_manual_approval_met() -> None:
    evaluator = PromotionEvaluator(
        live_config=LivePromotionConfig(
            min_sharpe_ratio=1.0,
            min_reconciliation_rate=0.99,
            max_critical_errors=0,
        )
    )

    result = evaluator.evaluate_paper_to_live(
        sharpe_ratio=1.2,
        reconciliation_rate=0.995,
        critical_errors=0,
        manual_approved=True,
        approver_id="tl-01",
        approval_justification="janela estavel",
    )

    assert result.go is True
    assert result.reasons == []
    assert result.rollback_to_paper is False


def test_paper_to_live_no_go_when_sharpe_below_threshold() -> None:
    result = PromotionEvaluator().evaluate_paper_to_live(
        sharpe_ratio=0.5,
        reconciliation_rate=1.0,
        critical_errors=0,
        manual_approved=True,
        approver_id="tl-01",
        approval_justification="ok",
    )
    assert result.go is False
    assert any("sharpe_ratio" in item for item in result.reasons)


def test_paper_to_live_no_go_when_reconciliation_rate_below_threshold() -> None:
    result = PromotionEvaluator().evaluate_paper_to_live(
        sharpe_ratio=2.0,
        reconciliation_rate=0.80,
        critical_errors=0,
        manual_approved=True,
        approver_id="tl-01",
        approval_justification="ok",
    )
    assert result.go is False
    assert any("reconciliation_rate" in item for item in result.reasons)


def test_paper_to_live_no_go_when_critical_errors_present() -> None:
    result = PromotionEvaluator().evaluate_paper_to_live(
        sharpe_ratio=2.0,
        reconciliation_rate=1.0,
        critical_errors=1,
        manual_approved=True,
        approver_id="tl-01",
        approval_justification="ok",
    )
    assert result.go is False
    assert any("critical_errors" in item for item in result.reasons)


def test_paper_to_live_no_go_when_manual_approval_missing() -> None:
    result = PromotionEvaluator().evaluate_paper_to_live(
        sharpe_ratio=2.0,
        reconciliation_rate=1.0,
        critical_errors=0,
        manual_approved=False,
        approver_id=None,
        approval_justification=None,
    )
    assert result.go is False
    assert "manual_approval_required" in result.reasons


def test_paper_to_live_manual_approval_requires_approver_and_justification() -> None:
    result = PromotionEvaluator().evaluate_paper_to_live(
        sharpe_ratio=2.0,
        reconciliation_rate=1.0,
        critical_errors=0,
        manual_approved=True,
        approver_id="",
        approval_justification="",
    )
    assert result.go is False
    assert "approver_id_required" in result.reasons
    assert "approval_justification_required" in result.reasons


def test_paper_to_live_sets_rollback_flag_on_post_promotion_critical_event() -> None:
    result = PromotionEvaluator().evaluate_paper_to_live(
        sharpe_ratio=2.0,
        reconciliation_rate=1.0,
        critical_errors=0,
        manual_approved=True,
        approver_id="tl-01",
        approval_justification="ok",
        post_promotion_critical_event=True,
    )
    assert result.go is False
    assert result.rollback_to_paper is True
    assert "post_promotion_critical_event_detected" in result.reasons


def test_paper_to_live_result_is_frozen() -> None:
    result = LivePromotionResult(
        go=True,
        reasons=[],
        sharpe_ratio=1.5,
        reconciliation_rate=1.0,
        critical_errors=0,
        manual_approved=True,
        approver_id="qa",
        approval_justification="ok",
        rollback_to_paper=False,
        evaluated_at="2026-03-26T00:00:00+00:00",
    )

    with pytest.raises((AttributeError, TypeError)):
        result.go = False  # type: ignore[misc]


def test_preflight_compatibility_requires_status_ok() -> None:
    assert is_preflight_compatible_for_live({"status": "ok"}) is True
    assert is_preflight_compatible_for_live({"status": "alert"}) is False
    assert is_preflight_compatible_for_live({}) is False

