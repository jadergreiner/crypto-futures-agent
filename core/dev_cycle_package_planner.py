from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class BacklogCandidate:
    id: str
    title: str
    valor: float
    urgencia: float
    reducao_risco: float
    esforco: float
    dependencies: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StageLimit:
    stage: str
    max_payload_chars: int
    max_parallel_items: int


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

        ready.sort(key=lambda item: (-calculate_priority_score(item), item.id))
        chosen = ready[0]
        selected.append(chosen)
        selected_ids.add(chosen.id)
        remaining.pop(chosen.id, None)

    return selected


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
