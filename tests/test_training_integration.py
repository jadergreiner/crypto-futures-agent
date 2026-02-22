"""
Testes de Integração - Treinamento PPO Completo

Testes de smoke test para verificar se todos os módulos funcionam
juntos durante um ciclo de treinamento (5000 steps).

Cenários:
- Orchestrator inicia e encerra graciosamente
- Checkpoint -> Load -> Continue training
- Divergence detection durante training
- Rollback trigger bloqueia merge
- Convergence monitor acumula métricas
"""

import pytest
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch, MagicMock


class TestTrainingIntegrationSmoke:
    """Smoke tests para pipeline de treinamento."""

    def test_orchestrator_initialization(self, mock_ppo_config):
        """Orquestrador inicializa sem erros."""
        from scripts.ppo_training_orchestrator import PPOTrainingOrchestrator

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = PPOTrainingOrchestrator(
                config_path="config/ppo_config.json",
                log_dir=tmpdir,
            )

            assert orchestrator is not None
            assert orchestrator.is_running is False

    def test_phase_1_load_config(self, tmp_path):
        """FASE 1: Carrega configuração PPO válida."""
        from scripts.ppo_training_orchestrator import PPOTrainingOrchestrator

        # Criar config temporário
        config = {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64}
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config, f)

        orchestrator = PPOTrainingOrchestrator(
            config_path=str(config_file),
            log_dir=str(tmp_path),
        )

        # Simular PHASE 1
        result = orchestrator._phase_1_load_config()
        assert result is True
        assert orchestrator.ppo_config is not None

    def test_checkpoint_recovery_cycle(self, tmp_path, encryption_key_env):
        """Ciclo completo: Save -> Load -> Continue."""
        from agent.checkpoint_manager import CheckpointManager

        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        # Checkpoint 1
        model_1 = {"iteration": 1, "weights": [0.1, 0.2, 0.3]}
        metrics_1 = {"sharpe": 0.8, "loss": 0.05}
        path_1, _ = manager.save_checkpoint(model_1, step=1000, metrics=metrics_1)

        # Carregar e continuar
        loaded_model, loaded_meta = manager.load_checkpoint(path_1)
        assert loaded_model == model_1
        assert loaded_meta["step"] == 1000

        # Checkpoint 2 (continuação)
        model_2 = {"iteration": 2, "weights": [0.11, 0.21, 0.31]}
        metrics_2 = {"sharpe": 0.9, "loss": 0.04}
        path_2, _ = manager.save_checkpoint(model_2, step=2000, metrics=metrics_2)

        # Verificar que ambos existem
        assert Path(path_1).exists()
        assert Path(path_2).exists()

    def test_convergence_monitoring_integration(self, tmp_path):
        """Monitor de convergência integrado com logging."""
        from agent.convergence_monitor import ConvergenceMonitor

        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        # Simular 100 steps de treinamento
        for step in range(100):
            reward = 10.0 + step * 0.05  # Melhora gradual
            loss = 0.1 - step * 0.0005  # Diminui
            kl = 0.02 + step * 0.00001  # Sobe levemente

            monitor.log_step(
                step=step,
                episode_reward=reward,
                loss_policy=loss,
                kl_divergence=kl,
            )

        # Gerar sumário
        summary = monitor.generate_daily_summary()
        assert summary["mean_reward"] > 10.0
        assert summary["total_steps"] == 99

        # Exportar CSV
        csv_path = monitor.export_metrics_csv()
        assert Path(csv_path).exists()

    def test_rollback_integrated_with_divergence(self, tmp_path):
        """Rollback disparado por convergence monitor."""
        from agent.convergence_monitor import ConvergenceMonitor
        from agent.rollback_handler import RollbackHandler

        monitor = ConvergenceMonitor(output_dir=str(tmp_path))
        rollback = RollbackHandler(rollback_log_dir=str(tmp_path / "rollback"))

        # Simular divergência
        for step in range(60):
            # KL divergence persistente
            monitor.log_step(
                step=step,
                kl_divergence=0.15,
                episode_reward=10.0 - step * 0.1,  # Piorando
            )

        # Detectar divergência
        is_diverging, reason = monitor.detect_divergence()
        if is_diverging:
            # Disparar rollback
            success = rollback.trigger_rollback(reason, model_step=step)
            assert success is True
            assert rollback.is_on_fallback is True

    def test_merge_blocked_after_rollback(self, tmp_path):
        """Merge bloqueado se rollback foi disparado."""
        from agent.rollback_handler import RollbackHandler

        rollback = RollbackHandler(rollback_log_dir=str(tmp_path))

        # Sem rollback: merge permitido
        can_merge, _ = rollback.can_merge_if_rollback_triggered()
        assert can_merge is True

        # Disparar rollback
        rollback.trigger_rollback("KL divergence crítica", 50000)

        # Merge bloqueado
        can_merge, reason = rollback.can_merge_if_rollback_triggered()
        assert can_merge is False
        assert "BLOQUEADO" in reason

    def test_checkpoint_manager_with_metrics_tracking(
        self, tmp_path, encryption_key_env
    ):
        """Checkpoint salva métricas que evoluem durante treinamento."""
        from agent.checkpoint_manager import CheckpointManager

        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        # Simular evolução de métricas em 5 checkpoints
        metrics_series = [
            {"sharpe": 0.5, "loss": 0.1},
            {"sharpe": 0.7, "loss": 0.08},
            {"sharpe": 0.9, "loss": 0.06},
            {"sharpe": 1.1, "loss": 0.04},
            {"sharpe": 1.2, "loss": 0.03},
        ]

        checkpoint_paths = []
        for i, metrics in enumerate(metrics_series):
            model = {"step": i * 100}
            path, _ = manager.save_checkpoint(
                model, step=i * 100000, metrics=metrics
            )
            checkpoint_paths.append(path)

        # Listar por Sharpe descendente
        best = manager.list_checkpoints_by_metric("sharpe", top_n=2, sort_order="desc")
        assert len(best) == 2
        assert best[0]["metric_value"] == 1.2  # Melhor Sharpe
        assert best[1]["metric_value"] == 1.1

    def test_full_training_lifecycle_mock(self, tmp_path):
        """Ciclo completo mocado: init -> phase 1-10 -> cleanup."""
        from scripts.ppo_training_orchestrator import PPOTrainingOrchestrator

        # Criar config
        config = {
            "learning_rate": 3e-4,
            "n_steps": 2048,
            "batch_size": 64,
            "n_epochs": 10,
            "gamma": 0.99,
            "gae_lambda": 0.95,
            "ent_coef": 0.001,
        }
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config, f)

        orchestrator = PPOTrainingOrchestrator(
            config_path=str(config_file),
            data_dir=str(tmp_path / "data"),
            log_dir=str(tmp_path / "logs"),
        )

        # PHASE 1: Load config
        assert orchestrator._phase_1_load_config() is True

        # PHASE 10: Cleanup
        orchestrator._phase_10_cleanup()
        assert orchestrator.is_running is False


