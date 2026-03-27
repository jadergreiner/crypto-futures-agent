from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class PackageHandoffContractResult:
    valid: bool
    invalid_items: tuple[str, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class TraceabilityCheckpointResult:
    ready: bool
    missing_links: tuple[str, ...]


@dataclass(frozen=True)
class DocAdvocateGateResult:
    blocked: bool
    required_docs: tuple[str, ...]
    missing_docs: tuple[str, ...]
    missing_sync_items: tuple[str, ...]


@dataclass(frozen=True)
class PackageThroughputDashboard:
    total_items: int
    completed_items: int
    blocked_items: int
    wip_by_stage: dict[str, int]


@dataclass(frozen=True)
class BacklogSLAResult:
    violations: tuple[str, ...]
    compliant: bool


@dataclass(frozen=True)
class GoNoGoDecision:
    decision: str
    failed_criteria: tuple[str, ...]


@dataclass(frozen=True)
class PMPreflightResult:
    ready_for_acceptance: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class ExecutiveClosure:
    package_id: str
    status: str
    commit_hash: str
    clean_tree: bool
    total_items: int
    completed_items: int
    generated_at: str


def consolidate_package_handoff_contract(
    *,
    handoffs: list[Mapping[str, Any]],
    required_fields: list[str],
) -> PackageHandoffContractResult:
    invalid_items: list[str] = []
    errors: list[str] = []

    for index, handoff in enumerate(handoffs, start=1):
        item_id = str(handoff.get("id", f"item_{index}")).strip() or f"item_{index}"
        missing = [field for field in required_fields if not str(handoff.get(field, "")).strip()]
        if missing:
            invalid_items.append(item_id)
            errors.extend([f"{item_id}:campo_obrigatorio_ausente_{field}" for field in missing])

    return PackageHandoffContractResult(
        valid=not errors,
        invalid_items=tuple(invalid_items),
        errors=tuple(errors),
    )


def build_traceability_checkpoint(items: list[Mapping[str, Any]]) -> TraceabilityCheckpointResult:
    missing: list[str] = []
    for item in items:
        item_id = str(item.get("id", "")).strip() or "item_desconhecido"
        tests = item.get("tests", [])
        code = item.get("code", [])
        docs = item.get("docs", [])
        if not tests:
            missing.append(f"{item_id}:tests_ausentes")
        if not code:
            missing.append(f"{item_id}:codigo_ausente")
        if not docs:
            missing.append(f"{item_id}:docs_ausentes")
    return TraceabilityCheckpointResult(ready=not missing, missing_links=tuple(missing))


def evaluate_doc_advocate_gate(
    *,
    changed_files: list[str],
    existing_docs: list[str],
    synced_item_ids: list[str],
    expected_item_ids: list[str],
) -> DocAdvocateGateResult:
    required_docs: set[str] = {"docs/BACKLOG.md", "docs/SYNCHRONIZATION.md"}
    if any(path.startswith("core/") or path.startswith("scripts/") for path in changed_files):
        required_docs.add("docs/ARQUITETURA_ALVO.md")

    missing_docs = sorted(doc for doc in required_docs if doc not in existing_docs)
    missing_sync = sorted(item_id for item_id in expected_item_ids if item_id not in synced_item_ids)
    blocked = bool(missing_docs or missing_sync)
    return DocAdvocateGateResult(
        blocked=blocked,
        required_docs=tuple(sorted(required_docs)),
        missing_docs=tuple(missing_docs),
        missing_sync_items=tuple(missing_sync),
    )


def build_package_throughput_dashboard(snapshots: list[Mapping[str, Any]]) -> PackageThroughputDashboard:
    wip: dict[str, int] = {}
    completed = 0
    blocked = 0
    for row in snapshots:
        stage = str(row.get("stage", "unknown")).strip() or "unknown"
        status = str(row.get("status", "")).strip().upper()
        wip[stage] = wip.get(stage, 0) + 1
        if status == "CONCLUIDO":
            completed += 1
        if status == "AGUARDANDO_CORRECAO":
            blocked += 1
    return PackageThroughputDashboard(
        total_items=len(snapshots),
        completed_items=completed,
        blocked_items=blocked,
        wip_by_stage=wip,
    )


def evaluate_backlog_sla(
    *,
    items: list[Mapping[str, Any]],
    sla_hours_by_status: Mapping[str, int],
    now_utc: datetime,
) -> BacklogSLAResult:
    violations: list[str] = []
    for item in items:
        item_id = str(item.get("id", "")).strip() or "item_desconhecido"
        status = str(item.get("status", "")).strip()
        age_hours = int(item.get("age_hours", 0))
        limit = int(sla_hours_by_status.get(status, 10**9))
        if age_hours > limit:
            violations.append(f"{item_id}:sla_estourado_{status}:{age_hours}>{limit}")
    return BacklogSLAResult(violations=tuple(violations), compliant=not violations)


def evaluate_package_go_no_go(criteria: Mapping[str, bool]) -> GoNoGoDecision:
    failed = tuple(sorted(key for key, ok in criteria.items() if not ok))
    if failed:
        return GoNoGoDecision(decision="NO_GO", failed_criteria=failed)
    return GoNoGoDecision(decision="GO", failed_criteria=())


def run_pm_preflight_check(
    *,
    item_statuses: Mapping[str, str],
    suite_passed: bool,
    clean_tree: bool,
    commit_hash: str,
) -> PMPreflightResult:
    errors: list[str] = []
    not_done = sorted(item_id for item_id, status in item_statuses.items() if status != "CONCLUIDO")
    if not_done:
        errors.append(f"itens_nao_concluidos:{','.join(not_done)}")
    if not suite_passed:
        errors.append("suite_nao_esta_verde")
    if not clean_tree:
        errors.append("arvore_local_suja")
    if not commit_hash.strip():
        errors.append("commit_hash_ausente")
    return PMPreflightResult(ready_for_acceptance=not errors, errors=tuple(errors))


def generate_package_resume_runbook(blocked_items: list[Mapping[str, str]]) -> tuple[str, ...]:
    steps: list[str] = []
    for row in blocked_items:
        item_id = row.get("item_id", "").strip()
        stage = row.get("blocked_stage", "").strip()
        return_stage = row.get("return_stage", "").strip() or stage
        reason = row.get("reason_code", "").strip() or "motivo_nao_informado"
        steps.append(f"{item_id}:corrigir_{return_stage}:{reason}")
    return tuple(steps)


def build_package_executive_closure(
    *,
    package_id: str,
    item_statuses: Mapping[str, str],
    commit_hash: str,
    clean_tree: bool,
) -> ExecutiveClosure:
    total = len(item_statuses)
    completed = sum(1 for status in item_statuses.values() if status == "CONCLUIDO")
    status = "ACEITE" if total > 0 and completed == total and clean_tree and bool(commit_hash.strip()) else "DEVOLVER_PARA_AJUSTE"
    return ExecutiveClosure(
        package_id=package_id.strip(),
        status=status,
        commit_hash=commit_hash.strip(),
        clean_tree=clean_tree,
        total_items=total,
        completed_items=completed,
        generated_at=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )
