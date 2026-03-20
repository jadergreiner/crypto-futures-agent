import pytest

from core.model2.live_exchange import Model2LiveExchange


class DummyClient:
    pass


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
