import json

from core.model2.signal_adapter import (
    M2_007_2_RULE_ID,
    SignalAdapterInput,
    build_legacy_trade_signal_payload,
)


def _base_input() -> SignalAdapterInput:
    return SignalAdapterInput(
        technical_signal_id=11,
        opportunity_id=101,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side="SHORT",
        entry_price=97.0,
        stop_loss=110.0,
        take_profit=84.0,
        status="CONSUMED",
        signal_timestamp=1_700_000_100_000,
        payload={"foo": "bar"},
    )


def test_build_legacy_trade_signal_payload_success() -> None:
    result = build_legacy_trade_signal_payload(_base_input())
    assert result.exportable is True
    assert result.reason == "ok"
    payload = result.payload
    assert payload is not None
    assert payload["symbol"] == "BTCUSDT"
    assert payload["direction"] == "SHORT"
    assert payload["execution_mode"] == "PENDING"
    assert payload["status"] == "ACTIVE"

    details = json.loads(payload["confluence_details"])
    assert details["adapter"] == "m2_007_2"
    assert details["rule_id"] == M2_007_2_RULE_ID
    assert details["m2_technical_signal_id"] == 11
    assert details["would_send_real_order"] is False


def test_build_legacy_trade_signal_payload_rejects_non_consumed() -> None:
    source = _base_input()
    result = build_legacy_trade_signal_payload(
        SignalAdapterInput(**{**source.__dict__, "status": "CREATED"})
    )
    assert result.exportable is False
    assert result.reason == "status_not_consumed"


def test_build_legacy_trade_signal_payload_rejects_invalid_side() -> None:
    source = _base_input()
    result = build_legacy_trade_signal_payload(
        SignalAdapterInput(**{**source.__dict__, "signal_side": "BUY"})
    )
    assert result.exportable is False
    assert result.reason == "unsupported_signal_side"
