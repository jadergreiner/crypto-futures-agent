from core.model2.scanner import (
    M2_002_RULE_ID,
    M2_002_THESIS_TYPE,
    DetectorInput,
    detect_initial_short_failure,
)


def _base_smc(structure: str = "range") -> dict:
    return {
        "structure": {"type": structure},
        "order_blocks": [
            {
                "timestamp": 1_700_000_000_000,
                "zone_low": 100.0,
                "zone_high": 110.0,
                "type": "bearish",
                "status": "FRESH",
                "zone_id": 9,
            }
        ],
        "fvgs": [],
    }


def _base_input(candles: list[dict], smc: dict | None = None) -> DetectorInput:
    return DetectorInput(
        symbol="BTCUSDT",
        timeframe="H4",
        candles=candles,
        indicators=[],
        smc=_base_smc() if smc is None else smc,
        scan_timestamp=1_700_000_001_000,
    )


def test_detects_valid_short_failure_pattern() -> None:
    candles = [
        {"timestamp": 1, "open": 97.0, "high": 99.0, "low": 95.0, "close": 98.0},
        {"timestamp": 2, "open": 100.0, "high": 111.0, "low": 97.0, "close": 98.0},
        {"timestamp": 3, "open": 98.0, "high": 99.0, "low": 96.0, "close": 97.0},
    ]

    result = detect_initial_short_failure(_base_input(candles))

    assert result is not None
    assert result.detected is True
    assert result.side == "SHORT"
    assert result.thesis_type == M2_002_THESIS_TYPE
    assert result.trigger_price == 97.0
    assert result.invalidation_price == 110.0
    assert result.rule_id == M2_002_RULE_ID
    assert result.metadata["rejection_candle"]["timestamp"] == 2


def test_rejects_when_candle_does_not_touch_zone() -> None:
    candles = [
        {"timestamp": 1, "open": 97.0, "high": 99.0, "low": 95.0, "close": 98.0},
        {"timestamp": 2, "open": 100.0, "high": 99.9, "low": 95.0, "close": 98.0},
        {"timestamp": 3, "open": 98.0, "high": 99.0, "low": 96.0, "close": 97.0},
    ]

    assert detect_initial_short_failure(_base_input(candles)) is None


def test_rejects_when_rejection_is_not_visible() -> None:
    candles = [
        {"timestamp": 1, "open": 97.0, "high": 99.0, "low": 95.0, "close": 98.0},
        {"timestamp": 2, "open": 101.0, "high": 102.0, "low": 97.0, "close": 98.0},
        {"timestamp": 3, "open": 98.0, "high": 99.0, "low": 96.0, "close": 97.0},
    ]

    assert detect_initial_short_failure(_base_input(candles)) is None


def test_rejects_when_context_is_bullish() -> None:
    candles = [
        {"timestamp": 1, "open": 97.0, "high": 99.0, "low": 95.0, "close": 98.0},
        {"timestamp": 2, "open": 100.0, "high": 111.0, "low": 97.0, "close": 98.0},
        {"timestamp": 3, "open": 98.0, "high": 99.0, "low": 96.0, "close": 97.0},
    ]

    smc = _base_smc(structure="bullish")
    assert detect_initial_short_failure(_base_input(candles, smc=smc)) is None


def test_rejects_when_trigger_is_not_broken() -> None:
    candles = [
        {"timestamp": 1, "open": 97.0, "high": 99.0, "low": 95.0, "close": 98.0},
        {"timestamp": 2, "open": 100.0, "high": 111.0, "low": 97.0, "close": 98.0},
        {"timestamp": 3, "open": 98.0, "high": 102.0, "low": 97.0, "close": 99.0},
    ]

    assert detect_initial_short_failure(_base_input(candles)) is None
