"""Live execution and reconciliation services for Model 2.0."""

from __future__ import annotations

import time
import uuid
from typing import Any

from config.execution_config import AUTHORIZED_SYMBOLS, EXECUTION_CONFIG
from .live_exchange import Model2LiveExchange
from .live_execution import (
    LiveExecutionConfig,
    LiveExecutionGateInput,
    M2_009_3_RULE_ID,
    M2_009_4_RULE_ID,
    M2_010_1_RULE_ID,
    SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
    SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
    SIGNAL_EXECUTION_STATUS_PROTECTED,
    SIGNAL_EXECUTION_STATUS_READY,
    evaluate_live_execution_gate,
)
from .repository import Model2ThesisRepository

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
    ) -> None:
        self.repository = repository
        self.config = config
        self.exchange = exchange

    @staticmethod
    def build_config(
        *,
        execution_mode: str,
        live_symbols: tuple[str, ...],
        max_daily_entries: int,
        max_margin_per_position_usd: float,
        max_signal_age_ms: int,
        symbol_cooldown_ms: int,
        leverage: int | None = None,
        authorized_symbols: tuple[str, ...] | None = None,
    ) -> LiveExecutionConfig:
        return LiveExecutionConfig(
            execution_mode=str(execution_mode).strip().lower(),
            live_symbols=tuple(symbol.upper() for symbol in live_symbols),
            authorized_symbols=authorized_symbols or tuple(sorted(AUTHORIZED_SYMBOLS)),
            max_daily_entries=int(max_daily_entries),
            max_margin_per_position_usd=float(max_margin_per_position_usd),
            max_signal_age_ms=int(max_signal_age_ms),
            symbol_cooldown_ms=int(symbol_cooldown_ms),
            leverage=int(leverage or EXECUTION_CONFIG.get("leverage", 10)),
        )

    def _ensure_live_exchange(self) -> Model2LiveExchange:
        if self.exchange is None:
            raise RuntimeError("Live exchange is required when execution_mode=live.")
        return self.exchange

    def _build_gate_input(self, candidate: dict[str, Any], now_ms: int) -> LiveExecutionGateInput:
        exchange = self.exchange if self.config.execution_mode == "live" else None
        position = exchange.get_open_position(str(candidate["symbol"])) if exchange else None
        available_balance = exchange.get_available_balance() if exchange else None

        return LiveExecutionGateInput(
            technical_signal_id=int(candidate["id"]),
            opportunity_id=int(candidate["opportunity_id"]),
            symbol=str(candidate["symbol"]),
            timeframe=str(candidate["timeframe"]),
            signal_side=str(candidate["signal_side"]),
            technical_signal_status=str(candidate["status"]),
            signal_timestamp=int(candidate["signal_timestamp"]),
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
        )

    def stage_signal_execution_candidates(
        self,
        *,
        symbol: str | None,
        timeframe: str | None,
        limit: int,
        now_ms: int,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for candidate in self.repository.list_consumed_technical_signals(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        ):
            gate_input = self._build_gate_input(candidate, now_ms=now_ms)
            decision = evaluate_live_execution_gate(gate_input)
            result = self.repository.create_signal_execution_candidate(
                technical_signal_id=int(candidate["id"]),
                opportunity_id=int(candidate["opportunity_id"]),
                symbol=str(candidate["symbol"]),
                timeframe=str(candidate["timeframe"]),
                signal_side=str(candidate["signal_side"]),
                signal_timestamp=int(candidate["signal_timestamp"]),
                gate_decision=decision,
                execution_mode=self.config.execution_mode,
                now_ms=now_ms,
            )
            items.append(
                {
                    "technical_signal_id": int(candidate["id"]),
                    "symbol": str(candidate["symbol"]),
                    "timeframe": str(candidate["timeframe"]),
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
        raw_qty = order_response.get("executedQty") or order_response.get("executed_qty")
        raw_price = order_response.get("avgPrice") or order_response.get("avg_price") or order_response.get("price")
        try:
            filled_qty = float(raw_qty) if raw_qty is not None and float(raw_qty) > 0 else None
        except (TypeError, ValueError):
            filled_qty = None
        try:
            filled_price = float(raw_price) if raw_price is not None and float(raw_price) > 0 else None
        except (TypeError, ValueError):
            filled_price = None

        if fallback_position is not None:
            if filled_qty is None:
                filled_qty = float(fallback_position.get("position_size_qty") or 0) or None
            if filled_price is None:
                filled_price = float(fallback_position.get("entry_price") or 0) or None
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
        protection_state = exchange.get_protection_state(symbol=symbol, signal_side=signal_side)
        sl_order = protection_state.get("sl_order_id")
        tp_order = protection_state.get("tp_order_id")
        protection_was_missing = not (protection_state.get("has_sl") and protection_state.get("has_tp"))
        protection_errors: list[dict[str, str]] = []

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

        current_position = exchange.get_open_position(symbol)
        emergency_quantity = float(
            (current_position or {}).get("position_size_qty")
            or execution.get("filled_qty")
            or execution.get("requested_qty")
            or 0.0
        )
        close_response = None
        if emergency_quantity > 0:
            close_response = exchange.close_position_market(
                symbol=symbol,
                signal_side=signal_side,
                quantity=emergency_quantity,
            )
        failed = self.repository.mark_signal_execution_failed(
            execution_id=int(execution["id"]),
            now_ms=now_ms,
            reason="protection_not_armed",
            rule_id=M2_009_4_RULE_ID,
            metadata={
                "emergency_close_response": close_response,
                "protection_state": final_state,
                "protection_errors": protection_errors,
            },
        )
        return {
            "status": failed.current_status,
            "reason": failed.reason,
            "emergency_close_response": close_response,
        }

    def _execute_ready_signal(self, execution: dict[str, Any], now_ms: int) -> dict[str, Any]:
        if self.config.execution_mode != "live":
            return {
                "execution_id": int(execution["id"]),
                "status": execution["status"],
                "reason": "shadow_mode_no_order_sent",
            }

        exchange = self._ensure_live_exchange()
        quantity = exchange.calculate_entry_quantity(
            symbol=str(execution["symbol"]),
            entry_price=float(execution["entry_price"]),
            margin_usd=self.config.max_margin_per_position_usd,
            leverage=self.config.leverage,
        )
        if quantity <= 0:
            failed = self.repository.mark_signal_execution_failed(
                execution_id=int(execution["id"]),
                now_ms=now_ms,
                reason="invalid_requested_quantity",
                rule_id=M2_009_3_RULE_ID,
                metadata={"entry_price": float(execution["entry_price"])},
            )
            return {
                "execution_id": int(execution["id"]),
                "status": failed.current_status,
                "reason": failed.reason,
            }

        client_order_id = self._client_order_id(int(execution["id"]))
        order_response = exchange.place_market_entry(
            symbol=str(execution["symbol"]),
            signal_side=str(execution["signal_side"]),
            quantity=quantity,
            client_order_id=client_order_id,
        )
        entry_sent = self.repository.mark_signal_execution_entry_sent(
            execution_id=int(execution["id"]),
            now_ms=now_ms,
            requested_qty=quantity,
            exchange_order_id=str(order_response.get("orderId") or order_response.get("order_id") or ""),
            client_order_id=client_order_id,
            rule_id=M2_009_3_RULE_ID,
            metadata={"order_response": order_response},
        )

        current_position = exchange.get_open_position(str(execution["symbol"]))
        filled_qty, filled_price = self._extract_fill_from_order_response(
            order_response,
            fallback_position=current_position,
        )
        if filled_qty is None or filled_price is None:
            return {
                "execution_id": int(execution["id"]),
                "status": entry_sent.current_status,
                "reason": entry_sent.reason,
                "exchange_order_id": order_response.get("orderId") or order_response.get("order_id"),
            }

        filled = self.repository.mark_signal_execution_entry_filled(
            execution_id=int(execution["id"]),
            now_ms=now_ms,
            filled_qty=float(filled_qty),
            filled_price=float(filled_price),
            rule_id=M2_009_3_RULE_ID,
            metadata={"order_response": order_response},
        )
        refreshed_execution = self.repository.get_signal_execution(int(execution["id"])) or execution
        protection = self._arm_protection(refreshed_execution, now_ms=now_ms)
        return {
            "execution_id": int(execution["id"]),
            "entry_sent_status": entry_sent.current_status,
            "entry_filled_status": filled.current_status,
            "status": protection["status"],
            "reason": protection["reason"],
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
                exited = self.repository.mark_signal_execution_exited(
                    execution_id=execution_id,
                    now_ms=now_ms,
                    exit_reason="position_closed_before_protection",
                    rule_id=M2_010_1_RULE_ID,
                    exit_price=None,
                    metadata={"source": "reconcile_missing_position"},
                )
                return {
                    "execution_id": execution_id,
                    "status": exited.current_status,
                    "reason": exited.reason,
                }
            protection = self._arm_protection(execution, now_ms=now_ms)
            return {
                "execution_id": execution_id,
                "status": protection["status"],
                "reason": protection["reason"],
            }

        if execution["status"] == SIGNAL_EXECUTION_STATUS_PROTECTED:
            if position is None:
                exited = self.repository.mark_signal_execution_exited(
                    execution_id=execution_id,
                    now_ms=now_ms,
                    exit_reason="exchange_position_closed",
                    rule_id=M2_010_1_RULE_ID,
                    exit_price=None,
                    metadata={"source": "reconcile_protected_missing_position"},
                )
                return {
                    "execution_id": execution_id,
                    "status": exited.current_status,
                    "reason": exited.reason,
                }

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
