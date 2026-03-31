"""Suite M2-028.2: Contrato de promocao GO/NO-GO paper→live."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import cast

import pytest

from core.model2.promotion_gate import (
    LivePromotionConfig,
    LivePromotionResult,
    PromotionEvaluator,
    is_preflight_compatible_for_live,
)
from scripts.model2.migrate import run_up


@pytest.fixture()
def model2_db(tmp_path: Path) -> str:
    db_path = tmp_path / "modelo2_test.db"
    output_dir = tmp_path / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return str(db_path)


def _fetch_promotion_row(db_path: str, decision_id: str) -> sqlite3.Row:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM promotion_history WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    assert row is not None
    return cast(sqlite3.Row, row)


def test_paper_to_live_go_when_all_criteria_and_manual_approval_met(
    model2_db: str,
) -> None:
    evaluator = PromotionEvaluator(
        live_config=LivePromotionConfig(
            min_sharpe_ratio=1.0,
            min_reconciliation_rate=0.99,
            max_critical_errors=0,
        ),
        model2_db_path=model2_db,
    )

    result = evaluator.evaluate_paper_to_live(
        decision_id="m2-028-2-go-001",
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

    row = _fetch_promotion_row(model2_db, "m2-028-2-go-001")
    assert row["go_no_go"] == "GO"
    assert row["manual_approved"] == 1
    assert row["approver_id"] == "tl-01"
    assert row["approval_justification"] == "janela estavel"
    assert row["rollback_to_paper"] == 0
    assert row["event_type"] == "EVALUATION"


def test_paper_to_live_no_go_when_sharpe_below_threshold(model2_db: str) -> None:
    result = PromotionEvaluator(model2_db_path=model2_db).evaluate_paper_to_live(
        decision_id="m2-028-2-no-go-sharpe",
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
        decision_id="m2-028-2-no-go-reconciliation",
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
        decision_id="m2-028-2-no-go-critical-errors",
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
        decision_id="m2-028-2-no-go-manual",
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
        decision_id="m2-028-2-manual-fields",
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


def test_paper_to_live_sets_rollback_flag_on_post_promotion_critical_event(
    model2_db: str,
) -> None:
    result = PromotionEvaluator(model2_db_path=model2_db).evaluate_paper_to_live(
        decision_id="m2-028-2-rollback-001",
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

    row = _fetch_promotion_row(model2_db, "m2-028-2-rollback-001")
    assert row["go_no_go"] == "NO_GO"
    assert row["rollback_to_paper"] == 1
    assert row["event_type"] == "ROLLBACK_EVENT"


def test_paper_to_live_persists_no_go_with_reasons(model2_db: str) -> None:
    result = PromotionEvaluator(model2_db_path=model2_db).evaluate_paper_to_live(
        decision_id="m2-028-2-no-go-001",
        sharpe_ratio=0.2,
        reconciliation_rate=0.75,
        critical_errors=2,
        manual_approved=False,
        approver_id=None,
        approval_justification=None,
    )

    assert result.go is False
    row = _fetch_promotion_row(model2_db, "m2-028-2-no-go-001")
    reasons = json.loads(str(row["reasons"]))
    assert row["go_no_go"] == "NO_GO"
    assert isinstance(reasons, list)
    assert any("sharpe_ratio" in reason for reason in reasons)
    assert "manual_approval_required" in reasons


def test_paper_to_live_is_idempotent_by_decision_id(model2_db: str) -> None:
    evaluator = PromotionEvaluator(model2_db_path=model2_db)

    first = evaluator.evaluate_paper_to_live(
        decision_id="m2-028-2-idempotencia-001",
        sharpe_ratio=1.3,
        reconciliation_rate=1.0,
        critical_errors=0,
        manual_approved=True,
        approver_id="tl-01",
        approval_justification="ok",
    )
    second = evaluator.evaluate_paper_to_live(
        decision_id="m2-028-2-idempotencia-001",
        sharpe_ratio=1.3,
        reconciliation_rate=1.0,
        critical_errors=0,
        manual_approved=True,
        approver_id="tl-01",
        approval_justification="ok",
    )

    assert first.go is True
    assert second.go is True
    with sqlite3.connect(model2_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM promotion_history WHERE decision_id = ?",
            ("m2-028-2-idempotencia-001",),
        ).fetchone()
    assert count is not None
    assert int(count[0]) == 1


def test_paper_to_live_requires_decision_id_for_auditability(model2_db: str) -> None:
    result = PromotionEvaluator(model2_db_path=model2_db).evaluate_paper_to_live(
        decision_id="",
        sharpe_ratio=2.0,
        reconciliation_rate=1.0,
        critical_errors=0,
        manual_approved=True,
        approver_id="tl-01",
        approval_justification="ok",
    )

    assert result.go is False
    assert any(
        "promotion_audit_persist_failed" in reason
        for reason in result.reasons
    )


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

