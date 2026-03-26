"""Volatility-aware sizing helpers for M2-028.3."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VolatilitySizingConfig:
    min_multiplier: float = 0.35
    max_multiplier: float = 0.55
    low_vol_threshold_pct: float = 2.0
    high_vol_threshold_pct: float = 6.0
    min_size_fraction: float = 0.01
    max_size_fraction: float = 1.0


@dataclass(frozen=True)
class VolatilitySizingResult:
    adjusted_size_fraction: float
    multiplier: float
    atr_normalized_pct: float | None
    applied: bool


def compute_volatility_multiplier(
    atr_normalized_pct: float | None,
    config: VolatilitySizingConfig,
) -> float:
    if atr_normalized_pct is None:
        return 1.0

    atr = float(atr_normalized_pct)
    if atr <= config.low_vol_threshold_pct:
        return float(config.max_multiplier)
    if atr >= config.high_vol_threshold_pct:
        return float(config.min_multiplier)

    span = config.high_vol_threshold_pct - config.low_vol_threshold_pct
    if span <= 0:
        return 1.0

    ratio = (atr - config.low_vol_threshold_pct) / span
    return float(config.max_multiplier - ratio * (config.max_multiplier - config.min_multiplier))


def adjust_size_for_volatility(
    *,
    base_size_fraction: float,
    atr_normalized_pct: float | None,
    execution_mode: str,
    config: VolatilitySizingConfig | None = None,
) -> VolatilitySizingResult:
    cfg = config or VolatilitySizingConfig()
    mode = str(execution_mode).strip().lower()
    multiplier = compute_volatility_multiplier(atr_normalized_pct, cfg)
    base = max(0.0, float(base_size_fraction))
    suggested = max(cfg.min_size_fraction, min(cfg.max_size_fraction, base * multiplier))

    if mode == "shadow":
        return VolatilitySizingResult(
            adjusted_size_fraction=base,
            multiplier=multiplier,
            atr_normalized_pct=atr_normalized_pct,
            applied=False,
        )

    return VolatilitySizingResult(
        adjusted_size_fraction=suggested,
        multiplier=multiplier,
        atr_normalized_pct=atr_normalized_pct,
        applied=True,
    )