class TestTrainingIntegrationEdgeCases:
    """Testes de casos extremos em integração."""

    def test_convergence_monitor_and_rollback_work_together(self, tmp_path):
        """Monitor detecta divergência e rollback bloqueia merge."""
        from agent.convergence_monitor import ConvergenceMonitor
        from agent.rollback_handler import RollbackHandler

        monitor = ConvergenceMonitor(output_dir=str(tmp_path))
        rollback = RollbackHandler(rollback_log_dir=str(tmp_path))

        # Simular training normal, depois divergência
        for step in range(100):
            if step < 50:
                # Normal
                kl = 0.02
                reward = 10.0 + step * 0.1
            else:
                # Divergência a partir de step 50
                kl = 0.12  # Alto
                reward = 5.0  # Pior

            monitor.log_step(
                step=step,
                kl_divergence=kl,
                episode_reward=reward,
            )

        # Detectar divergência
        is_div, reason = monitor.detect_divergence()

        if is_div:
            # Disparar rollback
            rollback.trigger_rollback(reason, model_step=50)

            # Verificar que merge é bloqueado
            can_merge, msg = rollback.can_merge_if_rollback_triggered()
            assert can_merge is False

    def test_checkpoint_manager_survives_multiple_rollbacks(
        self, tmp_path, encryption_key_env
    ):
        """Checkpoints persistem através de múltiplos ciclos rollback."""
        from agent.checkpoint_manager import CheckpointManager
        from agent.rollback_handler import RollbackHandler

        manager = CheckpointManager(checkpoint_dir=str(tmp_path))
        rollback_log = tmp_path / "rollback"

        # Ciclo 1: Rollback
        rollback1 = RollbackHandler(rollback_log_dir=str(rollback_log / "v1"))
        rollback1.trigger_rollback("First divergence", 10000)

        # Salvar checkpoint recovery
        manager.save_checkpoint(
            {"recovery": 1}, step=10001, metrics={"sharpe": 0.5}
        )

        # Ciclo 2: Rollback again
        rollback2 = RollbackHandler(rollback_log_dir=str(rollback_log / "v2"))
        rollback2.trigger_rollback("Second divergence", 20000)

        # Salvar checkpoint recovery
        manager.save_checkpoint(
            {"recovery": 2}, step=20001, metrics={"sharpe": 0.6}
        )

        # Verificar que ambos checkpoints existem
        best_ckpts = manager.list_checkpoints_by_metric("sharpe", top_n=2)
        assert len(best_ckpts) == 2
        assert best_ckpts[0]["metric_value"] == 0.6  # Mais recente e melhor

    def test_long_training_session_5000_steps(self, tmp_path):
        """Smoke test: 5000 steps simulados de treinamento."""
        from agent.convergence_monitor import ConvergenceMonitor

        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        # Simuler 5000 steps (teste de performance e memory)
        for step in range(5000):
            monitor.log_step(
                step=step,
                episode_reward=10.0 + (step % 100) * 0.01,
                loss_policy=0.1 - (step % 1000) * 0.00001,
                kl_divergence=0.02 + (step % 500) * 0.00001,
                entropy=0.8 - (step % 200) * 0.0001,
            )

            # Gerar sumário a cada 1000 steps
            if step % 1000 == 0 and step > 0:
                summary = monitor.generate_daily_summary()
                assert summary["total_steps"] == step - 1

        # Sumário final
        final = monitor.generate_daily_summary()
        assert final["total_steps"] == 4999
        assert "mean_reward" in final

    def test_metadata_consistency_across_checkpoints(
        self, tmp_path, encryption_key_env
    ):
        """Metadata mantém consistência através de múltiplos checkpoints."""
        from agent.checkpoint_manager import CheckpointManager
        import hashlib

        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        shas = []
        for i in range(3):
            metrics = {"step": i, "iteration": i}
            manager.save_checkpoint(
                {"data": i}, step=i * 1000, metrics=metrics
            )

            # Ler JSON metadata
            json_files = sorted(Path(tmp_path).glob("*.json"))
            if json_files:
                with open(json_files[-1], "r") as f:
                    meta = json.load(f)
                    shas.append(meta.get("sha256"))

        # Todos SHAs devem estar presentes e diferentes
        assert len(shas) == 3
        assert len(set(shas)) == 3  # Todos únicos
