from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


STAGE_TL_DA = "tl_da"
STAGE_DA_PM = "da_pm"


@dataclass(frozen=True)
class HandoffValidationResult:
    is_valid: bool
    stage: str
    payload_size_chars: int
    errors: list[str]


def _normalize_stage(stage: str) -> str:
    normalized = stage.strip().lower()
    if normalized not in {STAGE_TL_DA, STAGE_DA_PM}:
        raise ValueError("stage_invalido")
    return normalized


def _split_items(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(";") if part.strip()]
    return []


def _as_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def parse_handoff_text(text: str) -> dict[str, str]:
    """Extrai pares chave:valor de payloads em formato de lista markdown."""
    payload: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace(" ", "_")
        payload[normalized_key] = value.strip()
    return payload


def validate_handoff_payload(stage: str, payload: Mapping[str, Any]) -> HandoffValidationResult:
    normalized_stage = _normalize_stage(stage)
    errors: list[str] = []

    payload_size_chars = len(str(dict(payload)))
    if payload_size_chars > 1800:
        errors.append("payload_excede_limite_1800_chars")

    if normalized_stage == STAGE_TL_DA:
        _validate_tl_da(payload, errors)
    else:
        _validate_da_pm(payload, errors)

    return HandoffValidationResult(
        is_valid=not errors,
        stage=normalized_stage,
        payload_size_chars=payload_size_chars,
        errors=errors,
    )


def _validate_tl_da(payload: Mapping[str, Any], errors: list[str]) -> None:
    required = [
        "id",
        "decisao",
        "status_backlog",
        "resumo_tecnico",
        "docs_impactadas",
        "evidencias",
        "guardrails",
        "pendencias",
    ]
    _validate_required_fields(payload, required, errors)

    if _as_text(payload.get("decisao")) != "APROVADO":
        errors.append("decisao_invalida_tl_da")

    if _as_text(payload.get("status_backlog")) != "REVISADO_APROVADO":
        errors.append("status_backlog_invalido_tl_da")

    if len(_as_text(payload.get("id"))) > 20:
        errors.append("id_excede_20_chars")

    if len(_as_text(payload.get("resumo_tecnico"))) > 300:
        errors.append("resumo_tecnico_excede_300_chars")

    docs = _split_items(payload.get("docs_impactadas"))
    if len(docs) < 1 or len(docs) > 8:
        errors.append("docs_impactadas_fora_do_intervalo_1_8")

    evidencias = _split_items(payload.get("evidencias"))
    if len(evidencias) < 1 or len(evidencias) > 8:
        errors.append("evidencias_fora_do_intervalo_1_8")

    guardrails = _as_text(payload.get("guardrails")).lower()
    for guardrail in ("risk_gate", "circuit_breaker", "decision_id"):
        if guardrail not in guardrails:
            errors.append(f"guardrail_ausente_{guardrail}")

    pendencias = _split_items(payload.get("pendencias"))
    if len(pendencias) > 4:
        errors.append("pendencias_excede_4_itens")


def _validate_da_pm(payload: Mapping[str, Any], errors: list[str]) -> None:
    required = [
        "id",
        "status_backlog",
        "recomendacao",
        "resumo_executivo",
        "docs_atualizadas",
        "sync",
        "validacoes",
        "pendencias",
    ]
    _validate_required_fields(payload, required, errors)

    if len(_as_text(payload.get("id"))) > 20:
        errors.append("id_excede_20_chars")

    if _as_text(payload.get("status_backlog")) != "REVISADO_APROVADO":
        errors.append("status_backlog_invalido_da_pm")

    recomendacao = _as_text(payload.get("recomendacao"))
    if recomendacao not in {"ACEITE_RECOMENDADO", "DEVOLVER_PARA_AJUSTE"}:
        errors.append("recomendacao_invalida_da_pm")

    if len(_as_text(payload.get("resumo_executivo"))) > 350:
        errors.append("resumo_executivo_excede_350_chars")

    docs = _split_items(payload.get("docs_atualizadas"))
    if len(docs) < 1 or len(docs) > 10:
        errors.append("docs_atualizadas_fora_do_intervalo_1_10")

    validacoes = _split_items(payload.get("validacoes"))
    if len(validacoes) < 1 or len(validacoes) > 6:
        errors.append("validacoes_fora_do_intervalo_1_6")

    pendencias = _split_items(payload.get("pendencias"))
    if len(pendencias) > 5:
        errors.append("pendencias_excede_5_itens")


def _validate_required_fields(
    payload: Mapping[str, Any], required: list[str], errors: list[str]
) -> None:
    for field in required:
        value = payload.get(field)
        if value is None:
            errors.append(f"campo_obrigatorio_ausente_{field}")
            continue
        if isinstance(value, str) and not value.strip():
            errors.append(f"campo_obrigatorio_vazio_{field}")
