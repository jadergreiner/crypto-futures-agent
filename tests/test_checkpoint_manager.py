"""
Testes para o Módulo checkpoint_manager.py

Cenários cobertos:
- Salvamento e carregamento com criptografia
- Validação de integridade SHA256
- Listagem e ordenação por métrica
- Limpeza de checkpoints antigos
- Casos de erro e recuperação
"""

import pytest
import os
import json
from pathlib import Path
from agent.checkpoint_manager import CheckpointManager


class TestCheckpointManagerBasic:
    """Testes básicos de save/load."""

    def test_init_raises_no_env_key(self):
        """Falha se PPO_CHECKPOINT_KEY não está definida."""
        os.environ.pop("PPO_CHECKPOINT_KEY", None)
        with pytest.raises(ValueError, match="não definida"):
            CheckpointManager()

    def test_init_with_valid_key(self, encryption_key_env, mock_checkpoint_dir):
        """Inicializa com chave válida."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)
        assert manager.checkpoint_dir.exists()
        assert manager.keep_last_n == 10

    def test_save_checkpoint_encrypted(
        self, mock_checkpoint_dir, encryption_key_env, mock_checkpoint_data
    ):
        """Salva checkpoint com criptografia."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        ckpt_path, backup_path = manager.save_checkpoint(
            model=mock_checkpoint_data["model"],
            step=mock_checkpoint_data["step"],
            metrics=mock_checkpoint_data["metrics"],
            encrypt=True,
        )

        assert Path(ckpt_path).exists()
        assert Path(backup_path).exists()
        assert ckpt_path.endswith(".enc")

    def test_save_checkpoint_plaintext(
        self, mock_checkpoint_dir, encryption_key_env, mock_checkpoint_data
    ):
        """Salva checkpoint sem criptografia (apenas backup)."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        ckpt_path, backup_path = manager.save_checkpoint(
            model=mock_checkpoint_data["model"],
            step=mock_checkpoint_data["step"],
            metrics=mock_checkpoint_data["metrics"],
            encrypt=False,
        )

        assert Path(ckpt_path).exists()
        assert ckpt_path.endswith(".joblib")


class TestCheckpointManagerLoad:
    """Testes de carregamento e validação."""

    def test_load_checkpoint_encrypted(
        self, mock_checkpoint_dir, encryption_key_env, mock_checkpoint_data
    ):
        """Carrega checkpoint criptografado com sucesso."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        # Salvar
        ckpt_path, _ = manager.save_checkpoint(
            model=mock_checkpoint_data["model"],
            step=mock_checkpoint_data["step"],
            metrics=mock_checkpoint_data["metrics"],
            encrypt=True,
        )

        # Carregar
        model, metadata = manager.load_checkpoint(ckpt_path, decrypt=True)
        assert model == mock_checkpoint_data["model"]
        assert metadata["step"] == mock_checkpoint_data["step"]
        assert "sharpe" in metadata["metrics"]

    def test_load_checkpoint_fails_corrupt(
        self, mock_checkpoint_dir, encryption_key_env
    ):
        """Falha ao carregar checkpoint corrompido."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        # Criar arquivo vazio para simular corrupção
        corrupt_file = Path(mock_checkpoint_dir) / "corrupt.joblib.enc"
        corrupt_file.write_bytes(b"corrupted_data_xyz")

        with pytest.raises((ValueError, Exception)):
            manager.load_checkpoint(str(corrupt_file), decrypt=True)

    def test_validate_checkpoint(self, mock_checkpoint_dir, encryption_key_env, mock_checkpoint_data):
        """Valida checkpoint sem carregar modelo completo."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        ckpt_path, _ = manager.save_checkpoint(
            model=mock_checkpoint_data["model"],
            step=mock_checkpoint_data["step"],
            metrics=mock_checkpoint_data["metrics"],
        )

        is_valid = manager.validate_checkpoint(ckpt_path)
        assert is_valid is True


