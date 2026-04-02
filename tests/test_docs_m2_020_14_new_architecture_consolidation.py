"""Suite RED — M2-020.14: Consolidar documentacao da nova arquitetura.

Todos os testes desta suite devem guiar a consolidacao documental do estado
model-driven vigente do M2, sem alterar codigo de runtime.

Mapeamento requisito -> teste:
  RF-001 -> test_backlog_m2_020_14_define_escopo_documental_model_driven
  RF-002 -> test_arquitetura_alvo_reforca_fluxo_nominal_sem_legado_nominal
  RF-003 -> test_regras_negocio_refletem_decisao_direta_do_modelo
  RF-004 -> test_runbook_conecta_operacao_ao_que_operador_ve_em_iniciar_bat
  RF-005 -> test_prd_formaliza_promessa_operacional_model_driven
  RF-006 -> test_sync_registra_consolidacao_m2_020_14
  RNF-001 -> test_docs_m2_020_14_respeitam_fail_safe_e_guardrails
  RNF-002 -> test_docs_m2_020_14_nao_contradizem_origem_model_driven
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG = REPO_ROOT / "docs" / "BACKLOG.md"
ARQUITETURA = REPO_ROOT / "docs" / "ARQUITETURA_ALVO.md"
REGRAS = REPO_ROOT / "docs" / "REGRAS_DE_NEGOCIO.md"
RUNBOOK = REPO_ROOT / "docs" / "RUNBOOK_M2_OPERACAO.md"
PRD = REPO_ROOT / "docs" / "PRD.md"
ADRS = REPO_ROOT / "docs" / "ADRS.md"
DIAGRAMAS = REPO_ROOT / "docs" / "DIAGRAMAS.md"
MODELAGEM = REPO_ROOT / "docs" / "MODELAGEM_DE_DADOS.md"
SYNC = REPO_ROOT / "docs" / "SYNCHRONIZATION.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.docs
def test_backlog_m2_020_14_define_escopo_documental_model_driven() -> None:
    text = _read(BACKLOG)
    assert "### TAREFA M2-020.14 - Consolidar documentacao da nova arquitetura" in text
    assert "Status: Em analise" in text or "Status: TESTES_PRONTOS" in text
    assert "Atualizar docs tecnicos e runbook para fluxo model-driven" in text
    assert "Fontes de verdade do M2 refletem decisao direta do modelo" in text


@pytest.mark.docs
def test_backlog_m2_020_14_lista_escopo_documental_ampliado() -> None:
    text = _read(BACKLOG)
    assert "Escopo documental ampliado:" in text
    assert "`docs/ADRS.md`" in text
    assert "`docs/DIAGRAMAS.md`" in text
    assert "`docs/MODELAGEM_DE_DADOS.md`" in text


@pytest.mark.docs
def test_arquitetura_alvo_reforca_fluxo_nominal_sem_legado_nominal() -> None:
    text = _read(ARQUITETURA)
    assert "M2-020.14" in text
    assert "fluxo nominal" in text.lower()
    assert "decisao direta do modelo" in text.lower()
    assert "legado heuristico" in text.lower()


@pytest.mark.docs
def test_regras_negocio_refletem_decisao_direta_do_modelo() -> None:
    text = _read(REGRAS)
    assert "M2-020.14" in text
    assert "decisao oficial exibida ao operador" in text.lower()
    assert "model-driven" in text.lower()
    assert "risk_gate" in text
    assert "circuit_breaker" in text


@pytest.mark.docs
def test_runbook_conecta_operacao_ao_que_operador_ve_em_iniciar_bat() -> None:
    text = _read(RUNBOOK)
    assert "M2-020.14" in text
    assert "iniciar.bat" in text
    assert "source=RL_MODEL" in text or "source = RL_MODEL" in text
    assert "decision_id" in text
    assert "reason_code" in text


@pytest.mark.docs
def test_prd_formaliza_promessa_operacional_model_driven() -> None:
    text = _read(PRD)
    assert "M2-020.14" in text
    assert "decisao direta do modelo" in text.lower()
    assert "iniciar.bat" in text
    assert "observabilidade" in text.lower()


@pytest.mark.docs
def test_sync_registra_consolidacao_m2_020_14() -> None:
    text = _read(SYNC)
    assert "M2-020.14" in text
    assert "docs/ARQUITETURA_ALVO.md" in text
    assert "docs/ADRS.md" in text
    assert "docs/DIAGRAMAS.md" in text
    assert "docs/MODELAGEM_DE_DADOS.md" in text
    assert "docs/REGRAS_DE_NEGOCIO.md" in text
    assert "docs/RUNBOOK_M2_OPERACAO.md" in text
    assert "docs/PRD.md" in text


@pytest.mark.docs
def test_docs_m2_020_14_respeitam_fail_safe_e_guardrails() -> None:
    joined = "\n".join([
        _read(ARQUITETURA),
        _read(REGRAS),
        _read(RUNBOOK),
    ]).lower()
    assert "fail-safe" in joined
    assert "risk_gate" in joined
    assert "circuit_breaker" in joined
    assert "decision_id" in joined


@pytest.mark.docs
def test_docs_m2_020_14_nao_contradizem_origem_model_driven() -> None:
    joined = "\n".join([
        _read(ARQUITETURA),
        _read(REGRAS),
        _read(PRD),
        _read(RUNBOOK),
    ]).lower()
    assert "decisao direta do modelo" in joined
    assert "origem nominal puramente model-driven" in joined
