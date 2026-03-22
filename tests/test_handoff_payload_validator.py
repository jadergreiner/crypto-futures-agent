from core.handoff_payload_validator import (
    STAGE_DA_PM,
    STAGE_TL_DA,
    parse_handoff_text,
    validate_handoff_payload,
)


def _payload_tl_da_valido() -> dict[str, str]:
    return {
        "id": "BLID-100",
        "decisao": "APROVADO",
        "status_backlog": "REVISADO_APROVADO",
        "resumo_tecnico": "Implementacao validada com testes e guardrails ativos",
        "docs_impactadas": "docs/BACKLOG.md; docs/SYNCHRONIZATION.md",
        "evidencias": "pytest ok; mypy ok",
        "guardrails": "risk_gate=ATIVO; circuit_breaker=ATIVO; decision_id=IDEMPOTENTE",
        "pendencias": "Nenhuma",
    }


def _payload_da_pm_valido() -> dict[str, str]:
    return {
        "id": "BLID-100",
        "status_backlog": "REVISADO_APROVADO",
        "recomendacao": "ACEITE_RECOMENDADO",
        "resumo_executivo": "Docs sincronizadas e validacoes concluidas sem pendencias",
        "docs_atualizadas": "docs/BACKLOG.md; docs/SYNCHRONIZATION.md",
        "sync": "sim (entry 2026-03-22)",
        "validacoes": "markdownlint ok; pytest docs sync ok",
        "pendencias": "Nenhuma",
    }


def test_validate_tl_da_payload_valido() -> None:
    result = validate_handoff_payload(STAGE_TL_DA, _payload_tl_da_valido())
    assert result.is_valid is True
    assert result.errors == []


def test_validate_tl_da_rejeita_decisao_invalida() -> None:
    payload = _payload_tl_da_valido()
    payload["decisao"] = "DEVOLVIDO"

    result = validate_handoff_payload(STAGE_TL_DA, payload)
    assert result.is_valid is False
    assert "decisao_invalida_tl_da" in result.errors


def test_validate_tl_da_rejeita_payload_maior_que_limite() -> None:
    payload = _payload_tl_da_valido()
    payload["resumo_tecnico"] = "x" * 1900

    result = validate_handoff_payload(STAGE_TL_DA, payload)
    assert result.is_valid is False
    assert "payload_excede_limite_1800_chars" in result.errors


def test_validate_da_pm_payload_valido() -> None:
    result = validate_handoff_payload(STAGE_DA_PM, _payload_da_pm_valido())
    assert result.is_valid is True
    assert result.errors == []


def test_validate_da_pm_rejeita_recomendacao_invalida() -> None:
    payload = _payload_da_pm_valido()
    payload["recomendacao"] = "GO"

    result = validate_handoff_payload(STAGE_DA_PM, payload)
    assert result.is_valid is False
    assert "recomendacao_invalida_da_pm" in result.errors


def test_parse_handoff_text_extrai_campos_para_validacao() -> None:
    payload_text = """
    - id: BLID-100
    - status_backlog: REVISADO_APROVADO
    - recomendacao: ACEITE_RECOMENDADO
    - resumo_executivo: resumo curto
    - docs_atualizadas: docs/BACKLOG.md; docs/SYNCHRONIZATION.md
    - sync: sim (entry)
    - validacoes: markdownlint ok; pytest ok
    - pendencias: Nenhuma
    """

    payload = parse_handoff_text(payload_text)
    result = validate_handoff_payload(STAGE_DA_PM, payload)

    assert result.is_valid is True
