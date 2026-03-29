"""Stage-oriented test and type-check matrix for dev-cycle gates."""

from __future__ import annotations

from typing import Final, Mapping, TypedDict

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

FAST_PROFILE_BUDGET_SECONDS: Final[int] = 45


class GuardrailMetadata(TypedDict):
    risk_gate: str
    circuit_breaker: str
    decision_id: str


class WorkflowStageEntry(TypedDict):
    label: str
    profile: str
    command: str
    guardrails: GuardrailMetadata


WorkflowStageMatrix = dict[str, WorkflowStageEntry]

_GUARDRAILS: Final[GuardrailMetadata] = {
    "risk_gate": "ATIVO",
    "circuit_breaker": "ATIVO",
    "decision_id": "IDEMPOTENTE",
}

_WORKFLOW_STAGE_PROFILE: Final[dict[str, str]] = {
    "1.backlog-development": "rapido",
    "2.product-owner": "rapido",
    "3.solution-architect": "rapido",
    "4.qa-tdd": "rapido",
    "5.software-engineer": "rapido",
    "6.tech-lead": "completo",
    "7.doc-advocate": "regressao",
    "8.project-manager": "regressao",
}

_WORKFLOW_STAGE_LABEL: Final[dict[str, str]] = {
    "1.backlog-development": "Higiene inicial do backlog",
    "2.product-owner": "Priorizacao e valor",
    "3.solution-architect": "Refino tecnico e riscos",
    "4.qa-tdd": "Suite RED e gate critico",
    "5.software-engineer": "Implementacao GREEN",
    "6.tech-lead": "Reproducao tecnica completa",
    "7.doc-advocate": "Governanca documental",
    "8.project-manager": "Aceite final e fechamento",
}

_PROFILE_TARGETS: Final[dict[str, tuple[str, ...]]] = {
    "rapido": (
        "tests/test_model2_state_contract.py",
        "tests/test_model2_order_layer.py",
        "tests/test_docs_model2_sync.py",
    ),
    "completo": ("tests/",),
    "regressao": (
        "tests/test_model2_m2_019_9_risk_regression.py",
        "tests/test_model2_m2_026_1_risk_gate_telemetry.py",
        "tests/test_blid092_circuit_breaker_contract.py",
        "tests/test_docs_model2_sync.py",
    ),
}

_REQUIRED_MARKERS_BY_STAGE: Final[dict[str, set[str]]] = {
    "4.qa-tdd": {"contract", "risk", "docs"},
    "5.software-engineer": {"contract", "risk", "docs"},
    "6.tech-lead": {"contract", "risk", "docs"},
    "7.doc-advocate": {"docs"},
    "8.project-manager": {"contract", "risk", "docs"},
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


def _validate_workflow_stage(stage: str) -> None:
    if stage not in _WORKFLOW_STAGE_PROFILE:
        raise ValueError(f"unsupported stage: {stage}")


def resolve_stage_profile(stage: str) -> str:
    """Resolve execution profile by workflow stage with fail-safe fallback."""
    _validate_workflow_stage(stage)
    return _WORKFLOW_STAGE_PROFILE[stage]


def build_profile_targets(profile: str) -> list[str]:
    """Return immutable targets as a list for pytest command composition."""
    if profile not in _PROFILE_TARGETS:
        raise ValueError(f"unsupported profile: {profile}")
    return list(_PROFILE_TARGETS[profile])


def build_profile_command(profile: str) -> str:
    """Build canonical pytest command for a profile."""
    if profile == "completo":
        return "pytest -q tests/"
    if profile == "rapido":
        targets = " ".join(build_profile_targets(profile))
        return f'pytest -q {targets} -m "unit or contract or docs" -k "risk_gate or circuit_breaker or risk"'
    if profile == "regressao":
        targets = " ".join(build_profile_targets(profile))
        return f'pytest -q {targets} -m "contract or integration or docs" -k "risk_gate or circuit_breaker or risk"'
    raise ValueError(f"unsupported profile: {profile}")


def build_stage_command(stage: str) -> str:
    """Build deterministic stage command preserving profile semantics."""
    profile = resolve_stage_profile(stage)
    base_command = build_profile_command(profile)
    if profile == "completo":
        return base_command
    return f'{base_command} -k "{stage} or risk_gate or circuit_breaker or docs or contract"'


def validate_gate_execution(stage: str, executed_markers: Mapping[str, str] | set[str]) -> bool:
    """Validate mandatory gate markers for stages that require strict gating."""
    _validate_workflow_stage(stage)
    required = _REQUIRED_MARKERS_BY_STAGE.get(stage, set())
    if not required:
        return True

    markers = set(executed_markers.keys()) if isinstance(executed_markers, Mapping) else set(executed_markers)
    normalized_markers = {marker.strip().lower() for marker in markers}
    return required.issubset(normalized_markers)


def build_workflow_stage_matrix() -> WorkflowStageMatrix:
    """Build stage matrix for agents 1..8 with immutable guardrail metadata."""
    matrix: WorkflowStageMatrix = {}
    for stage, profile in _WORKFLOW_STAGE_PROFILE.items():
        guardrails: GuardrailMetadata = {
            "risk_gate": _GUARDRAILS["risk_gate"],
            "circuit_breaker": _GUARDRAILS["circuit_breaker"],
            "decision_id": _GUARDRAILS["decision_id"],
        }
        matrix[stage] = {
            "label": _WORKFLOW_STAGE_LABEL[stage],
            "profile": profile,
            "command": build_stage_command(stage),
            "guardrails": guardrails,
        }
    return matrix
