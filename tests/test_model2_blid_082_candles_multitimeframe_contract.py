#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Suite RED BLID-082 reabertura: contrato auditavel de candles multi-timeframe."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.operator_cycle_status import _build_symbol_report


def _create_market_db_with_ohlcv_rows(
    *,
    symbol: str,
    include_d1: bool = True,
    include_h4: bool = True,
    include_h1: bool = True,
    include_m5: bool = True,
) -> str:
    """Cria DB temporario com tabelas ohlcv_* e dados simples por timeframe."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("CREATE TABLE ohlcv_d1 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_h4 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_h1 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_m5 (symbol TEXT, timestamp INTEGER)")

    if include_d1:
        for ts in (1774656000000, 1774742400000):
            conn.execute(
                "INSERT INTO ohlcv_d1 (symbol, timestamp) VALUES (?, ?)",
                (symbol, ts),
            )
    if include_h4:
        for ts in (1774800000000, 1774814400000):
            conn.execute(
                "INSERT INTO ohlcv_h4 (symbol, timestamp) VALUES (?, ?)",
                (symbol, ts),
            )
    if include_h1:
        for ts in (1774810800000, 1774814400000):
            conn.execute(
                "INSERT INTO ohlcv_h1 (symbol, timestamp) VALUES (?, ?)",
                (symbol, ts),
            )
    if include_m5:
        for ts in (1774817100000, 1774817400000):
            conn.execute(
                "INSERT INTO ohlcv_m5 (symbol, timestamp) VALUES (?, ?)",
                (symbol, ts),
            )

    conn.commit()
    conn.close()
    return tmp.name


def _build_report(
    *,
    symbol: str = "BTCUSDT",
    scan_h4: dict[str, object] | None = None,
    scan_h1: dict[str, object] | None = None,
    db_path: str,
) -> str:
    with (
        patch(
            "scripts.model2.operator_cycle_status._query_last_decision_from_db",
            return_value=("HOLD", 0.0),
        ),
        patch(
            "scripts.model2.operator_cycle_status._query_episode_info",
            return_value=(None, False, 0.0),
        ),
        patch(
            "scripts.model2.operator_cycle_status._query_risk_state_from_db",
            return_value=None,
        ),
    ):
        return _build_symbol_report(
            symbol=symbol,
            scan_h4=scan_h4,
            scan_h1=scan_h1,
            live_execute_summary=None,
            exchange=None,
            last_train_time="N/A",
            pending_episodes=0,
            db_path=db_path,
        )


def test_build_symbol_report_candles_quando_exibe_linha_entao_inclui_d1_h4_h1_m5() -> None:
    """REQ-1: contrato novo deve exibir todos os timeframes do loop canonico."""
    db_path = _create_market_db_with_ohlcv_rows(symbol="BTCUSDT")
    report = _build_report(
        db_path=db_path,
        scan_h4={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 17:00:00 BRT"}}},
        scan_h1={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 18:00:00 BRT"}}},
    )
    candles_line = next(line for line in report.splitlines() if "Candles  :" in line)
    assert "D1:" in candles_line
    assert "H4:" in candles_line
    assert "H1:" in candles_line
    assert "M5:" in candles_line


def test_build_symbol_report_candles_quando_renderiza_entao_separa_scan_e_db() -> None:
    """REQ-2: saida deve separar contagem de scan da contagem persistida em DB."""
    db_path = _create_market_db_with_ohlcv_rows(symbol="BTCUSDT")
    report = _build_report(
        db_path=db_path,
        scan_h4={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 17:00:00 BRT"}}},
        scan_h1={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 18:00:00 BRT"}}},
    )
    candles_line = next(line for line in report.splitlines() if "Candles  :" in line)
    assert "scan=" in candles_line
    assert "db=" in candles_line


def test_build_symbol_report_candles_quando_db_tem_m5_entao_nao_exibe_m5_na() -> None:
    """REQ-3: M5 nao pode ser N/A quando houver persistencia em ohlcv_m5."""
    db_path = _create_market_db_with_ohlcv_rows(symbol="BTCUSDT", include_m5=True)
    report = _build_report(
        db_path=db_path,
        scan_h4={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 17:00:00 BRT"}}},
        scan_h1={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 18:00:00 BRT"}}},
    )
    candles_line = next(line for line in report.splitlines() if "Candles  :" in line)
    assert "M5: N/A" not in candles_line


def test_build_symbol_report_candles_quando_runtime_sem_d1_entao_estado_nao_executado() -> None:
    """REQ-4: ausencia de artefato runtime para D1 deve ser rotulada como nao_executado."""
    db_path = _create_market_db_with_ohlcv_rows(symbol="BTCUSDT")
    report = _build_report(
        db_path=db_path,
        scan_h4={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 17:00:00 BRT"}}},
        scan_h1={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 18:00:00 BRT"}}},
    )
    candles_line = next(line for line in report.splitlines() if "Candles  :" in line)
    assert "D1:" in candles_line
    assert "nao_executado" in candles_line


def test_build_symbol_report_candles_quando_db_sem_m5_entao_estado_sem_persistencia() -> None:
    """REQ-5: sem linha no DB para M5 deve explicitar sem_persistencia."""
    db_path = _create_market_db_with_ohlcv_rows(symbol="BTCUSDT", include_m5=False)
    report = _build_report(
        db_path=db_path,
        scan_h4={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 17:00:00 BRT"}}},
        scan_h1={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 18:00:00 BRT"}}},
    )
    candles_line = next(line for line in report.splitlines() if "Candles  :" in line)
    assert "M5:" in candles_line
    assert "sem_persistencia" in candles_line


def test_build_symbol_report_candles_quando_db_inacessivel_entao_exibe_estado_degradado() -> None:
    """REQ-6: fail-safe deve manter saida com estado degradado explicito."""
    report = _build_report(
        db_path="C:/nao/existe/crypto_agent.db",
        scan_h4={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 17:00:00 BRT"}}},
        scan_h1={"symbols": {"BTCUSDT": {"candles_count": 120, "last_candle_time": "2026-03-29 18:00:00 BRT"}}},
    )
    candles_line = next(line for line in report.splitlines() if "Candles  :" in line)
    assert "degradado" in candles_line
