"""Suite RED M2-024.14: Politica de rollback operacional por severidade.

Objetivo: Definir politica de rollback por severidade com acoes claras para
interrupcao, observacao e retomada segura.

Status: RED — testes devem falhar antes da implementacao.
"""

from __future__ import annotations

import pytest


class TestRollbackPolicyContract:
    """RED: Contrato de politica de rollback por severidade."""

    def test_get_rollback_action_critical_is_interrupt(self) -> None:
        """R1: Severidade CRITICAL -> acao INTERRUPT_AND_HALT."""
        from core.model2.rollback_policy import get_rollback_action

        action = get_rollback_action(severity="CRITICAL")
        assert action == "INTERRUPT_AND_HALT"

    def test_get_rollback_action_high_is_interrupt(self) -> None:
        """R2: Severidade HIGH -> acao INTERRUPT_AND_HALT."""
        from core.model2.rollback_policy import get_rollback_action

        action = get_rollback_action(severity="HIGH")
        assert action == "INTERRUPT_AND_HALT"

    def test_get_rollback_action_medium_is_observe(self) -> None:
        """R3: Severidade MEDIUM -> acao OBSERVE_AND_ALERT."""
        from core.model2.rollback_policy import get_rollback_action

        action = get_rollback_action(severity="MEDIUM")
        assert action == "OBSERVE_AND_ALERT"

    def test_get_rollback_action_low_is_log(self) -> None:
        """R4: Severidade LOW -> acao LOG_ONLY."""
        from core.model2.rollback_policy import get_rollback_action

        action = get_rollback_action(severity="LOW")
        assert action == "LOG_ONLY"

    def test_get_rollback_action_unknown_severity_is_interrupt(self) -> None:
        """Guardrail: Severidade desconhecida -> INTERRUPT_AND_HALT (fail-safe)."""
        from core.model2.rollback_policy import get_rollback_action

        action = get_rollback_action(severity="UNKNOWN_SEVERITY")
        assert action == "INTERRUPT_AND_HALT"

    def test_rollback_decision_returns_dict_with_required_fields(self) -> None:
        """R5: Decisao de rollback retorna campos obrigatorios."""
        from core.model2.rollback_policy import evaluate_rollback

        result = evaluate_rollback(
            severity="CRITICAL",
            reason_code="circuit_breaker_blocked",
        )

        required = {"action", "severity", "reason_code", "safe_to_resume", "alert_message"}
        assert required.issubset(result.keys())

    def test_rollback_critical_not_safe_to_resume(self) -> None:
        """R6: CRITICAL nao e seguro retomar automaticamente."""
        from core.model2.rollback_policy import evaluate_rollback

        result = evaluate_rollback(
            severity="CRITICAL",
            reason_code="circuit_breaker_blocked",
        )

        assert result["safe_to_resume"] is False

    def test_rollback_low_is_safe_to_resume(self) -> None:
        """R7: LOW e seguro retomar (apenas log)."""
        from core.model2.rollback_policy import evaluate_rollback

        result = evaluate_rollback(
            severity="LOW",
            reason_code="duplicate_decision_id",
        )

        assert result["safe_to_resume"] is True

    def test_rollback_policy_constants_exported(self) -> None:
        """R8: Constantes de politica exportadas do modulo."""
        from core.model2.rollback_policy import (
            ROLLBACK_ACTION_INTERRUPT,
            ROLLBACK_ACTION_OBSERVE,
            ROLLBACK_ACTION_LOG,
        )

        assert ROLLBACK_ACTION_INTERRUPT == "INTERRUPT_AND_HALT"
        assert ROLLBACK_ACTION_OBSERVE == "OBSERVE_AND_ALERT"
        assert ROLLBACK_ACTION_LOG == "LOG_ONLY"

    def test_evaluate_rollback_does_not_raise(self) -> None:
        """Guardrail: evaluate_rollback nunca levanta excecao."""
        from core.model2.rollback_policy import evaluate_rollback

        result = evaluate_rollback(severity="", reason_code="")
        assert isinstance(result, dict)
        assert "action" in result
