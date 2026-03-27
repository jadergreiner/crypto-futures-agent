from pathlib import Path

import pandas as pd

import scripts.model2.sync_ohlcv_from_binance as sync_module


class _FakeCollector:
    def __init__(self, _client: object) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def fetch_historical(self, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
        self.calls.append((symbol, timeframe, days))
        return pd.DataFrame(
            [
                {
                    "timestamp": 1700000000000,
                    "symbol": symbol,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.5,
                    "close": 100.5,
                    "volume": 123.0,
                    "quote_volume": 12361.5,
                    "trades_count": 77,
                }
            ]
        )


def test_sync_ohlcv_from_binance_persists_m5_in_legacy_db(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sync_module, "create_binance_client", lambda: object())
    monkeypatch.setattr(sync_module, "BinanceCollector", _FakeCollector)

    source_db = tmp_path / "crypto_agent.db"
    output_dir = tmp_path / "runtime"

    summary = sync_module.sync_ohlcv_from_binance(
        source_db_path=source_db,
        symbols=["BTCUSDT"],
        timeframes=["M5"],
        output_dir=output_dir,
    )

    assert summary["status"] == "ok"
    assert summary["synced_count"] == 1
    assert summary["error_count"] == 0
    assert Path(str(summary["output_file"])).exists()

    from data.database import DatabaseManager

    db = DatabaseManager(str(source_db))
    rows = db.get_ohlcv("m5", "BTCUSDT")

    assert len(rows) == 1
    assert rows[0]["timestamp"] == 1700000000000
    assert rows[0]["close"] == 100.5
