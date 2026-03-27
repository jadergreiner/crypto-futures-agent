"""RED->GREEN suite for M2-031.5 sprint capacity gate."""

from __future__ import annotations

import pytest

from core.dev_cycle_package_planner import (
    BacklogCandidate,
    apply_sprint_capacity_gate,
)


def _candidate(item_id: str) -> BacklogCandidate:
    return BacklogCandidate(
        id=item_id,
        title=f"Item {item_id}",
        valor=5.0,
        urgencia=4.0,
        reducao_risco=4.0,
        esforco=2.0,
    )


def test_apply_sprint_capacity_gate_schedules_only_within_capacity() -> None:
    package = [_candidate(f"M2-031.{idx}") for idx in range(1, 6)]

    plan = apply_sprint_capacity_gate(package, sprint_capacity=3)

    assert [item.id for item in plan.scheduled] == ["M2-031.1", "M2-031.2", "M2-031.3"]
    assert [item.id for item in plan.deferred] == ["M2-031.4", "M2-031.5"]


def test_apply_sprint_capacity_gate_marks_deferred_items_with_reason_and_justification() -> None:
    package = [_candidate("M2-031.1"), _candidate("M2-031.2")]

    plan = apply_sprint_capacity_gate(package, sprint_capacity=1)

    assert len(plan.deferred) == 1
    deferred = plan.deferred[0]
    assert deferred.id == "M2-031.2"
    assert deferred.reason_code == "capacidade_sprint_excedida"
    assert deferred.justification == "Item adiado por limite da sprint (1)."


def test_apply_sprint_capacity_gate_has_no_deferred_when_capacity_covers_package() -> None:
    package = [_candidate("M2-031.1"), _candidate("M2-031.2")]

    plan = apply_sprint_capacity_gate(package, sprint_capacity=5)

    assert [item.id for item in plan.scheduled] == ["M2-031.1", "M2-031.2"]
    assert plan.deferred == ()


def test_apply_sprint_capacity_gate_rejects_invalid_capacity() -> None:
    with pytest.raises(ValueError, match="sprint_capacity_invalida"):
        apply_sprint_capacity_gate([_candidate("M2-031.1")], sprint_capacity=0)
