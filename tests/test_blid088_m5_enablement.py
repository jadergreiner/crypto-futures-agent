import sys

from scripts.model2 import daily_pipeline
from scripts.model2 import scan
from scripts.model2 import schedule_daily_pipeline
from scripts.model2 import sync_ohlcv_from_binance


def test_scan_timeframe_map_includes_m5() -> None:
    assert scan.TIMEFRAME_TO_TABLE["M5"] == "ohlcv_m5"


def test_daily_pipeline_accepts_m5_timeframe(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "argv", ["daily_pipeline.py", "--timeframe", "M5"])
    args = daily_pipeline._parse_args()
    assert args.timeframe == "M5"


def test_schedule_daily_pipeline_accepts_m5_timeframe(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "argv", ["schedule_daily_pipeline.py", "--timeframe", "M5"])
    args = schedule_daily_pipeline._parse_args()
    assert args.timeframe == "M5"


def test_sync_ohlcv_from_binance_accepts_m5_timeframe(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "argv", ["sync_ohlcv_from_binance.py", "--timeframe", "M5"])
    args = sync_ohlcv_from_binance._parse_args()
    assert "M5" in args.timeframe
