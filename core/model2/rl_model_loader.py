"""Carregador de modelo RL com fallback determinístico para Model 2.0.

Implementa RF-RL-004: o agente PPO deve operar em modo degradado
(fallback determinístico) caso o checkpoint não esteja disponível.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_FALLBACK_CONFIDENCE = 0.70
_PPO_AVAILABLE: bool | None = None


def _check_ppo_available() -> bool:
    global _PPO_AVAILABLE
    if _PPO_AVAILABLE is None:
        try:
            import stable_baselines3  # noqa: F401
            _PPO_AVAILABLE = True
        except ImportError:
            _PPO_AVAILABLE = False
    return bool(_PPO_AVAILABLE)


class RLModelLoader:
    """Carrega modelo PPO e provê predição com fallback determinístico.

    Quando o checkpoint não está disponível ou ocorre erro de carga,
    o loader entra em modo fallback e retorna confiança padrão.
    """

    def __init__(self, checkpoint_path: Path | str | None = None) -> None:
        self._model: Any = None
        self._fallback_mode: bool = False
        self._fallback_reason: str = ""
        self._checkpoint_path: Path | None = (
            Path(checkpoint_path) if checkpoint_path else None
        )
        self._load()

    # ------------------------------------------------------------------
    # Propriedades públicas
    # ------------------------------------------------------------------

    @property
    def is_fallback(self) -> bool:
        """True se o loader está em modo fallback determinístico."""
        return self._fallback_mode

    @property
    def fallback_reason(self) -> str:
        """Motivo pelo qual o fallback foi ativado."""
        return self._fallback_reason

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Tenta carregar o checkpoint PPO; ativa fallback em caso de falha."""
        if not _check_ppo_available():
            self._activate_fallback("stable_baselines3 nao disponivel")
            return

        path = self._resolve_checkpoint()
        if path is None or not path.exists():
            self._activate_fallback(
                f"checkpoint nao encontrado: {path}"
            )
            return

        try:
            from stable_baselines3 import PPO  # type: ignore[import]

            self._model = PPO.load(str(path))
            logger.info("[RL] Modelo PPO carregado: %s", path)
        except Exception as exc:
            self._activate_fallback(f"erro ao carregar checkpoint: {exc}")

    def _resolve_checkpoint(self) -> Path | None:
        """Resolve o caminho do checkpoint procurando nos locais padrão."""
        if self._checkpoint_path is not None:
            return self._checkpoint_path

        repo_root = Path(__file__).resolve().parents[2]
        candidates = [
            repo_root / "checkpoints" / "ppo_training" / "ppo_model.pkl",
            repo_root / "checkpoints" / "ppo_training" / "best_model.pkl",
            repo_root / "models" / "ppo_model.pkl",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _activate_fallback(self, reason: str) -> None:
        self._fallback_mode = True
        self._fallback_reason = reason
        logger.warning(
            "[RL] Modo fallback determinístico ativado: %s", reason
        )

    # ------------------------------------------------------------------
    # Predição
    # ------------------------------------------------------------------

    def predict_confidence(
        self,
        features: np.ndarray,
        signal_side: str = "",
    ) -> tuple[float, str]:
        """Retorna (confiança, acao) para o vetor de features fornecido.

        Em modo fallback, retorna confiança padrão baseada no signal_side
        determinístico sem executar inferência do modelo PPO.

        Args:
            features: Vetor de features (n_features,).
            signal_side: Direção do sinal determinístico (BUY/SELL/LONG/SHORT).

        Returns:
            Tupla (confiança [0.0–1.0], acao ['LONG'|'SHORT'|'HOLD']).
        """
        if self._fallback_mode or self._model is None:
            return self._deterministic_fallback(signal_side)

        try:
            action_id, _states = self._model.predict(
                features.reshape(1, -1) if features.ndim == 1 else features,
                deterministic=True,
            )
            action_map = {0: "HOLD", 1: "LONG", 2: "SHORT"}
            action = action_map.get(int(action_id.flat[0]), "HOLD")

            expected = (
                "LONG"
                if signal_side.upper() in {"BUY", "LONG"}
                else "SHORT"
                if signal_side.upper() in {"SELL", "SHORT"}
                else ""
            )
            if action == expected:
                confidence = 0.85
            elif action == "HOLD":
                confidence = 0.55
            else:
                confidence = 0.30
            return confidence, action
        except Exception as exc:
            logger.error("[RL] Erro em predict_confidence: %s", exc)
            return self._deterministic_fallback(signal_side)

    @staticmethod
    def _deterministic_fallback(signal_side: str) -> tuple[float, str]:
        side = signal_side.upper()
        if side in {"BUY", "LONG"}:
            return _DEFAULT_FALLBACK_CONFIDENCE, "LONG"
        if side in {"SELL", "SHORT"}:
            return _DEFAULT_FALLBACK_CONFIDENCE, "SHORT"
        return _DEFAULT_FALLBACK_CONFIDENCE, "HOLD"
