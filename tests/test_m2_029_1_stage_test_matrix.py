"""RED suite for M2-029.1 - stage-oriented test matrix."""

from __future__ import annotations

import pytest


@pytest.fixture
def stage_order() -> list[str]:
    return ["preflight", "decision", "execution", "docs"]


def test_stage_matrix_has_required_stages(stage_order: list[str]) -> None:
    from core.model2.stage_test_matrix import build_stage_matrix

    matrix = build_stage_matrix()
    for stage in stage_order:
        assert stage in matrix


def test_stage_matrix_has_pytest_commands(stage_order: list[str]) -> None:
    from core.model2.stage_test_matrix import build_stage_matrix

    matrix = build_stage_matrix()
    for stage in stage_order:
        cmd = matrix[stage]["command"]
        assert cmd.startswith("pytest -q")


def test_stage_matrix_has_scope_labels(stage_order: list[str]) -> None:
    from core.model2.stage_test_matrix import build_stage_matrix

    matrix = build_stage_matrix()
    for stage in stage_order:
        assert matrix[stage]["label"] != ""


def test_stage_matrix_has_mypy_policy() -> None:
    from core.model2.stage_test_matrix import mypy_policy_for_stage

    policy = mypy_policy_for_stage("execution")
    assert policy == "strict_changed_modules"


def test_stage_matrix_unknown_stage_fails_safe() -> None:
    from core.model2.stage_test_matrix import mypy_policy_for_stage

    with pytest.raises(ValueError):
        mypy_policy_for_stage("unknown")
