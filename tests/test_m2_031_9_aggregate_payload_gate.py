"""RED->GREEN suite for M2-031.9 aggregate payload gate by package."""

from __future__ import annotations

import pytest

from core.dev_cycle_package_planner import evaluate_aggregate_payload_gate


def _handoff(item_id: str, size: int) -> dict[str, str]:
    return {"id": item_id, "payload": "x" * size}


def test_evaluate_aggregate_payload_gate_accepts_when_total_is_within_limit() -> None:
    handoffs = [
        _handoff("M2-031.9-A", 20),
        _handoff("M2-031.9-B", 30),
    ]

    result = evaluate_aggregate_payload_gate(handoffs, limit_chars=500)

    assert result.requires_compaction is False
    assert result.overflow_chars == 0
    assert result.compaction_candidates == ()
    assert result.total_payload_chars > 0


def test_evaluate_aggregate_payload_gate_flags_compaction_when_limit_is_exceeded() -> None:
    handoffs = [
        _handoff("M2-031.9-A", 500),
        _handoff("M2-031.9-B", 200),
        _handoff("M2-031.9-C", 100),
    ]

    result = evaluate_aggregate_payload_gate(handoffs, limit_chars=700)

    assert result.requires_compaction is True
    assert result.overflow_chars > 0
    assert result.compaction_candidates[0] == "M2-031.9-A"


def test_evaluate_aggregate_payload_gate_uses_fallback_id_when_missing() -> None:
    handoffs = [
        {"payload": "x" * 200},
        {"id": "", "payload": "x" * 210},
    ]

    result = evaluate_aggregate_payload_gate(handoffs, limit_chars=200)

    assert result.requires_compaction is True
    assert result.compaction_candidates
    assert result.compaction_candidates[0].startswith("payload_")


def test_evaluate_aggregate_payload_gate_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="limit_chars_invalido"):
        evaluate_aggregate_payload_gate([_handoff("M2-031.9-A", 10)], limit_chars=0)
