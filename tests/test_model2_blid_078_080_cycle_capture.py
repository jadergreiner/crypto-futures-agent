"""Suite RED para BLID-078 e BLID-080.

Valida o pacote minimo de captura do ciclo M2:
1. Candles reais nao podem aparecer como contexto fresco quando ausentes.
2. Episodios persistidos precisam refletir no status operacional.
3. O resumo de persistencia precisa expor metadados suficientes para
   integracao com o status por simbolo.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

import core.model2.live_service as live_service_module
from core.model2.cycle_report import SymbolReport, format_symbol_report
from core.model2.model_decision import ModelDecision
from scripts.model2.persist_training_episodes import run_persist_training_episodes


ServiceFactory = Callable[[Path], live_service_module.Model2LiveExecutionService]


def _criar_decisao(symbol: str = "BTCUSDT") -> ModelDecision:
    return ModelDecision(
        action="OPEN_LONG",
        confidence=0.81,
        size_fraction=0.25,
        sl_target=49000.0,
        tp_target=52000.0,
        reason_code="teste_red",
        decision_timestamp=1_742_668_800_000,
        symbol=symbol,
        model_version="qa-red",
        metadata={},
    )


def _criar_source_db(path: Path, *, with_candle: bool = True) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE ohlcv_h4 (
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL
            )
            """
        )
        if with_candle:
            conn.execute(
                """
                INSERT INTO ohlcv_h4 (
                    symbol, timestamp, open, high, low, close, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("BTCUSDT", 1_742_668_800_000, 50000.0, 51000.0,
                 49500.0, 50500.0, 123.0),
            )
        conn.commit()


def _criar_model2_db_com_execucao(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE opportunities (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE technical_signals (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                signal_timestamp INTEGER,
                status TEXT DEFAULT 'CREATED'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE signal_executions (
                id INTEGER PRIMARY KEY,
                technical_signal_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_side TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                entry_filled_at INTEGER,
                exited_at INTEGER,
                exit_price REAL,
                payload_json TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO technical_signals (
                id, symbol, timeframe, entry_price, stop_loss,
                take_profit, signal_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "BTCUSDT", "H4", 50000.0, 49000.0, 52000.0,
             1_742_668_700_000),
        )
        conn.execute(
            """
            INSERT INTO signal_executions (
                id, technical_signal_id, symbol, timeframe, signal_side,
                status, updated_at, entry_filled_at, exited_at, exit_price,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                10,
                1,
                "BTCUSDT",
                "H4",
                "LONG",
                "CLOSED",
                1_742_668_900_000,
                1_742_668_800_000,
                1_742_669_000_000,
                52500.0,
                "{}",
            ),
        )
        conn.commit()


def _criar_training_episodes_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE training_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_key TEXT NOT NULL UNIQUE,
                cycle_run_id TEXT NOT NULL,
                execution_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                status TEXT NOT NULL,
                event_timestamp INTEGER NOT NULL,
                label TEXT NOT NULL,
                reward_proxy REAL,
                features_json TEXT NOT NULL,
                target_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, features_json,
                target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "exec:10:1742668900000",
                "20260322T181820Z",
                10,
                "BTCUSDT",
                "H4",
                "CLOSED",
                1_742_668_900_000,
                "win",
                0.25,
                "{}",
                "{}",
                1_742_668_905_000,
            ),
        )
        conn.commit()


@pytest.fixture  # type: ignore[misc]
def service_factory(monkeypatch: pytest.MonkeyPatch) -> ServiceFactory:
    class _FakeLoader:
        checkpoint_timestamp = None

    class _FakeInferenceService:
        model_version = "qa-red"

    class _FakeAlerts:
        def publish_critical(self, event_type: str, details: dict[str, Any]) -> None:
            return None

    monkeypatch.setattr(live_service_module, "RLModelLoader", _FakeLoader)
    monkeypatch.setattr(
        live_service_module,
        "ModelInferenceService",
        _FakeInferenceService,
    )
    monkeypatch.setattr(
        live_service_module,
        "Model2LiveAlertPublisher",
        _FakeAlerts,
    )

    def _factory(db_path: Path) -> live_service_module.Model2LiveExecutionService:
        config = SimpleNamespace(
            execution_mode="shadow",
            live_symbols=("BTCUSDT",),
            authorized_symbols=("BTCUSDT",),
            short_only=False,
            max_daily_entries=10,
            max_margin_per_position_usd=100.0,
            max_signal_age_ms=60_000,
            symbol_cooldown_ms=0,
            funding_rate_max_for_short=0.05,
            leverage=2,
            db_path=str(db_path),
        )
        return live_service_module.Model2LiveExecutionService(
            repository=Mock(),
            config=config,
            exchange=None,
            alert_publisher=_FakeAlerts(),
        )

    return _factory


