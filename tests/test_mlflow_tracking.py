"""
Testes RED — BLID-095: Rastreamento MLflow no Trainer e ConvergenceMonitor.

Fase RED: todos os testes DEVEM falhar antes da implementacao.
Estrutura AAA (Arrange / Act / Assert).
"""

import os
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path


# ---------------------------------------------------------------------------
# R1 — mlflow.start_run() chamado em train_phase1 e train_phase2
# ---------------------------------------------------------------------------

class TestMlflowRunStarted:
    """R1: mlflow_client.start_run() chamado em train_phase1/phase2."""

    def test_mlflow_run_started_train_phase1_inicia_run(self, tmp_path):
        """train_phase1_exploration deve chamar mlflow.start_run()."""
        # Arrange
        import mlflow
        from agent.trainer import Trainer

        mock_env_data = {"ohlcv": MagicMock()}
        trainer = Trainer(save_dir=str(tmp_path))

        with patch("agent.trainer.mlflow") as mock_mlflow, \
             patch.object(trainer, "create_env", return_value=MagicMock()), \
             patch("agent.trainer.DummyVecEnv", return_value=MagicMock()), \
             patch("agent.trainer.VecNormalize", return_value=MagicMock()), \
             patch("agent.trainer.PPO") as mock_ppo:
            mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_model = MagicMock()
            mock_ppo.return_value = mock_model

            # Act
            trainer.train_phase1_exploration(mock_env_data, total_timesteps=100)

        # Assert
        mock_mlflow.start_run.assert_called_once()

    def test_mlflow_run_started_train_phase2_inicia_run(self, tmp_path):
        """train_phase2_refinement deve chamar mlflow.start_run()."""
        # Arrange
        from agent.trainer import Trainer

        mock_env_data = {"ohlcv": MagicMock()}
        trainer = Trainer(save_dir=str(tmp_path))
        trainer.model = MagicMock()

        with patch("agent.trainer.mlflow") as mock_mlflow, \
             patch.object(trainer, "create_env", return_value=MagicMock()), \
             patch("agent.trainer.DummyVecEnv", return_value=MagicMock()), \
             patch("agent.trainer.VecNormalize", return_value=MagicMock()):
            mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)

            # Act
            trainer.train_phase2_refinement(mock_env_data, total_timesteps=100, load_phase1=False)

        # Assert
        mock_mlflow.start_run.assert_called_once()


# ---------------------------------------------------------------------------
# R2 — PPOConfig logada como params mlflow
# ---------------------------------------------------------------------------

class TestMlflowParamsLogged:
    """R2: PPOConfig logada como params mlflow (lr, batch_size, etc)."""

    EXPECTED_PARAMS = [
        "learning_rate", "batch_size", "n_steps", "n_epochs",
        "gamma", "gae_lambda", "clip_range", "ent_coef",
    ]

    def test_mlflow_params_logged_phase1_loga_todos_hiperparametros(self, tmp_path):
        """train_phase1_exploration deve logar todos os 8 hiperparametros PPOConfig."""
        # Arrange
        from agent.trainer import Trainer
        from config.ppo_config import PPOConfig

        config = PPOConfig()
        trainer = Trainer(save_dir=str(tmp_path), config=config)

        with patch("agent.trainer.mlflow") as mock_mlflow, \
             patch.object(trainer, "create_env", return_value=MagicMock()), \
             patch("agent.trainer.DummyVecEnv", return_value=MagicMock()), \
             patch("agent.trainer.VecNormalize", return_value=MagicMock()), \
             patch("agent.trainer.PPO") as mock_ppo:
            mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_ppo.return_value = MagicMock()

            # Act
            trainer.train_phase1_exploration({"ohlcv": MagicMock()}, total_timesteps=100)

        # Assert — log_params chamado com todos os campos esperados
        log_params_calls = mock_mlflow.log_params.call_args_list
        assert len(log_params_calls) >= 1, "mlflow.log_params nao foi chamado"
        logged_keys = set()
        for c in log_params_calls:
            logged_keys.update(c[0][0].keys() if c[0] else c[1].get("params", {}).keys())
        for param in self.EXPECTED_PARAMS:
            assert param in logged_keys, f"Parametro '{param}' nao logado no MLflow"


# ---------------------------------------------------------------------------
# R3 — metricas logadas por step via ConvergenceMonitor.log_step()
# ---------------------------------------------------------------------------

