"""Live execution and reconciliation services for Model 2.0."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
from notifications.model2_live_alerts import Model2LiveAlertPublisher
from risk.circuit_breaker import CircuitBreaker, CircuitBreakerState
from risk.risk_gate import RiskGate, RiskGateStatus

from config.execution_config import AUTHORIZED_SYMBOLS, EXECUTION_CONFIG
from .cycle_report import (
    SymbolReport,
    format_symbol_report,
    collect_training_info,
    collect_position_info,
)
from .rl_model_loader import RLModelLoader
from .live_exchange import Model2LiveExchange
from .live_execution import (
    LiveExecutionConfig,
    LiveExecutionGateDecision,
    LiveExecutionGateInput,
    M2_009_3_RULE_ID,
    M2_009_4_RULE_ID,
    M2_010_1_RULE_ID,
    SIGNAL_EXECUTION_STATUS_BLOCKED,
    SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
    SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
    SIGNAL_EXECUTION_STATUS_PROTECTED,
    SIGNAL_EXECUTION_STATUS_READY,
    evaluate_live_execution_gate,
)
from .model_decision import (
    ACTION_CLOSE,
    ACTION_HOLD,
    ACTION_OPEN_LONG,
    ACTION_OPEN_SHORT,
    ACTION_REDUCE,
    ModelDecision,
    ModelDecisionInput,
)
from .model_inference_service import ModelInferenceService
from .model_state_builder import M2_020_3_RULE_ID, build_model_decision_input
from .repository import Model2ThesisRepository

# Regra que garante que guard-rails permanecem no caminho critico
# independente da acao do modelo (M2-020.5)
M2_020_5_RULE_ID = "M2-020.5-RULE-GUARDRAILS-ACTIVE"

_PROTECTION_MAX_RETRIES = 3
_PROTECTION_RETRY_BASE_DELAY_S = 1.0


class Model2LiveExecutionService:
    """Coordinates live/shadow entry, protection and reconciliation."""

    def __init__(
        self,
        *,
        repository: Model2ThesisRepository,
        config: LiveExecutionConfig,
        exchange: Model2LiveExchange | None = None,
        risk_gate: RiskGate | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        alert_publisher: Model2LiveAlertPublisher | None = None,
    ) -> None:
        self.repository = repository
        self.config = config
        self.exchange = exchange
        self._risk_gate = risk_gate or RiskGate()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._guardrail_balance_initialized = False
        self._rl_loader = RLModelLoader()
        self._inference_service = ModelInferenceService()
        self._alert_publisher = alert_publisher or Model2LiveAlertPublisher()
        self._last_train_time = "N/A"
        if self._rl_loader.checkpoint_timestamp:
            self._last_train_time = datetime.fromtimestamp(
                self._rl_loader.checkpoint_timestamp, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
        # Config para busca de dados de treino (BD)
        self._db_path = getattr(
            config, "db_path",
            "db/modelo2.db"
        )

    def _emit_operational_alert(self, event_type: str, details: dict[str, Any]) -> None:
        try:
            self._alert_publisher.publish_critical(event_type, details)
        except Exception:
            # Alertas nunca podem interromper o fluxo principal.
            return

    def _log_operational_status(
        self,
        symbol: str,
        decision: ModelDecision,
        candles_count: int = 0,
        last_candle_time: str = "",
    ) -> None:
        """Formata status operacional usando novo padrao cycle_report."""
        try:
            # Coletar dados de treino
            last_train, pending = collect_training_info(self._db_path)

            # Coletar posicao aberta
            pos_info = collect_position_info(symbol, exchange_client=self.exchange)

            # Montar report
            now = datetime.now(timezone.utc)
            timeframe = "H4"  # padrao para M2
            execution_mode = "live" if self.config.execution_mode == "live" else "shadow"

            report = SymbolReport(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
                candles_count=candles_count,
                last_candle_time=last_candle_time,
                decision=decision.action,
                confidence=decision.confidence,
                decision_fresh=True,
                episode_id=None,  # sera preenchido apos execucao
                episode_persisted=False,
                reward=0.0,
                last_train_time=last_train,
                pending_episodes=pending,
                has_position=bool(pos_info["has_position"]),
                position_side=str(pos_info.get("position_side", "")),
                position_qty=float(pos_info.get("position_qty", 0.0)),
                position_entry_price=float(pos_info.get("position_entry_price", 0.0)),
                position_mark_price=float(pos_info.get("position_mark_price", 0.0)),
                position_pnl_pct=float(pos_info.get("position_pnl_pct", 0.0)),
                position_pnl_usd=float(pos_info.get("position_pnl_usd", 0.0)),
                execution_mode=execution_mode,
            )

            # Exibir relatorio formatado
            output = format_symbol_report(report)
            print(output, flush=True)

        except Exception as exc:
            # Fallback seguro para log antigo se houver erro
            logger = logging.getLogger(__name__)
            logger.warning("Falha ao formatar novo status: %s. Usando fallback.", exc)
            self._log_operational_status_fallback(symbol, decision)

    def _log_operational_status_fallback(
        self,
        symbol: str,
        decision: ModelDecision,
    ) -> None:
        """Fallback para log antigo se novo formato falhar."""
        now = datetime.now(timezone.utc)
        pos_str = "None"
        pnl_str = "0.00"

        if self.exchange:
            try:
                position = self.exchange.get_open_position(symbol)
                if position:
                    direction = position.get("direction", "NONE")
                    size = position.get("position_size_qty", 0.0)
                    entry_price = position.get("entry_price", 0.0)
                    mark_price = position.get("mark_price", 0.0)
                    pos_str = f"{direction} {size:.4f}"

                    pnl = 0.0
                    if entry_price > 0 and size > 0:
                        if direction == "LONG":
                            pnl = (mark_price - entry_price) * size
                        elif direction == "SHORT":
                            pnl = (entry_price - mark_price) * size
                    pnl_str = f"{pnl:+.2f}"
            except Exception:
                pass

        log_template = (
            "[{timestamp}] [M2][{symbol}] | Data: OK | Model: Ran | "
            "Decision: {decision} | RL: Stored (Pending: N/A) | "
            "Last Train: {last_train} | Position: {position} | PnL: {pnl}"
        )
        log_line = log_template.format(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            symbol=symbol,
            decision=decision.action,
            last_train=self._last_train_time,
            position=pos_str,
            pnl=pnl_str,
        )
        print(log_line, flush=True)

    @staticmethod
    def build_config(
        *,
        execution_mode: str,
        live_symbols: tuple[str, ...],
        short_only: bool,
        max_daily_entries: int,
        max_margin_per_position_usd: float,
        max_signal_age_ms: int,
        symbol_cooldown_ms: int,
        funding_rate_max_for_short: float,
        leverage: int | None = None,
        authorized_symbols: tuple[str, ...] | None = None,
    ) -> LiveExecutionConfig:
        return LiveExecutionConfig(
            execution_mode=str(execution_mode).strip().lower(),
            live_symbols=tuple(symbol.upper() for symbol in live_symbols),
            authorized_symbols=authorized_symbols or tuple(sorted(AUTHORIZED_SYMBOLS)),
            short_only=bool(short_only),
            max_daily_entries=int(max_daily_entries),
            max_margin_per_position_usd=float(max_margin_per_position_usd),
            max_signal_age_ms=int(max_signal_age_ms),
            symbol_cooldown_ms=int(symbol_cooldown_ms),
            funding_rate_max_for_short=float(funding_rate_max_for_short),
            leverage=int(leverage or EXECUTION_CONFIG.get("leverage", 10)),
        )

    def _ensure_live_exchange(self) -> Model2LiveExchange:
        if self.exchange is None:
            raise RuntimeError("Live exchange is required when execution_mode=live.")
        return self.exchange

    @staticmethod
    def _safe_json_dict(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _lookup_nested(payload: dict[str, Any], *path: str) -> Any:
        current: Any = payload
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _extract_funding_and_basis(self, candidate: dict[str, Any]) -> tuple[float | None, float | None]:
        payload = self._safe_json_dict(candidate.get("payload_json"))
        funding = self._to_float(payload.get("funding_rate"))
        if funding is None:
            funding = self._to_float(self._lookup_nested(payload, "market_context", "funding_rate"))
        if funding is None:
            funding = self.repository.get_latest_funding_rate(symbol=str(candidate["symbol"]))

        basis = self._to_float(payload.get("basis"))
        if basis is None:
            basis = self._to_float(self._lookup_nested(payload, "market_context", "basis"))
        if basis is None:
            basis = self.repository.get_latest_basis_value(symbol=str(candidate["symbol"]))
        return funding, basis

    @staticmethod
    def _signal_side_from_action(action: str) -> str | None:
        normalized_action = str(action).strip().upper()
        if normalized_action == ACTION_OPEN_LONG:
            return "LONG"
        if normalized_action == ACTION_OPEN_SHORT:
            return "SHORT"
        return None

    def _compute_bbapt_context(self, execution: dict[str, Any], now_ms: int) -> dict[str, Any]:
        payload = self._safe_json_dict(execution.get("payload_json"))
        signal_side = str(execution.get("signal_side") or "")
        entry_price = self._to_float(execution.get("entry_price")) or 0.0
        stop_loss = self._to_float(execution.get("stop_loss")) or 0.0
        take_profit = self._to_float(execution.get("take_profit")) or 0.0

        risk_distance = abs(stop_loss - entry_price)
        reward_distance = abs(entry_price - take_profit)
        rr_ratio = reward_distance / risk_distance if risk_distance > 0 else 0.0
        funding = self._to_float(payload.get("funding_rate"))
        if funding is None:
            funding = self._to_float(self._lookup_nested(payload, "market_context", "funding_rate"))
        basis = self._to_float(payload.get("basis"))
        if basis is None:
            basis = self._to_float(self._lookup_nested(payload, "market_context", "basis"))

        feature_vector = [
            float(entry_price),
            float(stop_loss),
            float(take_profit),
            float(rr_ratio),
            float(funding or 0.0),
            float(basis or 0.0),
        ]
        confidence, action = self._rl_loader.predict_confidence(
            features=np.array(feature_vector, dtype=float),
            signal_side=signal_side,
        )

        market_regime = str(self._lookup_nested(payload, "market_context", "market_regime") or payload.get("market_regime") or "RISK_ON").upper()
        perf = self.repository.get_live_performance_snapshot(
            execution_mode=self.config.execution_mode,
            limit=20,
        )
        loss_streak = int(perf.get("loss_streak", 0.0))
        failure_ratio = float(perf.get("recent_failure_ratio", 0.0))

        factor = 1.0
        if market_regime in {"RISK_OFF", "NEUTRAL", "NEUTRO"}:
            factor *= 0.8
        if loss_streak > 0:
            factor *= max(0.7, 1.0 - (0.1 * min(loss_streak, 3)))
        if failure_ratio >= 0.40:
            factor *= 0.8
        factor = min(1.0, max(0.5, factor))

        return {
            "rl_confidence": float(confidence),
            "rl_action": str(action),
            "rl_fallback": bool(self._rl_loader.is_fallback),
            "rl_fallback_reason": self._rl_loader.fallback_reason,
            "market_regime": market_regime,
            "loss_streak": loss_streak,
            "recent_failure_ratio": failure_ratio,
            "bbapt_factor": float(factor),
            "computed_at": int(now_ms),
        }

    def _build_gate_input(
        self,
        candidate: dict[str, Any],
        now_ms: int,
        *,
        signal_side_override: str | None = None,
    ) -> LiveExecutionGateInput:
        exchange = self.exchange if self.config.execution_mode == "live" else None
        position = exchange.get_open_position(str(candidate["symbol"])) if exchange else None
        available_balance = exchange.get_available_balance() if exchange else None
        funding_rate, basis_value = self._extract_funding_and_basis(candidate)
        effective_signal_side = str(signal_side_override or candidate["signal_side"])
        guardrail_state = self._snapshot_guardrail_state(available_balance)

        return LiveExecutionGateInput(
            technical_signal_id=int(candidate["id"]),
            opportunity_id=int(candidate["opportunity_id"]),
            symbol=str(candidate["symbol"]),
            timeframe=str(candidate["timeframe"]),
            signal_side=effective_signal_side,
            technical_signal_status=str(candidate["status"]),
            signal_timestamp=int(candidate["signal_timestamp"]),
            short_only=bool(self.config.short_only),
            funding_rate=funding_rate,
            basis_value=basis_value,
            funding_rate_max_for_short=float(self.config.funding_rate_max_for_short),
            execution_mode=self.config.execution_mode,
            live_symbols=self.config.live_symbols,
            authorized_symbols=self.config.authorized_symbols,
            available_balance_usd=available_balance,
            max_margin_per_position_usd=self.config.max_margin_per_position_usd,
            recent_entries_today=self.repository.count_live_entries_today(
                execution_mode=self.config.execution_mode,
                now_ms=now_ms,
            ),
            max_daily_entries=self.config.max_daily_entries,
            symbol_active_execution_count=self.repository.count_active_live_executions_for_symbol(
                symbol=str(candidate["symbol"]),
                execution_mode=self.config.execution_mode,
            ),
            open_position_qty=float(position["position_size_qty"]) if position else 0.0,
            cooldown_active=self.repository.has_recent_live_entry_for_symbol(
                symbol=str(candidate["symbol"]),
                execution_mode=self.config.execution_mode,
                now_ms=now_ms,
                cooldown_window_ms=self.config.symbol_cooldown_ms,
            ),
            signal_age_ms=max(0, int(now_ms) - int(candidate["signal_timestamp"])),
            max_signal_age_ms=self.config.max_signal_age_ms,
            risk_gate_status=str(guardrail_state["risk_gate_status"]),
            risk_gate_allows_order=bool(guardrail_state["risk_gate_allows_order"]),
            risk_gate_drawdown_pct=self._to_float(guardrail_state.get("risk_gate_drawdown_pct")),
            circuit_breaker_state=str(guardrail_state["circuit_breaker_state"]),
            circuit_breaker_allows_trading=bool(guardrail_state["circuit_breaker_allows_trading"]),
            circuit_breaker_drawdown_pct=self._to_float(guardrail_state.get("circuit_breaker_drawdown_pct")),
        )

    def _snapshot_guardrail_state(self, available_balance: float | None) -> dict[str, Any]:
        if self.config.execution_mode != "live":
            return {
                "risk_gate_status": RiskGateStatus.ACTIVE.value,
                "risk_gate_allows_order": True,
                "risk_gate_drawdown_pct": 0.0,
                "circuit_breaker_state": CircuitBreakerState.NORMAL.value,
                "circuit_breaker_allows_trading": True,
                "circuit_breaker_drawdown_pct": 0.0,
            }

        if available_balance is None:
            return {
                "risk_gate_status": "unavailable",
                "risk_gate_allows_order": False,
                "risk_gate_drawdown_pct": None,
                "circuit_breaker_state": "unavailable",
                "circuit_breaker_allows_trading": False,
                "circuit_breaker_drawdown_pct": None,
            }

        normalized_balance = float(available_balance)
        if not self._guardrail_balance_initialized:
            self._risk_gate._portfolio_value = normalized_balance
            self._risk_gate._peak_portfolio_value = normalized_balance
            self._circuit_breaker._portfolio_current = normalized_balance
            self._circuit_breaker._portfolio_peak = normalized_balance
            self._guardrail_balance_initialized = True
        else:
            self._risk_gate.update_portfolio_value(normalized_balance)
            self._circuit_breaker.update_portfolio_value(normalized_balance)

        circuit_breaker_status = self._circuit_breaker.check_status()
        risk_metrics = self._risk_gate.get_risk_metrics()

        return {
            "risk_gate_status": self._risk_gate.status.value,
            "risk_gate_allows_order": self._risk_gate.can_execute_order("market"),
            "risk_gate_drawdown_pct": float(risk_metrics.drawdown_pct),
            "circuit_breaker_state": self._circuit_breaker.state.value,
            "circuit_breaker_allows_trading": bool(
                circuit_breaker_status.get("trading_allowed", self._circuit_breaker.can_trade())
            ),
            "circuit_breaker_drawdown_pct": self._to_float(circuit_breaker_status.get("drawdown_pct")),
        }

    def _enforce_guardrails_before_order(
        self,
        execution: dict[str, Any],
        now_ms: int,
    ) -> dict[str, Any] | None:
        if self.config.execution_mode != "live":
            return None

        exchange = self._ensure_live_exchange()
        guardrail_state = self._snapshot_guardrail_state(exchange.get_available_balance())

        if str(guardrail_state["risk_gate_status"]).lower() == "unavailable":
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="risk_gate_state_unavailable",
                rule_id=M2_009_3_RULE_ID,
                metadata={"guardrails": guardrail_state},
            )
            self._emit_operational_alert(
                "risk_gate_state_unavailable",
                {
                    "execution_id": int(execution["id"]),
                    "symbol": str(execution.get("symbol") or ""),
                    "reason": failed.reason,
                    "guardrails": guardrail_state,
                },
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
            }

        if not bool(guardrail_state["risk_gate_allows_order"]):
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="risk_gate_blocked",
                rule_id=M2_009_3_RULE_ID,
                metadata={"guardrails": guardrail_state},
            )
            self._emit_operational_alert(
                "risk_gate_blocked",
                {
                    "execution_id": int(execution["id"]),
                    "symbol": str(execution.get("symbol") or ""),
                    "reason": failed.reason,
                    "guardrails": guardrail_state,
                },
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
            }

        if str(guardrail_state["circuit_breaker_state"]).lower() == "unavailable":
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="circuit_breaker_state_unavailable",
                rule_id=M2_009_3_RULE_ID,
                metadata={"guardrails": guardrail_state},
            )
            self._emit_operational_alert(
                "circuit_breaker_state_unavailable",
                {
                    "execution_id": int(execution["id"]),
                    "symbol": str(execution.get("symbol") or ""),
                    "reason": failed.reason,
                    "guardrails": guardrail_state,
                },
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
            }

        if not bool(guardrail_state["circuit_breaker_allows_trading"]):
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="circuit_breaker_blocked",
                rule_id=M2_009_3_RULE_ID,
                metadata={"guardrails": guardrail_state},
            )
            self._emit_operational_alert(
                "circuit_breaker_blocked",
                {
                    "execution_id": int(execution["id"]),
                    "symbol": str(execution.get("symbol") or ""),
                    "reason": failed.reason,
                    "guardrails": guardrail_state,
                },
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
            }

        return None

    def stage_signal_execution_candidates(
        self,
        *,
        symbol: str | None,
        timeframe: str | None,
        limit: int,
        now_ms: int,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        print("[DEBUG] Staging candidates...", flush=True)
        for candidate in self.repository.list_consumed_technical_signals(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        ):
            position_state: dict[str, Any] = {
                "has_open_position": False,
                "position_size_qty": 0.0,
                "entry_price": None,
            }
            if self.config.execution_mode == "live" and self.exchange is not None:
                position = self.exchange.get_open_position(str(candidate["symbol"]))
                if position:
                    position_state = {
                        "has_open_position": True,
                        "position_size_qty": float(position.get("position_size_qty") or 0.0),
                        "entry_price": float(position.get("entry_price") or 0.0),
                    }

            source_gate_input = self._build_gate_input(candidate, now_ms=now_ms)
            payload = self._safe_json_dict(candidate.get("payload_json"))
            payload_market_context = self._lookup_nested(payload, "market_context")
            market_context = {
                **(dict(payload_market_context) if isinstance(payload_market_context, dict) else {}),
                "funding_rate": source_gate_input.funding_rate,
                "basis": source_gate_input.basis_value,
                "market_regime": str(
                    self._lookup_nested(payload, "market_context", "market_regime")
                    or payload.get("market_regime")
                    or "UNKNOWN"
                ).upper(),
            }

            builder_result = build_model_decision_input(
                candidate=candidate,
                decision_timestamp=int(now_ms),
                model_version=self._inference_service.model_version,
                execution_mode=self.config.execution_mode,
                max_margin_per_position_usd=self.config.max_margin_per_position_usd,
                market_context=market_context,
                position_state=position_state,
                risk_context={
                    "available_balance_usd": source_gate_input.available_balance_usd,
                    "active_executions_for_symbol": source_gate_input.symbol_active_execution_count,
                    "recent_entries_today": source_gate_input.recent_entries_today,
                    "max_daily_entries": self.config.max_daily_entries,
                    "cooldown_active": source_gate_input.cooldown_active,
                    "signal_age_ms": source_gate_input.signal_age_ms,
                    "max_signal_age_ms": source_gate_input.max_signal_age_ms,
                    "open_position_qty": source_gate_input.open_position_qty,
                    "short_only": self.config.short_only,
                    "funding_rate_max_for_short": source_gate_input.funding_rate_max_for_short,
                    "risk_gate_status": source_gate_input.risk_gate_status,
                    "risk_gate_allows_order": source_gate_input.risk_gate_allows_order,
                    "risk_gate_drawdown_pct": source_gate_input.risk_gate_drawdown_pct,
                    "circuit_breaker_state": source_gate_input.circuit_breaker_state,
                    "circuit_breaker_allows_trading": source_gate_input.circuit_breaker_allows_trading,
                    "circuit_breaker_drawdown_pct": source_gate_input.circuit_breaker_drawdown_pct,
                },
            )

            inference = None
            model_input: ModelDecisionInput | None = builder_result.model_input
            if model_input is not None:
                inference = self._inference_service.infer(model_input)

            inference_model_version = (
                str(inference.model_version)
                if inference is not None
                else self._inference_service.model_version
            )
            inference_latency_ms = int(inference.inference_latency_ms) if inference is not None else 0
            inference_rule_id = (
                str(inference.rule_id)
                if inference is not None
                else M2_020_3_RULE_ID
            )
            decision_signal_side = None
            if inference is not None and inference.decision is not None:
                decision_signal_side = self._signal_side_from_action(inference.decision.action)

            inferred_decision: ModelDecision
            if inference is not None and inference.accepted and inference.decision is not None:
                inferred_decision = inference.decision
            elif builder_result.success is False:
                inferred_decision = ModelDecision(
                    action=ACTION_HOLD,
                    confidence=0.0,
                    size_fraction=0.0,
                    sl_target=None,
                    tp_target=None,
                    reason_code="invalid_model_inference_state",
                    decision_timestamp=int(now_ms),
                    symbol=str(candidate["symbol"]),
                    model_version=self._inference_service.model_version,
                    metadata={
                        "state_builder": {
                            "error_code": builder_result.error_code,
                            "error_message": builder_result.error_message,
                            "schema_version": builder_result.schema_version,
                            "generated_at_ms": builder_result.generated_at_ms,
                            "diagnostics": dict(builder_result.diagnostics),
                        }
                    },
                )
            else:
                inferred_decision = ModelDecision(
                    action=ACTION_HOLD,
                    confidence=0.0,
                    size_fraction=0.0,
                    sl_target=None,
                    tp_target=None,
                    reason_code=str(inference.reason if inference is not None else "inference_unavailable"),
                    decision_timestamp=int(now_ms),
                    symbol=str(candidate["symbol"]),
                    model_version=inference_model_version,
                    metadata={
                        "fallback_from_inference_error": dict(inference.details if inference is not None else {}),
                    },
                )

            # >>> Início da instrumentacao de log customizado
            self._log_operational_status(
                symbol=str(candidate["symbol"]),
                decision=inferred_decision,
                candles_count=0,
                last_candle_time="",
            )
            # <<< Fim da instrumentacao

            gate_input: LiveExecutionGateInput | None = None
            created_decision = self.repository.create_model_decision(
                decision_timestamp=int(inferred_decision.decision_timestamp),
                symbol=str(inferred_decision.symbol),
                action=str(inferred_decision.action),
                confidence=float(inferred_decision.confidence),
                size_fraction=float(inferred_decision.size_fraction),
                sl_target=(float(inferred_decision.sl_target) if inferred_decision.sl_target is not None else None),
                tp_target=(float(inferred_decision.tp_target) if inferred_decision.tp_target is not None else None),
                model_version=inference_model_version,
                reason_code=str(inferred_decision.reason_code),
                inference_latency_ms=inference_latency_ms,
                input_payload={
                    "symbol": str(model_input.symbol) if model_input is not None else str(candidate["symbol"]),
                    "timeframe": str(model_input.timeframe) if model_input is not None else str(candidate["timeframe"]),
                    "market_state": dict(model_input.market_state) if model_input is not None else {},
                    "position_state": dict(model_input.position_state) if model_input is not None else position_state,
                    "risk_state": dict(model_input.risk_state) if model_input is not None else {},
                    "state_schema_version": str(builder_result.schema_version),
                    "state_generated_at_ms": int(builder_result.generated_at_ms),
                    "state_builder": {
                        "success": bool(builder_result.success),
                        "diagnostics": dict(builder_result.diagnostics),
                        "rule_id": M2_020_3_RULE_ID,
                    },
                },
                output_payload={
                    "accepted": bool(inference.accepted if inference is not None else False),
                    "reason": str(
                        inference.reason
                        if inference is not None
                        else (builder_result.error_message or "invalid_model_inference_state")
                    ),
                    "state_builder": {
                        "success": bool(builder_result.success),
                        "error_code": builder_result.error_code,
                        "diagnostics": dict(builder_result.diagnostics),
                        "rule_id": M2_020_3_RULE_ID,
                    },
                    "decision": {
                        "action": str(inferred_decision.action),
                        "confidence": float(inferred_decision.confidence),
                        "size_fraction": float(inferred_decision.size_fraction),
                        "execution_signal_side": decision_signal_side,
                    },
                },
                created_at=int(now_ms),
            )

            execution_signal_side = self._signal_side_from_action(inferred_decision.action)
            if execution_signal_side is not None:
                gate_input = self._build_gate_input(
                    candidate,
                    now_ms=now_ms,
                    signal_side_override=execution_signal_side,
                )

            if builder_result.success is False:
                decision = LiveExecutionGateDecision(
                    allow_execution=False,
                    target_status=SIGNAL_EXECUTION_STATUS_BLOCKED,
                    reason="invalid_model_inference_state",
                    rule_id=M2_020_3_RULE_ID,
                    details={
                        "decision_id": int(created_decision.decision_id),
                        "error_code": builder_result.error_code,
                        "error_message": builder_result.error_message,
                        "state_schema_version": builder_result.schema_version,
                    },
                )
            elif inferred_decision.action == ACTION_HOLD:
                decision = LiveExecutionGateDecision(
                    allow_execution=False,
                    target_status=SIGNAL_EXECUTION_STATUS_BLOCKED,
                    reason="model_action_hold",
                    rule_id=inference_rule_id,
                    details={
                        "decision_id": int(created_decision.decision_id),
                        "model_version": inference_model_version,
                        "inference_latency_ms": inference_latency_ms,
                    },
                )
            elif str(inferred_decision.action).upper() == ACTION_REDUCE:
                # REDUCE indica intencao de reducao de posicao existente.
                # Nao mapeia para entrada nova — guard-rails nao sao contornados.
                decision = LiveExecutionGateDecision(
                    allow_execution=False,
                    target_status=SIGNAL_EXECUTION_STATUS_BLOCKED,
                    reason="model_action_reduce_no_entry",
                    rule_id=M2_020_5_RULE_ID,
                    details={
                        "action": str(inferred_decision.action),
                        "decision_id": int(created_decision.decision_id),
                    },
                )
            elif str(inferred_decision.action).upper() == ACTION_CLOSE:
                # CLOSE indica intencao de encerramento de posicao existente.
                # Nao gera ordem de entrada — guard-rails permanecem no caminho critico.
                decision = LiveExecutionGateDecision(
                    allow_execution=False,
                    target_status=SIGNAL_EXECUTION_STATUS_BLOCKED,
                    reason="model_action_close_no_entry",
                    rule_id=M2_020_5_RULE_ID,
                    details={
                        "action": str(inferred_decision.action),
                        "decision_id": int(created_decision.decision_id),
                    },
                )
            elif execution_signal_side is None:
                # Acao desconhecida ou nao suportada — bloquear por seguranca (fail-safe).
                decision = LiveExecutionGateDecision(
                    allow_execution=False,
                    target_status=SIGNAL_EXECUTION_STATUS_BLOCKED,
                    reason="model_action_not_supported_for_entry",
                    rule_id=M2_020_5_RULE_ID,
                    details={
                        "action": str(inferred_decision.action),
                        "decision_id": int(created_decision.decision_id),
                    },
                )
            else:
                assert gate_input is not None
                decision = evaluate_live_execution_gate(gate_input)

            result = self.repository.create_signal_execution_candidate(
                technical_signal_id=int(candidate["id"]),
                opportunity_id=int(candidate["opportunity_id"]),
                symbol=str(candidate["symbol"]),
                timeframe=str(candidate["timeframe"]),
                signal_side=str(execution_signal_side or candidate["signal_side"]),
                signal_timestamp=int(candidate["signal_timestamp"]),
                gate_decision=decision,
                execution_mode=self.config.execution_mode,
                now_ms=now_ms,
                decision_id=int(created_decision.decision_id),
                decision_trace={
                    "decision_id": int(created_decision.decision_id),
                    "model_version": inference_model_version,
                    "inference_latency_ms": inference_latency_ms,
                    "action": str(inferred_decision.action),
                    "execution_signal_side": execution_signal_side,
                    "source_signal_side": str(candidate["signal_side"]),
                    "confidence": float(inferred_decision.confidence),
                    "reason_code": str(inferred_decision.reason_code),
                },
            )
            items.append(
                {
                    "technical_signal_id": int(candidate["id"]),
                    "symbol": str(candidate["symbol"]),
                    "timeframe": str(candidate["timeframe"]),
                    "decision_id": int(created_decision.decision_id),
                    "model_version": inference_model_version,
                    "inference_latency_ms": inference_latency_ms,
                    "action": str(inferred_decision.action),
                    "signal_side": str(execution_signal_side or candidate["signal_side"]),
                    "created": bool(result.created),
                    "execution_id": result.execution_id,
                    "status": result.current_status,
                    "reason": result.reason,
                }
            )
        return items

    def _client_order_id(self, execution_id: int) -> str:
        return f"m2live_{execution_id}_{uuid.uuid4().hex[:16]}"

    def _extract_fill_from_order_response(
        self,
        order_response: dict[str, Any],
        *,
        fallback_position: dict[str, Any] | None,
    ) -> tuple[float | None, float | None]:
        # support many possible SDK field names for executed quantity
        qty_keys = (
            "executedQty",
            "executed_qty",
            "cumQty",
            "cum_qty",
            "filledQty",
            "filled_qty",
            "cumQuote",
            "cum_quote",
        )
        price_keys = ("avgPrice", "avg_price", "price", "avgPricePerUnit", "avg_price_per_unit")

        raw_qty = None
        raw_price = None
        for k in qty_keys:
            if k in (order_response or {}):
                raw_qty = order_response.get(k)
                if raw_qty is not None:
                    break
        for k in price_keys:
            if k in (order_response or {}):
                raw_price = order_response.get(k)
                if raw_price is not None:
                    break

        try:
            filled_qty = float(raw_qty) if raw_qty is not None and float(raw_qty) > 0 else None
        except (TypeError, ValueError):
            filled_qty = None
        try:
            filled_price = float(raw_price) if raw_price is not None and float(raw_price) > 0 else None
        except (TypeError, ValueError):
            filled_price = None

        # If basic extraction failed, try to query the exchange for the order
        if (filled_qty is None or filled_price is None) and isinstance(order_response, dict):
            # prefer explicit order id fields
            order_id = (
                order_response.get("orderId")
                or order_response.get("order_id")
                or order_response.get("orderIdStr")
                or order_response.get("clientOrderId")
                or order_response.get("client_order_id")
            )
            try:
                if order_id and self.exchange is not None:
                    raw_symbol = self.exchange._safe_get(order_response, ["symbol"]) or order_response.get("symbol")
                    symbol = str(raw_symbol) if raw_symbol else ""
                    remote = self.exchange.query_order(symbol=symbol, order_id=order_id) if symbol else None
                    if remote:
                        for k in qty_keys:
                            if k in remote and remote.get(k) is not None:
                                parsed_qty = self._to_float(remote.get(k))
                                if parsed_qty is not None and parsed_qty > 0:
                                    filled_qty = parsed_qty
                                    break
                        for k in price_keys:
                            if k in remote and remote.get(k) is not None:
                                parsed_price = self._to_float(remote.get(k))
                                if parsed_price is not None and parsed_price > 0:
                                    filled_price = parsed_price
                                    break
            except Exception:
                # ignore query failures here and fallback to position
                pass

        if fallback_position is not None:
            if filled_qty is None:
                try:
                    filled_qty = float(fallback_position.get("position_size_qty") or 0) or None
                except Exception:
                    filled_qty = None
            if filled_price is None:
                try:
                    filled_price = float(fallback_position.get("entry_price") or 0) or None
                except Exception:
                    filled_price = None
        return filled_qty, filled_price

    def _place_protective_order_with_retry(
        self,
        exchange: Model2LiveExchange,
        *,
        symbol: str,
        signal_side: str,
        trigger_price: float,
        order_type: str,
    ) -> tuple[Any, list[dict[str, str]]]:
        """Envia ordem de proteção com retry exponencial (mínimo 3 tentativas)."""
        errors: list[dict[str, str]] = []
        response = None
        for attempt in range(_PROTECTION_MAX_RETRIES):
            try:
                response = exchange.place_protective_order(
                    symbol=symbol,
                    signal_side=signal_side,
                    trigger_price=trigger_price,
                    order_type=order_type,
                )
                return response, errors
            except Exception as exc:
                if exchange.is_existing_protection_error(exc):
                    return None, []
                delay = _PROTECTION_RETRY_BASE_DELAY_S * (2 ** attempt)
                errors.append(
                    {
                        "order_type": order_type,
                        "attempt": str(attempt + 1),
                        "error": str(exc),
                    }
                )
                if attempt < _PROTECTION_MAX_RETRIES - 1:
                    time.sleep(delay)
        return response, errors

    def _arm_protection(self, execution: dict[str, Any], now_ms: int) -> dict[str, Any]:
        exchange = self._ensure_live_exchange()
        signal_side = str(execution["signal_side"])
        symbol = str(execution["symbol"])
        current_status = str(execution.get("status") or SIGNAL_EXECUTION_STATUS_ENTRY_FILLED)
        protection_state = exchange.get_protection_state(symbol=symbol, signal_side=signal_side)
        sl_order = protection_state.get("sl_order_id")
        tp_order = protection_state.get("tp_order_id")
        protection_was_missing = not (protection_state.get("has_sl") and protection_state.get("has_tp"))
        protection_errors: list[dict[str, str]] = []

        # Ensure there is an open position before attempting reduce-only protections.
        # Sometimes the exchange reports fills but the position is not yet visible;
        # retry a couple times with a short delay before giving up.
        pos = exchange.get_open_position(symbol)
        if pos is None:
            for attempt in range(2):
                time.sleep(1.0)
                pos = exchange.get_open_position(symbol)
                if pos is not None:
                    break
        if pos is None:
            # No position visible yet: keep lifecycle at ENTRY_FILLED/PROTECTED and retry on reconcile.
            self._record_reconcile_note(
                int(execution.get("id") or 0),
                now_ms,
                {
                    "reason": "no_open_position_before_protection",
                    "symbol": symbol,
                    "action": "defer_retry",
                    "protection_state": protection_state,
                },
            )
            self._emit_operational_alert(
                "protection_deferred_no_open_position",
                {
                    "execution_id": int(execution.get("id") or 0),
                    "symbol": symbol,
                    "signal_side": signal_side,
                    "status": current_status,
                },
            )
            return {"status": current_status, "reason": "protection_deferred_no_open_position"}

        if not protection_state.get("has_sl"):
            sl_response, sl_errors = self._place_protective_order_with_retry(
                exchange,
                symbol=symbol,
                signal_side=signal_side,
                trigger_price=float(execution["stop_loss"]),
                order_type="STOP_MARKET",
            )
            protection_errors.extend(sl_errors)
            if sl_response is not None:
                sl_order = exchange.extract_order_identifier(sl_response) or sl_order

        if not protection_state.get("has_tp"):
            tp_response, tp_errors = self._place_protective_order_with_retry(
                exchange,
                symbol=symbol,
                signal_side=signal_side,
                trigger_price=float(execution["take_profit"]),
                order_type="TAKE_PROFIT_MARKET",
            )
            protection_errors.extend(tp_errors)
            if tp_response is not None:
                tp_order = exchange.extract_order_identifier(tp_response) or tp_order

        final_state = exchange.get_protection_state(symbol=symbol, signal_side=signal_side)
        if final_state.get("has_sl") and final_state.get("has_tp"):
            protected = self.repository.mark_signal_execution_protected(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                stop_order_id=str(final_state.get("sl_order_id") or sl_order or ""),
                take_profit_order_id=str(final_state.get("tp_order_id") or tp_order or ""),
                rule_id=M2_009_4_RULE_ID,
                metadata={
                    "source": "live_execution_service",
                    "status_before": execution["status"],
                },
            )
            reason = protected.reason
            if str(execution["status"]) == SIGNAL_EXECUTION_STATUS_PROTECTED and protection_was_missing:
                reason = "protection_armed"
            return {
                "status": protected.current_status,
                "reason": reason,
                "stop_order_id": final_state.get("sl_order_id") or sl_order,
                "take_profit_order_id": final_state.get("tp_order_id") or tp_order,
            }

        # Protection is best-effort right after fill and should not block acceptance.
        # Keep current status and rely on reconcile retries with full audit trail.
        self._record_reconcile_note(
            int(execution.get("id") or 0),
            now_ms,
            {
                "reason": "protection_not_armed",
                "symbol": symbol,
                "action": "defer_retry",
                "protection_state": final_state,
                "protection_errors": protection_errors,
            },
        )
        self._emit_operational_alert(
            "protection_not_armed",
            {
                "execution_id": int(execution.get("id") or 0),
                "symbol": symbol,
                "signal_side": signal_side,
                "status": current_status,
                "protection_state": final_state,
                "protection_errors": protection_errors,
            },
        )
        return {
            "status": current_status,
            "reason": "protection_not_armed_deferred",
        }

    def _execute_ready_signal(self, execution: dict[str, Any], now_ms: int) -> dict[str, Any]:
        if self.config.execution_mode != "live":
            return {
                "execution_id": int(execution["id"]),
                "status": execution["status"],
                "reason": "shadow_mode_no_order_sent",
            }

        guardrail_failure = self._enforce_guardrails_before_order(execution, now_ms=now_ms)
        if guardrail_failure is not None:
            return guardrail_failure

        if self.config.short_only and str(execution.get("signal_side") or "").upper() != "SHORT":
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="short_only_enforced",
                rule_id=M2_009_3_RULE_ID,
                metadata={"signal_side": execution.get("signal_side")},
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
            }

        exchange = self._ensure_live_exchange()
        bbapt = self._compute_bbapt_context(execution, now_ms=now_ms)
        if bbapt["rl_confidence"] < 0.50:
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="rl_confidence_below_threshold",
                rule_id=M2_009_3_RULE_ID,
                metadata={"bbapt": bbapt},
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
                "bbapt": bbapt,
            }

        effective_margin = max(
            0.01,
            float(self.config.max_margin_per_position_usd) * float(bbapt["bbapt_factor"]),
        )
        quantity = exchange.calculate_entry_quantity(
            symbol=str(execution["symbol"]),
            entry_price=float(execution["entry_price"]),
            margin_usd=effective_margin,
            leverage=self.config.leverage,
        )
        if quantity <= 0:
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="invalid_requested_quantity",
                rule_id=M2_009_3_RULE_ID,
                metadata={
                    "entry_price": float(execution["entry_price"]),
                    "effective_margin_usd": effective_margin,
                    "bbapt": bbapt,
                },
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
            }

        # Nota: validação de min_notional por símbolo é feita em
        # `exchange.calculate_entry_quantity()`; se a quantidade retornada
        # for 0.0, tratamos como `invalid_requested_quantity` acima.

        client_order_id = self._client_order_id(int(execution["id"]))
        # Enviar ordem com tratamento de excecoes para evitar crash do ciclo
        try:
            order_response = exchange.place_market_entry(
                symbol=str(execution["symbol"]),
                signal_side=str(execution["signal_side"]),
                quantity=quantity,
                client_order_id=client_order_id,
            )
        except Exception as exc:
            # Registrar falha e marcar execucao como failed sem propagar
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="exchange_error",
                rule_id=M2_009_3_RULE_ID,
                metadata={
                    "error": str(exc),
                    "effective_margin_usd": effective_margin,
                    "bbapt": bbapt,
                },
            )
            self._emit_operational_alert(
                "exchange_error",
                {
                    "execution_id": int(execution["id"]),
                    "symbol": str(execution.get("symbol") or ""),
                    "reason": failed.reason,
                    "error": str(exc),
                },
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
            }
        entry_sent = self.repository.mark_signal_execution_entry_sent(
            execution_id=int(execution["id"]),
            now_ms=now_ms,
            requested_qty=quantity,
            exchange_order_id=str(order_response.get("orderId") or order_response.get("order_id") or ""),
            client_order_id=client_order_id,
            rule_id=M2_009_3_RULE_ID,
            metadata={
                "order_response": order_response,
                "effective_margin_usd": effective_margin,
                "bbapt": bbapt,
            },
        )

        # Após envio, aguardar e tentar obter confirmação de fill/posição.
        # Estratégia: 1) checar posição aberta; 2) tentar extrair do order_response;
        # 3) consultar a ordem no exchange via `query_order` e re-extrair; 4) repetir polling curto.
        POLL_RETRIES = 5
        POLL_DELAY_S = 1.0
        filled_qty = None
        filled_price = None
        last_remote_order = None

        for attempt in range(POLL_RETRIES):
            current_position = exchange.get_open_position(str(execution["symbol"]))
            # try to extract from current position first
            if current_position is not None:
                try:
                    filled_qty = float((current_position.get("position_size_qty") or 0) or 0) or None
                except Exception:
                    filled_qty = None
                try:
                    filled_price = float((current_position.get("entry_price") or 0) or 0) or None
                except Exception:
                    filled_price = None

            # if still missing, try to extract from immediate order response
            if (filled_qty is None or filled_price is None) and isinstance(order_response, dict):
                q_filled, q_price = self._extract_fill_from_order_response(order_response, fallback_position=current_position)
                if q_filled is not None:
                    filled_qty = filled_qty or q_filled
                if q_price is not None:
                    filled_price = filled_price or q_price

            # if still missing, try remote query by order id
            if (filled_qty is None or filled_price is None) and isinstance(order_response, dict):
                order_id = (
                    order_response.get("orderId")
                    or order_response.get("order_id")
                    or order_response.get("clientOrderId")
                    or order_response.get("client_order_id")
                )
                try:
                    if order_id and self.exchange is not None:
                        raw_symbol = self.exchange._safe_get(order_response, ["symbol"]) or order_response.get("symbol")
                        symbol = str(raw_symbol) if raw_symbol else ""
                        last_remote_order = self.exchange.query_order(symbol=symbol, order_id=order_id) if symbol else None
                        if last_remote_order:
                            q_filled, q_price = self._extract_fill_from_order_response(last_remote_order, fallback_position=current_position)
                            if q_filled is not None:
                                filled_qty = filled_qty or q_filled
                            if q_price is not None:
                                filled_price = filled_price or q_price
                except Exception:
                    pass

            if filled_qty is not None and filled_price is not None:
                break

            # wait before next attempt
            time.sleep(POLL_DELAY_S)

        # Se não conseguimos extrair fill após polling, retornar estado ENTRY_SENT para re-tentativa posterior
        if filled_qty is None or filled_price is None:
            # atualizar metadata com última ordem remota, se houver
            metadata = {"order_response": order_response}
            if last_remote_order is not None:
                metadata["remote_order"] = last_remote_order
            metadata["bbapt"] = bbapt
            return {
                "execution_id": int(execution["id"]),
                "status": entry_sent.current_status,
                "reason": entry_sent.reason,
                "exchange_order_id": order_response.get("orderId") or order_response.get("order_id"),
                "note": "awaiting_fill_after_send",
                "metadata": metadata,
            }

        # Persistir fill e armar proteções
        filled = self.repository.mark_signal_execution_entry_filled(
            execution_id=int(execution["id"]),
            now_ms=now_ms,
            filled_qty=float(filled_qty),
            filled_price=float(filled_price),
            rule_id=M2_009_3_RULE_ID,
            metadata={
                "order_response": order_response,
                "remote_order": last_remote_order,
                "effective_margin_usd": effective_margin,
                "bbapt": bbapt,
            },
        )
        refreshed_execution = self.repository.get_signal_execution(int(execution["id"])) or execution
        protection = self._arm_protection(refreshed_execution, now_ms=now_ms)
        return {
            "execution_id": int(execution["id"]),
            "entry_sent_status": entry_sent.current_status,
            "entry_filled_status": filled.current_status,
            "status": protection["status"],
            "reason": protection["reason"],
            "bbapt": bbapt,
        }

    def run_execute(
        self,
        *,
        symbol: str | None,
        timeframe: str | None,
        limit: int,
        now_ms: int,
    ) -> dict[str, Any]:
        staged = self.stage_signal_execution_candidates(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            now_ms=now_ms,
        )
        ready_rows = self.repository.list_signal_executions(
            statuses=(SIGNAL_EXECUTION_STATUS_READY,),
            execution_mode=self.config.execution_mode,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )
        processed: list[dict[str, Any]] = []
        for execution in ready_rows:
            processed.append(self._execute_ready_signal(execution, now_ms=now_ms))

        return {
            "execution_mode": self.config.execution_mode,
            "staged": staged,
            "processed_ready": processed,
        }

    def _record_reconcile_note(self, execution_id: int, now_ms: int, payload: dict[str, Any]) -> None:
        self.repository.record_signal_execution_event(
            execution_id=execution_id,
            now_ms=now_ms,
            from_status=None,
            to_status=None,
            event_type="RECONCILIATION",
            rule_id=M2_010_1_RULE_ID,
            payload=payload,
        )

    def _mark_reconciliation_divergence(
        self,
        *,
        execution: dict[str, Any],
        now_ms: int,
        reason: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        execution_id = int(execution["id"])
        status_before = str(execution.get("status") or "")
        event_payload = {
            "result": "critical_divergence",
            "reason": reason,
            "status_before": status_before,
            **metadata,
        }
        self._record_reconcile_note(execution_id, now_ms=now_ms, payload=event_payload)

        failed = self.repository.mark_signal_execution_failed(
            execution_id=execution_id,
            now_ms=now_ms,
            reason=reason,
            rule_id=M2_010_1_RULE_ID,
            metadata=event_payload,
        )
        self._emit_operational_alert(
            "reconciliation_critical_divergence",
            {
                "execution_id": execution_id,
                "symbol": str(execution.get("symbol") or ""),
                "status_before": status_before,
                "reason": failed.reason,
                "metadata": metadata,
            },
        )
        return {
            "execution_id": execution_id,
            "status": failed.current_status,
            "reason": failed.reason,
        }

    def _mark_external_close_exit(
        self,
        *,
        execution: dict[str, Any],
        now_ms: int,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        execution_id = int(execution["id"])
        status_before = str(execution.get("status") or "")
        event_payload = {
            "result": "external_close_detected",
            "status_before": status_before,
            **metadata,
        }
        self._record_reconcile_note(execution_id, now_ms=now_ms, payload=event_payload)

        exited = self.repository.mark_signal_execution_exited(
            execution_id=execution_id,
            now_ms=now_ms,
            exit_reason="external_close_detected",
            rule_id=M2_010_1_RULE_ID,
            exit_price=None,
            metadata=event_payload,
        )
        return {
            "execution_id": execution_id,
            "status": exited.current_status,
            "reason": exited.reason,
        }

    def _reconcile_single_execution(self, execution: dict[str, Any], now_ms: int) -> dict[str, Any]:
        exchange = self._ensure_live_exchange()
        execution_id = int(execution["id"])
        symbol = str(execution["symbol"])
        signal_side = str(execution["signal_side"])
        position = exchange.get_open_position(symbol)

        if execution["status"] == SIGNAL_EXECUTION_STATUS_READY:
            if position is None:
                return {
                    "execution_id": execution_id,
                    "status": execution["status"],
                    "reason": "ready_without_position",
                }
            filled = self.repository.mark_signal_execution_entry_filled(
                execution_id=execution_id,
                now_ms=now_ms,
                filled_qty=float(position["position_size_qty"]),
                filled_price=float(position["entry_price"]),
                rule_id=M2_010_1_RULE_ID,
                metadata={"source": "reconcile_ready_position_detected"},
            )
            refreshed = self.repository.get_signal_execution(execution_id) or execution
            protection = self._arm_protection(refreshed, now_ms=now_ms)
            return {
                "execution_id": execution_id,
                "status": protection["status"],
                "reason": protection["reason"],
                "filled_status": filled.current_status,
            }

        if execution["status"] == SIGNAL_EXECUTION_STATUS_ENTRY_SENT:
            if position is None:
                if execution.get("entry_sent_at") and (now_ms - int(execution["entry_sent_at"])) > 30_000:
                    failed = self.repository.mark_signal_execution_failed(
                        execution_id=execution_id,
                        now_ms=now_ms,
                        reason="entry_fill_timeout",
                        rule_id=M2_010_1_RULE_ID,
                        metadata={"entry_sent_at": execution.get("entry_sent_at")},
                    )
                    self._emit_operational_alert(
                        "entry_fill_timeout",
                        {
                            "execution_id": execution_id,
                            "symbol": symbol,
                            "reason": failed.reason,
                            "entry_sent_at": execution.get("entry_sent_at"),
                        },
                    )
                    return {
                        "execution_id": execution_id,
                        "status": failed.current_status,
                        "reason": failed.reason,
                    }
                return {
                    "execution_id": execution_id,
                    "status": execution["status"],
                    "reason": "awaiting_fill",
                }

            filled = self.repository.mark_signal_execution_entry_filled(
                execution_id=execution_id,
                now_ms=now_ms,
                filled_qty=float(position["position_size_qty"]),
                filled_price=float(position["entry_price"]),
                rule_id=M2_010_1_RULE_ID,
                metadata={"source": "reconcile_entry_sent_position_detected"},
            )
            refreshed = self.repository.get_signal_execution(execution_id) or execution
            protection = self._arm_protection(refreshed, now_ms=now_ms)
            return {
                "execution_id": execution_id,
                "status": protection["status"],
                "reason": protection["reason"],
                "filled_status": filled.current_status,
            }

        if execution["status"] == SIGNAL_EXECUTION_STATUS_ENTRY_FILLED:
            if position is None:
                return self._mark_reconciliation_divergence(
                    execution=execution,
                    now_ms=now_ms,
                    reason="reconciliation_divergence_entry_filled_without_position",
                    metadata={
                        "source": "reconcile_missing_position",
                        "symbol": symbol,
                        "signal_side": signal_side,
                    },
                )
            protection = self._arm_protection(execution, now_ms=now_ms)
            return {
                "execution_id": execution_id,
                "status": protection["status"],
                "reason": protection["reason"],
            }

        if execution["status"] == SIGNAL_EXECUTION_STATUS_PROTECTED:
            if position is None:
                return self._mark_external_close_exit(
                    execution=execution,
                    now_ms=now_ms,
                    metadata={
                        "source": "reconcile_protected_external_close",
                        "symbol": symbol,
                        "signal_side": signal_side,
                    },
                )

            protection = exchange.get_protection_state(symbol=symbol, signal_side=signal_side)
            if protection.get("has_sl") and protection.get("has_tp"):
                self._record_reconcile_note(
                    execution_id,
                    now_ms=now_ms,
                    payload={"result": "protection_ok", "symbol": symbol},
                )
                return {
                    "execution_id": execution_id,
                    "status": execution["status"],
                    "reason": "protection_ok",
                }

            arm_result = self._arm_protection(execution, now_ms=now_ms)
            return {
                "execution_id": execution_id,
                "status": arm_result["status"],
                "reason": arm_result["reason"],
            }

        return {
            "execution_id": execution_id,
            "status": execution["status"],
            "reason": "status_not_reconciled",
        }

    def run_reconcile(
        self,
        *,
        symbol: str | None,
        timeframe: str | None,
        limit: int,
        now_ms: int,
    ) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for execution in self.repository.list_signal_executions(
            statuses=(
                SIGNAL_EXECUTION_STATUS_READY,
                SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
                SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
                SIGNAL_EXECUTION_STATUS_PROTECTED,
            ),
            execution_mode="live",
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        ):
            items.append(self._reconcile_single_execution(execution, now_ms=now_ms))
        return {
            "execution_mode": self.config.execution_mode,
            "reconciled": items,
        }
