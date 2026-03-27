"""Daily drawdown admission gate for M2-028.4."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DrawdownGateDecision:
    """Decision emitted by the daily drawdown gate."""

    allowed: bool
    reason: str
    frozen: bool
    current_drawdown_pct: float


class DailyDrawdownGate:
    """Blocks admissions when daily drawdown reaches configured threshold."""

    def __init__(self, *, max_daily_drawdown_pct: float, initial_equity: float) -> None:
        self._max_daily_drawdown_pct = float(max_daily_drawdown_pct)
        self._initial_equity = max(0.0, float(initial_equity))
        self._accumulated_loss = 0.0
        self._frozen = False

    @property
    def accumulated_loss(self) -> float:
        return self._accumulated_loss

    def register_loss(self, loss_amount: float) -> None:
        value = float(loss_amount)
        if value <= 0.0:
            return
        self._accumulated_loss += value

    def reset_for_new_day_utc(self) -> None:
        self._accumulated_loss = 0.0
        self._frozen = False

    def evaluate(self) -> DrawdownGateDecision:
        current_drawdown_pct = self._compute_drawdown_pct()
        if self._frozen:
            return DrawdownGateDecision(
                allowed=False,
                reason="DAILY_DRAWDOWN_LIMIT",
                frozen=True,
                current_drawdown_pct=current_drawdown_pct,
            )

        if current_drawdown_pct >= self._max_daily_drawdown_pct:
            self._frozen = True
            return DrawdownGateDecision(
                allowed=False,
                reason="DAILY_DRAWDOWN_LIMIT",
                frozen=True,
                current_drawdown_pct=current_drawdown_pct,
            )

        return DrawdownGateDecision(
            allowed=True,
            reason="OK",
            frozen=False,
            current_drawdown_pct=current_drawdown_pct,
        )

    def _compute_drawdown_pct(self) -> float:
        if self._initial_equity <= 0.0:
            return 0.0
        return float((self._accumulated_loss / self._initial_equity) * 100.0)
