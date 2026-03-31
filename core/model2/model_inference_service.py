"""Servico desacoplado de inferencia para decisao model-driven (M2-020.2)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

import numpy as np
from numpy.typing import NDArray

from .model_decision import (
    ACTION_HOLD,
    ACTION_OPEN_LONG,
    ACTION_OPEN_SHORT,
    M2_020_1_RULE_ID,
    ModelDecision,
    ModelDecisionInput,
    evaluate_model_decision_payload,
)
from .protection_head import ProtectionHeadRegistry
from .rl_model_loader import RLModelLoader

M2_020_2_RULE_ID = "M2-020.2-RULE-DECOUPLED-INFERENCE-SERVICE"
DEFAULT_MODEL_VERSION = "m2-inference-v1"


class InferenceProvider(Protocol):
    """Contrato de provider de inferencia para permitir troca de implementacao."""

    def infer(self, model_input: ModelDecisionInput) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class InferenceServiceResult:
    """Resultado de inferencia com telemetria operacional."""

    accepted: bool
    decision: ModelDecision | None
    model_version: str
    inference_latency_ms: int
    reason: str
    rule_id: str
    details: Mapping[str, Any]


class TechnicalSignalInferenceProvider:
    """Provider inicial para M2-020.2 com inferencia baseada no candidato atual.

    Mantem o comportamento estavel enquanto desacopla o ponto de decisao.
    """

    def __init__(self, *, model_first: bool = True) -> None:
        self._repo_root = Path(__file__).resolve().parents[2]
        self._model_first = bool(model_first)
        self._default_loader = RLModelLoader()
        self._protection_heads = ProtectionHeadRegistry(repo_root=self._repo_root)
        self._loaders_by_symbol: dict[str, RLModelLoader] = {}

    @staticmethod
    def _resolve_action_from_signal_side(signal_side: str) -> str:
        normalized = str(signal_side).strip().upper()
        if normalized == "LONG":
            return ACTION_OPEN_LONG
        if normalized == "SHORT":
            return ACTION_OPEN_SHORT
        return ACTION_HOLD

    @staticmethod
    def _resolve_action_from_rl_action(rl_action: str) -> str:
        normalized = str(rl_action).strip().upper()
        if normalized == "LONG":
            return ACTION_OPEN_LONG
        if normalized == "SHORT":
            return ACTION_OPEN_SHORT
        return ACTION_HOLD

    @staticmethod
    def _build_features(model_input: ModelDecisionInput) -> NDArray[np.float64]:
        market_state = dict(model_input.market_state)
        risk_state = dict(model_input.risk_state)
        position_state = dict(model_input.position_state)
        market_context = market_state.get("market_context")
        market_context_dict = dict(market_context) if isinstance(market_context, Mapping) else {}

        close_price = float(market_state.get("close_price") or market_state.get("entry_price") or 0.0)
        stop_loss = float(market_state.get("stop_loss") or 0.0)
        take_profit = float(market_state.get("take_profit") or 0.0)
        funding_rate = float(
            market_state.get("funding_rate")
            or market_context_dict.get("funding_rate")
            or 0.0
        )
        basis = float(
            market_state.get("basis")
            or market_context_dict.get("basis")
            or 0.0
        )
        signal_age_ms = float(risk_state.get("signal_age_ms") or 0.0)
        if signal_age_ms <= 0:
            signal_timestamp = market_state.get("signal_timestamp")
            try:
                if signal_timestamp is not None:
                    signal_age_ms = max(
                        0.0,
                        float(model_input.decision_timestamp) - float(signal_timestamp),
                    )
            except (TypeError, ValueError):
                signal_age_ms = 0.0
        open_position_qty = float(position_state.get("position_size_qty") or 0.0)

        risk_distance = abs(stop_loss - close_price)
        reward_distance = abs(take_profit - close_price)
        rr_ratio = reward_distance / risk_distance if risk_distance > 0 else 0.0

        features = np.array(
            [
                close_price,
                stop_loss,
                take_profit,
                rr_ratio,
                funding_rate,
                basis,
                signal_age_ms / 3_600_000.0,  # horas
                open_position_qty,
            ],
            dtype=float,
        )
        return features

    def _resolve_loader_for_symbol(self, symbol: str) -> RLModelLoader:
        normalized_symbol = str(symbol).strip().upper()
        if normalized_symbol in self._loaders_by_symbol:
            return self._loaders_by_symbol[normalized_symbol]

        entry_checkpoint = (
            self._repo_root
            / "models"
            / "sub_agents"
            / f"{normalized_symbol}_entry_ppo.zip"
        )
        if entry_checkpoint.exists():
            loader = RLModelLoader(checkpoint_path=entry_checkpoint)
        else:
            loader = self._default_loader

        self._loaders_by_symbol[normalized_symbol] = loader
        return loader

    @staticmethod
    def _confidence_from_rl(
        *,
        action: str,
        rl_confidence: float,
        rl_action: str,
    ) -> tuple[float, str]:
        if action == ACTION_HOLD:
            return 0.50, "inference_hold_signal"

        expected_side = "LONG" if action == ACTION_OPEN_LONG else "SHORT"
        normalized_rl_action = str(rl_action).strip().upper()

        base = max(0.0, min(1.0, float(rl_confidence)))
        if normalized_rl_action == expected_side:
            return max(0.55, min(0.95, base)), "inference_from_symbol_model_agreement"
        if normalized_rl_action == "HOLD":
            return max(0.45, min(0.75, base)), "inference_from_symbol_model_neutral"
        return max(0.30, min(0.65, base)), "inference_from_symbol_model_divergence"

    @staticmethod
    def _to_safe_float(raw_value: Any) -> float | None:
        try:
            if raw_value is None:
                return None
            return float(raw_value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _dimension_protection_targets(
        cls,
        *,
        action: str,
        entry_price: float | None,
        base_sl: float | None,
        base_tp: float | None,
        rl_confidence: float,
        rl_action: str,
        explicit_sl_multiplier: float | None = None,
        explicit_tp_multiplier: float | None = None,
        explicit_source: str | None = None,
    ) -> tuple[float | None, float | None, str]:
        """Dimensiona SL/TP por simbolo usando sinal do modelo com fallback seguro.

        Mantem fail-safe: se qualquer pre-condicao falhar, retorna alvos originais.
        """
        if action not in {ACTION_OPEN_LONG, ACTION_OPEN_SHORT}:
            return base_sl, base_tp, "hold_no_dimensioning"

        entry = cls._to_safe_float(entry_price)
        sl = cls._to_safe_float(base_sl)
        tp = cls._to_safe_float(base_tp)
        if entry is None or sl is None or tp is None:
            return base_sl, base_tp, "base_targets_missing"

        risk_distance = abs(sl - entry)
        if risk_distance <= 0:
            return base_sl, base_tp, "non_positive_risk_distance"

        if explicit_sl_multiplier is not None and explicit_tp_multiplier is not None:
            risk_multiplier = max(0.75, min(1.25, float(explicit_sl_multiplier)))
            rr_target = max(0.70, min(2.00, float(explicit_tp_multiplier)))
            profile = str(explicit_source or "trained")
        else:
            normalized_confidence = max(0.0, min(1.0, float(rl_confidence)))
            expected_side = "LONG" if action == ACTION_OPEN_LONG else "SHORT"
            normalized_rl_action = str(rl_action).strip().upper()

            if normalized_rl_action == expected_side:
                # Mais confiança -> stop mais justo e alvo mais ambicioso.
                risk_multiplier = max(0.80, 1.05 - (0.20 * normalized_confidence))
                rr_target = min(1.80, 1.00 + (0.80 * normalized_confidence))
                profile = "aligned"
            elif normalized_rl_action == "HOLD":
                # Conservador neutro: preserva distancia base.
                risk_multiplier = 1.00
                rr_target = 1.00
                profile = "neutral"
            else:
                # Divergencia: sai mais cedo (tp mais curto) e reduz risco de permanencia.
                risk_multiplier = 1.10
                rr_target = 0.80
                profile = "divergent"

        adjusted_risk = max(1e-9, risk_distance * risk_multiplier)
        adjusted_reward = max(1e-9, adjusted_risk * rr_target)

        if action == ACTION_OPEN_LONG:
            adjusted_sl = entry - adjusted_risk
            adjusted_tp = entry + adjusted_reward
            geometry_ok = adjusted_sl < entry < adjusted_tp
        else:
            adjusted_sl = entry + adjusted_risk
            adjusted_tp = entry - adjusted_reward
            geometry_ok = adjusted_tp < entry < adjusted_sl

        if not geometry_ok:
            return base_sl, base_tp, "fallback_invalid_geometry"

        if explicit_sl_multiplier is not None and explicit_tp_multiplier is not None:
            return adjusted_sl, adjusted_tp, f"rl_head_{profile}"
        return adjusted_sl, adjusted_tp, f"rl_dynamic_{profile}"

    def infer(self, model_input: ModelDecisionInput) -> Mapping[str, Any]:
        signal_side = str(model_input.market_state.get("signal_side") or "").upper()
        symbol = str(model_input.symbol).upper()
        fallback_action = self._resolve_action_from_signal_side(signal_side)

        entry_value = model_input.market_state.get("entry_price")
        base_sl_value = model_input.market_state.get("stop_loss")
        base_tp_value = model_input.market_state.get("take_profit")
        sl_value = self._to_safe_float(base_sl_value)
        tp_value = self._to_safe_float(base_tp_value)
        protection_sizing_source = "base_signal_targets"
        loader = self._resolve_loader_for_symbol(symbol)
        features = self._build_features(model_input)
        rl_confidence, rl_action = loader.predict_confidence(
            features=features,
            signal_side=signal_side,
        )

        if self._model_first:
            action = self._resolve_action_from_rl_action(rl_action)
            action_source = "rl_action"
        else:
            action = fallback_action
            action_source = "signal_side"

        if action == ACTION_HOLD:
            size_fraction = 0.0
            sl_value = None
            tp_value = None
            confidence = 0.50
            reason = "inference_hold_signal"
            if not self._model_first:
                rl_confidence = confidence
                rl_action = "HOLD"
        else:
            size_fraction = 1.0
            head_prediction = self._protection_heads.predict(
                symbol=symbol,
                features=features.tolist(),
            )
            sl_value, tp_value, protection_sizing_source = self._dimension_protection_targets(
                action=action,
                entry_price=self._to_safe_float(entry_value),
                base_sl=self._to_safe_float(base_sl_value),
                base_tp=self._to_safe_float(base_tp_value),
                rl_confidence=float(rl_confidence),
                rl_action=str(rl_action),
                explicit_sl_multiplier=(head_prediction.sl_multiplier if head_prediction is not None else None),
                explicit_tp_multiplier=(head_prediction.tp_multiplier if head_prediction is not None else None),
                explicit_source=(head_prediction.source if head_prediction is not None else None),
            )
            confidence, reason = self._confidence_from_rl(
                action=action,
                rl_confidence=float(rl_confidence),
                rl_action=str(rl_action),
            )

        return {
            "action": action,
            "confidence": confidence,
            "size_fraction": size_fraction,
            "sl": sl_value,
            "tp": tp_value,
            "reason": reason,
            "metadata": {
                "provider": "TechnicalSignalInferenceProvider",
                "source_rule_id": M2_020_1_RULE_ID,
                "symbol": symbol,
                "model_first": bool(self._model_first),
                "action_source": action_source,
                "signal_side": signal_side,
                "fallback_action": fallback_action,
                "rl_action": str(rl_action),
                "rl_confidence": float(rl_confidence),
                "protection_sizing_source": protection_sizing_source,
                "rl_fallback": bool(loader.is_fallback),
                "rl_fallback_reason": loader.fallback_reason,
            },
        }


class ModelInferenceService:
    """Executa inferencia de forma desacoplada e retorna decisao validada."""

    def __init__(
        self,
        *,
        provider: InferenceProvider | None = None,
        model_version: str = DEFAULT_MODEL_VERSION,
        competence_checker: Callable[[str], bool] | None = None,
    ) -> None:
        self._provider = provider or TechnicalSignalInferenceProvider()
        self._model_version = str(model_version)
        self._competence_checker = competence_checker

    @property
    def model_version(self) -> str:
        return self._model_version

    def is_model_competent(self) -> tuple[bool, str]:
        if not self._model_version.strip():
            return False, "model_version_missing"

        if not callable(getattr(self._provider, "infer", None)):
            return False, "provider_infer_unavailable"

        if self._competence_checker is not None:
            try:
                if not bool(self._competence_checker(self._model_version)):
                    return False, "competence_checker_rejected"
            except Exception:
                return False, "competence_checker_error"

        return True, "ok"

    def infer(self, model_input: ModelDecisionInput) -> InferenceServiceResult:
        competent, competence_reason = self.is_model_competent()
        if not competent:
            return InferenceServiceResult(
                accepted=False,
                decision=None,
                model_version=self._model_version,
                inference_latency_ms=0,
                reason="model_incompetent",
                rule_id=M2_020_2_RULE_ID,
                details={"competence_reason": competence_reason},
            )

        started = time.perf_counter()
        try:
            raw_payload = self._provider.infer(model_input)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return InferenceServiceResult(
                accepted=False,
                decision=None,
                model_version=self._model_version,
                inference_latency_ms=max(0, elapsed_ms),
                reason="inference_provider_error",
                rule_id=M2_020_2_RULE_ID,
                details={"error": str(exc)},
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        outcome = evaluate_model_decision_payload(model_input, raw_payload)
        return InferenceServiceResult(
            accepted=bool(outcome.allow_execution and outcome.decision is not None),
            decision=outcome.decision,
            model_version=self._model_version,
            inference_latency_ms=max(0, elapsed_ms),
            reason=str(outcome.reason),
            rule_id=M2_020_2_RULE_ID,
            details=dict(outcome.details),
        )
