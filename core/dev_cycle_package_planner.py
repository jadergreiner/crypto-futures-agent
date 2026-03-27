from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class BacklogCandidate:
    id: str
    title: str
    valor: float
    urgencia: float
    reducao_risco: float
    esforco: float
    risco_residual: float = 0.0
    dependencies: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StageLimit:
    stage: str
    max_payload_chars: int
    max_parallel_items: int


@dataclass(frozen=True)
class DeferredPackageItem:
    id: str
    reason_code: str
    justification: str


@dataclass(frozen=True)
class SprintCapacityPlan:
    sprint_capacity: int
    scheduled: tuple[BacklogCandidate, ...]
    deferred: tuple[DeferredPackageItem, ...]


@dataclass(frozen=True)
class StageProgressSnapshot:
    item_id: str
    stage: str
    status: str
    decision: str
    note: str
    updated_at: str


@dataclass(frozen=True)
class PackagePayloadEntry:
    item_id: str
    payload_chars: int


@dataclass(frozen=True)
class AggregatePayloadGateResult:
    total_payload_chars: int
    limit_chars: int
    overflow_chars: int
    requires_compaction: bool
    compaction_candidates: tuple[str, ...]
    entries: tuple[PackagePayloadEntry, ...]


@dataclass(frozen=True)
class GuardrailDiffCheckResult:
    blocked: bool
    touched_guardrails: tuple[str, ...]
    missing_evidences: tuple[str, ...]
    required_evidences: tuple[str, ...]


_STAGE_LIMITS: dict[str, StageLimit] = {
    "2.product-owner": StageLimit(stage="2.product-owner", max_payload_chars=1200, max_parallel_items=20),
    "3.solution-architect": StageLimit(
        stage="3.solution-architect",
        max_payload_chars=1600,
        max_parallel_items=20,
    ),
    "4.qa-tdd": StageLimit(stage="4.qa-tdd", max_payload_chars=2500, max_parallel_items=10),
    "5.software-engineer": StageLimit(
        stage="5.software-engineer",
        max_payload_chars=1800,
        max_parallel_items=5,
    ),
    "6.tech-lead": StageLimit(stage="6.tech-lead", max_payload_chars=1800, max_parallel_items=5),
    "7.doc-advocate": StageLimit(stage="7.doc-advocate", max_payload_chars=1800, max_parallel_items=8),
    "8.project-manager": StageLimit(
        stage="8.project-manager",
        max_payload_chars=1800,
        max_parallel_items=8,
    ),
}


def calculate_priority_score(candidate: BacklogCandidate) -> float:
    score = (
        candidate.valor * 0.45
        + candidate.urgencia * 0.25
        + candidate.reducao_risco * 0.20
        - candidate.esforco * 0.10
    )
    return round(score, 2)


def build_development_package(
    candidates: Iterable[BacklogCandidate],
    *,
    package_size: int = 20,
) -> list[BacklogCandidate]:
    if package_size <= 0:
        raise ValueError("package_size_invalido")

    remaining = {candidate.id: candidate for candidate in candidates}
    selected: list[BacklogCandidate] = []
    selected_ids: set[str] = set()

    while remaining and len(selected) < package_size:
        ready: list[BacklogCandidate] = []
        for candidate in remaining.values():
            unresolved = [dep for dep in candidate.dependencies if dep in remaining]
            if not unresolved:
                ready.append(candidate)
        if not ready:
            # Dependencia circular ou invalida: fail-safe para nao montar pacote inconsistente.
            break

        # Desempate auditavel: score PO -> risco_residual -> id.
        ready.sort(key=lambda item: (-calculate_priority_score(item), -item.risco_residual, item.id))
        chosen = ready[0]
        selected.append(chosen)
        selected_ids.add(chosen.id)
        remaining.pop(chosen.id, None)

    return selected


def validate_cross_dependencies(
    candidates: Iterable[BacklogCandidate],
    *,
    package_ids: Iterable[str] | None = None,
) -> list[str]:
    """
    Valida dependencias cruzadas de um pacote candidato.

    Regras:
    - dependencia_inexistente: dependencia nao encontrada na base candidata
    - dependencia_fora_do_pacote: dependencia existe, mas esta fora do pacote alvo
    - dependencia_circular: ciclo detectado entre itens do pacote
    """
    candidate_list = list(candidates)
    candidate_map = {candidate.id: candidate for candidate in candidate_list}
    if package_ids is None:
        scoped_ids = set(candidate_map.keys())
    else:
        scoped_ids = set(package_ids)

    issues: set[str] = set()

    for item_id in sorted(scoped_ids):
        candidate = candidate_map.get(item_id)
        if candidate is None:
            issues.add(f"item_inexistente_no_pacote:{item_id}")
            continue

        for dep_id in sorted(candidate.dependencies):
            dependency = candidate_map.get(dep_id)
            if dependency is None:
                issues.add(f"dependencia_inexistente:{item_id}->{dep_id}")
                continue
            if dep_id not in scoped_ids:
                issues.add(f"dependencia_fora_do_pacote:{item_id}->{dep_id}")

    visited: set[str] = set()
    visiting: set[str] = set()
    path: list[str] = []

    def _dfs(node_id: str) -> None:
        visiting.add(node_id)
        path.append(node_id)
        node = candidate_map[node_id]

        for dep_id in node.dependencies:
            if dep_id not in scoped_ids or dep_id not in candidate_map:
                continue

            if dep_id in visiting:
                start = path.index(dep_id)
                cycle_path = path[start:] + [dep_id]
                issues.add(f"dependencia_circular:{'->'.join(cycle_path)}")
                continue

            if dep_id not in visited:
                _dfs(dep_id)

        path.pop()
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in sorted(scoped_ids):
        if node_id in candidate_map and node_id not in visited:
            _dfs(node_id)

    return sorted(issues)


