"""Deterministic order-layer decision for Model 2.0 technical signals (M2-007.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Collection

from config.execution_config import AUTHORIZED_SYMBOLS

M2_007_1_RULE_ID = "M2-007.1-RULE-ORDER-LAYER-CONSUMER"
TECHNICAL_SIGNAL_STATUS_CREATED = "CREATED"
TECHNICAL_SIGNAL_STATUS_CONSUMED = "CONSUMED"
TECHNICAL_SIGNAL_STATUS_CANCELLED = "CANCELLED"
SUPPORTED_ENTRY_TYPES = frozenset({"MARKET", "LIMIT"})

REASON_CODE_CATALOG: dict[str, str] = {
    "decision_recorded_no_real_order": "ops.decision_recorded_no_real_order",
    "status_not_created": "ops.status_not_created",
    "symbol_not_authorized": "ops.symbol_not_authorized",
    "unsupported_signal_side": "ops.unsupported_signal_side",
    "short_only_enforced": "ops.short_only_enforced",
    "unsupported_entry_type": "ops.unsupported_entry_type",
    "invalid_price_geometry": "ops.invalid_price_geometry",
    "insufficient_balance": "ops.insufficient_balance",
}


@dataclass(frozen=True)
class OrderLayerInput:
    """Input payload for order-layer decision on a technical signal."""

    signal_id: int
    opportunity_id: int
    symbol: str
    timeframe: str
    signal_side: str
    entry_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str
    signal_timestamp: int
    payload: Mapping[str, Any]
    decision_timestamp: int
    decision_id: int | None = None


@dataclass(frozen=True)
class OrderLayerDecision:
    """Order-layer decision output for a technical signal."""

    should_transition: bool
    target_status: str
    reason: str
    rule_id: str
    details: Mapping[str, Any]


def _is_geometry_valid(signal_side: str, entry_price: float, stop_loss: float, take_profit: float) -> bool:
    if signal_side == "LONG":
        return stop_loss < entry_price < take_profit
    if signal_side == "SHORT":
        return take_profit < entry_price < stop_loss
    return False


def evaluate_signal_for_order_layer(
    order_input: OrderLayerInput,
    *,
    authorized_symbols: Collection[str] | None = None,
    short_only: bool = False,
) -> OrderLayerDecision:
    """Evaluate CREATED technical signal for order-layer consumption."""

    symbols = set(authorized_symbols) if authorized_symbols is not None else set(AUTHORIZED_SYMBOLS)

    if order_input.status != TECHNICAL_SIGNAL_STATUS_CREATED:
        return OrderLayerDecision(
            should_transition=False,
            target_status=order_input.status,
            reason="status_not_created",
            rule_id=M2_007_1_RULE_ID,
            details={"current_status": order_input.status},
        )

    if order_input.symbol not in symbols:
        return OrderLayerDecision(
            should_transition=True,
            target_status=TECHNICAL_SIGNAL_STATUS_CANCELLED,
            reason="symbol_not_authorized",
            rule_id=M2_007_1_RULE_ID,
            details={"symbol": order_input.symbol},
        )

    if order_input.signal_side not in {"LONG", "SHORT"}:
        return OrderLayerDecision(
            should_transition=True,
            target_status=TECHNICAL_SIGNAL_STATUS_CANCELLED,
            reason="unsupported_signal_side",
            rule_id=M2_007_1_RULE_ID,
            details={"signal_side": order_input.signal_side},
        )

    if short_only and order_input.signal_side != "SHORT":
        return OrderLayerDecision(
            should_transition=True,
            target_status=TECHNICAL_SIGNAL_STATUS_CANCELLED,
            reason="short_only_enforced",
            rule_id=M2_007_1_RULE_ID,
            details={"signal_side": order_input.signal_side},
        )

    if order_input.entry_type not in SUPPORTED_ENTRY_TYPES:
        return OrderLayerDecision(
            should_transition=True,
            target_status=TECHNICAL_SIGNAL_STATUS_CANCELLED,
            reason="unsupported_entry_type",
            rule_id=M2_007_1_RULE_ID,
            details={"entry_type": order_input.entry_type},
        )

    if not _is_geometry_valid(
        order_input.signal_side,
        entry_price=order_input.entry_price,
        stop_loss=order_input.stop_loss,
        take_profit=order_input.take_profit,
    ):
        return OrderLayerDecision(
            should_transition=True,
            target_status=TECHNICAL_SIGNAL_STATUS_CANCELLED,
            reason="invalid_price_geometry",
            rule_id=M2_007_1_RULE_ID,
            details={
                "signal_side": order_input.signal_side,
                "entry_price": order_input.entry_price,
                "stop_loss": order_input.stop_loss,
                "take_profit": order_input.take_profit,
            },
        )

    return OrderLayerDecision(
        should_transition=True,
        target_status=TECHNICAL_SIGNAL_STATUS_CONSUMED,
        reason="decision_recorded_no_real_order",
        rule_id=M2_007_1_RULE_ID,
        details={
            "execution_plan": "NO_REAL_ORDER_PHASE1",
            "would_send_real_order": False,
            "planned_action": "QUEUE_FOR_FUTURE_EXECUTION_LAYER",
            "decision_timestamp": order_input.decision_timestamp,
        },
    )
