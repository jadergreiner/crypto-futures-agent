from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG = REPO_ROOT / "docs" / "BACKLOG.md"
ARCH = REPO_ROOT / "docs" / "ARQUITETURA_ALVO.md"
RULES = REPO_ROOT / "docs" / "REGRAS_DE_NEGOCIO.md"
SYNC = REPO_ROOT / "docs" / "SYNCHRONIZATION.md"


@pytest.mark.docs
def test_m2_024_15_backlog_has_doc_section_and_doc_comment() -> None:
    text = BACKLOG.read_text(encoding="utf-8")
    assert "### TAREFA M2-024.15 - Governanca de docs e runbook do pacote M2-024" in text
    assert (
        "Status: TESTES_PRONTOS" in text
        or "Status: EM_DESENVOLVIMENTO" in text
        or "Status: IMPLEMENTADO" in text
        or "Status: REVISADO_APROVADO" in text
        or "Status: CONCLUIDO" in text
    )
    assert "QA: Suite RED em tests/test_model2_m2_024_15_docs_governance.py" in text


@pytest.mark.docs
def test_m2_024_15_architecture_documents_runbook_governance() -> None:
    text = ARCH.read_text(encoding="utf-8")
    assert "M2-024.15" in text
    assert "runbook unico do pacote M2-024" in text
    assert "matriz de guardrails" in text


@pytest.mark.docs
def test_m2_024_15_rules_adds_rn_029_docs_governance() -> None:
    text = RULES.read_text(encoding="utf-8")
    assert "### RN-029 - Governanca Documental do Pacote M2-024 (M2-024.15)" in text
    assert "risk_gate" in text
    assert "circuit_breaker" in text
    assert "decision_id" in text


@pytest.mark.docs
def test_m2_024_15_synchronization_registers_sync_entry() -> None:
    text = SYNC.read_text(encoding="utf-8")
    assert "[SYNC-174]" in text
    assert "M2-024.15" in text
    assert "docs/ARQUITETURA_ALVO.md" in text
    assert "docs/REGRAS_DE_NEGOCIO.md" in text
    assert "docs/BACKLOG.md" in text
