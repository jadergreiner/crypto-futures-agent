"""Stage-oriented test and type-check matrix for dev-cycle gates."""

from __future__ import annotations

from typing import Final

StageMatrix = dict[str, dict[str, str]]

_STAGE_MATRIX: Final[StageMatrix] = {
    "preflight": {
        "label": "Schema and startup guards",
        "command": "pytest -q tests/test_model2_m2_027_2_preflight.py",
    },
    "decision": {
        "label": "Decision contract and risk filters",
        "command": "pytest -q tests/test_model2_order_layer.py",
    },
    "execution": {
        "label": "Execution and reconciliation",
        "command": "pytest -q tests/test_model2_live_execution.py",
    },
    "docs": {
        "label": "Documentation sync and model checks",
        "command": "pytest -q tests/test_docs_model2_sync.py",
    },
}

_MYPY_POLICY_BY_STAGE: Final[dict[str, str]] = {
    "preflight": "strict_changed_modules",
    "decision": "strict_changed_modules",
    "execution": "strict_changed_modules",
    "docs": "strict_changed_modules",
}


def build_stage_matrix() -> StageMatrix:
    """Return a copy to avoid accidental mutation by callers."""
    return {stage: data.copy() for stage, data in _STAGE_MATRIX.items()}


def mypy_policy_for_stage(stage: str) -> str:
    """Resolve mypy policy with fail-safe validation for unknown stages."""
    try:
        return _MYPY_POLICY_BY_STAGE[stage]
    except KeyError as exc:
        raise ValueError(f"unsupported stage: {stage}") from exc
