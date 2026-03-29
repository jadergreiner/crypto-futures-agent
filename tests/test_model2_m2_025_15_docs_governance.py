from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG = REPO_ROOT / "docs" / "BACKLOG.md"
ARCH = REPO_ROOT / "docs" / "ARQUITETURA_ALVO.md"
ADRS = REPO_ROOT / "docs" / "ADRS.md"
DIAGRAMS = REPO_ROOT / "docs" / "DIAGRAMAS.md"
DATA_MODEL = REPO_ROOT / "docs" / "MODELAGEM_DE_DADOS.md"
PRD = REPO_ROOT / "docs" / "PRD.md"
RULES = REPO_ROOT / "docs" / "REGRAS_DE_NEGOCIO.md"
RUNBOOK = REPO_ROOT / "docs" / "RUNBOOK_M2_OPERACAO.md"
SYNC = REPO_ROOT / "docs" / "SYNCHRONIZATION.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.docs
def test_m2_025_15_backlog_marks_testes_prontos_and_qa_suite() -> None:
    text = _read(BACKLOG)
    assert "### TAREFA M2-025.15 - Governanca e auditoria documental do pacote" in text
    assert (
        "Status: TESTES_PRONTOS" in text
        or "Status: EM_DESENVOLVIMENTO" in text
        or "Status: IMPLEMENTADO" in text
        or "Status: REVISADO_APROVADO" in text
        or "Status: CONCLUIDO" in text
    )
    assert "Escopo documental ampliado:" in text
    assert "QA: Suite RED em tests/test_model2_m2_025_15_docs_governance.py" in text


@pytest.mark.docs
def test_m2_025_15_architecture_closure_is_documented() -> None:
    text = _read(ARCH)
    assert "M2-025.15" in text
    assert "governanca documental" in text.lower()
    assert "docs/ADRS.md" in text
    assert "docs/DIAGRAMAS.md" in text


@pytest.mark.docs
def test_m2_025_15_adrs_has_explicit_traceability_record() -> None:
    text = _read(ADRS)
    assert "M2-025.15" in text
    assert "governanca documental" in text.lower()
    assert "SYNCHRONIZATION" in text


@pytest.mark.docs
def test_m2_025_15_diagramas_references_cross_doc_sync() -> None:
    text = _read(DIAGRAMS)
    assert "M2-025.15" in text
    assert "ARQUITETURA_ALVO" in text
    assert "REGRAS_DE_NEGOCIO" in text
    assert "RUNBOOK_M2_OPERACAO" in text


@pytest.mark.docs
def test_m2_025_15_modelagem_and_prd_are_aligned() -> None:
    model_text = _read(DATA_MODEL)
    prd_text = _read(PRD)
    assert "M2-025.15" in model_text
    assert "M2-025.15" in prd_text
    assert "governanca documental" in model_text.lower()
    assert "governanca documental" in prd_text.lower()


@pytest.mark.docs
def test_m2_025_15_rules_preserve_guardrails_in_new_governance_rule() -> None:
    text = _read(RULES)
    assert "M2-025.15" in text
    assert "risk_gate" in text
    assert "circuit_breaker" in text
    assert "decision_id" in text


@pytest.mark.docs
def test_m2_025_15_runbook_has_troubleshooting_linked_to_iniciar_logs() -> None:
    text = _read(RUNBOOK)
    assert "M2-025.15" in text
    assert "iniciar.bat" in text
    assert "startup_log.txt" in text
    assert "m2_cycle.log" in text
    assert "checklist" in text.lower()


@pytest.mark.docs
def test_m2_025_15_sync_registers_qa_red_entry_with_all_docs() -> None:
    text = _read(SYNC)
    assert "[SYNC-282]" in text
    assert "M2-025.15" in text
    assert "4.qa-tdd" in text
    assert "tests/test_model2_m2_025_15_docs_governance.py" in text
    assert "docs/ARQUITETURA_ALVO.md" in text
    assert "docs/ADRS.md" in text
    assert "docs/DIAGRAMAS.md" in text
    assert "docs/MODELAGEM_DE_DADOS.md" in text
    assert "docs/PRD.md" in text
    assert "docs/REGRAS_DE_NEGOCIO.md" in text
    assert "docs/RUNBOOK_M2_OPERACAO.md" in text
    assert "docs/SYNCHRONIZATION.md" in text
