from __future__ import annotations

from config.settings import _normalize_symbol_scope


def test_normalize_symbol_scope_expande_placeholder_m2_symbols() -> None:
    result = _normalize_symbol_scope(
        "M2_SYMBOLS:",
        fallback_symbols=("BTCUSDT", "ETHUSDT"),
    )

    assert result == ("BTCUSDT", "ETHUSDT")


def test_normalize_symbol_scope_mescla_placeholder_e_simbolos_explicitos() -> None:
    result = _normalize_symbol_scope(
        "BTCUSDT,M2_SYMBOLS:,ETHUSDT,BTCUSDT",
        fallback_symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
    )

    assert result == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_normalize_symbol_scope_ignora_vazios() -> None:
    result = _normalize_symbol_scope(
        " , , ",
        fallback_symbols=("BTCUSDT",),
    )

    assert result == ()