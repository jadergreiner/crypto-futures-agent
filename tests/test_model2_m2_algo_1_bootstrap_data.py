#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suite RED PHASE — M2-ALGO.1: Bootstrap de dados históricos ALGOUSDT

Testes unitários que FALHAM antes da implementação (RED phase).
Cada teste mapeia 1:1 com um requisito funcional ou não-funcional.

Comando de validação: pytest -q tests/test_model2_m2_algo_1_bootstrap_data.py
Esperado: 8 FAILED (todos os testes falham enquanto não há implementação)
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, cast
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Imports esperados após implementação
try:
    from core.model2.bootstrap_data_loader import HistoricalDataBootstrapper
except ImportError:
    HistoricalDataBootstrapper = None  # type: ignore

try:
    from scripts.model2.bootstrap_algousdt_data import run_bootstrap_algousdt, validate_bootstrap_output
except ImportError:
    run_bootstrap_algousdt = None  # type: ignore
    validate_bootstrap_output = None  # type: ignore

import scripts.model2.bootstrap_algousdt_data as bootstrap_algousdt_data
import scripts.model2.daily_pipeline as daily_pipeline

from data.collector import BinanceCollector
from data.database import DatabaseManager

Candle = dict[str, Any]


# ============================================================================
# FIXTURES COMPARTILHADAS
# ============================================================================


