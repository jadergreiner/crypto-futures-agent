import pytest

from core.model2.live_exchange import Model2LiveExchange


class DummyClient:
    pass


class _FakeRestApiForClose:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def new_order(
        self,
        symbol,
        side,
        type,
        position_side=None,
        time_in_force=None,
        quantity=None,
        reduce_only=None,
        price=None,
        new_client_order_id=None,
        new_order_resp_type=None,
        price_match=None,
        self_trade_prevention_mode=None,
        good_till_date=None,
        recv_window=None,
    ):
        call = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "position_side": position_side,
            "quantity": quantity,
            "reduce_only": reduce_only,
            "price": price,
            "recv_window": recv_window,
        }
        self.calls.append(call)
        if str(reduce_only).lower() not in {"true", "1"}:
            raise RuntimeError("reduce_only required")
        return {"orderId": "close-1"}


class _FakeClientForClose:
    def __init__(self) -> None:
        self.rest_api = _FakeRestApiForClose()


class _FakeRestApiForProtectiveFail:
    def __init__(self) -> None:
        self.new_algo_order_calls = 0
        self.new_order_calls = 0

    def new_algo_order(
        self,
        algo_type,
        symbol,
        side,
        type,
        position_side=None,
        time_in_force=None,
        quantity=None,
        price=None,
        trigger_price=None,
        working_type=None,
        price_match=None,
        close_position=None,
        price_protect=None,
        reduce_only=None,
        activate_price=None,
        callback_rate=None,
        client_algo_id=None,
        new_order_resp_type=None,
        self_trade_prevention_mode=None,
        good_till_date=None,
        recv_window=None,
    ):
        self.new_algo_order_calls += 1
        raise RuntimeError("algo failed")

    def new_order(
        self,
        symbol,
        side,
        type,
        position_side=None,
        time_in_force=None,
        quantity=None,
        reduce_only=None,
        price=None,
        new_client_order_id=None,
        new_order_resp_type=None,
        price_match=None,
        self_trade_prevention_mode=None,
        good_till_date=None,
        recv_window=None,
    ):
        self.new_order_calls += 1
        raise RuntimeError("new_order failed")


class _FakeClientForProtectiveFail:
    def __init__(self) -> None:
        self.rest_api = _FakeRestApiForProtectiveFail()


def test_calculate_entry_quantity_respects_precision_and_rounding(monkeypatch):
    ex = Model2LiveExchange(DummyClient())

    # Monkeypatch symbol precision info to a fixed precision
    monkeypatch.setattr(
        ex, "_get_symbol_precision_info", lambda symbol: {"quantity_precision": 2, "price_precision": 2, "tick_size": None, "min_notional": None}
    )

    # entry_price 100, margin 1, leverage 10 -> notional 10, raw_qty=0.1 -> rounded to 0.1 with precision 2
    qty = ex.calculate_entry_quantity("BTCUSDT", entry_price=100.0, margin_usd=1.0, leverage=10)
    assert qty == 0.1


def test_calculate_entry_quantity_respects_min_notional(monkeypatch):
    ex = Model2LiveExchange(DummyClient())

    # Simular min_notional = 20 USD
    monkeypatch.setattr(
        ex, "_get_symbol_precision_info", lambda symbol: {"quantity_precision": 8, "price_precision": 8, "tick_size": None, "min_notional": 20.0}
    )

    # entry_price 100, margin 0.1, leverage 1 -> notional 0.1 -> deve retornar 0.0 ( abaixo do min_notional )
    qty = ex.calculate_entry_quantity("BTCUSDT", entry_price=100.0, margin_usd=0.1, leverage=1)
    assert qty == 0.0

    # entry_price 50, margin 1, leverage 1 -> notional 1 -> ainda abaixo -> 0
    qty = ex.calculate_entry_quantity("BTCUSDT", entry_price=50.0, margin_usd=1.0, leverage=1)
    assert qty == 0.0

    # entry_price 100, margin 5, leverage 1 -> notional 5 -> abaixo
    qty = ex.calculate_entry_quantity("BTCUSDT", entry_price=100.0, margin_usd=5.0, leverage=1)
    assert qty == 0.0

    # entry_price 100, margin 20, leverage 1 -> notional 20 -> deve retornar >= 0
    qty = ex.calculate_entry_quantity("BTCUSDT", entry_price=100.0, margin_usd=20.0, leverage=1)
    assert qty >= 0.0


def test_close_position_market_never_sends_plain_market_without_reduce_only() -> None:
    ex = Model2LiveExchange(_FakeClientForClose())

    response = ex.close_position_market(symbol="ETHUSDT", signal_side="SHORT", quantity=0.01)
    assert response.get("orderId") == "close-1"
    assert ex._client.rest_api.calls
    assert all(str(call.get("reduce_only")).lower() in {"true", "1"} for call in ex._client.rest_api.calls)


def test_place_protective_order_does_not_fallback_to_market_close(monkeypatch) -> None:
    ex = Model2LiveExchange(_FakeClientForProtectiveFail())
    monkeypatch.setattr(
        ex,
        "get_open_position",
        lambda symbol: {"position_size_qty": 0.01, "symbol": symbol, "direction": "SHORT"},
    )

    close_called = {"value": False}

    def _unexpected_close(**kwargs):  # type: ignore[no-untyped-def]
        close_called["value"] = True
        raise AssertionError("close_position_market should not be called")

    monkeypatch.setattr(ex, "close_position_market", _unexpected_close)

    with pytest.raises(RuntimeError):
        ex.place_protective_order(
            symbol="ETHUSDT",
            signal_side="SHORT",
            trigger_price=2100.0,
            order_type="STOP_MARKET",
        )
    assert close_called["value"] is False
