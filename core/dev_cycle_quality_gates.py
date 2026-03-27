from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CoverageGateResult:
    passed: bool
    failed_modules: tuple[str, ...]


@dataclass(frozen=True)
class MypyScopePlan:
    targets: tuple[str, ...]
    command: str


@dataclass(frozen=True)
class PayloadContractResult:
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class TraceabilityAuditResult:
    valid: bool
    missing_links: tuple[str, ...]


@dataclass(frozen=True)
class TLReproductionAudit:
    ready: bool
    required_steps: tuple[str, ...]
    missing_steps: tuple[str, ...]


@dataclass(frozen=True)
class GuardrailPreflightResult:
    blocked: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PromotionMatrixResult:
    decision: str
    failed_metrics: tuple[str, ...]


@dataclass(frozen=True)
class RegressionAuditResult:
    ready: bool
    missing_checks: tuple[str, ...]


@dataclass(frozen=True)
class SlashAndHandoffContractResult:
    valid: bool
    errors: tuple[str, ...]


def evaluate_minimum_coverage_gate(
    *,
    coverage_by_module: Mapping[str, float],
    threshold_by_module: Mapping[str, float],
) -> CoverageGateResult:
    failed = []
    for module, threshold in threshold_by_module.items():
        current = float(coverage_by_module.get(module, 0.0))
        if current < float(threshold):
            failed.append(module)
    return CoverageGateResult(passed=not failed, failed_modules=tuple(sorted(failed)))


def build_mypy_strict_scope_plan(*, changed_files: Sequence[str], critical_contracts: Sequence[str]) -> MypyScopePlan:
    targets: list[str] = []
    for path in changed_files:
        clean = path.strip()
        if clean.endswith(".py") and (clean.startswith("core/") or clean.startswith("scripts/")):
            targets.append(clean)
    for path in critical_contracts:
        clean = path.strip()
        if clean and clean not in targets:
            targets.append(clean)
    if not targets:
        raise ValueError("mypy_scope_vazio")
    command = "mypy --strict " + " ".join(targets)
    return MypyScopePlan(targets=tuple(targets), command=command)


def validate_unified_payload_contract(
    *,
    stage_payloads: Mapping[str, Mapping[str, Any]],
    required_fields_by_stage: Mapping[str, Sequence[str]],
    max_chars_by_stage: Mapping[str, int],
) -> PayloadContractResult:
    errors: list[str] = []
    for stage, payload in stage_payloads.items():
        required = required_fields_by_stage.get(stage, ())
        for field in required:
            value = payload.get(field)
            if value is None or not str(value).strip():
                errors.append(f"{stage}:campo_obrigatorio_ausente_{field}")
        max_chars = int(max_chars_by_stage.get(stage, 10**9))
        if len(str(dict(payload))) > max_chars:
            errors.append(f"{stage}:payload_excede_limite")
    return PayloadContractResult(valid=not errors, errors=tuple(errors))


def audit_blid_traceability(items: Sequence[Mapping[str, Any]]) -> TraceabilityAuditResult:
    missing: list[str] = []
    for row in items:
        item_id = str(row.get("id", "")).strip() or "item_desconhecido"
        if not row.get("tests"):
            missing.append(f"{item_id}:tests")
        if not row.get("code"):
            missing.append(f"{item_id}:code")
        if not row.get("docs"):
            missing.append(f"{item_id}:docs")
    return TraceabilityAuditResult(valid=not missing, missing_links=tuple(missing))


def audit_tl_reproduction_script(*, available_steps: Sequence[str]) -> TLReproductionAudit:
    required = ("pytest_scope", "mypy_scope", "diff_guardrails", "risk_summary")
    missing = tuple(step for step in required if step not in available_steps)
    return TLReproductionAudit(ready=not missing, required_steps=required, missing_steps=missing)


def run_guardrail_diff_preflight(*, diff_text: str) -> GuardrailPreflightResult:
    normalized = diff_text.lower()
    reasons: list[str] = []
    if "risk_gate" in normalized and "disabled" in normalized:
        reasons.append("risk_gate_desabilitado")
    if "circuit_breaker" in normalized and "disabled" in normalized:
        reasons.append("circuit_breaker_desabilitado")
    if "decision_id" in normalized and "removed" in normalized:
        reasons.append("decision_id_idempotencia_quebrada")
    return GuardrailPreflightResult(blocked=bool(reasons), reasons=tuple(reasons))


def evaluate_shadow_to_paper_matrix(*, metrics: Mapping[str, float], thresholds: Mapping[str, float]) -> PromotionMatrixResult:
    failed = tuple(
        sorted(key for key, minimum in thresholds.items() if float(metrics.get(key, float("-inf"))) < float(minimum))
    )
    return PromotionMatrixResult(decision="NO_GO" if failed else "GO", failed_metrics=failed)


def evaluate_paper_to_live_matrix(
    *,
    metrics: Mapping[str, float],
    thresholds: Mapping[str, float],
    fail_safe_ok: bool,
) -> PromotionMatrixResult:
    failed = [key for key, minimum in thresholds.items() if float(metrics.get(key, float("-inf"))) < float(minimum)]
    if not fail_safe_ok:
        failed.append("fail_safe")
    failed_tuple = tuple(sorted(failed))
    return PromotionMatrixResult(decision="NO_GO" if failed_tuple else "GO", failed_metrics=failed_tuple)


def run_package_regression_audit(*, checks: Mapping[str, bool]) -> RegressionAuditResult:
    missing = tuple(sorted(key for key, ok in checks.items() if not ok))
    return RegressionAuditResult(ready=not missing, missing_checks=missing)


def validate_slash_and_handoff_contracts(
    *,
    slash_inputs: Mapping[str, str],
    handoff_payloads: Mapping[str, Mapping[str, Any]],
    required_handoff_keys: Mapping[str, Sequence[str]],
) -> SlashAndHandoffContractResult:
    errors: list[str] = []
    for command, payload in slash_inputs.items():
        if not command.strip().startswith("/"):
            errors.append(f"slash_invalido:{command}")
        if not payload.strip():
            errors.append(f"slash_payload_vazio:{command}")
    for handoff, handoff_payload in handoff_payloads.items():
        required = required_handoff_keys.get(handoff, ())
        for key in required:
            if key not in handoff_payload or not str(handoff_payload[key]).strip():
                errors.append(f"handoff_campo_ausente:{handoff}:{key}")
    return SlashAndHandoffContractResult(valid=not errors, errors=tuple(errors))
