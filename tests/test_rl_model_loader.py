"""Testes para RLModelLoader com fallback determinístico (RF-RL-004)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.model2.rl_model_loader import (
    RLModelLoader,
    _DEFAULT_FALLBACK_CONFIDENCE,
)


class TestFallbackSemCheckpoint:
    """Testa fallback quando checkpoint nao existe."""

    def test_fallback_ativo_sem_checkpoint(self) -> None:
        loader = RLModelLoader(checkpoint_path="/tmp/inexistente.pkl")
        assert loader.is_fallback is True
        assert loader.fallback_reason != ""

    def test_predict_long_fallback(self) -> None:
        loader = RLModelLoader(checkpoint_path="/tmp/inexistente.pkl")
        features = np.zeros(5, dtype=np.float32)
        confidence, action = loader.predict_confidence(features, signal_side="BUY")
        assert confidence == _DEFAULT_FALLBACK_CONFIDENCE
        assert action == "LONG"

    def test_predict_short_fallback(self) -> None:
        loader = RLModelLoader(checkpoint_path="/tmp/inexistente.pkl")
        features = np.zeros(5, dtype=np.float32)
        confidence, action = loader.predict_confidence(features, signal_side="SELL")
        assert confidence == _DEFAULT_FALLBACK_CONFIDENCE
        assert action == "SHORT"

    def test_predict_hold_fallback_side_vazio(self) -> None:
        loader = RLModelLoader(checkpoint_path="/tmp/inexistente.pkl")
        features = np.zeros(5, dtype=np.float32)
        confidence, action = loader.predict_confidence(features, signal_side="")
        assert confidence == _DEFAULT_FALLBACK_CONFIDENCE
        assert action == "HOLD"


class TestFallbackSemSB3:
    """Testa fallback quando stable_baselines3 nao esta instalado."""

    def test_fallback_quando_sb3_indisponivel(self, tmp_path: Path) -> None:
        fake_checkpoint = tmp_path / "ppo_model.pkl"
        fake_checkpoint.write_bytes(b"fake")

        with patch("core.model2.rl_model_loader._check_ppo_available", return_value=False):
            loader = RLModelLoader(checkpoint_path=fake_checkpoint)

        assert loader.is_fallback is True
        assert "nao disponivel" in loader.fallback_reason.lower()

    def test_predict_ainda_funciona_sem_sb3(self, tmp_path: Path) -> None:
        fake_checkpoint = tmp_path / "ppo_model.pkl"
        fake_checkpoint.write_bytes(b"fake")

        with patch("core.model2.rl_model_loader._check_ppo_available", return_value=False):
            loader = RLModelLoader(checkpoint_path=fake_checkpoint)

        features = np.ones(5, dtype=np.float32)
        confidence, action = loader.predict_confidence(features, signal_side="LONG")
        assert 0.0 <= confidence <= 1.0
        assert action in {"LONG", "SHORT", "HOLD"}


class TestComModeloCarregado:
    """Testa predicao quando um modelo PPO mock esta disponivel."""

    def test_predicao_com_modelo_mock(self, tmp_path: Path) -> None:
        fake_checkpoint = tmp_path / "ppo_model.pkl"
        fake_checkpoint.write_bytes(b"fake")

        mock_model = MagicMock()
        mock_model.predict.return_value = (np.array([1]), None)

        with (
            patch("core.model2.rl_model_loader._check_ppo_available", return_value=True),
            patch("stable_baselines3.PPO.load", return_value=mock_model),
        ):
            loader = RLModelLoader(checkpoint_path=fake_checkpoint)
            loader._model = mock_model
            loader._fallback_mode = False

        features = np.zeros(5, dtype=np.float32)
        confidence, action = loader.predict_confidence(features, signal_side="BUY")
        assert action == "LONG"
        assert confidence == 0.85  # PPO concorda com sinal

    def test_predicao_com_desacordo_baixa_confianca(self, tmp_path: Path) -> None:
        """PPO retorna SHORT mas sinal e LONG -> confianca baixa."""
        mock_model = MagicMock()
        mock_model.predict.return_value = (np.array([2]), None)  # SHORT

        loader = RLModelLoader.__new__(RLModelLoader)
        loader._model = mock_model
        loader._fallback_mode = False
        loader._fallback_reason = ""
        loader._checkpoint_path = None

        features = np.zeros(5, dtype=np.float32)
        confidence, action = loader.predict_confidence(features, signal_side="BUY")
        assert action == "SHORT"
        assert confidence == 0.30

    def test_predicao_hold_confianca_media(self) -> None:
        """PPO retorna HOLD -> confianca media."""
        mock_model = MagicMock()
        mock_model.predict.return_value = (np.array([0]), None)  # HOLD

        loader = RLModelLoader.__new__(RLModelLoader)
        loader._model = mock_model
        loader._fallback_mode = False
        loader._fallback_reason = ""
        loader._checkpoint_path = None

        features = np.zeros(5, dtype=np.float32)
        confidence, action = loader.predict_confidence(features, signal_side="SELL")
        assert action == "HOLD"
        assert confidence == 0.55

    def test_fallback_em_erro_de_predicao(self) -> None:
        """Erro durante predict ativa fallback automaticamente."""
        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("erro de GPU")

        loader = RLModelLoader.__new__(RLModelLoader)
        loader._model = mock_model
        loader._fallback_mode = False
        loader._fallback_reason = ""
        loader._checkpoint_path = None

        features = np.zeros(5, dtype=np.float32)
        confidence, action = loader.predict_confidence(features, signal_side="BUY")
        assert confidence == _DEFAULT_FALLBACK_CONFIDENCE
        assert action == "LONG"
