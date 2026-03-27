from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping

from core.dev_cycle_package_governance import (
    BacklogSLAResult,
    DocAdvocateGateResult,
    PMPreflightResult,
    TraceabilityCheckpointResult,
    build_traceability_checkpoint,
    evaluate_backlog_sla,
    evaluate_doc_advocate_gate,
    run_pm_preflight_check,
)
from core.dev_cycle_package_planner import GuardrailDiffCheckResult, verify_guardrail_diff
from core.dev_cycle_tl_reproduction import TLReproductionPlan, build_tl_reproduction_plan


@dataclass(frozen=True)
class StageSchemaValidationResult:
    valid: bool
    missing_fields: tuple[str, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class ResumeModeResult:
    can_resume: bool
    restart_stage: str
    reason: str


@dataclass(frozen=True)
class DevolutionMatrixResult:
    action: str
    return_stage: str
    reason_code: str


@dataclass(frozen=True)
class SlashCommandContractResult:
    valid: bool
    command: str
    error: str


@dataclass(frozen=True)
class DailyExecutiveSnapshot:
    snapshot_date: str
    total_items: int
    completed_items: int
    blocked_items: int
    top_blockers: tuple[str, ...]
    next_ready_items: tuple[str, ...]


_REQUIRED_FIELDS_BY_STAGE: dict[str, tuple[str, ...]] = {
    "2.product-owner": ("id", "score", "objetivo", "escopo", "guardrails", "Gate_payload"),
    "3.solution-architect": ("id", "requisitos", "modulos_afetados", "guardrails", "Gate_payload"),
    "4.qa-tdd": ("id", "arquivo_teste", "suite_testes", "guardrails", "Gate_payload"),
    "5.software-engineer": ("id", "status_backlog", "arquivos_alterados", "guardrails", "Gate_payload"),
    "6.tech-lead": ("id", "decisao", "status_backlog", "guardrails", "Gate_payload"),
    "7.doc-advocate": ("id", "status_backlog", "docs_atualizadas", "sync", "Gate_payload"),
    "8.project-manager": ("id", "status_backlog", "recomendacao", "Gate_payload"),
}

_ALLOWED_COMMANDS = {
    "/backlog-development",
    "/product-owner",
    "/solution-architect",
    "/qa-tdd",
    "/software-engineer",
    "/tech-lead",
    "/doc-advocate",
    "/project-manager",
}


def validate_stage_handoff_schema(*, stage: str, payload: Mapping[str, Any]) -> StageSchemaValidationResult:
    normalized_stage = stage.strip().lower()
    required = _REQUIRED_FIELDS_BY_STAGE.get(normalized_stage)
    if required is None:
        raise ValueError("stage_invalido")

    missing: list[str] = []
    for field in required:
        value = payload.get(field)
        if value is None or not str(value).strip():
            missing.append(field)
    errors = tuple(f"campo_obrigatorio_ausente_{field}" for field in missing)
    return StageSchemaValidationResult(valid=not missing, missing_fields=tuple(missing), errors=errors)


def evaluate_resume_mode(*, blocked_stage: str, corrected_handoff: Mapping[str, Any]) -> ResumeModeResult:
    stage = blocked_stage.strip()
    if not stage:
        raise ValueError("blocked_stage_invalido")

    if not corrected_handoff:
        return ResumeModeResult(can_resume=False, restart_stage=stage, reason="handoff_corrigido_ausente")

    return ResumeModeResult(can_resume=True, restart_stage=stage, reason="retomar_stage_bloqueado")


def resolve_devolution_matrix(*, stage: str, decision: str, motivo: str) -> DevolutionMatrixResult:
    normalized_stage = stage.strip()
    normalized_decision = decision.strip().upper()
    normalized_motivo = motivo.strip().lower()

    if normalized_decision == "DEVOLVIDO_PARA_REVISAO" and normalized_stage == "Tech Lead":
        return DevolutionMatrixResult(
            action="RETORNAR_STAGE_ESPECIFICO",
            return_stage="Software Engineer",
            reason_code="tl_devolvido_para_se",
        )
    if normalized_decision == "DEVOLVER_PARA_AJUSTE" and normalized_stage == "Project Manager":
        if "doc" in normalized_motivo:
            return DevolutionMatrixResult(
                action="RETORNAR_STAGE_ESPECIFICO",
                return_stage="Doc Advocate",
                reason_code="pm_ajuste_documentacao",
            )
        return DevolutionMatrixResult(
            action="RETORNAR_STAGE_ESPECIFICO",
            return_stage="Tech Lead",
            reason_code="pm_ajuste_validacao_tecnica",
        )
    return DevolutionMatrixResult(
        action="REEXECUTAR_STAGE_ATUAL",
        return_stage=normalized_stage,
        reason_code="reexecucao_stage_atual",
    )


def build_tl_local_reproduction(
    *,
    item_id: str,
    changed_files: list[str],
    pytest_targets: list[str] | None = None,
) -> TLReproductionPlan:
    return build_tl_reproduction_plan(
        item_id=item_id,
        changed_files=changed_files,
        pytest_targets=pytest_targets,
    )


def run_guardrail_diff_gate(
    *,
    diff_text: str,
    evidences_by_guardrail: Mapping[str, list[str] | str] | None = None,
) -> GuardrailDiffCheckResult:
    return verify_guardrail_diff(diff_text=diff_text, evidences_by_guardrail=evidences_by_guardrail)


def build_evidence_checkpoint(items: list[Mapping[str, Any]]) -> TraceabilityCheckpointResult:
    return build_traceability_checkpoint(items)


def run_documentation_gate(
    *,
    changed_files: list[str],
    existing_docs: list[str],
    synced_item_ids: list[str],
    expected_item_ids: list[str],
) -> DocAdvocateGateResult:
    return evaluate_doc_advocate_gate(
        changed_files=changed_files,
        existing_docs=existing_docs,
        synced_item_ids=synced_item_ids,
        expected_item_ids=expected_item_ids,
    )


def run_stage8_preacceptance(
    *,
    item_statuses: Mapping[str, str],
    suite_passed: bool,
    clean_tree: bool,
    commit_hash: str,
) -> PMPreflightResult:
    return run_pm_preflight_check(
        item_statuses=item_statuses,
        suite_passed=suite_passed,
        clean_tree=clean_tree,
        commit_hash=commit_hash,
    )


def validate_slash_command_contract(*, command: str, payload: str) -> SlashCommandContractResult:
    normalized_command = command.strip()
    if normalized_command not in _ALLOWED_COMMANDS:
        return SlashCommandContractResult(valid=False, command=normalized_command, error="comando_nao_suportado")
    if not payload.strip():
        return SlashCommandContractResult(valid=False, command=normalized_command, error="payload_vazio")
    return SlashCommandContractResult(valid=True, command=normalized_command, error="")


def build_daily_executive_snapshot(
    *,
    rows: list[Mapping[str, Any]],
    snapshot_date: datetime | None = None,
) -> DailyExecutiveSnapshot:
    dt = snapshot_date or datetime.now(tz=UTC)
    total = len(rows)
    completed = 0
    blocked = 0
    blockers: list[str] = []
    ready: list[str] = []

    for row in rows:
        item_id = str(row.get("id", "")).strip()
        status = str(row.get("status", "")).strip().upper()
        reason = str(row.get("reason", "")).strip()
        if status == "CONCLUIDO":
            completed += 1
        if status == "AGUARDANDO_CORRECAO":
            blocked += 1
            if item_id:
                blockers.append(f"{item_id}:{reason or 'sem_motivo'}")
        if status == "PRONTO":
            ready.append(item_id)

    return DailyExecutiveSnapshot(
        snapshot_date=dt.date().isoformat(),
        total_items=total,
        completed_items=completed,
        blocked_items=blocked,
        top_blockers=tuple(blockers[:10]),
        next_ready_items=tuple(item for item in ready[:10] if item),
    )


def evaluate_stage_status_sla(
    *,
    items: list[Mapping[str, Any]],
    sla_hours_by_status: Mapping[str, int],
    now_utc: datetime | None = None,
) -> BacklogSLAResult:
    reference = now_utc or datetime.now(tz=UTC)
    return evaluate_backlog_sla(items=items, sla_hours_by_status=sla_hours_by_status, now_utc=reference)
