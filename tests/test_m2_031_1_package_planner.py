"""RED->GREEN suite for M2-031.1 package planner (20 items)."""

from __future__ import annotations

from core.dev_cycle_package_planner import (
    BacklogCandidate,
    build_development_package,
    calculate_priority_score,
)


def test_calculate_priority_score_uses_po_formula() -> None:
    candidate = BacklogCandidate(
        id="M2-031.1",
        title="Teste",
        valor=5.0,
        urgencia=4.0,
        reducao_risco=5.0,
        esforco=2.0,
    )
    assert calculate_priority_score(candidate) == 4.05


def test_build_development_package_returns_exactly_20_items_when_available() -> None:
    candidates = [
        BacklogCandidate(
            id=f"M2-031.{i}",
            title=f"Item {i}",
            valor=5.0 if i <= 20 else 1.0,
            urgencia=5.0 if i <= 20 else 1.0,
            reducao_risco=5.0 if i <= 20 else 1.0,
            esforco=1.0,
        )
        for i in range(1, 26)
    ]

    package = build_development_package(candidates, package_size=20)

    assert len(package) == 20
    ids = [item.id for item in package]
    assert "M2-031.25" not in ids


def test_build_development_package_respects_dependency_order() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.1",
            title="Base",
            valor=3.0,
            urgencia=3.0,
            reducao_risco=3.0,
            esforco=1.0,
        ),
        BacklogCandidate(
            id="M2-031.2",
            title="Depende da base",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=1.0,
            dependencies=("M2-031.1",),
        ),
    ]

    package = build_development_package(candidates, package_size=2)
    ids = [item.id for item in package]

    assert ids == ["M2-031.1", "M2-031.2"]


def test_build_development_package_fails_safe_on_circular_dependency() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.1",
            title="A",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=1.0,
            dependencies=("M2-031.2",),
        ),
        BacklogCandidate(
            id="M2-031.2",
            title="B",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=1.0,
            dependencies=("M2-031.1",),
        ),
    ]

    package = build_development_package(candidates, package_size=20)
    assert package == []

