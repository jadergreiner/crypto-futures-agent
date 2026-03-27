"""RED->GREEN suite for M2-031.3 cross-dependency validator."""

from __future__ import annotations

from core.dev_cycle_package_planner import BacklogCandidate, validate_cross_dependencies


def test_validate_cross_dependencies_returns_empty_for_valid_package() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.1",
            title="Base",
            valor=4.0,
            urgencia=4.0,
            reducao_risco=4.0,
            esforco=2.0,
        ),
        BacklogCandidate(
            id="M2-031.3",
            title="Validador",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=2.0,
            dependencies=("M2-031.1",),
        ),
    ]

    issues = validate_cross_dependencies(candidates)
    assert issues == []


def test_validate_cross_dependencies_flags_missing_dependency() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.3",
            title="Validador",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=2.0,
            dependencies=("M2-031.99",),
        ),
    ]

    issues = validate_cross_dependencies(candidates)
    assert issues == ["dependencia_inexistente:M2-031.3->M2-031.99"]


def test_validate_cross_dependencies_flags_dependency_outside_package_scope() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.1",
            title="Base",
            valor=4.0,
            urgencia=4.0,
            reducao_risco=4.0,
            esforco=2.0,
        ),
        BacklogCandidate(
            id="M2-031.3",
            title="Validador",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=2.0,
            dependencies=("M2-031.1",),
        ),
    ]

    issues = validate_cross_dependencies(candidates, package_ids=("M2-031.3",))
    assert issues == ["dependencia_fora_do_pacote:M2-031.3->M2-031.1"]


def test_validate_cross_dependencies_flags_circular_dependency() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.3",
            title="A",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=2.0,
            dependencies=("M2-031.4",),
        ),
        BacklogCandidate(
            id="M2-031.4",
            title="B",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=2.0,
            dependencies=("M2-031.3",),
        ),
    ]

    issues = validate_cross_dependencies(candidates)
    assert issues == ["dependencia_circular:M2-031.3->M2-031.4->M2-031.3"]


def test_validate_cross_dependencies_flags_unknown_item_in_scope() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.3",
            title="Validador",
            valor=5.0,
            urgencia=5.0,
            reducao_risco=5.0,
            esforco=2.0,
        ),
    ]

    issues = validate_cross_dependencies(candidates, package_ids=("M2-031.3", "M2-031.20"))
    assert issues == ["item_inexistente_no_pacote:M2-031.20"]