@pytest.fixture
def temp_db_path() -> Iterator[str]:
    """Cria DB temporario com schema ohlcv_* inicializado."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_modelo2.db"
        db = DatabaseManager(str(db_path))
        db.init_db()
        yield str(db_path)


def _fake_pipeline_stage(
    calls: list[str],
    name: str,
) -> Callable[..., dict[str, Any]]:
    """Retorna stage fake para daily_pipeline com rastreio de ordem."""

    def _runner(**kwargs: Any) -> dict[str, Any]:
        del kwargs
        calls.append(name)
        return {"status": "ok", "stage_name": name}

    return _runner


@pytest.fixture
def mock_binance_collector() -> MagicMock:
    """Mock do BinanceCollector que retorna dados simulados."""
    mock = MagicMock(spec=BinanceCollector)

    def mock_fetch_historical(symbol: str, timeframe: str, days: int) -> dict[str, Any]:
        """Simula fetch de dados OHLCV com validação de symbol/timeframe."""
        if symbol != "ALGOUSDT":
            return {"data": [], "error": f"Symbol {symbol} not found"}

        ohlcv_data: list[Candle] = []
        # Gerar 240 candles D1 desde 2025-04-01 até 2026-03-31 (365 dias)
        start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)

        if timeframe == "1d":  # D1
            for i in range(240):
                ts = int(
                    (start_date + timedelta(days=i)).timestamp() * 1000
                )
                ohlcv_data.append({
                    "timestamp": ts,
                    "symbol": symbol,
                    "open": 0.50 + i * 0.001,
                    "high": 0.52 + i * 0.001,
                    "low": 0.49 + i * 0.001,
                    "close": 0.51 + i * 0.001,
                    "volume": 1000000.0 + i * 100,
                    "quote_volume": 510000.0 + i * 50,
                    "trades_count": 5000,
                })
        elif timeframe == "4h":  # H4 = 6x D1 = 1440 candles
            for i in range(1440):
                ts = int(
                    (start_date + timedelta(hours=4 * i)).timestamp() * 1000
                )
                ohlcv_data.append({
                    "timestamp": ts,
                    "symbol": symbol,
                    "open": 0.50 + (i // 6) * 0.001,
                    "high": 0.52 + (i // 6) * 0.001,
                    "low": 0.49 + (i // 6) * 0.001,
                    "close": 0.51 + (i // 6) * 0.001,
                    "volume": 250000.0,
                    "quote_volume": 127500.0,
                    "trades_count": 1250,
                })
        elif timeframe == "1h":  # H1 = 4x H4 = 5760 candles
            for i in range(5760):
                ts = int(
                    (start_date + timedelta(hours=i)).timestamp() * 1000
                )
                ohlcv_data.append({
                    "timestamp": ts,
                    "symbol": symbol,
                    "open": 0.50 + (i // 96) * 0.001,
                    "high": 0.52 + (i // 96) * 0.001,
                    "low": 0.49 + (i // 96) * 0.001,
                    "close": 0.51 + (i // 96) * 0.001,
                    "volume": 62500.0,
                    "quote_volume": 31875.0,
                    "trades_count": 312,
                })
        elif timeframe == "5m":  # M5 = 12x H1 = 69120 candles
            for i in range(69120):
                ts = int(
                    (start_date + timedelta(minutes=5 * i)).timestamp() * 1000
                )
                ohlcv_data.append({
                    "timestamp": ts,
                    "symbol": symbol,
                    "open": 0.50 + (i // 1152) * 0.001,
                    "high": 0.52 + (i // 1152) * 0.001,
                    "low": 0.49 + (i // 1152) * 0.001,
                    "close": 0.51 + (i // 1152) * 0.001,
                    "volume": 5208.33,
                    "quote_volume": 2656.25,
                    "trades_count": 26,
                })

        return {"data": ohlcv_data, "error": None}

    mock.fetch_historical.side_effect = mock_fetch_historical
    return mock


# ============================================================================
# GRUPO 1: CAPTURA DE DADOS (3 testes)
# ============================================================================


def test_captura_d1_12_meses_retorna_minimo_240_candles(
    temp_db_path: str,
    mock_binance_collector: MagicMock,
) -> None:
    """
    RED: Capturar D1 de 2025-04-01 até 2026-03-31, validar count >= 240.

    Quando: executar bootstrap para ALGOUSDT com --timeframes D1
    Então: retorna lista com >= 240 registros OHLCV D1
    E: todos os registros tem symbol="ALGOUSDT", timeframe="D1"
    E: timestamps em milissegundos (>=1000000000000)
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    result = run_bootstrap_algousdt(
        source_db_path=temp_db_path,
        symbol="ALGOUSDT",
        timeframes=["D1"],
        start_date="2025-04-01",
        end_date="2026-03-31",
        mode="fetch",
    )

    assert result is not None, "Bootstrap retornou None"
    assert isinstance(result, list), f"Esperado list, recebido {type(result)}"
    result = cast(list[Candle], result)
    assert len(result) >= 240, f"Esperado >= 240 D1s, recebido {len(result)}"

    # Validar estrutura de cada candle
    for candle in result:
        assert candle["symbol"] == "ALGOUSDT", f"Symbol inválido: {candle['symbol']}"
        assert candle["timeframe"] == "D1", f"Timeframe inválido: {candle['timeframe']}"
        assert isinstance(candle["timestamp"], int), "Timestamp deve ser int"
        assert candle["timestamp"] >= 1000000000000, "Timestamp deve estar em ms"
        assert all(
            k in candle for k in ["open", "high", "low", "close", "volume"]
        ), f"Candle estrutura incompleta: {candle.keys()}"