def get_stage_limits_catalog() -> dict[str, StageLimit]:
    return dict(_STAGE_LIMITS)


def validate_stage_limits(*, stage: str, payload_chars: int, items_in_batch: int) -> list[str]:
    normalized_stage = stage.strip().lower()
    limit = _STAGE_LIMITS.get(normalized_stage)
    if limit is None:
        raise ValueError("stage_invalido")

    errors: list[str] = []
    if payload_chars > limit.max_payload_chars:
        errors.append("payload_excede_limite_do_stage")
    if items_in_batch > limit.max_parallel_items:
        errors.append("itens_excedem_capacidade_do_stage")
    return errors


def apply_sprint_capacity_gate(
    package: Iterable[BacklogCandidate],
    *,
    sprint_capacity: int,
) -> SprintCapacityPlan:
    if sprint_capacity <= 0:
        raise ValueError("sprint_capacity_invalida")

    package_list = list(package)
    scheduled = tuple(package_list[:sprint_capacity])
    deferred_items = package_list[sprint_capacity:]
    deferred = tuple(
        DeferredPackageItem(
            id=item.id,
            reason_code="capacidade_sprint_excedida",
            justification=f"Item adiado por limite da sprint ({sprint_capacity}).",
        )
        for item in deferred_items
    )

    return SprintCapacityPlan(
        sprint_capacity=sprint_capacity,
        scheduled=scheduled,
        deferred=deferred,
    )


def build_stage_progress_snapshot(
    *,
    item_id: str,
    stage: str,
    status: str,
    decision: str,
    note: str = "",
) -> StageProgressSnapshot:
    normalized_item_id = item_id.strip()
    normalized_stage = stage.strip().lower()
    normalized_status = status.strip().upper()
    normalized_decision = decision.strip().upper()

    if not normalized_item_id:
        raise ValueError("item_id_invalido")
    if not normalized_stage:
        raise ValueError("stage_invalido")
    if not normalized_status:
        raise ValueError("status_invalido")
    if not normalized_decision:
        raise ValueError("decision_invalida")

    return StageProgressSnapshot(
        item_id=normalized_item_id,
        stage=normalized_stage,
        status=normalized_status,
        decision=normalized_decision,
        note=note.strip(),
        updated_at=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )


def append_stage_progress_snapshot(
    *,
    output_path: Path | str,
    snapshot: StageProgressSnapshot,
) -> None:
    target = Path(output_path)
    row = {
        "item_id": snapshot.item_id,
        "stage": snapshot.stage,
        "status": snapshot.status,
        "decision": snapshot.decision,
        "note": snapshot.note,
        "updated_at": snapshot.updated_at,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=True) + "\n")


def evaluate_aggregate_payload_gate(
    handoffs: Iterable[Mapping[str, Any]],
    *,
    limit_chars: int,
) -> AggregatePayloadGateResult:
    if limit_chars <= 0:
        raise ValueError("limit_chars_invalido")

    entries_list: list[PackagePayloadEntry] = []
    for index, handoff in enumerate(handoffs, start=1):
        item_id_raw = str(handoff.get("id", "")).strip()
        item_id = item_id_raw if item_id_raw else f"payload_{index}"
        payload_chars = len(str(dict(handoff)))
        entries_list.append(PackagePayloadEntry(item_id=item_id, payload_chars=payload_chars))

    total_chars = sum(entry.payload_chars for entry in entries_list)
    overflow = max(0, total_chars - limit_chars)
    requires_compaction = overflow > 0

    compaction_candidates: list[str] = []
    if requires_compaction:
        recovered_chars = 0
        for entry in sorted(entries_list, key=lambda value: value.payload_chars, reverse=True):
            compaction_candidates.append(entry.item_id)
            recovered_chars += entry.payload_chars
            if recovered_chars >= overflow:
                break

    return AggregatePayloadGateResult(
        total_payload_chars=total_chars,
        limit_chars=limit_chars,
        overflow_chars=overflow,
        requires_compaction=requires_compaction,
        compaction_candidates=tuple(compaction_candidates),
        entries=tuple(entries_list),
    )


def verify_guardrail_diff(
    *,
    diff_text: str,
    evidences_by_guardrail: Mapping[str, Iterable[str] | str] | None = None,
) -> GuardrailDiffCheckResult:
    if evidences_by_guardrail is None:
        evidences_by_guardrail = {}

    normalized_diff = diff_text.lower()
    touched: list[str] = []

    sensitive_patterns = (
        ("risk_gate", r"\brisk[_ ]?gate(?:\b|_)"),
        ("circuit_breaker", r"\bcircuit[_ ]?breaker(?:\b|_)"),
        ("decision_id", r"\bdecision[_ ]?id\b|\bidempot"),
    )
    for guardrail, pattern in sensitive_patterns:
        if re.search(pattern, normalized_diff):
            touched.append(guardrail)

    touched_sorted = tuple(sorted(set(touched)))
    missing: list[str] = []

    for guardrail in touched_sorted:
        raw_evidence = evidences_by_guardrail.get(guardrail)
        evidence_items: list[str]
        if isinstance(raw_evidence, str):
            evidence_items = [raw_evidence.strip()] if raw_evidence.strip() else []
        elif raw_evidence is None:
            evidence_items = []
        else:
            evidence_items = [str(item).strip() for item in raw_evidence if str(item).strip()]

        if not evidence_items:
            missing.append(guardrail)

    blocked = bool(missing)
    required = tuple(touched_sorted)
    return GuardrailDiffCheckResult(
        blocked=blocked,
        touched_guardrails=touched_sorted,
        missing_evidences=tuple(missing),
        required_evidences=required,
    )
