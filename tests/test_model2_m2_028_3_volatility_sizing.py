"""Suite M2-028.3: Sizing dinamico por volatilidade."""

from __future__ import annotations

from core.model2.volatility_sizing import (
    VolatilitySizingConfig,
    adjust_size_for_volatility,
    compute_volatility_multiplier,
)


def test_multiplier_increases_size_in_low_volatility() -> None:
    cfg = VolatilitySizingConfig(min_multiplier=0.35, max_multiplier=0.55, low_vol_threshold_pct=2.0, high_vol_threshold_pct=6.0)
    multiplier = compute_volatility_multiplier(1.5, cfg)
    assert multiplier == 0.55


def test_multiplier_reduces_size_in_high_volatility() -> None:
    cfg = VolatilitySizingConfig(min_multiplier=0.35, max_multiplier=0.55, low_vol_threshold_pct=2.0, high_vol_threshold_pct=6.0)
    multiplier = compute_volatility_multiplier(8.0, cfg)
    assert multiplier == 0.35


def test_multiplier_interpolates_between_thresholds() -> None:
    cfg = VolatilitySizingConfig(min_multiplier=0.35, max_multiplier=0.55, low_vol_threshold_pct=2.0, high_vol_threshold_pct=6.0)
    multiplier = compute_volatility_multiplier(4.0, cfg)
    assert 0.35 < multiplier < 0.55


def test_shadow_mode_keeps_base_size_and_marks_not_applied() -> None:
    result = adjust_size_for_volatility(
        base_size_fraction=0.4,
        atr_normalized_pct=7.0,
        execution_mode="shadow",
    )
    assert result.applied is False
    assert result.adjusted_size_fraction == 0.4


def test_live_mode_applies_adjustment_and_clamps_to_range() -> None:
    result = adjust_size_for_volatility(
        base_size_fraction=2.0,
        atr_normalized_pct=1.0,
        execution_mode="live",
    )
    assert result.applied is True
    assert 0.01 <= result.adjusted_size_fraction <= 1.0