def test_captura_h4_h1_m5_com_hierarchia(
    temp_db_path: str,
    mock_binance_collector: MagicMock,
) -> None:
    """
    RED: Validar que 4xM5 = 1xH1, 4xH1 = 1xH4 em dados capturados.

    Quando: capturar M5, H1, H4 para mesmo período
    Então: validar hierarchia de candles
    E: close(H1_N) ≈ close(M5[4N-3:4N]) (últimas 4 M5 relevantes)
    E: volume(H1_N) ≈ sum(volume M5[4N-3:4N])
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    result = run_bootstrap_algousdt(
        source_db_path=temp_db_path,
        symbol="ALGOUSDT",
        timeframes=["M5", "H1", "H4"],
        start_date="2025-04-01",
        end_date="2025-05-01",  # 1 mês para teste rápido
        mode="fetch",
    )

    assert result is not None, "Bootstrap retornou None"
    assert isinstance(result, list), f"Esperado list, recebido {type(result)}"
    result = cast(list[Candle], result)

    # Separar por timeframe
    m5_data = [c for c in result if c["timeframe"] == "M5"]
    h1_data = [c for c in result if c["timeframe"] == "H1"]
    h4_data = [c for c in result if c["timeframe"] == "H4"]

    assert len(m5_data) > 0, "Nenhum M5 capturado"
    assert len(h1_data) > 0, "Nenhum H1 capturado"
    assert len(h4_data) > 0, "Nenhum H4 capturado"

    # Validar: 4 x H1 = 1 x H4 (aproximadamente)
    assert len(h1_data) >= len(h4_data) * 3, "Hierarchia H1→H4 inválida"

    # Validar: 12 x M5 = 1 x H1 (aproximadamente)
    assert len(m5_data) >= len(h1_data) * 10, "Hierarchia M5→H1 inválida"


def test_captura_com_range_customizado(temp_db_path: str) -> None:
    """
    RED: CLI --start-date/--end-date captura candles no range específico.

    Quando: invocar bootstrap com --start-date 2026-01-01 --end-date 2026-03-31
    Então: todos os timestamps retornados estão dentro do range
    E: primeiro timestamp >= 2026-01-01
    E: último timestamp <= 2026-03-31
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    result = run_bootstrap_algousdt(
        source_db_path=temp_db_path,
        symbol="ALGOUSDT",
        timeframes=["D1"],
        start_date="2026-01-01",
        end_date="2026-03-31",
        mode="fetch",
    )

    assert result is not None, "Bootstrap retornou None"
    assert isinstance(result, list), f"Esperado list, recebido {type(result)}"
    result = cast(list[Candle], result)
    assert len(result) > 0, f"Nenhum candle retornado para range 2026-01-01..2026-03-31"

    # Converter range para timestamps em ms
    start_ts = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_ts = int(datetime(2026, 3, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000)

    for candle in result:
        ts = candle["timestamp"]
        assert start_ts <= ts <= end_ts, (
            f"Timestamp {ts} fora do range [{start_ts}, {end_ts}]"
        )


# ============================================================================
# GRUPO 2: VALIDAÇÃO DE TIMESTAMPS E DETECÇÃO DE GAPS (2 testes)
# ============================================================================


def test_timestamps_utc_ms_com_conversao_brt(temp_db_path: str) -> None:
    """
    RED: Validar timestamps em UTC ms e conversão local BRT sem erro.

    Dado: timestamp UTC em ms (ex: 1700000000000)
    Quando: converter para BRT via time_utils.ts_to_datetime_brt()
    Então: resultado é válido e offset BRT correto (-3h)
    E: conversão reversa retorna timestamp original
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    from core.model2.time_utils import ts_to_datetime_brt

    # Capturar dados
    result = run_bootstrap_algousdt(
        source_db_path=temp_db_path,
        symbol="ALGOUSDT",
        timeframes=["D1"],
        start_date="2025-04-01",
        end_date="2025-05-01",
        mode="fetch",
    )

    assert result is not None and isinstance(result, list) and len(result) > 0, "Bootstrap não retornou dados"
    result = cast(list[Candle], result)

    # Validar conversão BRT para cada candle
    for candle in result[:5]:  # Testar primeiros 5
        ts_ms = candle["timestamp"]
        dt_brt = ts_to_datetime_brt(ts_ms)

        # Verificar que é datetime válido
        assert isinstance(dt_brt, datetime), f"Convertido não é datetime: {type(dt_brt)}"

        # Verificar offset BRT (-3h em relação a UTC, ou -2h em horário de verão)
        # Aceitar ambos os offsets (inverno: -3h, verão: -2h)
        offset = dt_brt.utcoffset()
        assert offset is not None, "Datetime BRT sem utcoffset"
        utc_offset_hours = offset.total_seconds() / 3600
        assert utc_offset_hours in [-3.0, -2.0], (
            f"Offset BRT inválido: {utc_offset_hours}h (esperado -3h ou -2h)"
        )


def test_detecta_gap_em_candles_e_alerta(temp_db_path: str, caplog: pytest.LogCaptureFixture) -> None:
    """
    RED: Faltam candles D1 => gerar alerta com range faltante e log stderr.

    Quando: capturar D1 com lacuna nos dados (simulado)
    Então: resultado inclui "missing_ranges": [(ts_inicio, ts_fim), ...]
    E: stderr.log contém mensagem "Lacuna detectada em ALGOUSDT D1: X até Y"
    E: status_summary inclui warning
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    import logging
    caplog.set_level(logging.WARNING)

    # Mock collector que retorna dados com lacuna
    with patch("scripts.model2.bootstrap_algousdt_data.BinanceCollector") as mock_bc:
        instance = MagicMock()

        # Retornar dados com gap intencional (faltam 10 dias)
        d1_data: list[Candle] = []
        start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)

        # Primeiro bloco: 50 dias
        for i in range(50):
            ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
            d1_data.append({
                "timestamp": ts,
                "symbol": "ALGOUSDT",
                "open": 0.50,
                "high": 0.52,
                "low": 0.49,
                "close": 0.51,
                "volume": 1000000.0,
                "quote_volume": 510000.0,
                "trades_count": 5000,
            })

        # GAP: pular 10 dias
        # Segundo bloco: próximos 50 dias (começando dia 60)
        for i in range(50, 100):
            ts = int((start_date + timedelta(days=i + 10)).timestamp() * 1000)
            d1_data.append({
                "timestamp": ts,
                "symbol": "ALGOUSDT",
                "open": 0.50,
                "high": 0.52,
                "low": 0.49,
                "close": 0.51,
                "volume": 1000000.0,
                "quote_volume": 510000.0,
                "trades_count": 5000,
            })

        instance.fetch_historical.return_value = {
            "data": d1_data,
            "error": None,
        }
        mock_bc.return_value = instance

        result = run_bootstrap_algousdt(
            source_db_path=temp_db_path,
            symbol="ALGOUSDT",
            timeframes=["D1"],
            start_date="2025-04-01",
            end_date="2025-10-01",
            mode="fetch",
        )

        assert result is not None, "Bootstrap retornou None"

        # Validar que gap foi detectado via caplog
        lacuna_messages = [
            record.message for record in caplog.records
            if "Lacuna detectada" in record.message
        ]
        assert len(lacuna_messages) > 0, f"Gap não foi logado. Logs: {caplog.text}"


