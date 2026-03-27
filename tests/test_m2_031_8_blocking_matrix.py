"""RED->GREEN suite for M2-031.8 blocking matrix by devolucao type."""

from __future__ import annotations

from pathlib import Path


def test_resolve_blocked_routing_tl_devolvido_returns_to_se() -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    routing = DevCycleExecutor.resolve_blocked_routing(
        stage_name="Tech Lead",
        decision="DEVOLVIDO_PARA_REVISAO",
        motivo="guardrail ausente",
    )

    assert routing.return_stage == "Software Engineer"
    assert routing.reason_code == "tl_devolvido_para_se"


def test_resolve_blocked_routing_pm_devolver_doc_reason_returns_to_doc_advocate() -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    routing = DevCycleExecutor.resolve_blocked_routing(
        stage_name="Project Manager",
        decision="DEVOLVER_PARA_AJUSTE",
        motivo="ajuste de doc e sync pendente",
    )

    assert routing.return_stage == "Doc Advocate"
    assert routing.reason_code == "pm_ajuste_documentacao"


def test_executor_returns_matrix_fields_on_blocked_stage(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"

    def _devolver(_: dict[str, object]) -> dict[str, object]:
        return {"decision": "DEVOLVER_PARA_AJUSTE", "motivo": "mypy regressao no pacote"}

    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=None)
    result = executor.run(
        item_id="M2-031.8",
        stages=[("Project Manager", _devolver)],
    )

    assert result["status"] == "AGUARDANDO_CORRECAO"
    assert result["return_stage"] == "Tech Lead"
    assert result["return_action"] == "RETORNAR_STAGE_ESPECIFICO"
    assert result["return_reason_code"] == "pm_ajuste_validacao_tecnica"


def test_executor_keeps_same_stage_for_non_special_devolvido() -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    routing = DevCycleExecutor.resolve_blocked_routing(
        stage_name="Solution Architect",
        decision="DEVOLVIDO_PARA_REVISAO",
        motivo="payload incompleto",
    )

    assert routing.return_stage == "Solution Architect"
    assert routing.action == "REEXECUTAR_STAGE_ATUAL"
