"""Live execution contracts and deterministic gate logic for Model 2.0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

M2_009_1_RULE_ID = "M2-009.1-RULE-SIGNAL-EXECUTION-LIFECYCLE"
M2_009_2_RULE_ID = "M2-009.2-RULE-LIVE-GATE"
M2_009_3_RULE_ID = "M2-009.3-RULE-MARKET-ENTRY"
M2_009_4_RULE_ID = "M2-009.4-RULE-PROTECTION-FAILSAFE"
M2_010_1_RULE_ID = "M2-010.1-RULE-LIVE-RECONCILE"

TECHNICAL_SIGNAL_STATUS_CONSUMED = "CONSUMED"
ENTRY_ORDER_TYPE_MARKET = "MARKET"

SIGNAL_EXECUTION_STATUS_READY = "READY"
SIGNAL_EXECUTION_STATUS_BLOCKED = "BLOCKED"
SIGNAL_EXECUTION_STATUS_ENTRY_SENT = "ENTRY_SENT"
SIGNAL_EXECUTION_STATUS_ENTRY_FILLED = "ENTRY_FILLED"
SIGNAL_EXECUTION_STATUS_PROTECTED = "PROTECTED"
SIGNAL_EXECUTION_STATUS_EXITED = "EXITED"
SIGNAL_EXECUTION_STATUS_FAILED = "FAILED"
SIGNAL_EXECUTION_STATUS_CANCELLED = "CANCELLED"

OFFICIAL_SIGNAL_EXECUTION_STATUSES = (
    SIGNAL_EXECUTION_STATUS_READY,
    SIGNAL_EXECUTION_STATUS_BLOCKED,
    SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
    SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
    SIGNAL_EXECUTION_STATUS_PROTECTED,
    SIGNAL_EXECUTION_STATUS_EXITED,
    SIGNAL_EXECUTION_STATUS_FAILED,
    SIGNAL_EXECUTION_STATUS_CANCELLED,
)
FINAL_SIGNAL_EXECUTION_STATUSES = frozenset(
    {
        SIGNAL_EXECUTION_STATUS_BLOCKED,
        SIGNAL_EXECUTION_STATUS_EXITED,
        SIGNAL_EXECUTION_STATUS_FAILED,
        SIGNAL_EXECUTION_STATUS_CANCELLED,
    }
)
ACTIVE_SIGNAL_EXECUTION_STATUSES = frozenset(
    {
        SIGNAL_EXECUTION_STATUS_READY,
        SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
        SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
        SIGNAL_EXECUTION_STATUS_PROTECTED,
    }
)
ALLOWED_SIGNAL_EXECUTION_TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_READY,
            SIGNAL_EXECUTION_STATUS_BLOCKED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_READY: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
            SIGNAL_EXECUTION_STATUS_FAILED,
            SIGNAL_EXECUTION_STATUS_CANCELLED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_ENTRY_SENT: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
            SIGNAL_EXECUTION_STATUS_FAILED,
            SIGNAL_EXECUTION_STATUS_CANCELLED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_ENTRY_FILLED: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_PROTECTED,
            SIGNAL_EXECUTION_STATUS_EXITED,
            SIGNAL_EXECUTION_STATUS_FAILED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_PROTECTED: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_EXITED,
            SIGNAL_EXECUTION_STATUS_FAILED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_BLOCKED: frozenset(),
    SIGNAL_EXECUTION_STATUS_EXITED: frozenset(),
    SIGNAL_EXECUTION_STATUS_FAILED: frozenset(),
    SIGNAL_EXECUTION_STATUS_CANCELLED: frozenset(),
}


def is_valid_signal_execution_transition(from_status: str | None, to_status: str) -> bool:
    """Return whether a signal execution transition is allowed."""

    allowed = ALLOWED_SIGNAL_EXECUTION_TRANSITIONS.get(from_status)
    if allowed is None:
        return False
    return to_status in allowed


@dataclass(frozen=True)
class LiveExecutionConfig:
    """Static runtime configuration for live/shadow execution."""

    execution_mode: str
    live_symbols: tuple[str, ...]
    authorized_symbols: tuple[str, ...]
    short_only: bool
    max_daily_entries: int
    max_margin_per_position_usd: float
    max_signal_age_ms: int
    symbol_cooldown_ms: int
    funding_rate_max_for_short: float
    leverage: int


@dataclass(frozen=True)
class LiveExecutionGateInput:
    """Inputs required to decide if a technical signal may enter live execution."""

    technical_signal_id: int
    opportunity_id: int
    symbol: str
    timeframe: str
    signal_side: str
    technical_signal_status: str
    signal_timestamp: int
    short_only: bool
    funding_rate: float | None
    basis_value: float | None
    funding_rate_max_for_short: float
    execution_mode: str
    live_symbols: tuple[str, ...]
    authorized_symbols: tuple[str, ...]
    available_balance_usd: float | None
    max_margin_per_position_usd: float
    recent_entries_today: int
    max_daily_entries: int
    symbol_active_execution_count: int
    open_position_qty: float
    cooldown_active: bool
    signal_age_ms: int
    max_signal_age_ms: int
    risk_gate_status: str
    risk_gate_allows_order: bool
    risk_gate_drawdown_pct: float | None
    circuit_breaker_state: str
    circuit_breaker_allows_trading: bool
    circuit_breaker_drawdown_pct: float | None


@dataclass(frozen=True)
class LiveExecutionGateDecision:
    """Decision emitted by the deterministic live gate."""

    allow_execution: bool
    target_status: str
    reason: str
    rule_id: str
    details: Mapping[str, Any]


def _blocked(reason: str, **details: Any) -> LiveExecutionGateDecision:
    return LiveExecutionGateDecision(
        allow_execution=False,
        target_status=SIGNAL_EXECUTION_STATUS_BLOCKED,
        reason=reason,
        rule_id=M2_009_2_RULE_ID,
        details=details,
    )


def evaluate_live_execution_gate(gate_input: LiveExecutionGateInput) -> LiveExecutionGateDecision:
    """Evaluate whether a CONSUMED technical signal can enter live execution."""

    execution_mode = str(gate_input.execution_mode).strip().lower()
    if execution_mode not in {"shadow", "live"}:
        return _blocked(
            "unsupported_execution_mode",
            execution_mode=gate_input.execution_mode,
        )

    if gate_input.technical_signal_status != TECHNICAL_SIGNAL_STATUS_CONSUMED:
        return _blocked(
            "status_not_consumed",
            current_status=gate_input.technical_signal_status,
        )

    risk_gate_status = str(gate_input.risk_gate_status).strip().lower()
    if risk_gate_status in {"", "unknown", "unavailable"}:
        return _blocked(
            "risk_gate_state_unavailable",
            risk_gate_status=gate_input.risk_gate_status,
            risk_gate_drawdown_pct=gate_input.risk_gate_drawdown_pct,
        )

    if not bool(gate_input.risk_gate_allows_order):
        return _blocked(
            "risk_gate_blocked",
            risk_gate_status=gate_input.risk_gate_status,
            risk_gate_drawdown_pct=gate_input.risk_gate_drawdown_pct,
        )

    circuit_breaker_state = str(gate_input.circuit_breaker_state).strip().lower()
    if circuit_breaker_state in {"", "unknown", "unavailable"}:
        return _blocked(
            "circuit_breaker_state_unavailable",
            circuit_breaker_state=gate_input.circuit_breaker_state,
            circuit_breaker_drawdown_pct=gate_input.circuit_breaker_drawdown_pct,
        )

    if not bool(gate_input.circuit_breaker_allows_trading):
        return _blocked(
            "circuit_breaker_blocked",
            circuit_breaker_state=gate_input.circuit_breaker_state,
            circuit_breaker_drawdown_pct=gate_input.circuit_breaker_drawdown_pct,
        )

    if gate_input.signal_side not in {"LONG", "SHORT"}:
        return _blocked(
            "unsupported_signal_side",
            signal_side=gate_input.signal_side,
        )

    if bool(gate_input.short_only) and gate_input.signal_side != "SHORT":
        return _blocked(
            "short_only_enforced",
            signal_side=gate_input.signal_side,
        )

    authorized_symbols = {symbol.upper() for symbol in gate_input.authorized_symbols}
    if authorized_symbols and gate_input.symbol.upper() not in authorized_symbols:
        return _blocked(
            "symbol_not_authorized",
            symbol=gate_input.symbol,
        )

    live_symbols = {symbol.upper() for symbol in gate_input.live_symbols}
    if live_symbols and gate_input.symbol.upper() not in live_symbols:
        return _blocked(
            "symbol_not_enabled",
            symbol=gate_input.symbol,
        )

    if gate_input.signal_age_ms > gate_input.max_signal_age_ms:
        return _blocked(
            "signal_expired",
            signal_age_ms=int(gate_input.signal_age_ms),
            max_signal_age_ms=int(gate_input.max_signal_age_ms),
        )

    if gate_input.symbol_active_execution_count > 0:
        return _blocked(
            "active_execution_exists",
            symbol=gate_input.symbol,
            active_count=int(gate_input.symbol_active_execution_count),
        )

    if gate_input.open_position_qty > 0:
        return _blocked(
            "open_position_exists",
            symbol=gate_input.symbol,
            open_position_qty=float(gate_input.open_position_qty),
        )

    if gate_input.cooldown_active:
        return _blocked(
            "symbol_in_cooldown",
            symbol=gate_input.symbol,
        )

    if gate_input.recent_entries_today >= gate_input.max_daily_entries:
        return _blocked(
            "daily_limit_reached",
            recent_entries_today=int(gate_input.recent_entries_today),
            max_daily_entries=int(gate_input.max_daily_entries),
        )

    if gate_input.max_margin_per_position_usd <= 0:
        return _blocked(
            "invalid_margin_limit",
            max_margin_per_position_usd=float(gate_input.max_margin_per_position_usd),
        )

    if gate_input.signal_side == "SHORT":
        if gate_input.funding_rate is not None and gate_input.funding_rate > gate_input.funding_rate_max_for_short:
            return _blocked(
                "funding_unfavorable",
                funding_rate=float(gate_input.funding_rate),
                threshold=float(gate_input.funding_rate_max_for_short),
            )
        if gate_input.basis_value is not None and gate_input.basis_value < 0:
            return _blocked(
                "negative_basis",
                basis_value=float(gate_input.basis_value),
            )

    if execution_mode == "live":
        if gate_input.available_balance_usd is None:
            return _blocked("balance_unavailable")
        if gate_input.available_balance_usd < gate_input.max_margin_per_position_usd:
            return _blocked(
                "insufficient_balance",
                available_balance_usd=float(gate_input.available_balance_usd),
                required_margin_usd=float(gate_input.max_margin_per_position_usd),
            )

    return LiveExecutionGateDecision(
        allow_execution=True,
        target_status=SIGNAL_EXECUTION_STATUS_READY,
        reason="ready_for_live_execution",
        rule_id=M2_009_2_RULE_ID,
        details={
            "execution_mode": execution_mode,
            "max_margin_per_position_usd": float(gate_input.max_margin_per_position_usd),
            "recent_entries_today": int(gate_input.recent_entries_today),
            "signal_age_ms": int(gate_input.signal_age_ms),
        },
    )
