"""Suite RED para M2-025.14: expandir go_live_preflight com checks de episodio/treino/candle.

Testa:
- Preflight verifica que modelo RL tem episodios de treino suficientes
- Preflight verifica frescor dos candles (ultima atualizacao < threshold)
- Preflight verifica que checkpoints de treino existem
- Falha em qualquer check retorna status de erro claro
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from scripts.model2.go_live_preflight import run_go_live_preflight


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _criar_db_minimo(db_path: Path) -> None:
    """Cria schema minimo para preflight."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT, side TEXT,
            thesis_type TEXT, zone_low REAL, zone_high REAL, trigger_price REAL,
            invalidation_price REAL, status TEXT, created_at_ms INTEGER,
            expires_at_ms INTEGER, metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS technical_signals (
            id INTEGER PRIMARY KEY, opportunity_id INTEGER, symbol TEXT,
            timeframe TEXT, signal_side TEXT, entry_type TEXT, entry_price REAL,
            stop_loss REAL, take_profit REAL, status TEXT, signal_timestamp INTEGER,
            payload TEXT
        );
        CREATE TABLE IF NOT EXISTS signal_executions (
            id INTEGER PRIMARY KEY, signal_id INTEGER, status TEXT, symbol TEXT,
            signal_side TEXT, entry_price REAL, stop_loss REAL, take_profit REAL,
            created_at_ms INTEGER, updated_at_ms INTEGER
        );
        CREATE TABLE IF NOT EXISTS signal_execution_events (
            id INTEGER PRIMARY KEY, signal_execution_id INTEGER,
            from_status TEXT, to_status TEXT, reason TEXT, ts_ms INTEGER
        );
        CREATE TABLE IF NOT EXISTS opportunity_events (
            id INTEGER PRIMARY KEY, opportunity_id INTEGER,
            from_status TEXT, to_status TEXT, reason TEXT, ts_ms INTEGER
        );
        CREATE TABLE IF NOT EXISTS ohlcv_cache (
            id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT,
            ts_open INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL,
            UNIQUE(symbol, timeframe, ts_open)
        );
    """)
    conn.commit()
    conn.close()


def _stub_ok(**kwargs: Any) -> dict[str, Any]:
    output_dir = Path(kwargs["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "stub.json"
    out.write_text("{}", encoding="utf-8")
    return {"status": "ok", "output_file": str(out)}


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_preflight_check_candle_freshness_falha_se_candles_ausentes() -> None:
    """Preflight deve falhar se nao houver candles recentes no DB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "modelo2.db"
        _criar_db_minimo(db_path)
        # DB vazio - sem candles

        with patch("scripts.model2.go_live_preflight.run_up", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_execute", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_reconcile", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_dashboard", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_healthcheck", side_effect=lambda **kw: _stub_ok(**kw)):

            resultado = run_go_live_preflight(
                db_path=str(db_path),
                output_dir=tmpdir,
                check_candle_freshness=True,
                candle_max_age_minutes=60,
            )

        assert resultado["candle_freshness_check"]["passed"] is False


def test_preflight_check_treino_falha_se_checkpoint_ausente() -> None:
    """Preflight deve falhar se nao existir checkpoint de treino RL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "modelo2.db"
        _criar_db_minimo(db_path)
        checkpoints_dir = Path(tmpdir) / "checkpoints"
        checkpoints_dir.mkdir()
        # Sem checkpoints

        with patch("scripts.model2.go_live_preflight.run_up", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_execute", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_reconcile", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_dashboard", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_healthcheck", side_effect=lambda **kw: _stub_ok(**kw)):

            resultado = run_go_live_preflight(
                db_path=str(db_path),
                output_dir=tmpdir,
                check_train_checkpoint=True,
                checkpoints_dir=str(checkpoints_dir),
            )

        assert resultado["train_checkpoint_check"]["passed"] is False


def test_preflight_check_episodio_falha_se_minimo_nao_atingido() -> None:
    """Preflight deve falhar se episodios de treino < minimo exigido."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "modelo2.db"
        _criar_db_minimo(db_path)
        checkpoints_dir = Path(tmpdir) / "checkpoints"
        checkpoints_dir.mkdir()
        # Checkpoint com poucos episodios
        chk = checkpoints_dir / "ppo_step_000100_2026-01-01T000000.pt"
        chk.write_bytes(b"fake")

        with patch("scripts.model2.go_live_preflight.run_up", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_execute", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_reconcile", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_dashboard", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_healthcheck", side_effect=lambda **kw: _stub_ok(**kw)):

            resultado = run_go_live_preflight(
                db_path=str(db_path),
                output_dir=tmpdir,
                check_train_episodes=True,
                min_train_steps=10_000,
                checkpoints_dir=str(checkpoints_dir),
            )

        assert resultado["train_episodes_check"]["passed"] is False


def test_preflight_todos_checks_ok_retorna_go() -> None:
    """Preflight com todos os checks OK deve retornar status go."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "modelo2.db"
        _criar_db_minimo(db_path)

        # Inserir candle recente
        conn = sqlite3.connect(str(db_path))
        import time
        ts_recente = int(time.time() * 1000) - 60_000  # 1 min atras
        conn.execute(
            "INSERT INTO ohlcv_cache (symbol, timeframe, ts_open, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?,?)",
            ("BTCUSDT", "4h", ts_recente, 97000.0, 98000.0, 96000.0, 97500.0, 100.0),
        )
        conn.commit()
        conn.close()

        checkpoints_dir = Path(tmpdir) / "checkpoints"
        checkpoints_dir.mkdir()
        chk = checkpoints_dir / "ppo_step_050000_2026-01-01T000000.pt"
        chk.write_bytes(b"fake")

        with patch("scripts.model2.go_live_preflight.run_up", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_execute", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_reconcile", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_dashboard", side_effect=lambda **kw: _stub_ok(**kw)), \
             patch("scripts.model2.go_live_preflight.run_live_healthcheck", side_effect=lambda **kw: _stub_ok(**kw)):

            resultado = run_go_live_preflight(
                db_path=str(db_path),
                output_dir=tmpdir,
                check_candle_freshness=True,
                candle_max_age_minutes=60,
                check_train_checkpoint=True,
                check_train_episodes=True,
                min_train_steps=10_000,
                checkpoints_dir=str(checkpoints_dir),
            )

        assert resultado["candle_freshness_check"]["passed"] is True
        assert resultado["train_checkpoint_check"]["passed"] is True
        assert resultado["train_episodes_check"]["passed"] is True
