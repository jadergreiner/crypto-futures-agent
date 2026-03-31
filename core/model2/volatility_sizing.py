"""Volatility-aware sizing helpers for M2-028.3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _coerce_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _resolve_numeric(
    *,
    key: str,
    fallback: float,
    defaults: Mapping[str, Any],
    symbol_overrides: Mapping[str, Any],
) -> float:
    if key in symbol_overrides:
        return _coerce_float(symbol_overrides.get(key), fallback)
    if key in defaults:
        return _coerce_float(defaults.get(key), fallback)
    return float(fallback)


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


def resolve_volatility_sizing_config(
    *,
    symbol: str | None,
    risk_params: Mapping[str, Any] | None,
) -> VolatilitySizingConfig:
    """Resolve configuracao de sizing com fallback global e override por simbolo."""
    base = VolatilitySizingConfig()
    params = risk_params if isinstance(risk_params, Mapping) else {}

    defaults_raw = params.get("volatility_sizing_defaults", {})
    defaults = defaults_raw if isinstance(defaults_raw, Mapping) else {}

    by_symbol_raw = params.get("volatility_sizing_by_symbol", {})
    by_symbol = by_symbol_raw if isinstance(by_symbol_raw, Mapping) else {}

    symbol_key = str(symbol or "").upper()
    symbol_overrides_raw = by_symbol.get(symbol_key) or by_symbol.get(str(symbol or ""))
    symbol_overrides = (
        symbol_overrides_raw
        if isinstance(symbol_overrides_raw, Mapping)
        else {}
    )

    min_multiplier = _resolve_numeric(
        key="min_multiplier",
        fallback=base.min_multiplier,
        defaults=defaults,
        symbol_overrides=symbol_overrides,
    )
    max_multiplier = _resolve_numeric(
        key="max_multiplier",
        fallback=base.max_multiplier,
        defaults=defaults,
        symbol_overrides=symbol_overrides,
    )
    low_vol_threshold_pct = _resolve_numeric(
        key="low_vol_threshold_pct",
        fallback=base.low_vol_threshold_pct,
        defaults=defaults,
        symbol_overrides=symbol_overrides,
    )
    high_vol_threshold_pct = _resolve_numeric(
        key="high_vol_threshold_pct",
        fallback=base.high_vol_threshold_pct,
        defaults=defaults,
        symbol_overrides=symbol_overrides,
    )
    min_size_fraction = _resolve_numeric(
        key="min_size_fraction",
        fallback=base.min_size_fraction,
        defaults=defaults,
        symbol_overrides=symbol_overrides,
    )
    max_size_fraction = _resolve_numeric(
        key="max_size_fraction",
        fallback=base.max_size_fraction,
        defaults=defaults,
        symbol_overrides=symbol_overrides,
    )

    if min_multiplier > max_multiplier:
        min_multiplier, max_multiplier = max_multiplier, min_multiplier
    if low_vol_threshold_pct > high_vol_threshold_pct:
        low_vol_threshold_pct, high_vol_threshold_pct = (
            high_vol_threshold_pct,
            low_vol_threshold_pct,
        )
    min_size_fraction = max(0.0, min_size_fraction)
    max_size_fraction = max(min_size_fraction, max_size_fraction)

    return VolatilitySizingConfig(
        min_multiplier=min_multiplier,
        max_multiplier=max_multiplier,
        low_vol_threshold_pct=low_vol_threshold_pct,
        high_vol_threshold_pct=high_vol_threshold_pct,
        min_size_fraction=min_size_fraction,
        max_size_fraction=max_size_fraction,
    )


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
    symbol: str | None = None,
    risk_params: Mapping[str, Any] | None = None,
) -> VolatilitySizingResult:
    cfg = config or resolve_volatility_sizing_config(
        symbol=symbol,
        risk_params=risk_params,
    )
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

