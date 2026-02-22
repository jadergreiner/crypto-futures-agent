"""
Testes para o Módulo rollback_handler.py

Cenários cobertos:
- Avaliação de critérios de rollback
- Disparo de rollback automático
- Status e logging
- Bloqueio de merge
- Recuperação e reset
"""

import pytest
import json
from pathlib import Path
from agent.rollback_handler import RollbackHandler


class TestRollbackHandlerBasic:
    """Testes básicos de inicialização."""

    def test_init_creates_log_dir(self, tmp_path):
        """Cria diretório de histórico de rollback."""
        rollback_dir = tmp_path / "rollback_logs"
        handler = RollbackHandler(rollback_log_dir=str(rollback_dir))

        assert rollback_dir.exists()
        assert handler.is_on_fallback is False

    def test_init_with_custom_module(self, tmp_path):
        """Aceita módulo heurístico customizado."""
        handler = RollbackHandler(
            heuristic_signals_module="custom.fallback.module",
            rollback_log_dir=str(tmp_path),
        )

        assert handler.heuristic_signals_module == "custom.fallback.module"


class TestRollbackHandlerCriteria:
    """Testes de avaliação de critérios de rollback."""

    def test_should_rollback_high_kl_persistent(self, tmp_path):
        """Rollback por KL divergence alto por 50+ steps."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        should_rb, reason = handler.should_rollback(
            kl_divergence=0.15,
            kl_history_steps=50,  # 50 steps com KL > 0.1
            sharpe_backtest=0.5,
            max_drawdown=2.0,
        )

        assert should_rb is True
        assert "KL" in reason

    def test_should_rollback_sharpe_negative(self, tmp_path):
        """Rollback por Sharpe crítico negativo."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        should_rb, reason = handler.should_rollback(
            kl_divergence=0.02,
            kl_history_steps=10,
            sharpe_backtest=-1.5,  # < -1.0
            max_drawdown=3.0,
        )

        assert should_rb is True
        assert "Sharpe" in reason

    def test_should_rollback_drawdown_extreme(self, tmp_path):
        """Rollback por drawdown > 20%."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        should_rb, reason = handler.should_rollback(
            kl_divergence=0.02,
            kl_history_steps=5,
            sharpe_backtest=0.5,
            max_drawdown=25.0,  # > 20%
        )

        assert should_rb is True
        assert "drawdown" in reason

    def test_should_rollback_no_improvement(self, tmp_path):
        """Rollback por 200+ episodes sem melhora."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        should_rb, reason = handler.should_rollback(
            kl_divergence=0.02,
            kl_history_steps=5,
            sharpe_backtest=0.5,
            max_drawdown=3.0,
            reward_improvement_episodes=(5.0, 250),  # 250 episodes sem melhora
        )

        assert should_rb is True
        assert "200" in reason

    def test_should_not_rollback_normal_conditions(self, tmp_path):
        """Não rollback com métricas normais."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        should_rb, reason = handler.should_rollback(
            kl_divergence=0.02,
            kl_history_steps=5,
            sharpe_backtest=0.8,
            max_drawdown=3.0,
            reward_improvement_episodes=(10.0, 50),
        )

        assert should_rb is False
        assert reason is None

    def test_should_rollback_multiple_criteria(self, tmp_path):
        """Rollback se múltiplos critérios falharem (only first is tested)."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        should_rb, reason = handler.should_rollback(
            kl_divergence=0.15,
            kl_history_steps=50,
            sharpe_backtest=-2.0,  # Ambos falhando
            max_drawdown=25.0,     # Todos falhando
        )

        assert should_rb is True
        # Será o primeiro critério acionado