class TestMlflowMetricsLoggedPerStep:
    """R3: metricas logadas por step no ConvergenceMonitor."""

    EXPECTED_METRICS = [
        "reward_mean", "sharpe", "win_rate", "drawdown",
        "profit_factor", "ep_len_mean", "kl_div",
    ]

    def test_mlflow_metrics_logged_convergence_monitor_loga_reward_mean(self, tmp_path):
        """ConvergenceMonitor.log_step() deve chamar mlflow.log_metric com reward_mean."""
        # Arrange
        from agent.convergence_monitor import ConvergenceMonitor

        monitor = ConvergenceMonitor(output_dir=str(tmp_path / "logs"))

        with patch("agent.convergence_monitor.mlflow") as mock_mlflow:
            # Act
            monitor.log_step(
                step=100,
                episode_reward=0.5,
                episode_length=200,
                kl_divergence=0.01,
                entropy=0.02,
            )

        # Assert
        called_metrics = {
            c[0][0] for c in mock_mlflow.log_metric.call_args_list
        }
        assert "reward_mean" in called_metrics

    def test_mlflow_metrics_logged_convergence_monitor_loga_todas_metricas(self, tmp_path):
        """ConvergenceMonitor.log_step() deve logar todas as 7 metricas obrigatorias."""
        # Arrange
        from agent.convergence_monitor import ConvergenceMonitor

        monitor = ConvergenceMonitor(output_dir=str(tmp_path / "logs"))

        with patch("agent.convergence_monitor.mlflow") as mock_mlflow:
            # Act
            monitor.log_step(
                step=100,
                episode_reward=0.5,
                episode_length=200,
                kl_divergence=0.01,
                entropy=0.02,
                sharpe=1.2,
                win_rate=0.55,
                drawdown=0.05,
                profit_factor=1.8,
            )

        # Assert
        called_metrics = {
            c[0][0] for c in mock_mlflow.log_metric.call_args_list
        }
        for metric in self.EXPECTED_METRICS:
            assert metric in called_metrics, f"Metrica '{metric}' nao logada no MLflow"

    def test_mlflow_metrics_logged_step_passado_como_argumento(self, tmp_path):
        """ConvergenceMonitor.log_step() deve passar step como argumento de step para log_metric."""
        # Arrange
        from agent.convergence_monitor import ConvergenceMonitor

        monitor = ConvergenceMonitor(output_dir=str(tmp_path / "logs"))
        step_val = 500

        with patch("agent.convergence_monitor.mlflow") as mock_mlflow:
            # Act
            monitor.log_step(step=step_val, episode_reward=1.0)

        # Assert — verifica que step foi passado em pelo menos uma chamada
        for c in mock_mlflow.log_metric.call_args_list:
            args = c[0]
            kwargs = c[1]
            step_arg = args[2] if len(args) > 2 else kwargs.get("step")
            if step_arg == step_val:
                return
        pytest.fail(f"Nenhuma chamada log_metric recebeu step={step_val}")


# ---------------------------------------------------------------------------
# R4 — modelo salvo como MLflow artifact ao final de cada fase
# ---------------------------------------------------------------------------

class TestMlflowArtifactSaved:
    """R4: modelo salvo como MLflow artifact ao final de cada fase."""

    def test_mlflow_artifact_saved_phase1_loga_artifact(self, tmp_path):
        """train_phase1_exploration deve chamar mlflow.log_artifact com o .zip salvo."""
        # Arrange
        from agent.trainer import Trainer

        trainer = Trainer(save_dir=str(tmp_path))

        with patch("agent.trainer.mlflow") as mock_mlflow, \
             patch.object(trainer, "create_env", return_value=MagicMock()), \
             patch("agent.trainer.DummyVecEnv", return_value=MagicMock()), \
             patch("agent.trainer.VecNormalize", return_value=MagicMock()), \
             patch("agent.trainer.PPO") as mock_ppo:
            mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_ppo.return_value = MagicMock()

            # Act
            trainer.train_phase1_exploration({"ohlcv": MagicMock()}, total_timesteps=100)

        # Assert
        mock_mlflow.log_artifact.assert_called()
        artifact_path = mock_mlflow.log_artifact.call_args[0][0]
        assert artifact_path.endswith(".zip"), f"Artifact nao eh .zip: {artifact_path}"

    def test_mlflow_artifact_saved_phase2_loga_artifact(self, tmp_path):
        """train_phase2_refinement deve chamar mlflow.log_artifact com o .zip salvo."""
        # Arrange
        from agent.trainer import Trainer

        trainer = Trainer(save_dir=str(tmp_path))
        trainer.model = MagicMock()

        with patch("agent.trainer.mlflow") as mock_mlflow, \
             patch.object(trainer, "create_env", return_value=MagicMock()), \
             patch("agent.trainer.DummyVecEnv", return_value=MagicMock()), \
             patch("agent.trainer.VecNormalize", return_value=MagicMock()):
            mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)

            # Act
            trainer.train_phase2_refinement({"ohlcv": MagicMock()}, total_timesteps=100, load_phase1=False)

        # Assert
        mock_mlflow.log_artifact.assert_called()
        artifact_path = mock_mlflow.log_artifact.call_args[0][0]
        assert artifact_path.endswith(".zip"), f"Artifact nao eh .zip: {artifact_path}"


