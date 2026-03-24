"""RED Phase - Suite M2-028.1: Contrato de promocao GO/NO-GO shadow→paper.

Cobre:
  R1: PromotionEvaluator e PromotionResult existem e sao importaveis.
  R2: GO retornado quando todos os criterios sao atendidos.
  R3: NO-GO quando win_rate abaixo do threshold.
  R4: NO-GO quando episode_count abaixo do minimo.
  R5: NO-GO quando max_drawdown_pct excede o limite.
  R6: Multiplos motivos NO-GO acumulados.
  R7: PromotionConfig padrao usa thresholds conservadores.
  R8: PromotionResult inclui evaluated_at em formato ISO UTC.
  R9: GO aprovado quando win_rate exatamente igual ao threshold (borda inclusiva).
  R10: Guardrail: evaluate nunca lanca excecao; entrada invalida vira NO-GO.
  R11: PromotionResult e frozen (imutavel apos criacao).

Status: RED - testes devem FALHAR antes da implementacao.
"""
from __future__ import annotations

import pytest


class TestPromotionGateImports:
    """R1: Modulo e classes existem."""

    def test_promotion_gate_module_importable(self) -> None:
        """R1: core/model2/promotion_gate.py deve ser importavel."""
        from core.model2 import promotion_gate  # nao existe ainda  # noqa: F401

    def test_promotion_result_frozen_rejects_mutation(self) -> None:
        """R11: PromotionResult deve ser frozen dataclass (imutavel)."""
        from core.model2.promotion_gate import PromotionResult  # nao existe ainda

        result = PromotionResult(
            go=True,
            reasons=[],
            win_rate=0.6,
            episode_count=50,
            max_drawdown_pct=0.02,
            evaluated_at="2026-03-24T00:00:00Z",
        )
        with pytest.raises((AttributeError, TypeError)):
            result.go = False  # type: ignore[misc]


class TestPromotionEvaluatorGo:
    """R2/R9: Criterios GO."""

    def test_returns_go_when_all_criteria_met(self) -> None:
        """R2: GO quando win_rate, episodes e drawdown atendem thresholds."""
        from core.model2.promotion_gate import PromotionEvaluator, PromotionConfig

        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        result = PromotionEvaluator(config=config).evaluate(
            win_rate=0.60, episode_count=50, max_drawdown_pct=0.03
        )
        assert result.go is True
        assert result.reasons == []

    def test_go_when_win_rate_exactly_at_threshold(self) -> None:
        """R9: GO aprovado quando win_rate == min_win_rate (borda inclusiva)."""
        from core.model2.promotion_gate import PromotionEvaluator, PromotionConfig

        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        result = PromotionEvaluator(config=config).evaluate(
            win_rate=0.55, episode_count=30, max_drawdown_pct=0.05
        )
        assert result.go is True


class TestPromotionEvaluatorNoGo:
    """R3/R4/R5/R6: Criterios NO-GO."""

    def test_no_go_when_win_rate_below_threshold(self) -> None:
        """R3: NO-GO quando win_rate < min_win_rate."""
        from core.model2.promotion_gate import PromotionEvaluator, PromotionConfig

        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        result = PromotionEvaluator(config=config).evaluate(
            win_rate=0.40, episode_count=50, max_drawdown_pct=0.02
        )
        assert result.go is False
        assert any("win_rate" in r for r in result.reasons)

    def test_no_go_when_episodes_below_minimum(self) -> None:
        """R4: NO-GO quando episode_count < min_episodes."""
        from core.model2.promotion_gate import PromotionEvaluator, PromotionConfig

        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        result = PromotionEvaluator(config=config).evaluate(
            win_rate=0.60, episode_count=10, max_drawdown_pct=0.02
        )
        assert result.go is False
        assert any("episode" in r for r in result.reasons)

    def test_no_go_when_drawdown_exceeds_threshold(self) -> None:
        """R5: NO-GO quando max_drawdown_pct > limite configurado."""
        from core.model2.promotion_gate import PromotionEvaluator, PromotionConfig

        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        result = PromotionEvaluator(config=config).evaluate(
            win_rate=0.60, episode_count=50, max_drawdown_pct=0.08
        )
        assert result.go is False
        assert any("drawdown" in r for r in result.reasons)

    def test_accumulates_multiple_no_go_reasons(self) -> None:
        """R6: Todos os motivos NO-GO acumulados, nao apenas o primeiro."""
        from core.model2.promotion_gate import PromotionEvaluator, PromotionConfig

        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        result = PromotionEvaluator(config=config).evaluate(
            win_rate=0.40, episode_count=5, max_drawdown_pct=0.10
        )
        assert result.go is False
        assert len(result.reasons) >= 3


class TestPromotionConfig:
    """R7: Defaults conservadores."""

    def test_config_defaults_are_conservative(self) -> None:
        """R7: PromotionConfig padrao usa thresholds conservadores de risk_params."""
        from core.model2.promotion_gate import PromotionConfig

        config = PromotionConfig()
        assert config.min_win_rate > 0.50
        assert config.min_episodes >= 20
        assert config.max_drawdown_pct <= 0.05


class TestPromotionResult:
    """R8: Atributos de resultado."""

    def test_result_includes_evaluated_at_iso_timestamp(self) -> None:
        """R8: PromotionResult inclui evaluated_at em formato ISO UTC."""
        from core.model2.promotion_gate import PromotionEvaluator, PromotionConfig

        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        result = PromotionEvaluator(config=config).evaluate(
            win_rate=0.60, episode_count=50, max_drawdown_pct=0.02
        )
        assert result.evaluated_at is not None
        assert "T" in result.evaluated_at


class TestPromotionGuardrail:
    """R10: Guardrail fail-safe."""

    def test_invalid_input_returns_no_go_never_raises(self) -> None:
        """R10: Entrada invalida (negativa, NaN) retorna NO-GO, nunca lanca excecao."""
        from core.model2.promotion_gate import PromotionEvaluator, PromotionConfig

        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        result = PromotionEvaluator(config=config).evaluate(
            win_rate=-1.0, episode_count=-5, max_drawdown_pct=float("nan")
        )
        assert result.go is False
        assert len(result.reasons) > 0
