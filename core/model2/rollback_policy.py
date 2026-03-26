"""Politica de rollback operacional por severidade para M2-024.14.

Define acoes claras para interrupcao, observacao e retomada segura
pos-incidente, baseado na severidade do evento.
"""

from __future__ import annotations

ROLLBACK_ACTION_INTERRUPT = "INTERRUPT_AND_HALT"
ROLLBACK_ACTION_OBSERVE = "OBSERVE_AND_ALERT"
ROLLBACK_ACTION_LOG = "LOG_ONLY"

_SEVERITY_TO_ACTION: dict[str, str] = {
    "CRITICAL": ROLLBACK_ACTION_INTERRUPT,
    "HIGH": ROLLBACK_ACTION_INTERRUPT,
    "MEDIUM": ROLLBACK_ACTION_OBSERVE,
    "LOW": ROLLBACK_ACTION_LOG,
    "INFO": ROLLBACK_ACTION_LOG,
}

_SAFE_TO_RESUME: dict[str, bool] = {
    ROLLBACK_ACTION_INTERRUPT: False,
    ROLLBACK_ACTION_OBSERVE: False,
    ROLLBACK_ACTION_LOG: True,
}


def get_rollback_action(*, severity: str) -> str:
    """Retorna acao de rollback para a severidade informada.

    Args:
        severity: nivel de severidade (CRITICAL|HIGH|MEDIUM|LOW|INFO)

    Returns:
        acao de rollback; INTERRUPT_AND_HALT para severidades desconhecidas
        (fail-safe conservador).
    """
    return _SEVERITY_TO_ACTION.get(severity.upper() if severity else "", ROLLBACK_ACTION_INTERRUPT)


def evaluate_rollback(*, severity: str, reason_code: str) -> dict[str, object]:
    """Avalia politica de rollback para um evento de incidente.

    Args:
        severity: nivel de severidade do evento
        reason_code: codigo de razao do evento (do REASON_CODE_CATALOG)

    Returns:
        dict com:
        - action: acao recomendada (INTERRUPT_AND_HALT|OBSERVE_AND_ALERT|LOG_ONLY)
        - severity: severidade recebida
        - reason_code: reason_code recebido
        - safe_to_resume: True se retomada automatica eh segura
        - alert_message: mensagem de alerta para operador

    Guardrail: nunca levanta excecao.
    """
    try:
        action = get_rollback_action(severity=severity)
        safe = _SAFE_TO_RESUME.get(action, False)

        if action == ROLLBACK_ACTION_INTERRUPT:
            alert = (
                f"[ROLLBACK] {severity}/{reason_code}: interrupcao obrigatoria. "
                "Intervencao manual necessaria antes de retomada."
            )
        elif action == ROLLBACK_ACTION_OBSERVE:
            alert = (
                f"[ROLLBACK] {severity}/{reason_code}: monitoramento ativo. "
                "Retomada somente apos confirmacao manual."
            )
        else:
            alert = (
                f"[ROLLBACK] {severity}/{reason_code}: evento registrado. "
                "Operacao continua normalmente."
            )

        return {
            "action": action,
            "severity": severity,
            "reason_code": reason_code,
            "safe_to_resume": safe,
            "alert_message": alert,
        }
    except Exception:
        return {
            "action": ROLLBACK_ACTION_INTERRUPT,
            "severity": severity,
            "reason_code": reason_code,
            "safe_to_resume": False,
            "alert_message": "[ROLLBACK] Erro ao avaliar politica; interrupcao por fail-safe.",
        }