class TestCheckpointManagerListing:
    """Testes de listagem e ordenação."""

    def test_list_checkpoints_by_metric_sharpe(
        self, mock_checkpoint_dir, encryption_key_env
    ):
        """Lista checkpoints ordenados por Sharpe."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        # Salvar 3 checkpoints com Sharpe diferentes
        for i, sharpe in enumerate([0.8, 1.2, 0.5]):
            metrics = {"sharpe": sharpe, "loss": 0.1}
            manager.save_checkpoint(
                model={"dummy": i},
                step=i * 1000,
                metrics=metrics,
            )

        # Listar por Sharpe descending
        results = manager.list_checkpoints_by_metric("sharpe", top_n=3, sort_order="desc")
        assert len(results) == 3
        assert results[0]["metric_value"] == 1.2
        assert results[1]["metric_value"] == 0.8
        assert results[2]["metric_value"] == 0.5

    def test_list_checkpoints_top_n(
        self, mock_checkpoint_dir, encryption_key_env
    ):
        """Respeita limite top_n."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        for i in range(5):
            metrics = {"sharpe": float(i)}
            manager.save_checkpoint(
                model={"dummy": i},
                step=i * 1000,
                metrics=metrics,
            )

        results = manager.list_checkpoints_by_metric("sharpe", top_n=2)
        assert len(results) == 2


class TestCheckpointManagerCleanup:
    """Testes de limpeza de checkpoints antigos."""

    def test_cleanup_old_checkpoints_keeps_recent(
        self, mock_checkpoint_dir, encryption_key_env
    ):
        """Mantém apenas N checkpoints recentes."""
        manager = CheckpointManager(
            checkpoint_dir=mock_checkpoint_dir, keep_last_n=3
        )

        # Salvar 5 checkpoints
        for i in range(5):
            metrics = {"sharpe": float(i)}
            manager.save_checkpoint(
                model={"dummy": i},
                step=i * 1000,
                metrics=metrics,
            )

        deleted = manager.cleanup_old_checkpoints(keep_last_n=3)
        assert deleted == 2

        # Verificar que apenas 3 checkpoint JSONs permanecem
        json_files = list(Path(mock_checkpoint_dir).glob("*.json"))
        assert len(json_files) == 3

    def test_cleanup_zero_deletion_if_small_set(
        self, mock_checkpoint_dir, encryption_key_env
    ):
        """Não deleta nada se num checkpoints <= keep_last_n."""
        manager = CheckpointManager(
            checkpoint_dir=mock_checkpoint_dir, keep_last_n=10
        )

        for i in range(3):
            metrics = {"sharpe": float(i)}
            manager.save_checkpoint(
                model={"dummy": i},
                step=i * 1000,
                metrics=metrics,
            )

        deleted = manager.cleanup_old_checkpoints()
        assert deleted == 0


class TestCheckpointManagerMetadata:
    """Testes de metadata e auditoria."""

    def test_checkpoint_creates_metadata_json(
        self, mock_checkpoint_dir, encryption_key_env, mock_checkpoint_data
    ):
        """Cria arquivo JSON com metadata para auditoria."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        ckpt_path, _ = manager.save_checkpoint(
            model=mock_checkpoint_data["model"],
            step=mock_checkpoint_data["step"],
            metrics=mock_checkpoint_data["metrics"],
        )

        # Procurar arquivo JSON correspondente
        json_files = list(Path(mock_checkpoint_dir).glob("*.json"))
        assert len(json_files) > 0

        # Verificar conteúdo
        with open(json_files[-1], "r") as f:
            metadata = json.load(f)
            assert metadata["step"] == mock_checkpoint_data["step"]
            assert "sha256" in metadata
            assert "timestamp" in metadata


class TestCheckpointManagerEdgeCases:
    """Testes de casos extremos e recuperação."""

    def test_save_invalid_metrics_raises(self, mock_checkpoint_dir, encryption_key_env):
        """Rejeita metrics que não é dict."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        with pytest.raises(ValueError, match="dicionário"):
            manager.save_checkpoint(
                model={"dummy": "model"},
                step=100,
                metrics="not_a_dict",  # Inválido
            )

    def test_load_nonexistent_checkpoint_raises(self, mock_checkpoint_dir):
        """Falha ao carregar checkpoint que não existe."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        with pytest.raises(FileNotFoundError):
            manager.load_checkpoint("/nonexistent/path/checkpoint.joblib")

    def test_checkpoint_survives_multiple_iterations(
        self, mock_checkpoint_dir, encryption_key_env
    ):
        """Múltiplas save/load cycles funcionam corretamente."""
        manager = CheckpointManager(checkpoint_dir=mock_checkpoint_dir)

        for iteration in range(3):
            # Salvar
            data = {"model": {"iteration": iteration}}
            metrics = {"sharpe": float(iteration)}
            ckpt_path, _ = manager.save_checkpoint(
                model=data,
                step=iteration * 10000,
                metrics=metrics,
            )

            # Carregar
            loaded_model, loaded_metadata = manager.load_checkpoint(ckpt_path)
            assert loaded_model == data
            assert loaded_metadata["step"] == iteration * 10000
