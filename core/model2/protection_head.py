"""Modelo leve para previsao de multiplicadores de protecao (SL/TP) por simbolo."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class ProtectionMultipliers:
    """Saida do head de protecao com multiplicadores normalizados."""

    sl_multiplier: float
    tp_multiplier: float
    source: str


@dataclass(frozen=True)
class ProtectionHeadModel:
    """Regressor linear simples com normalizacao para SL/TP."""

    weights_sl: np.ndarray
    bias_sl: float
    weights_tp: np.ndarray
    bias_tp: float
    feature_mean: np.ndarray
    feature_std: np.ndarray

    def predict(self, features: Sequence[float]) -> tuple[float, float]:
        x = np.asarray(features, dtype=float)
        if x.ndim != 1:
            x = x.reshape(-1)
        if x.shape[0] != self.weights_sl.shape[0]:
            raise ValueError("feature_size_invalido")

        normalized = (x - self.feature_mean) / np.maximum(self.feature_std, 1e-9)
        raw_sl = float(np.dot(normalized, self.weights_sl) + self.bias_sl)
        raw_tp = float(np.dot(normalized, self.weights_tp) + self.bias_tp)

        sl_mult = 0.75 + 0.50 * _sigmoid(raw_sl)
        tp_mult = 0.70 + 1.30 * _sigmoid(raw_tp)
        return float(sl_mult), float(tp_mult)

    def to_json_dict(self) -> dict[str, object]:
        return {
            "weights_sl": self.weights_sl.tolist(),
            "bias_sl": float(self.bias_sl),
            "weights_tp": self.weights_tp.tolist(),
            "bias_tp": float(self.bias_tp),
            "feature_mean": self.feature_mean.tolist(),
            "feature_std": self.feature_std.tolist(),
        }

    @classmethod
    def from_json_dict(cls, payload: dict[str, object]) -> "ProtectionHeadModel":
        return cls(
            weights_sl=np.asarray(payload.get("weights_sl", []), dtype=float),
            bias_sl=float(payload.get("bias_sl", 0.0)),
            weights_tp=np.asarray(payload.get("weights_tp", []), dtype=float),
            bias_tp=float(payload.get("bias_tp", 0.0)),
            feature_mean=np.asarray(payload.get("feature_mean", []), dtype=float),
            feature_std=np.asarray(payload.get("feature_std", []), dtype=float),
        )


class ProtectionHeadRegistry:
    """Carrega e aplica modelos de protecao por simbolo."""

    def __init__(self, *, repo_root: Path) -> None:
        self._repo_root = Path(repo_root)
        self._cache: dict[str, ProtectionHeadModel | None] = {}

    def _resolve_model_path(self, symbol: str) -> Path:
        normalized = str(symbol).strip().upper()
        return self._repo_root / "models" / "protection_heads" / f"{normalized}_protection_head.json"

    def load(self, symbol: str) -> ProtectionHeadModel | None:
        normalized = str(symbol).strip().upper()
        if normalized in self._cache:
            return self._cache[normalized]

        path = self._resolve_model_path(normalized)
        if not path.exists():
            self._cache[normalized] = None
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                self._cache[normalized] = None
                return None
            model = ProtectionHeadModel.from_json_dict(payload)
            self._cache[normalized] = model
            return model
        except Exception:
            self._cache[normalized] = None
            return None

    def predict(self, *, symbol: str, features: Sequence[float]) -> ProtectionMultipliers | None:
        model = self.load(symbol)
        if model is None:
            return None
        try:
            sl_mult, tp_mult = model.predict(features)
            return ProtectionMultipliers(
                sl_multiplier=float(sl_mult),
                tp_multiplier=float(tp_mult),
                source="trained_protection_head",
            )
        except Exception:
            return None


def train_protection_head(
    *,
    features: np.ndarray,
    targets: np.ndarray,
    epochs: int = 300,
    learning_rate: float = 0.03,
) -> ProtectionHeadModel:
    """Treina regressao leve para multiplicadores de SL/TP."""
    if features.ndim != 2:
        raise ValueError("features_deve_ser_2d")
    if targets.ndim != 2 or targets.shape[1] != 2:
        raise ValueError("targets_deve_ser_nx2")
    if features.shape[0] != targets.shape[0]:
        raise ValueError("amostras_incompativeis")
    if features.shape[0] == 0:
        raise ValueError("sem_amostras")

    feature_mean = features.mean(axis=0)
    feature_std = features.std(axis=0)
    normalized = (features - feature_mean) / np.maximum(feature_std, 1e-9)

    y_sl = np.clip((targets[:, 0] - 0.75) / 0.50, 1e-5, 1 - 1e-5)
    y_tp = np.clip((targets[:, 1] - 0.70) / 1.30, 1e-5, 1 - 1e-5)

    z_sl = np.log(y_sl / (1.0 - y_sl))
    z_tp = np.log(y_tp / (1.0 - y_tp))

    n_features = normalized.shape[1]
    w_sl = np.zeros(n_features, dtype=float)
    b_sl = 0.0
    w_tp = np.zeros(n_features, dtype=float)
    b_tp = 0.0

    n = float(normalized.shape[0])
    for _ in range(max(1, int(epochs))):
        pred_sl = normalized @ w_sl + b_sl
        pred_tp = normalized @ w_tp + b_tp

        err_sl = pred_sl - z_sl
        err_tp = pred_tp - z_tp

        grad_w_sl = (normalized.T @ err_sl) / n
        grad_b_sl = float(err_sl.mean())
        grad_w_tp = (normalized.T @ err_tp) / n
        grad_b_tp = float(err_tp.mean())

        w_sl -= float(learning_rate) * grad_w_sl
        b_sl -= float(learning_rate) * grad_b_sl
        w_tp -= float(learning_rate) * grad_w_tp
        b_tp -= float(learning_rate) * grad_b_tp

    return ProtectionHeadModel(
        weights_sl=w_sl,
        bias_sl=float(b_sl),
        weights_tp=w_tp,
        bias_tp=float(b_tp),
        feature_mean=feature_mean,
        feature_std=feature_std,
    )


def _sigmoid(value: float) -> float:
    clipped = max(-50.0, min(50.0, float(value)))
    return 1.0 / (1.0 + float(np.exp(-clipped)))