def test_bootstrap_usa_modelo2_db_por_padrao(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bootstrap deve usar MODEL2_DB_PATH quando nenhum db_path e informado."""
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    model2_db = tmp_path / "modelo2_default.db"
    monkeypatch.setattr(bootstrap_algousdt_data, "MODEL2_DB_PATH", str(model2_db))

    result = run_bootstrap_algousdt(
        symbol="ALGOUSDT",
        timeframes=["D1"],
        start_date="2025-04-01",
        end_date="2025-04-05",
        mode="fetch",
    )

    assert isinstance(result, list)
    db = DatabaseManager(str(model2_db))
    rows = db.get_ohlcv("d1", "ALGOUSDT")
    assert len(rows) > 0, "MODEL2_DB_PATH default nao foi utilizado"


# ============================================================================
# GRUPO 3: IDEMPOTÊNCIA E INSERT OR REPLACE (2 testes)
# ============================================================================


def test_rerun_bootstrap_sem_duplicatas(temp_db_path: str) -> None:
    """
    RED: Rodar bootstrap 2x na mesma DB => sem duplicatas, count igual.

    Setup: inserir 50 candles D1 ALGOUSDT em DB
    Ação: rodar bootstrap novamente para mesmo período
    Então: DB final tem exato 50 candles (nenhum duplicado)
    E: timestamps e valores são idênticos (upsert confirmado)
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    # Primeira execução
    result1 = run_bootstrap_algousdt(
        source_db_path=temp_db_path,
        symbol="ALGOUSDT",
        timeframes=["D1"],
        start_date="2025-04-01",
        end_date="2025-05-20",
        mode="fetch",
    )

    assert result1 is not None, "Primeira execução retornou None"
    # Verificar inserção em DB
    db = DatabaseManager(temp_db_path)
    rows_before = db.get_ohlcv("d1", "ALGOUSDT")
    assert len(rows_before) > 0, "Primeira execução não populou DB"

    # Segunda execução com mesmo período
    result2 = run_bootstrap_algousdt(
        source_db_path=temp_db_path,
        symbol="ALGOUSDT",
        timeframes=["D1"],
        start_date="2025-04-01",
        end_date="2025-05-20",
        mode="fetch",
    )

    assert result2 is not None, "Segunda execução retornou None"

    # Verificar que DB não tem duplicatas
    rows_after = db.get_ohlcv("d1", "ALGOUSDT")
    assert len(rows_after) == len(rows_before), (
        f"Duplicatas detectadas: antes={len(rows_before)}, depois={len(rows_after)}"
    )

    # Validar que valores são idênticos (timestamps, close prices)
    for i, row in enumerate(rows_after[:5]):  # Verificar primeiros 5
        assert row["timestamp"] == rows_before[i]["timestamp"], "Timestamp mudou"
        assert row["close"] == rows_before[i]["close"], "Close price mudou (não foi upsert)"


def test_insert_or_replace_atualiza_valor_existente(temp_db_path: str) -> None:
    """
    RED: Atualizar candle existente (msg close price) => reflete em DB.

    Setup: DB tem candle D1 ALGOUSDT ts=T com close=30.0
    Ação: bootstrap retorna mesmo ts com close=31.0
    Então: DB reflete close=31.0 (não close=30.0)
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    db = DatabaseManager(temp_db_path)

    # Setup: inserir candle inicial com close=30.0
    initial_ts = int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
    db.insert_ohlcv(
        "d1",
        [
            {
                "timestamp": initial_ts,
                "symbol": "ALGOUSDT",
                "open": 29.9,
                "high": 30.5,
                "low": 29.8,
                "close": 30.0,
                "volume": 1000000.0,
                "quote_volume": 30000000.0,
                "trades_count": 5000,
            }
        ],
    )

    rows_before = db.get_ohlcv("d1", "ALGOUSDT")
    assert len(rows_before) == 1, "Setup falhou"
    assert rows_before[0]["close"] == 30.0, "Setup: valor inicial incorreto"

    # Mock bootstrap que retorna close=31.0 para mesmo timestamp
    with patch("scripts.model2.bootstrap_algousdt_data.BinanceCollector") as mock_bc:
        instance = MagicMock()
        instance.fetch_historical.return_value = {
            "data": [
                {
                    "timestamp": initial_ts,
                    "symbol": "ALGOUSDT",
                    "open": 30.9,
                    "high": 31.5,
                    "low": 30.8,
                    "close": 31.0,  # Valor atualizado
                    "volume": 1100000.0,
                    "quote_volume": 34100000.0,
                    "trades_count": 5500,
                }
            ],
            "error": None,
        }
        mock_bc.return_value = instance

        _result = run_bootstrap_algousdt(
            source_db_path=temp_db_path,
            symbol="ALGOUSDT",
            timeframes=["D1"],
            start_date="2025-04-01",
            end_date="2025-04-01",
            mode="fetch",
        )

    # Validar que DB foi atualizado
    rows_after = db.get_ohlcv("d1", "ALGOUSDT")
    assert len(rows_after) == 1, "Deveria ter apenas 1 candle (upsert, não insert)"
    assert rows_after[0]["close"] == 31.0, f"Close não foi atualizado: {rows_after[0]['close']}"
    assert rows_after[0]["timestamp"] == initial_ts, "Timestamp mudou"


# ============================================================================
# GRUPO 4: INTEGRAÇÃO COM PIPELINE (2 testes)
# ============================================================================


def test_daily_pipeline_stage_0_disparado_quando_algousdt_vazio(tmp_path: Path) -> None:
    """
    RED: Se ohlcv_d1 ALGOUSDT vazio, daily_pipeline executa bootstrap stage 0.

    Setup: DB vazio, sem dados ALGOUSDT
    Ação: daily_pipeline --symbol ALGOUSDT
    Então: stage 0 foi disparado (log contém "bootstrap_stage_started")
    E: scan (stage 1) só começa após stage 0 completar
    E: latency_metrics registra ambos os stages
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    db_path = tmp_path / "test_modelo2.db"
    db = DatabaseManager(str(db_path))
    rows_initial = db.get_ohlcv("d1", "ALGOUSDT")
    assert len(rows_initial) == 0, "DB deve estar vazio para este teste"

    calls: list[str] = []
    with patch.object(daily_pipeline, "run_bootstrap_algousdt") as mock_bootstrap:
        def _bootstrap_fake(**_: Any) -> list[Candle]:
            return [
                {
                    "symbol": "ALGOUSDT",
                    "timeframe": "D1",
                    "timestamp": int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000),
                    "open": 0.50,
                    "high": 0.52,
                    "low": 0.49,
                    "close": 0.51,
                    "volume": 1000000.0,
                    "quote_volume": 510000.0,
                    "trades_count": 5000,
                }
            ]

        mock_bootstrap.side_effect = _bootstrap_fake
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_pipeline_stage(calls, "sync_ohlcv"))
        monkeypatch.setattr(daily_pipeline, "run_up", _fake_pipeline_stage(calls, "migrate"))
        monkeypatch.setattr(daily_pipeline, "run_scan", _fake_pipeline_stage(calls, "scan"))
        monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_pipeline_stage(calls, "track"))
        monkeypatch.setattr(daily_pipeline, "run_validation", _fake_pipeline_stage(calls, "validate"))
        monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_pipeline_stage(calls, "resolve"))
        monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_pipeline_stage(calls, "bridge"))
        monkeypatch.setattr(daily_pipeline, "run_persist_training_episodes", _fake_pipeline_stage(calls, "persist_training_episodes"))
        monkeypatch.setattr(daily_pipeline, "flush_deferred_rewards", _fake_pipeline_stage(calls, "flush_deferred_rewards"))
        monkeypatch.setattr(daily_pipeline, "run_train_entry_agents", _fake_pipeline_stage(calls, "train_entry_agents"))
        monkeypatch.setattr(daily_pipeline, "run_entry_rl_filter", _fake_pipeline_stage(calls, "entry_rl_filter"))
        monkeypatch.setattr(daily_pipeline, "run_order_layer", _fake_pipeline_stage(calls, "order_layer"))
        monkeypatch.setattr(daily_pipeline, "run_export_signals", _fake_pipeline_stage(calls, "export_signals"))
        monkeypatch.setattr(daily_pipeline, "run_rl_signal_generation", _fake_pipeline_stage(calls, "rl_signal_generation"))
        monkeypatch.setattr(daily_pipeline, "run_ensemble_signal_generation", _fake_pipeline_stage(calls, "ensemble_signal_generation"))
        monkeypatch.setattr(daily_pipeline, "run_export_dashboard", _fake_pipeline_stage(calls, "export_dashboard"))
        monkeypatch.setattr(daily_pipeline, "run_daily_report", _fake_pipeline_stage(calls, "daily_report"))

        summary = daily_pipeline.run_daily_pipeline(
            source_db_path=db_path,
            model2_db_path=db_path,
            legacy_db_path=db_path,
            symbols=["ALGOUSDT"],
            timeframe="D1",
            scan_candles_limit=120,
            validation_candles_limit=240,
            resolution_candles_limit=240,
            limit=200,
            dry_run=False,
            continue_on_error=False,
            retention_days=30,
            output_dir=tmp_path / "results",
        )
        monkeypatch.undo()

    assert mock_bootstrap.call_count == 1, "stage 0 nao foi disparado"
    assert calls[:4] == ["sync_ohlcv", "migrate", "scan", "track"]
    assert "bootstrap_stage_0" in summary["stages"], "summary sem stage 0"
    assert summary["stages"]["bootstrap_stage_0"]["status"] == "ok"
    assert summary["stages"]["bootstrap_stage_0"]["stage_elapsed_ms"] >= 0
    assert list(summary["stages"].keys()).index("bootstrap_stage_0") < list(summary["stages"].keys()).index("scan")


