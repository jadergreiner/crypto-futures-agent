"""RED->GREEN suite for M2-031.10 guardrail diff verifier."""

from __future__ import annotations

from core.dev_cycle_package_planner import verify_guardrail_diff


def test_verify_guardrail_diff_does_not_block_when_no_sensitive_guardrail_is_touched() -> None:
    diff_text = """
diff --git a/core/dev_cycle_executor.py b/core/dev_cycle_executor.py
+ retry label update
- progress formatting update
"""
    result = verify_guardrail_diff(diff_text=diff_text, evidences_by_guardrail={})

    assert result.blocked is False
    assert result.touched_guardrails == ()
    assert result.missing_evidences == ()


def test_verify_guardrail_diff_blocks_when_risk_gate_changes_without_evidence() -> None:
    diff_text = """
diff --git a/core/model2/risk_gate.py b/core/model2/risk_gate.py
- if risk_gate_enabled:
+ if False:
"""
    result = verify_guardrail_diff(diff_text=diff_text, evidences_by_guardrail={})

    assert result.blocked is True
    assert result.touched_guardrails == ("risk_gate",)
    assert result.missing_evidences == ("risk_gate",)


def test_verify_guardrail_diff_accepts_when_all_touched_guardrails_have_evidence() -> None:
    diff_text = """
diff --git a/core/model2/guards.py b/core/model2/guards.py
- circuit_breaker_open = old()
+ circuit_breaker_open = new()
- decision_id = payload.get("decision_id")
+ decision_id = payload["decision_id"]
"""
    result = verify_guardrail_diff(
        diff_text=diff_text,
        evidences_by_guardrail={
            "circuit_breaker": ["tests/test_guardrails.py::test_cb"],
            "decision_id": ["tests/test_idempotence.py::test_decision_id"],
        },
    )

    assert result.blocked is False
    assert result.touched_guardrails == ("circuit_breaker", "decision_id")
    assert result.missing_evidences == ()


def test_verify_guardrail_diff_blocks_only_missing_subset_of_evidence() -> None:
    diff_text = """
diff --git a/core/model2/guards.py b/core/model2/guards.py
- risk_gate = old()
+ risk_gate = new()
- circuit_breaker = old()
+ circuit_breaker = new()
"""
    result = verify_guardrail_diff(
        diff_text=diff_text,
        evidences_by_guardrail={"risk_gate": "tests/test_guardrails.py::test_risk"},
    )

    assert result.blocked is True
    assert result.touched_guardrails == ("circuit_breaker", "risk_gate")
    assert result.missing_evidences == ("circuit_breaker",)