# ---------------------------------------------------------------------------
# R5 — mlflow.load_model() ou PPO.load via artifact URI funciona
# ---------------------------------------------------------------------------

class TestMlflowModelLoadable:
    """R5: modelo carregavel via artifact URI do MLflow."""

    def test_mlflow_model_loadable_artifact_uri_retorna_ppo(self, tmp_path):
        """Deve ser possivel carregar PPO via mlflow artifact URI."""
        # Arrange
        from agent.trainer import Trainer
        from stable_baselines3 import PPO as SB3_PPO

        trainer = Trainer(save_dir=str(tmp_path))

        # Simula artifact URI que o mlflow retornaria
        fake_uri = str(tmp_path / "phase1_exploration.zip")

        # Cria arquivo dummy para simular artefato salvo
        import zipfile
        with zipfile.ZipFile(fake_uri, "w") as zf:
            zf.writestr("data", "dummy")

        with patch("agent.trainer.mlflow") as mock_mlflow, \
             patch("agent.trainer.PPO") as mock_ppo_cls:
            mock_mlflow.get_artifact_uri.return_value = fake_uri
            mock_loaded = MagicMock(spec=SB3_PPO)
            mock_ppo_cls.load.return_value = mock_loaded

            # Act — carregar via URI
            loaded = trainer.load_model_from_mlflow_artifact(run_id="abc123", artifact_name="phase1_exploration.zip")

        # Assert
        assert loaded is not None
        mock_ppo_cls.load.assert_called_once()

    def test_mlflow_model_loadable_mlflow_tracking_nao_bloqueia_execucao(self, tmp_path):
        """Excecao no MLflow nao deve bloquear train_phase1 (try/except obrigatorio)."""
        # Arrange
        from agent.trainer import Trainer

        trainer = Trainer(save_dir=str(tmp_path))

        with patch("agent.trainer.mlflow") as mock_mlflow, \
             patch.object(trainer, "create_env", return_value=MagicMock()), \
             patch("agent.trainer.DummyVecEnv", return_value=MagicMock()), \
             patch("agent.trainer.VecNormalize", return_value=MagicMock()), \
             patch("agent.trainer.PPO") as mock_ppo:
            # Simula falha no MLflow
            mock_mlflow.start_run.side_effect = Exception("MLflow indisponivel")
            mock_ppo.return_value = MagicMock()

            # Act & Assert — nao deve lancar excecao
            try:
                trainer.train_phase1_exploration({"ohlcv": MagicMock()}, total_timesteps=100)
            except Exception as e:
                pytest.fail(f"Excecao no MLflow bloqueou execucao: {e}")


# ---------------------------------------------------------------------------
# R6 — ppo_model.zip presente em .gitignore
# ---------------------------------------------------------------------------

class TestGitignoreContainsPpoZip:
    """R6: ppo_model.zip e checkpoints/*.zip presentes no .gitignore."""

    GITIGNORE_PATH = Path(__file__).parent.parent / ".gitignore"

    def test_gitignore_contains_ppo_zip_entrada_presente(self):
        """O arquivo .gitignore deve conter entrada para ppo_model.zip."""
        # Arrange
        assert self.GITIGNORE_PATH.exists(), ".gitignore nao encontrado"

        # Act
        content = self.GITIGNORE_PATH.read_text(encoding="utf-8")

        # Assert
        assert "ppo_model.zip" in content, "ppo_model.zip nao encontrado no .gitignore"

    def test_gitignore_contains_checkpoints_ppo_zip_glob(self):
        """O .gitignore deve cobrir checkpoints/ppo_training/ppo_model.zip."""
        # Arrange
        assert self.GITIGNORE_PATH.exists(), ".gitignore nao encontrado"

        # Act
        content = self.GITIGNORE_PATH.read_text(encoding="utf-8")

        # Assert — aceita glob ou caminho direto
        has_coverage = (
            "checkpoints/ppo_training/ppo_model.zip" in content
            or "checkpoints/**/*.zip" in content
            or "checkpoints/ppo_training/" in content
        )
        assert has_coverage, "checkpoints/ppo_training/ppo_model.zip nao coberto no .gitignore"

    def test_gitignore_ppo_zip_nao_rastreado_pelo_git(self):
        """ppo_model.zip nao deve estar rastreado pelo git (git rm --cached executado)."""
        # Arrange
        import subprocess

        # Act
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "checkpoints/ppo_training/ppo_model.zip"],
            capture_output=True,
            cwd=str(self.GITIGNORE_PATH.parent),
        )

        # Assert — exit code != 0 significa que o arquivo NAO esta rastreado (correto)
        assert result.returncode != 0, (
            "checkpoints/ppo_training/ppo_model.zip ainda esta rastreado pelo git. "
            "Execute: git rm --cached checkpoints/ppo_training/ppo_model.zip"
        )
