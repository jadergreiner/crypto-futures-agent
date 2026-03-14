import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG_PATH = REPO_ROOT / "docs" / "BACKLOG.md"


def _task_blocks(markdown: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^###\s+TAREFA\s+([^\n]+)$", markdown, flags=re.MULTILINE))
    blocks: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        blocks.append((match.group(1).strip(), markdown[start:end]))
    return blocks


def _is_path_like(token: str) -> bool:
    normalized = token.strip()
    if "/" in normalized or "\\" in normalized:
        return True
    return bool(re.search(r"\.[A-Za-z0-9]+$", normalized))


def test_concluded_backlog_tasks_have_existing_evidence_paths() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    blocks = _task_blocks(text)
    assert blocks, "No task blocks found in docs/BACKLOG.md"

    for task_name, block in blocks:
        status_match = re.search(r"^Status:\s*(.+)$", block, flags=re.MULTILINE)
        assert status_match is not None, f"Missing Status line in task: {task_name}"
        status = status_match.group(1).strip()
        if not status.startswith("CONCLUIDA"):
            continue

        assert "Evidencias:" in block, f"Missing Evidencias section in concluded task: {task_name}"
        evidence_section = block.split("Evidencias:", maxsplit=1)[1]
        evidence_paths = re.findall(r"`([^`]+)`", evidence_section)
        assert evidence_paths, f"Missing evidence paths in concluded task: {task_name}"

        for rel_path in evidence_paths:
            normalized = rel_path.strip().rstrip(".,")
            if not normalized:
                continue
            if not _is_path_like(normalized):
                continue
            if "*" in normalized or "?" in normalized:
                matches = list(REPO_ROOT.glob(normalized))
                if matches:
                    continue
                parent = (REPO_ROOT / normalized).parent.resolve()
                assert parent.exists(), (
                    f"Wildcard evidence parent does not exist for task '{task_name}': {normalized}"
                )
                continue

            absolute = (REPO_ROOT / normalized).resolve()
            assert absolute.exists(), (
                f"Evidence path does not exist for task '{task_name}': {normalized}"
            )


def test_m2_006_subtasks_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "INICIATIVA M2-006 - Ponte de Sinal" in text
    assert "M2-006.1.1" in text
    assert "M2-006.1.2" in text
    assert "M2-006.1.3" in text
    assert "M2-006.1.4" in text


def test_m2_007_adapter_task_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "INICIATIVA M2-007 - Integracao com execucao" in text
    assert "TAREFA M2-007.2 - Adaptar technical_signals para trade_signals legado" in text


def test_m2_007_observability_task_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "TAREFA M2-007.3 - Observabilidade do fluxo de sinais" in text


def test_m2_008_daily_pipeline_task_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "INICIATIVA M2-008 - Orquestracao operacional" in text
    assert "TAREFA M2-008.1 - Orquestrar pipeline diario ponta a ponta" in text


def test_m2_008_scheduled_execution_task_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "TAREFA M2-008.2 - Operacionalizar execucao agendada" in text


def test_m2_008_operational_hardening_task_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "TAREFA M2-008.3 - Hardening operacional (monitoramento e alertas)" in text


def test_m2_009_live_execution_tasks_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "INICIATIVA M2-009 - Execucao real nativa" in text
    assert "TAREFA M2-009.1 - Modelar ciclo de vida de execucao" in text
    assert "TAREFA M2-009.2 - Gate live do M2" in text
    assert "TAREFA M2-009.3 - Executor de entrada MARKET" in text
    assert "TAREFA M2-009.4 - Fail-safe de protecao" in text


def test_m2_010_live_reconcile_tasks_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "INICIATIVA M2-010 - Reconciliacao e observabilidade live" in text
    assert "TAREFA M2-010.1 - Reconciliador de ordens e posicoes" in text
    assert "TAREFA M2-010.2 - Dashboard live" in text
    assert "TAREFA M2-010.3 - Healthcheck e runbook" in text


def test_m2_011_m2_013_phase2_delivery_tracks_declared_in_backlog() -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    assert "INICIATIVA M2-011 - Orquestracao operacional live" in text
    assert "TAREFA M2-011.1 - Runner live_execute" in text
    assert "TAREFA M2-011.2 - Runner live_reconcile" in text
    assert "TAREFA M2-011.3 - Runner live_cycle" in text
    assert "INICIATIVA M2-012 - Hardening de risco" in text
    assert "TAREFA M2-012.1 - Contadores persistidos no M2" in text
    assert "TAREFA M2-012.2 - Configuracao explicita de ativacao" in text
    assert "TAREFA M2-012.3 - Exclusividade por simbolo" in text
    assert "INICIATIVA M2-013 - Documentacao canonica da Fase 2" in text
    assert "INICIATIVA M2-014 - Automacao de go-live da Fase 2" in text
    assert "TAREFA M2-014.1 - Runner unico de preflight para go-live" in text
    assert "Criterios de pronto para a Fase 2" in text
    assert "Go-live checklist da Fase 2" in text

