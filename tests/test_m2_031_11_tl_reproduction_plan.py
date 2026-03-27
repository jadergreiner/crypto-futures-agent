"""RED->GREEN suite for M2-031.11 Tech Lead scoped reproduction plan."""

from __future__ import annotations

import pytest

from core.dev_cycle_tl_reproduction import build_tl_reproduction_plan


def test_build_tl_reproduction_plan_derives_commands_from_changed_files() -> None:
    plan = build_tl_reproduction_plan(
        item_id="M2-031.11",
        changed_files=[
            "core/dev_cycle_executor.py",
            "tests/test_m2_031_8_blocking_matrix.py",
        ],
    )

    assert plan.pytest_targets == ("tests/test_m2_031_8_blocking_matrix.py",)
    assert plan.mypy_targets == ("core/dev_cycle_executor.py",)
    assert plan.commands[0].startswith("pytest -q ")
    assert plan.commands[1] == "mypy --strict core/dev_cycle_executor.py"


def test_build_tl_reproduction_plan_accepts_explicit_pytest_targets() -> None:
    plan = build_tl_reproduction_plan(
        item_id="M2-031.11",
        changed_files=["core/dev_cycle_package_planner.py"],
        pytest_targets=["tests/test_m2_031_9_aggregate_payload_gate.py"],
    )

    assert plan.pytest_targets == ("tests/test_m2_031_9_aggregate_payload_gate.py",)
    assert plan.mypy_targets == ("core/dev_cycle_package_planner.py",)


def test_build_tl_reproduction_plan_rejects_full_suite_target() -> None:
    with pytest.raises(ValueError, match="pytest_target_suite_total_proibido"):
        build_tl_reproduction_plan(
            item_id="M2-031.11",
            changed_files=["core/dev_cycle_executor.py"],
            pytest_targets=["tests/"],
        )


def test_build_tl_reproduction_plan_fails_safe_without_required_inputs() -> None:
    with pytest.raises(ValueError, match="changed_files_vazio"):
        build_tl_reproduction_plan(item_id="M2-031.11", changed_files=[])

    with pytest.raises(ValueError, match="item_id_invalido"):
        build_tl_reproduction_plan(item_id=" ", changed_files=["core/dev_cycle_executor.py"])

    with pytest.raises(ValueError, match="mypy_targets_vazio"):
        build_tl_reproduction_plan(
            item_id="M2-031.11",
            changed_files=["tests/test_m2_031_8_blocking_matrix.py"],
        )