class TestRollbackHandlerDispatch:
    """Testes de disparo de rollback."""

    def test_trigger_rollback_sets_state(self, tmp_path):
        """Disparo seta estado de fallback."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        success = handler.trigger_rollback(
            reason="KL divergence crítica",
            model_step=50000,
            metrics_snapshot={"sharpe": 0.5, "loss": 0.1},
        )

        assert success is True
        assert handler.is_on_fallback is True
        assert handler.rollback_step == 50000
        assert "KL divergence" in handler.rollback_reason

    def test_trigger_rollback_creates_log(self, tmp_path):
        """Cria arquivo JSON com evento de rollback."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        handler.trigger_rollback(
            reason="Test rollback",
            model_step=1000,
        )

        log_files = list(Path(tmp_path).glob("rollback_*.json"))
        assert len(log_files) == 1

        with open(log_files[0], "r") as f:
            log = json.load(f)
            assert log["reason"] == "Test rollback"
            assert log["step"] == 1000
            assert log["fallback_activated"] is True

    def test_trigger_rollback_with_metrics_snapshot(self, tmp_path):
        """Inclui snapshot de métricas no log."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        metrics = {
            "sharpe": 0.5,
            "loss": 0.1,
            "kl_div": 0.15,
            "drawdown": 25.0,
        }

        handler.trigger_rollback(
            reason="Multiple failures",
            model_step=50000,
            metrics_snapshot=metrics,
        )

        log_files = list(Path(tmp_path).glob("rollback_*.json"))
        with open(log_files[0], "r") as f:
            log = json.load(f)
            assert log["metrics_snapshot"] == metrics


class TestRollbackHandlerStatus:
    """Testes de status e recuperação."""

    def test_get_rollback_status_normal(self, tmp_path):
        """Status quando sem rollback."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        status = handler.get_rollback_status()

        assert status["is_on_fallback"] is False
        assert status["rollback_reason"] is None
        assert "Treinamento normal" in status["status_message"]

    def test_get_rollback_status_fallback(self, tmp_path):
        """Status quando em fallback."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))
        handler.trigger_rollback("Test reason", 5000)

        status = handler.get_rollback_status()

        assert status["is_on_fallback"] is True
        assert status["rollback_step"] == 5000
        assert "Test reason" in status["status_message"]

    def test_can_merge_if_rollback_triggered_blocks(self, tmp_path):
        """Merge bloqueado se rollback foi disparado."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))
        handler.trigger_rollback("KL divergence", 10000)

        can_merge, reason = handler.can_merge_if_rollback_triggered()

        assert can_merge is False
        assert "BLOQUEADO" in reason
        assert "rollback" in reason.lower()

    def test_can_merge_if_rollback_triggered_allows_normal(self, tmp_path):
        """Merge permitido sem rollback."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        can_merge, reason = handler.can_merge_if_rollback_triggered()

        assert can_merge is True
        assert reason is None

    def test_fallback_to_heuristics_without_should_rollback(self, tmp_path):
        """Ativa fallback diretamente sem should_rollback."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        success = handler.fallback_to_heuristics()

        assert success is True
        assert handler.is_on_fallback is True

    def test_fallback_to_heuristics_already_active(self, tmp_path):
        """Fallback já ativo retorna True."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))
        handler.trigger_rollback("First rollback", 1000)

        # Chamar novamente
        success = handler.fallback_to_heuristics()

        assert success is True
        # Deve manter dados do primeiro rollback
        assert handler.rollback_step == 1000


class TestRollbackHandlerReset:
    """Testes de reset de estado."""

    def test_reset_rollback_state_clears_flags(self, tmp_path):
        """Reset limpa estado de rollback."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))
        handler.trigger_rollback("Test", 5000)

        handler.reset_rollback_state()

        assert handler.is_on_fallback is False
        assert handler.rollback_reason is None
        assert handler.rollback_step is None

    def test_reset_requires_explicit_approval(self, tmp_path):
        """Reset é permitido mas deve ser explícito."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))
        handler.trigger_rollback("Test", 5000)

        # Reset deve funcionar, mas é uma ação explícita
        handler.reset_rollback_state()

        # Verificar que estado foi limpo
        status = handler.get_rollback_status()
        assert "Treinamento normal" in status["status_message"]


class TestRollbackHandlerHistory:
    """Testes de histórico e análise."""

    def test_get_rollback_log_summary_empty(self, tmp_path):
        """Sumário de histórico vazio."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        summary = handler.get_rollback_log_summary()

        assert summary["total_rollbacks_logged"] == 0
        assert summary["last_rollback_time"] is None

    def test_get_rollback_log_summary_with_events(self, tmp_path):
        """Sumário de histórico com múltiplos eventos."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        # Registrar 3 rollbacks com razões diferentes
        handler.trigger_rollback("Reason A", 1000)
        handler.reset_rollback_state()

        handler.trigger_rollback("Reason B", 2000)
        handler.reset_rollback_state()

        handler.trigger_rollback("Reason A", 3000)

        summary = handler.get_rollback_log_summary()

        assert summary["total_rollbacks_logged"] == 3
        assert summary["last_rollback_time"] is not None
        assert "reason_breakdown" in summary


class TestRollbackHandlerEdgeCases:
    """Testes de casos extremos."""

    def test_should_rollback_with_none_values(self, tmp_path):
        """Trata None values gracefully."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        should_rb, reason = handler.should_rollback(
            kl_divergence=0.02,
            kl_history_steps=5,
            sharpe_backtest=None,  # None
            max_drawdown=None,     # None
            reward_improvement_episodes=None,  # None
        )

        assert should_rb is False

    def test_trigger_rollback_idempotent(self, tmp_path):
        """Múltiplos triggers com mesmo estado."""
        handler = RollbackHandler(rollback_log_dir=str(tmp_path))

        result1 = handler.trigger_rollback("First", 1000)
        result2 = handler.trigger_rollback("Second", 2000)

        # Ambas devem ser bem-sucedidas
        assert result1 is True
        assert result2 is True

        # Último evento sobrescreve
        assert handler.rollback_reason == "Second"
        assert handler.rollback_step == 2000