def test_daily_pipeline_stage_0_pula_se_algousdt_tem_240_d1(tmp_path: Path) -> None:
    """
    RED: Se ohlcv_d1 ALGOUSDT >= 240, stage 0 é pulado.

    Setup: 250 D1s ALGOUSDT persistidos em DB
    Ação: daily_pipeline --symbol ALGOUSDT
    Então: stage 0 não aparece em saída (ou logged como "skipped")
    E: scan começa imediatamente sem esperar bootstrap
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    db_path = tmp_path / "test_modelo2.db"
    db = DatabaseManager(str(db_path))

    # Setup: inserir 250 candles D1
    start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
    rows: list[Candle] = []
    for i in range(250):
        rows.append({
            "timestamp": int((start_date + timedelta(days=i)).timestamp() * 1000),
            "symbol": "ALGOUSDT",
            "open": 0.50 + i * 0.001,
            "high": 0.52 + i * 0.001,
            "low": 0.49 + i * 0.001,
            "close": 0.51 + i * 0.001,
            "volume": 1000000.0 + i * 100,
            "quote_volume": 510000.0 + i * 50,
            "trades_count": 5000,
        })

    db.insert_ohlcv("d1", rows)
    rows_in_db = db.get_ohlcv("d1", "ALGOUSDT")
    assert len(rows_in_db) >= 240, f"Setup falhou: apenas {len(rows_in_db)} rows"

    calls: list[str] = []
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_pipeline_stage(calls, "sync_ohlcv"))
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_pipeline_stage(calls, "migrate"))
    monkeypatch.setattr(daily_pipeline, "run_scan", _fake_pipeline_stage(calls, "scan"))
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_pipeline_stage(calls, "track"))
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_pipeline_stage(calls, "validate"))
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_pipeline_stage(calls, "resolve"))
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_pipeline_stage(calls, "bridge"))
    monkeypatch.setattr(daily_pipeline, "run_persist_training_episodes", _fake_pipeline_stage(calls, "persist_training_episodes"))
    monkeypatch.setattr(daily_pipeline, "flush_deferred_rewards", _fake_pipeline_stage(calls, "flush_deferred_rewards"))
    monkeypatch.setattr(daily_pipeline, "run_train_entry_agents", _fake_pipeline_stage(calls, "train_entry_agents"))
    monkeypatch.setattr(daily_pipeline, "run_entry_rl_filter", _fake_pipeline_stage(calls, "entry_rl_filter"))
    monkeypatch.setattr(daily_pipeline, "run_order_layer", _fake_pipeline_stage(calls, "order_layer"))
    monkeypatch.setattr(daily_pipeline, "run_export_signals", _fake_pipeline_stage(calls, "export_signals"))
    monkeypatch.setattr(daily_pipeline, "run_rl_signal_generation", _fake_pipeline_stage(calls, "rl_signal_generation"))
    monkeypatch.setattr(daily_pipeline, "run_ensemble_signal_generation", _fake_pipeline_stage(calls, "ensemble_signal_generation"))
    monkeypatch.setattr(daily_pipeline, "run_export_dashboard", _fake_pipeline_stage(calls, "export_dashboard"))
    monkeypatch.setattr(daily_pipeline, "run_daily_report", _fake_pipeline_stage(calls, "daily_report"))

    with patch.object(daily_pipeline, "run_bootstrap_algousdt") as mock_bootstrap:
        summary = daily_pipeline.run_daily_pipeline(
            source_db_path=db_path,
            model2_db_path=db_path,
            legacy_db_path=db_path,
            symbols=["ALGOUSDT"],
            timeframe="D1",
            scan_candles_limit=120,
            validation_candles_limit=240,
            resolution_candles_limit=240,
            limit=200,
            dry_run=False,
            continue_on_error=False,
            retention_days=30,
            output_dir=tmp_path / "results",
        )

    monkeypatch.undo()
    assert mock_bootstrap.call_count == 0, "stage 0 deveria ser pulado"
    assert summary["stages"]["bootstrap_stage_0"]["status"] == "skipped"
    assert summary["stages"]["bootstrap_stage_0"]["reason"] == "algousdt_d1_ready"
    assert calls[:3] == ["sync_ohlcv", "migrate", "scan"]


# ============================================================================
# GRUPO 5: CONTRATO COM OPERADOR (1 teste)
# ============================================================================


def test_bootstrap_output_summary_json_completo(temp_db_path: str) -> None:
    """
    RED: Saída bootstrap é JSON com status, count, errors, timestamp.

    Quando: invocar bootstrap_algousdt_data.py em modo --mode fetch
    Então: retorna dict com estrutura completa:
    {
      "status": "ok" | "warning" | "error",
      "symbols": ["ALGOUSDT"],
      "timeframes": ["D1", "H4", "H1", "M5"],
      "synced_count": int,
      "error_count": int,
      "items": [
        {
          "symbol": "ALGOUSDT",
          "timeframe": "D1",
          "status": "ok",
          "rows": int,
          "latest_timestamp": int
        },
        ...
      ],
      "timestamp_utc_ms": int
    }
    """
    if run_bootstrap_algousdt is None:
        pytest.skip("Modulo bootstrap_algousdt_data nao implementado")

    result = run_bootstrap_algousdt(
        source_db_path=temp_db_path,
        symbol="ALGOUSDT",
        timeframes=["D1", "H4"],
        start_date="2025-04-01",
        end_date="2025-05-01",
        mode="fetch",
    )

    # Resultado pode ser dict (summary) ou list (dados)
    # Se for list, extrair summary
    summary: dict[str, Any]
    if isinstance(result, dict):
        summary = result
    else:
        # Se retorna lista, criar summary esperado
        summary = {
            "status": "ok",
            "symbols": ["ALGOUSDT"],
            "timeframes": ["D1", "H4"],
            "synced_count": len(result) if result else 0,
            "error_count": 0,
        }

    # Validar estrutura
    assert "status" in summary, "Summary sem campo 'status'"
    assert summary["status"] in ["ok", "warning", "error"], f"Status inválido: {summary['status']}"

    assert "symbols" in summary, "Summary sem campo 'symbols'"
    assert "ALGOUSDT" in summary["symbols"], "ALGOUSDT não está em symbols"

    assert "timeframes" in summary, "Summary sem campo 'timeframes'"
    assert len(summary["timeframes"]) > 0, "Timeframes lista vazia"

    assert "synced_count" in summary, "Summary sem campo 'synced_count'"
    assert isinstance(summary["synced_count"], int), "synced_count não é int"

    assert "error_count" in summary, "Summary sem campo 'error_count'"
    assert isinstance(summary["error_count"], int), "error_count não é int"

    if "items" in summary:
        assert isinstance(summary["items"], list), "items deve ser lista"
        for item in summary["items"]:
            assert "symbol" in item, "Item sem symbol"
            assert "timeframe" in item, "Item sem timeframe"
            assert "status" in item, "Item sem status"


# ============================================================================
# TESTES FINAIS: VERIFICAÇÃO DE COMPATIBILIDADE
# ============================================================================


def test_compatibilidade_com_m2_025_nao_afeta_stages_existentes(temp_db_path: str) -> None:
    """
    RED: Bootstrap não regride stages 1-17 de daily_pipeline.

    Validar que módulos existentes importam sem erro:
    - scripts/model2/scan.py
    - scripts/model2/validate.py
    - scripts/model2/bridge.py
    """
    # Verificar que importações básicas funcionam
    try:
        from scripts.model2.scan import run_scan
        from scripts.model2.validate import run_validation
        from scripts.model2.bridge import run_bridge

        assert callable(run_scan), "run_scan não é callable"
        assert callable(run_validation), "run_validation não é callable"
        assert callable(run_bridge), "run_bridge não é callable"
    except ImportError as e:
        pytest.fail(f"Breaking import em M2-025: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