def test_log_operational_status_sem_candles_marca_contexto_nao_fresco(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    service_factory: ServiceFactory,
) -> None:
    """Sem candles reais, o status nao pode marcar contexto como fresco."""
    db_path = tmp_path / "modelo2.db"
    _criar_training_episodes_db(db_path)
    service = service_factory(db_path)
    captured: dict[str, SymbolReport] = {}

    monkeypatch.setattr(
        live_service_module,
        "collect_training_info",
        lambda _db: ("2026-03-22 18:00:00", 3),
    )
    monkeypatch.setattr(
        live_service_module,
        "collect_position_info",
        lambda _symbol, exchange_client=None: {
            "has_position": False,
            "position_side": "",
            "position_qty": 0.0,
            "position_entry_price": 0.0,
            "position_mark_price": 0.0,
            "position_pnl_pct": 0.0,
            "position_pnl_usd": 0.0,
        },
    )

    def _capture(report: SymbolReport) -> str:
        captured["report"] = report
        return "report"

    monkeypatch.setattr(live_service_module, "format_symbol_report", _capture)

    service._log_operational_status(
        symbol="BTCUSDT",
        decision=_criar_decisao(),
        candles_count=0,
        last_candle_time="",
    )

    assert "report" in captured
    assert captured["report"].decision_fresh is False


def test_log_operational_status_com_episodio_persistido_reflete_reward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    service_factory: ServiceFactory,
) -> None:
    """Status operacional deve refletir o ultimo episodio persistido do simbolo."""
    db_path = tmp_path / "modelo2.db"
    _criar_training_episodes_db(db_path)
    service = service_factory(db_path)
    captured: dict[str, SymbolReport] = {}

    monkeypatch.setattr(
        live_service_module,
        "collect_training_info",
        lambda _db: ("2026-03-22 18:00:00", 1),
    )
    monkeypatch.setattr(
        live_service_module,
        "collect_position_info",
        lambda _symbol, exchange_client=None: {
            "has_position": False,
            "position_side": "",
            "position_qty": 0.0,
            "position_entry_price": 0.0,
            "position_mark_price": 0.0,
            "position_pnl_pct": 0.0,
            "position_pnl_usd": 0.0,
        },
    )

    def _capture(report: SymbolReport) -> str:
        captured["report"] = report
        return "report"

    monkeypatch.setattr(live_service_module, "format_symbol_report", _capture)

    service._log_operational_status(
        symbol="BTCUSDT",
        decision=_criar_decisao(),
        candles_count=12,
        last_candle_time="2026-03-22 18:00 UTC",
    )

    assert "report" in captured
    assert captured["report"].episode_persisted is True
    assert captured["report"].episode_id == 1
    assert captured["report"].reward == pytest.approx(0.25)


def test_run_persist_training_episodes_expoe_snapshot_por_simbolo(
    tmp_path: Path,
) -> None:
    """Resumo deve expor ultimo episodio de execucao para status por simbolo."""
    source_db = tmp_path / "source.db"
    model2_db = tmp_path / "modelo2.db"
    output_dir = tmp_path / "runtime"
    _criar_source_db(source_db)
    _criar_model2_db_com_execucao(model2_db)

    summary = run_persist_training_episodes(
        source_db_path=source_db,
        model2_db_path=model2_db,
        symbols=["BTCUSDT"],
        timeframe="H4",
        output_dir=output_dir,
    )

    snapshot = summary["latest_execution_episode_by_symbol"]["BTCUSDT"]
    assert snapshot["episode_key"].startswith("exec:")
    assert snapshot["reward_proxy"] == pytest.approx(0.05)
    assert snapshot["label"] == "win"


def test_format_symbol_report_sem_contexto_fresco_exibe_alerta() -> None:
    """Relatorio deve marcar ausencia de contexto fresco com alerta visual."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-22 18:18:20 BRT",
        candles_count=0,
        last_candle_time="",
        decision="OPEN_LONG",
        confidence=0.81,
        decision_fresh=False,
    )

    output = format_symbol_report(report)

    assert "Candles  : 0 capturados (ultimo: N/A) ⚠" in output


def test_format_symbol_report_com_episodio_persistido_exibe_reward() -> None:
    """Relatorio deve exibir id e reward quando episodio estiver persistido."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-22 18:18:20 BRT",
        candles_count=10,
        last_candle_time="2026-03-22 18:00 UTC",
        decision="OPEN_LONG",
        confidence=0.81,
        decision_fresh=True,
        episode_id=7,
        episode_persisted=True,
        reward=0.25,
    )

    output = format_symbol_report(report)

    assert "Episodio : #7 persistido | reward: +0.2500" in output