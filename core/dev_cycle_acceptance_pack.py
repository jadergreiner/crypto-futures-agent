from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DailyCycleSnapshot:
    snapshot_date: str
    by_stage: dict[str, int]
    blocked_items: tuple[str, ...]
    ready_items: tuple[str, ...]


@dataclass(frozen=True)
class BacklogSLAGovernance:
    compliant: bool
    violations: tuple[str, ...]


@dataclass(frozen=True)
class DocumentationImpactResult:
    required_docs: tuple[str, ...]
    missing_docs: tuple[str, ...]
    blocked: bool


@dataclass(frozen=True)
class AcceptanceRunbookResult:
    ready: bool
    steps: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class RiskReportResult:
    risk_score: float
    highlights: tuple[str, ...]


@dataclass(frozen=True)
class OrchestrationDecisionRunbook:
    decision: str
    checklist: tuple[str, ...]


@dataclass(frozen=True)
class OrphanExitGuardResult:
    blocked: bool
    reason_code: str


@dataclass(frozen=True)
class TransactionalConsistencyResult:
    consistent: bool
    reason_code: str


@dataclass(frozen=True)
class PackageRunbookGovernance:
    complete: bool
    missing_sections: tuple[str, ...]


def build_daily_cycle_snapshot(*, rows: Sequence[Mapping[str, Any]], snapshot_at: datetime | None = None) -> DailyCycleSnapshot:
    dt = snapshot_at or datetime.now(tz=UTC)
    by_stage: dict[str, int] = {}
    blocked: list[str] = []
    ready: list[str] = []
    for row in rows:
        stage = str(row.get("stage", "unknown")).strip() or "unknown"
        status = str(row.get("status", "")).strip().upper()
        item_id = str(row.get("id", "")).strip()
        by_stage[stage] = by_stage.get(stage, 0) + 1
        if status == "AGUARDANDO_CORRECAO" and item_id:
            blocked.append(item_id)
        if status == "PRONTO" and item_id:
            ready.append(item_id)
    return DailyCycleSnapshot(
        snapshot_date=dt.date().isoformat(),
        by_stage=by_stage,
        blocked_items=tuple(blocked),
        ready_items=tuple(ready),
    )


def govern_backlog_status_sla(*, items: Sequence[Mapping[str, Any]], limits_by_status: Mapping[str, int]) -> BacklogSLAGovernance:
    violations: list[str] = []
    for row in items:
        item_id = str(row.get("id", "")).strip() or "item_desconhecido"
        status = str(row.get("status", "")).strip()
        age_hours = int(row.get("age_hours", 0))
        limit = int(limits_by_status.get(status, 10**9))
        if age_hours > limit:
            violations.append(f"{item_id}:{status}:{age_hours}>{limit}")
    return BacklogSLAGovernance(compliant=not violations, violations=tuple(violations))


def evaluate_documentation_impact(*, changed_files: Sequence[str], docs_present: Sequence[str]) -> DocumentationImpactResult:
    required = {"docs/BACKLOG.md", "docs/SYNCHRONIZATION.md"}
    if any(path.startswith("core/") for path in changed_files):
        required.add("docs/ARQUITETURA_ALVO.md")
    if any(path.startswith("scripts/") for path in changed_files):
        required.add("docs/REGRAS_DE_NEGOCIO.md")
    missing = tuple(sorted(doc for doc in required if doc not in docs_present))
    return DocumentationImpactResult(
        required_docs=tuple(sorted(required)),
        missing_docs=missing,
        blocked=bool(missing),
    )


def build_final_acceptance_runbook(*, checks: Mapping[str, bool]) -> AcceptanceRunbookResult:
    steps = (
        "validar_backlog_concluido",
        "validar_suite_verde",
        "validar_commit_push",
        "validar_arvore_limpa",
    )
    missing = tuple(step for step in steps if not checks.get(step, False))
    return AcceptanceRunbookResult(ready=not missing, steps=steps, missing=missing)


def build_status_transition_sla_report(*, items: Sequence[Mapping[str, Any]]) -> BacklogSLAGovernance:
    return govern_backlog_status_sla(
        items=items,
        limits_by_status={
            "Em analise": 24,
            "TESTES_PRONTOS": 24,
            "EM_DESENVOLVIMENTO": 48,
            "IMPLEMENTADO": 24,
            "REVISADO_APROVADO": 24,
        },
    )


def build_pre_merge_risk_report(*, residual_risks: Sequence[str], failing_checks: Sequence[str]) -> RiskReportResult:
    score = float(len(residual_risks) * 1.5 + len(failing_checks) * 2.0)
    highlights = tuple(sorted(set(list(residual_risks) + list(failing_checks))))
    return RiskReportResult(risk_score=score, highlights=highlights)


def build_orchestration_decision_runbook(*, preflight_ok: bool, docs_ok: bool, clean_tree: bool) -> OrchestrationDecisionRunbook:
    checklist = ("preflight_ok", "docs_ok", "clean_tree")
    decision = "ACEITE" if preflight_ok and docs_ok and clean_tree else "DEVOLVER"
    return OrchestrationDecisionRunbook(decision=decision, checklist=checklist)


def evaluate_orphan_exit_guard(*, has_orphan_position: bool, has_external_fill_confirmation: bool) -> OrphanExitGuardResult:
    if has_orphan_position and not has_external_fill_confirmation:
        return OrphanExitGuardResult(blocked=True, reason_code="orphan_exit_blocked_without_external_fill")
    return OrphanExitGuardResult(blocked=False, reason_code="ok")


def validate_transactional_consistency(*, order_layer_state: str, live_execution_state: str) -> TransactionalConsistencyResult:
    if order_layer_state == live_execution_state:
        return TransactionalConsistencyResult(consistent=True, reason_code="ok")
    return TransactionalConsistencyResult(consistent=False, reason_code="state_divergence_between_layers")


def validate_package_runbook_governance(*, sections: Sequence[str]) -> PackageRunbookGovernance:
    required = ("objetivo", "guardrails", "rollback", "aceite")
    missing = tuple(section for section in required if section not in sections)
    return PackageRunbookGovernance(complete=not missing, missing_sections=missing)
