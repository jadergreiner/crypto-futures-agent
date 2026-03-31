"""Suite M2-028.3: Sizing dinamico por volatilidade."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core.model2.live_execution import LiveExecutionConfig
from core.model2.live_service import Model2LiveExecutionService
from core.model2.model_decision import ACTION_OPEN_LONG, ModelDecision
from core.model2.repository import Model2ThesisRepository
from core.model2.volatility_sizing import (
    VolatilitySizingConfig,
    adjust_size_for_volatility,
    compute_volatility_multiplier,
    resolve_volatility_sizing_config,
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


def test_resolve_config_uses_symbol_override_when_available() -> None:
    cfg = resolve_volatility_sizing_config(
        symbol="BTCUSDT",
        risk_params={
            "volatility_sizing_defaults": {
                "min_multiplier": 0.30,
                "max_multiplier": 0.50,
                "min_size_fraction": 0.02,
                "max_size_fraction": 0.80,
            },
            "volatility_sizing_by_symbol": {
                "BTCUSDT": {
                    "max_multiplier": 0.57,
                    "min_size_fraction": 0.03,
                }
            },
        },
    )

    assert cfg.min_multiplier == 0.30
    assert cfg.max_multiplier == 0.57
    assert cfg.min_size_fraction == 0.03
    assert cfg.max_size_fraction == 0.80


def test_resolve_config_fallbacks_to_global_defaults_without_symbol_override() -> None:
    cfg = resolve_volatility_sizing_config(
        symbol="SOLUSDT",
        risk_params={
            "volatility_sizing_defaults": {
                "min_multiplier": 0.31,
                "max_multiplier": 0.49,
                "low_vol_threshold_pct": 1.7,
                "high_vol_threshold_pct": 5.2,
            }
        },
    )

    assert cfg.min_multiplier == 0.31
    assert cfg.max_multiplier == 0.49
    assert cfg.low_vol_threshold_pct == 1.7
    assert cfg.high_vol_threshold_pct == 5.2


def _create_service(db_path: str, mode: str) -> Model2LiveExecutionService:
    repository = Model2ThesisRepository(db_path)
    config = LiveExecutionConfig(
        execution_mode=mode,
        live_symbols=("BTCUSDT",),
        authorized_symbols=("BTCUSDT",),
        short_only=False,
        max_daily_entries=10,
        max_margin_per_position_usd=10.0,
        max_signal_age_ms=240 * 60_000,
        symbol_cooldown_ms=60_000,
        funding_rate_max_for_short=0.0005,
        leverage=5,
    )
    return Model2LiveExecutionService(repository=repository, config=config)


def _seed_technical_signal(db_path: str, signal_id: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE technical_signals (
                id INTEGER PRIMARY KEY,
                payload_json TEXT NOT NULL DEFAULT '{}',
                updated_at INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "INSERT INTO technical_signals (id, payload_json, updated_at) VALUES (?, ?, ?)",
            (signal_id, "{}", 0),
        )
        conn.commit()


def test_live_service_persists_volatility_sizing_in_technical_signals(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "m2_028_3_live.db")
    _seed_technical_signal(db_path, signal_id=101)
    service = _create_service(db_path, mode="live")

    decision = ModelDecision(
        action=ACTION_OPEN_LONG,
        confidence=0.81,
        size_fraction=0.60,
        sl_target=None,
        tp_target=None,
        reason_code="RL_MODEL",
        decision_timestamp=1,
        symbol="BTCUSDT",
        model_version="rl-v1",
        metadata={},
    )

    updated = service._apply_volatility_sizing(
        inferred_decision=decision,
        candidate={"id": 101, "symbol": "BTCUSDT"},
        atr_normalized_pct=3.0,
        now_ms=123,
    )

    assert updated.size_fraction != 0.60
    assert updated.metadata["volatility_sizing"]["applied"] is True

    with sqlite3.connect(db_path) as conn:
        raw = conn.execute(
            "SELECT payload_json FROM technical_signals WHERE id = 101"
        ).fetchone()[0]
    payload = json.loads(raw)
    marker = payload["volatility_sizing"]

    assert marker["applied"] is True
    assert marker["atr_normalized_pct"] == 3.0
    assert marker["base_size_fraction"] == 0.60
    assert marker["adjusted_size_fraction"] == updated.size_fraction
    assert "multiplier" in marker


def test_live_service_shadow_keeps_size_but_persists_informative_metadata(
    tmp_path: Path,
) -> None:
    db_path = str(tmp_path / "m2_028_3_shadow.db")
    _seed_technical_signal(db_path, signal_id=202)
    service = _create_service(db_path, mode="shadow")

    decision = ModelDecision(
        action=ACTION_OPEN_LONG,
        confidence=0.72,
        size_fraction=0.44,
        sl_target=None,
        tp_target=None,
        reason_code="RL_MODEL",
        decision_timestamp=2,
        symbol="BTCUSDT",
        model_version="rl-v1",
        metadata={},
    )

    updated = service._apply_volatility_sizing(
        inferred_decision=decision,
        candidate={"id": 202, "symbol": "BTCUSDT"},
        atr_normalized_pct=7.0,
        now_ms=456,
    )

    assert updated.size_fraction == 0.44
    assert updated.metadata["volatility_sizing"]["applied"] is False

    with sqlite3.connect(db_path) as conn:
        raw = conn.execute(
            "SELECT payload_json FROM technical_signals WHERE id = 202"
        ).fetchone()[0]
    payload = json.loads(raw)
    marker = payload["volatility_sizing"]

    assert marker["applied"] is False
    assert marker["base_size_fraction"] == 0.44
    assert marker["adjusted_size_fraction"] == 0.44

