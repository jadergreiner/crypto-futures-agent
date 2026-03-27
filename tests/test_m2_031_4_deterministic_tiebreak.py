"""RED->GREEN suite for M2-031.4 deterministic tie-break."""

from __future__ import annotations

from core.dev_cycle_package_planner import BacklogCandidate, build_development_package


def test_tiebreak_prefers_higher_residual_risk_when_score_is_equal() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.4-A",
            title="A",
            valor=5.0,
            urgencia=4.0,
            reducao_risco=4.0,
            esforco=2.0,
            risco_residual=1.0,
        ),
        BacklogCandidate(
            id="M2-031.4-B",
            title="B",
            valor=5.0,
            urgencia=4.0,
            reducao_risco=4.0,
            esforco=2.0,
            risco_residual=3.0,
        ),
    ]

    package = build_development_package(candidates, package_size=1)
    assert [item.id for item in package] == ["M2-031.4-B"]


def test_tiebreak_uses_id_when_score_and_residual_risk_are_equal() -> None:
    candidates = [
        BacklogCandidate(
            id="M2-031.4-B",
            title="B",
            valor=5.0,
            urgencia=4.0,
            reducao_risco=4.0,
            esforco=2.0,
            risco_residual=2.0,
        ),
        BacklogCandidate(
            id="M2-031.4-A",
            title="A",
            valor=5.0,
            urgencia=4.0,
            reducao_risco=4.0,
            esforco=2.0,
            risco_residual=2.0,
        ),
    ]

    package = build_development_package(candidates, package_size=2)
    assert [item.id for item in package] == ["M2-031.4-A", "M2-031.4-B"]
