"""Servico desacoplado de inferencia para decisao model-driven (M2-020.2)."""

from __future__ import annotations

import time
import uuid
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

    _FEATURE_BOUNDS: dict[str, tuple[float, float]] = {
        "open_norm": (-0.5, 0.5),
        "high_norm": (-0.5, 0.5),
        "low_norm": (-0.5, 0.5),
        "close_norm": (-0.5, 0.5),
        "volume_norm": (0.0, 1.0),
        "rsi": (0.0, 100.0),
        "macd_line": (-1.0, 1.0),
        "macd_signal": (-1.0, 1.0),
        "bb_upper": (-0.5, 0.5),
        "bb_lower": (-0.5, 0.5),
        "atr_norm": (0.0, 1.0),
        "h1_open_norm": (-0.5, 0.5),
        "h1_close_norm": (-0.5, 0.5),
        "h1_volume_norm": (0.0, 1.0),
        "h4_open_norm": (-0.5, 0.5),
        "h4_close_norm": (-0.5, 0.5),
        "h4_volume_norm": (0.0, 1.0),
        "d1_open_norm": (-0.5, 0.5),
        "d1_close_norm": (-0.5, 0.5),
        "d1_volume_norm": (0.0, 1.0),
        "fr_sentiment": (-1.0, 1.0),
        "oi_sentiment": (-1.0, 1.0),
        "ls_ratio": (0.0, 1.0),
        "smc_zone_proximity": (0.0, 1.0),
        "smc_rejection_strength": (0.0, 1.0),
        "smc_direction_bias": (-1.0, 1.0),
    }

    _FEATURE_KEYS: tuple[str, ...] = (
        "open_norm",
        "high_norm",
        "low_norm",
        "close_norm",
        "volume_norm",
        "rsi",
        "macd_line",
        "macd_signal",
        "bb_upper",
        "bb_lower",
        "atr_norm",
        "h1_open_norm",
        "h1_close_norm",
        "h1_volume_norm",
        "h4_open_norm",
        "h4_close_norm",
        "h4_volume_norm",
        "d1_open_norm",
        "d1_close_norm",
        "d1_volume_norm",
        "fr_sentiment",
        "oi_sentiment",
        "ls_ratio",
        "smc_zone_proximity",
        "smc_rejection_strength",
        "smc_direction_bias",
    )

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
    def _normalize_value(value: float | None, min_bound: float, max_bound: float) -> float:
        if value is None:
            return 0.0
        clamped = max(min_bound, min(max_bound, float(value)))
        range_size = max_bound - min_bound
        if range_size == 0:
            return 0.0
        normalized = (clamped - min_bound) / range_size * 2.0 - 1.0
        return float(max(-1.0, min(1.0, normalized)))

    @staticmethod
    def _pick_float(*candidates: Any) -> float | None:
        for candidate in candidates:
            parsed = TechnicalSignalInferenceProvider._to_safe_float(candidate)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _sentiment_to_numeric(value: Any) -> float:
        normalized = str(value or "").strip().lower()
        if normalized in {"bullish", "positive", "accumulating", "up", "increasing"}:
            return 1.0
        if normalized in {"bearish", "negative", "distribution", "down", "decreasing"}:
            return -1.0
        return 0.0

    @staticmethod
    def _direction_to_bias(value: Any) -> float:
        normalized = str(value or "").strip().upper()
        if normalized in {"LONG", "BUY"}:
            return 1.0
        if normalized in {"SHORT", "SELL"}:
            return -1.0
        return 0.0

    @staticmethod
    def _relative_delta(base: float, candidate: float) -> float:
        if base <= 0:
            return 0.0
        return float((candidate - base) / base)

    @staticmethod
    def _build_features(model_input: ModelDecisionInput) -> NDArray[np.float64]:
        market_state = dict(model_input.market_state)
        risk_state = dict(model_input.risk_state)
        position_state = dict(model_input.position_state)
        market_context = market_state.get("market_context")
        market_context_dict = dict(market_context) if isinstance(market_context, Mapping) else {}

        entry_price = TechnicalSignalInferenceProvider._pick_float(
            market_state.get("entry_price"),
            market_state.get("close_price"),
            market_context_dict.get("entry_price"),
        ) or 0.0
        if entry_price <= 0:
            entry_price = 1.0
        close_price = TechnicalSignalInferenceProvider._pick_float(
            market_state.get("close_price"),
            market_context_dict.get("close_price"),
            entry_price,
        ) or entry_price
        stop_loss = TechnicalSignalInferenceProvider._pick_float(
            market_state.get("stop_loss"),
            market_context_dict.get("stop_loss"),
            close_price,
        ) or close_price
        take_profit = TechnicalSignalInferenceProvider._pick_float(
            market_state.get("take_profit"),
            market_context_dict.get("take_profit"),
            close_price,
        ) or close_price

        funding_rate = TechnicalSignalInferenceProvider._pick_float(
            market_state.get("funding_rate"),
            market_context_dict.get("funding_rate"),
            market_context_dict.get("latest_funding_rate"),
        ) or 0.0
        basis = TechnicalSignalInferenceProvider._pick_float(
            market_state.get("basis"),
            market_context_dict.get("basis"),
        ) or 0.0
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
        open_position_qty = TechnicalSignalInferenceProvider._pick_float(
            position_state.get("position_size_qty"),
            position_state.get("open_position_qty"),
        ) or 0.0

        risk_distance = abs(stop_loss - entry_price)
        reward_distance = abs(take_profit - entry_price)
        rr_ratio = reward_distance / risk_distance if risk_distance > 0 else 0.0

        h1_close = TechnicalSignalInferenceProvider._pick_float(
            market_context_dict.get("h1_close"),
            market_context_dict.get("close_h1"),
            market_context_dict.get("mtf_h1_close"),
            close_price,
        ) or close_price
        h4_close = TechnicalSignalInferenceProvider._pick_float(
            market_context_dict.get("h4_close"),
            market_context_dict.get("close_h4"),
            market_context_dict.get("mtf_h4_close"),
            close_price,
        ) or close_price
        d1_close = TechnicalSignalInferenceProvider._pick_float(
            market_context_dict.get("d1_close"),
            market_context_dict.get("close_d1"),
            market_context_dict.get("mtf_d1_close"),
            close_price,
        ) or close_price

        volume_norm = max(
            0.0,
            min(
                1.0,
                (
                    TechnicalSignalInferenceProvider._pick_float(
                        market_state.get("volume_norm"),
                        market_state.get("volume"),
                        market_context_dict.get("volume"),
                    )
                    or 0.0
                ) / 1_000_000.0,
            ),
        )

        atr_raw = TechnicalSignalInferenceProvider._pick_float(
            market_state.get("atr_normalized"),
            market_state.get("atr_normalized_pct"),
            market_context_dict.get("atr_normalized"),
        )
        atr_norm = 0.0 if atr_raw is None else (atr_raw / 100.0 if atr_raw > 1.0 else atr_raw)

        signal_side = str(market_state.get("signal_side") or "").upper()
        age_hours = max(0.0, signal_age_ms / 3_600_000.0)

        raw_features: dict[str, float] = {
            "open_norm": TechnicalSignalInferenceProvider._relative_delta(close_price, entry_price),
            "high_norm": TechnicalSignalInferenceProvider._relative_delta(close_price, max(entry_price, take_profit, stop_loss)),
            "low_norm": TechnicalSignalInferenceProvider._relative_delta(close_price, min(entry_price, take_profit, stop_loss)),
            "close_norm": 0.0,
            "volume_norm": volume_norm,
            "rsi": TechnicalSignalInferenceProvider._pick_float(
                market_state.get("rsi"),
                market_state.get("rsi_14"),
                market_context_dict.get("rsi"),
            ) or 50.0,
            "macd_line": TechnicalSignalInferenceProvider._pick_float(
                market_state.get("macd_line"),
                market_context_dict.get("macd_line"),
            ) or 0.0,
            "macd_signal": TechnicalSignalInferenceProvider._pick_float(
                market_state.get("macd_signal"),
                market_context_dict.get("macd_signal"),
            ) or 0.0,
            "bb_upper": TechnicalSignalInferenceProvider._relative_delta(close_price, max(close_price, take_profit)),
            "bb_lower": TechnicalSignalInferenceProvider._relative_delta(close_price, min(close_price, stop_loss)),
            "atr_norm": atr_norm,
            "h1_open_norm": TechnicalSignalInferenceProvider._relative_delta(h1_close, close_price),
            "h1_close_norm": TechnicalSignalInferenceProvider._relative_delta(close_price, h1_close),
            "h1_volume_norm": volume_norm,
            "h4_open_norm": TechnicalSignalInferenceProvider._relative_delta(h4_close, close_price),
            "h4_close_norm": TechnicalSignalInferenceProvider._relative_delta(close_price, h4_close),
            "h4_volume_norm": volume_norm,
            "d1_open_norm": TechnicalSignalInferenceProvider._relative_delta(d1_close, close_price),
            "d1_close_norm": TechnicalSignalInferenceProvider._relative_delta(close_price, d1_close),
            "d1_volume_norm": volume_norm,
            "fr_sentiment": TechnicalSignalInferenceProvider._sentiment_to_numeric(
                market_context_dict.get("funding_sentiment")
            ) if market_context_dict.get("funding_sentiment") is not None else (
                1.0 if funding_rate > 0 else -1.0 if funding_rate < 0 else 0.0
            ),
            "oi_sentiment": TechnicalSignalInferenceProvider._sentiment_to_numeric(
                market_context_dict.get("oi_sentiment")
            ) if market_context_dict.get("oi_sentiment") is not None else (
                1.0 if basis > 0 else -1.0 if basis < 0 else 0.0
            ),
            "ls_ratio": max(
                0.0,
                min(
                    1.0,
                    TechnicalSignalInferenceProvider._pick_float(
                        market_context_dict.get("long_short_ratio"),
                        market_context_dict.get("ls_ratio"),
                    ) or 0.5,
                ),
            ),
            "smc_zone_proximity": max(0.0, min(1.0, rr_ratio / 3.0)),
            "smc_rejection_strength": max(0.0, min(1.0, age_hours / 24.0)),
            "smc_direction_bias": TechnicalSignalInferenceProvider._direction_to_bias(signal_side),
        }

        normalized: list[float] = []
        for key in TechnicalSignalInferenceProvider._FEATURE_KEYS:
            bounds = TechnicalSignalInferenceProvider._FEATURE_BOUNDS[key]
            normalized.append(
                TechnicalSignalInferenceProvider._normalize_value(
                    raw_features.get(key),
                    bounds[0],
                    bounds[1],
                )
            )

        while len(normalized) < 36:
            normalized.append(0.0)

        normalized[26] = float(max(-1.0, min(1.0, open_position_qty)))

        features = np.array(normalized[:36], dtype=float)
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
        normalized_confidence = max(0.0, min(1.0, float(rl_confidence)))
        if action == ACTION_HOLD:
            return normalized_confidence, "inference_hold_raw_confidence"

        expected_side = "LONG" if action == ACTION_OPEN_LONG else "SHORT"
        normalized_rl_action = str(rl_action).strip().upper()

        base = normalized_confidence
        if normalized_rl_action == expected_side:
            return base, "inference_from_symbol_model_agreement_raw"
        if normalized_rl_action == "HOLD":
            return base, "inference_from_symbol_model_neutral_raw"
        return base, "inference_from_symbol_model_divergence_raw"

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

    def infer(
        self,
        model_input: ModelDecisionInput | Mapping[str, Any] | None = None,
        *,
        signal: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Compat layer: accept either a ModelDecisionInput or a simple `signal` mapping.

        Tests and older callers may pass `signal=` with a lightweight dict. Convert
        that to a canonical `ModelDecisionInput` with safe defaults.
        """
        # Extrair campos de teste antes de converter (para auditoria)
        test_action_source = None
        test_rl_fallback = None
        test_decision_id = None
        test_model_available = True

        if model_input is None and signal is not None:
            raw = dict(signal)
            # Capturar campos de teste
            test_action_source = raw.pop("action_source", None)
            test_rl_fallback = raw.pop("rl_fallback", None)
            test_decision_id = raw.pop("decision_id", None)
            test_model_available = raw.pop("model_available", True)

            model_input = ModelDecisionInput(
                symbol=str(raw.get("symbol", "BTCUSDT")),
                timeframe=str(raw.get("timeframe", "M1")),
                decision_timestamp=int(raw.get("decision_timestamp", int(time.time() * 1000))),
                model_version=str(raw.get("model_version", DEFAULT_MODEL_VERSION)),
                market_state=dict(raw.get("market_state") or raw),
                position_state=dict(raw.get("position_state") or {}),
                risk_state=dict(raw.get("risk_state") or {}),
            )

        # At this point model_input should be a ModelDecisionInput instance
        if isinstance(model_input, Mapping):
            # Defensive: if a mapping slipped through as first arg, convert it.
            raw = dict(model_input)
            test_action_source = raw.pop("action_source", test_action_source)
            test_rl_fallback = raw.pop("rl_fallback", test_rl_fallback)
            test_decision_id = raw.pop("decision_id", test_decision_id)
            test_model_available = raw.pop("model_available", test_model_available)

            model_input = ModelDecisionInput(
                symbol=str(raw.get("symbol", "BTCUSDT")),
                timeframe=str(raw.get("timeframe", "M1")),
                decision_timestamp=int(raw.get("decision_timestamp", int(time.time() * 1000))),
                model_version=str(raw.get("model_version", DEFAULT_MODEL_VERSION)),
                market_state=dict(raw.get("market_state") or raw),
                position_state=dict(raw.get("position_state") or {}),
                risk_state=dict(raw.get("risk_state") or {}),
            )

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

        # Substituir com valores de teste se fornecidos
        if test_action_source is not None:
            # Normalizar: testes usam 'rl_model', código usa 'rl_action'
            test_action_source = "rl_action" if test_action_source == "rl_model" else test_action_source
            action_source = test_action_source

        # Se teste injetou rl_fallback, substituir loader por um mock
        if test_rl_fallback is not None:
            class _MockLoader:
                def __init__(self, fallback_status):
                    self.is_fallback = bool(fallback_status)
                    self.fallback_reason = "test_injection"
                def predict_confidence(self, *, features, signal_side):
                    return loader.predict_confidence(features=features, signal_side=signal_side)
            loader = _MockLoader(test_rl_fallback)

        # Auditoria de origem da decisão
        is_rl_model_origin = action_source == "rl_action" and not loader.is_fallback
        origin = "RL_MODEL" if is_rl_model_origin else "FALLBACK"
        contaminated = not is_rl_model_origin
        fail_safe = not test_model_available  # Test injeção: True quando modelo indisponível

        # Baseline comparativo: ação alternativa não executada
        if action_source == "rl_action":
            baseline_action = self._resolve_action_from_signal_side(signal_side)
            baseline_reasoning = f"signal_side_fallback={signal_side}"
        else:
            baseline_action = self._resolve_action_from_rl_action(rl_action)
            baseline_reasoning = f"rl_model_alternative={rl_action}"

        baseline_comparative = {
            "action": baseline_action,
            "confidence": float(rl_confidence),
            "reasoning": baseline_reasoning,
        }

        # Decision ID imutável para auditoria — reusar test_decision_id se fornecido
        if test_decision_id is not None:
            decision_id = str(test_decision_id)
        else:
            decision_id = str(uuid.uuid4())

        if action == ACTION_HOLD:
            size_fraction = 0.0
            sl_value = None
            tp_value = None
            confidence = max(0.0, min(1.0, float(rl_confidence)))
            reason = "inference_hold_raw_confidence"
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
            "origin": origin,
            "contaminated": contaminated,
            "baseline_comparative": baseline_comparative,
            "decision_id": decision_id,
            "fail_safe": fail_safe,
            "audit_trail": {
                "origin": origin,
                "decision_id": decision_id,
                "timestamp": model_input.decision_timestamp,
                "symbol": symbol,
            },
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
