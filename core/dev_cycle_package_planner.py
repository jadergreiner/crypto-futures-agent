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

