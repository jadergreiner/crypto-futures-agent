import sqlite3
from pathlib import Path

import pytest

from config.settings import MODEL2_DB_PATH
from scripts.model2.reprocess import run_reprocess


def _prepare_source_db(tmp_path: Path) -> Path:
    source_db = tmp_path / "db" / "source.db"
    source_db.parent.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[int, str, float, float, float, float, float, float, int]] = []
    symbols = {
        "VALUSDT": [
            (1_000, 97.0, 99.0, 95.0, 98.0),
            (2_000, 100.0, 111.0, 97.0, 98.0),
            (3_000, 98.0, 99.0, 96.0, 97.0),
            (4_000, 97.0, 98.0, 95.0, 96.0),
            (90_000_000, 97.0, 98.0, 96.5, 97.0),
        ],
        "INVUSDT": [
            (1_000, 97.0, 99.0, 95.0, 98.0),
            (2_000, 100.0, 111.0, 97.0, 98.0),
            (3_000, 98.0, 99.0, 96.0, 97.0),
            (4_000, 111.0, 112.0, 111.0, 111.2),
            (90_000_000, 109.0, 109.5, 108.5, 109.0),
        ],
        "EXPUSDT": [
            (1_000, 97.0, 99.0, 95.0, 98.0),
            (2_000, 100.0, 111.0, 97.0, 98.0),
            (3_000, 98.0, 99.0, 96.0, 97.0),
            (4_000, 101.0, 102.0, 100.0, 101.0),
            (90_000_000, 101.0, 102.0, 100.0, 101.0),
        ],
    }

    for symbol, candles in symbols.items():
        for ts, o, h, l, c in candles:
            rows.append((ts, symbol, o, h, l, c, 100.0, 100.0, 10))

    with sqlite3.connect(source_db) as conn:
        conn.execute(
            """
            CREATE TABLE ohlcv_h4 (
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quote_volume REAL NOT NULL,
                trades_count INTEGER NOT NULL,
                PRIMARY KEY (timestamp, symbol)
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO ohlcv_h4 (
                timestamp, symbol, open, high, low, close, volume, quote_volume, trades_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()

    return source_db


def _fake_smc(_df):  # type: ignore[no-untyped-def]
    return {
        "structure": {"type": "range"},
        "order_blocks": [
            {
                "timestamp": 1_500,
                "zone_low": 100.0,
                "zone_high": 110.0,
                "type": "bearish",
                "status": "FRESH",
                "zone_id": 7,
            }
        ],
        "fvgs": [],
    }


def test_reprocess_generates_validated_invalidated_expired_and_rates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_db = _prepare_source_db(tmp_path)
    replay_db = tmp_path / "db" / "modelo2_replay.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"

    monkeypatch.setattr(
        "scripts.model2.reprocess.SmartMoneyConcepts.calculate_all_smc",
        _fake_smc,
    )

    summary = run_reprocess(
        source_db_path=source_db,
        replay_db_path=replay_db,
        symbols=["VALUSDT", "INVUSDT", "EXPUSDT"],
        timeframe="H4",
        start_ts=1_000,
        end_ts=90_000_000,
        candles_limit=120,
        transition_limit=200,
        output_dir=output_dir,
    )

    assert summary["status"] == "ok"
    assert summary["final_count_by_status"]["VALIDADA"] == 1
    assert summary["final_count_by_status"]["INVALIDADA"] == 1
    assert summary["final_count_by_status"]["EXPIRADA"] == 1
    assert summary["rates"]["directional"]["validated_over_validated_plus_invalidated"] == 0.5
    assert summary["rates"]["directional"]["invalidated_over_validated_plus_invalidated"] == 0.5
    assert summary["rates"]["resolved"]["validated_over_resolved"] == pytest.approx(1 / 3)
    assert summary["rates"]["resolved"]["invalidated_over_resolved"] == pytest.approx(1 / 3)
    assert Path(summary["output_file"]).exists()


def test_reprocess_blocks_operational_db_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_db = _prepare_source_db(tmp_path)
    monkeypatch.setattr(
        "scripts.model2.reprocess.SmartMoneyConcepts.calculate_all_smc",
        _fake_smc,
    )

    with pytest.raises(ValueError, match="Replay DB cannot match operational Model2 DB"):
        run_reprocess(
            source_db_path=source_db,
            replay_db_path=MODEL2_DB_PATH,
            symbols=["VALUSDT"],
            timeframe="H4",
            start_ts=1_000,
            end_ts=90_000_000,
            candles_limit=120,
            transition_limit=200,
            output_dir=tmp_path / "results",
        )
