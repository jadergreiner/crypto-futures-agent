"""Suite RED M2-025.9: Circuit breaker para dados stale persistentes.

Objetivo: Acionar circuit breaker quando estado stale persistir acima
da janela segura, evitando decisao com contexto degradado.

Status: RED — testes devem falhar antes da implementacao.
"""

from __future__ import annotations

import pytest


class TestStaleCBContract:
    """RED: Contrato do circuit breaker de dados stale."""

    def test_check_stale_cb_trips_when_stale_count_exceeds(self) -> None:
        """R1: CB abre quando contador de stale excede limite."""
        from core.model2.cycle_report import check_stale_circuit_breaker

        result = check_stale_circuit_breaker(
            stale_count=5,
            max_stale=3,
        )
        assert result["tripped"] is True
        assert result["reason"] == "stale_limit_exceeded"

    def test_check_stale_cb_closed_when_within_limit(self) -> None:
        """R2: CB fechado quando contador dentro do limite."""
        from core.model2.cycle_report import check_stale_circuit_breaker

        result = check_stale_circuit_breaker(
            stale_count=2,
            max_stale=3,
        )
        assert result["tripped"] is False

    def test_check_stale_cb_tripped_when_count_equals_max(self) -> None:
        """R3: CB abre quando count == max_stale (limite inclusivo)."""
        from core.model2.cycle_report import check_stale_circuit_breaker

        result = check_stale_circuit_breaker(
            stale_count=3,
            max_stale=3,
        )
        assert result["tripped"] is True

    def test_check_stale_cb_includes_required_fields(self) -> None:
        """R4: Resultado inclui campos obrigatorios."""
        from core.model2.cycle_report import check_stale_circuit_breaker

        result = check_stale_circuit_breaker(stale_count=1, max_stale=5)

        required = {"tripped", "stale_count", "max_stale", "reason", "alert_message"}
        assert required.issubset(result.keys())

    def test_check_stale_cb_does_not_raise(self) -> None:
        """Guardrail: Funcao nunca levanta excecao."""
        from core.model2.cycle_report import check_stale_circuit_breaker

        result = check_stale_circuit_breaker(stale_count=-1, max_stale=0)
        assert isinstance(result, dict)

    def test_check_stale_cb_alert_message_when_tripped(self) -> None:
        """R5: Mensagem de alerta presente quando CB acionado."""
        from core.model2.cycle_report import check_stale_circuit_breaker

        result = check_stale_circuit_breaker(stale_count=10, max_stale=3)
        assert result["tripped"] is True
        assert len(result["alert_message"]) > 0
