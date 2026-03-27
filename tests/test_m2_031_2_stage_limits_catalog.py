"""RED->GREEN suite for M2-031.2 stage limits catalog."""

from __future__ import annotations

import pytest

from core.dev_cycle_package_planner import get_stage_limits_catalog, validate_stage_limits


def test_get_stage_limits_catalog_contains_stages_2_to_8() -> None:
    catalog = get_stage_limits_catalog()
    assert sorted(catalog.keys()) == [
        "2.product-owner",
        "3.solution-architect",
        "4.qa-tdd",
        "5.software-engineer",
        "6.tech-lead",
        "7.doc-advocate",
        "8.project-manager",
    ]


def test_validate_stage_limits_accepts_payload_and_batch_within_limits() -> None:
    errors = validate_stage_limits(stage="4.qa-tdd", payload_chars=2000, items_in_batch=8)
    assert errors == []


def test_validate_stage_limits_flags_payload_above_limit() -> None:
    errors = validate_stage_limits(stage="2.product-owner", payload_chars=1201, items_in_batch=1)
    assert "payload_excede_limite_do_stage" in errors


def test_validate_stage_limits_flags_batch_above_capacity() -> None:
    errors = validate_stage_limits(stage="5.software-engineer", payload_chars=100, items_in_batch=6)
    assert "itens_excedem_capacidade_do_stage" in errors


def test_validate_stage_limits_rejects_unknown_stage() -> None:
    with pytest.raises(ValueError, match="stage_invalido"):
        validate_stage_limits(stage="1.backlog-development", payload_chars=10, items_in_batch=1)

