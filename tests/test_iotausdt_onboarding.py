"""Testes de onboarding do IOTAUSDT no ciclo RL Model 2.0.

Valida que o simbolo esta corretamente configurado em config/symbols.py,
que o playbook existe e funciona, que propagou para AUTHORIZED_SYMBOLS
e que o bootstrap stage esta registrado no daily_pipeline.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from config.symbols import ALL_SYMBOLS, SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS
from playbooks import IOTAPlaybook
import scripts.model2.daily_pipeline as daily_pipeline


# ---------------------------------------------------------------------------
# 1. Configuracao em config/symbols.py
# ---------------------------------------------------------------------------

def test_iotausdt_em_symbols() -> None:
    assert "IOTAUSDT" in SYMBOLS, "IOTAUSDT deve estar em SYMBOLS"


def test_iotausdt_campos_obrigatorios() -> None:
    cfg = SYMBOLS["IOTAUSDT"]
    for campo in ("papel", "ciclo_proprio", "correlacao_btc",
                  "beta_estimado", "classificacao", "caracteristicas"):
        assert campo in cfg, f"campo '{campo}' ausente em SYMBOLS['IOTAUSDT']"


def test_iotausdt_em_all_symbols() -> None:
    assert "IOTAUSDT" in ALL_SYMBOLS, (
        "IOTAUSDT deve propagar automaticamente para ALL_SYMBOLS"
    )


def test_iotausdt_classificacao() -> None:
    assert SYMBOLS["IOTAUSDT"]["classificacao"] == "mid_cap_l1"


def test_iotausdt_beta_range() -> None:
    beta = SYMBOLS["IOTAUSDT"]["beta_estimado"]
    assert 1.5 <= beta <= 3.5, f"beta {beta} fora do range esperado [1.5, 3.5]"


def test_iotausdt_correlacao_btc_range() -> None:
    corr = SYMBOLS["IOTAUSDT"]["correlacao_btc"]
    low, high = corr[0], corr[1]
    assert 0.4 <= low <= 0.9, f"correlacao_btc low={low} fora do range"
    assert low < high, "correlacao_btc: low deve ser menor que high"


def test_iotausdt_caracteristicas_iot() -> None:
    chars = SYMBOLS["IOTAUSDT"]["caracteristicas"]
    assert "iot" in chars, "IOTAUSDT deve ter 'iot' em caracteristicas"
    assert "layer1" in chars, "IOTAUSDT deve ter 'layer1' em caracteristicas"


# ---------------------------------------------------------------------------
# 2. Propagacao para AUTHORIZED_SYMBOLS
# ---------------------------------------------------------------------------

def test_iotausdt_em_authorized_symbols() -> None:
    assert "IOTAUSDT" in AUTHORIZED_SYMBOLS, (
        "IOTAUSDT deve propagar para AUTHORIZED_SYMBOLS"
    )


# ---------------------------------------------------------------------------
# 3. Playbook IOTAPlaybook
# ---------------------------------------------------------------------------

def test_iota_playbook_inicializa() -> None:
    pb = IOTAPlaybook()
    assert pb.symbol == "IOTAUSDT"


def test_iota_playbook_confluence_sem_contexto() -> None:
    pb = IOTAPlaybook()
    ajustes = pb.get_confluence_adjustments({})
    assert isinstance(ajustes, dict)


def test_iota_playbook_confluence_com_iot_narrative() -> None:
    pb = IOTAPlaybook()
    ajustes = pb.get_confluence_adjustments({"iot_narrative": True})
    assert "iot_narrative" in ajustes
    assert ajustes["iot_narrative"] > 0


def test_iota_playbook_confluence_risk_off_penaliza() -> None:
    pb = IOTAPlaybook()
    ajustes = pb.get_confluence_adjustments({"market_regime": "RISK_OFF"})
    assert "risk_off_penalty" in ajustes
    assert ajustes["risk_off_penalty"] < 0


def test_iota_playbook_risco_defaults() -> None:
    pb = IOTAPlaybook()
    ajustes = pb.get_risk_adjustments({})
    assert "position_size_multiplier" in ajustes
    assert "stop_multiplier" in ajustes
    assert 0.0 < ajustes["position_size_multiplier"] <= 1.0


def test_iota_playbook_risco_alta_volatilidade() -> None:
    pb = IOTAPlaybook()
    ajustes_normal = pb.get_risk_adjustments({"atr_pct": 3.0})
    ajustes_alta_vol = pb.get_risk_adjustments({"atr_pct": 7.0})
    assert ajustes_alta_vol["position_size_multiplier"] < ajustes_normal[
        "position_size_multiplier"
    ], "alta volatilidade deve reduzir position_size_multiplier"


def test_iota_playbook_cycle_phase_retorna_string() -> None:
    pb = IOTAPlaybook()
    fase = pb.get_cycle_phase({})
    assert isinstance(fase, str) and len(fase) > 0


def test_iota_playbook_cycle_phase_iot_narrativa() -> None:
    pb = IOTAPlaybook()
    fase = pb.get_cycle_phase(
        {"market_narrative": "IOT", "d1_bias": "LONG"}
    )
    assert "NARRATIVA" in fase or "IOTA" in fase


def test_iota_playbook_should_trade_neutro_retorna_false() -> None:
    pb = IOTAPlaybook()
    assert pb.should_trade("RISK_ON", "NEUTRO") is False


def test_iota_playbook_should_trade_risk_on_long_retorna_true() -> None:
    pb = IOTAPlaybook()
    assert pb.should_trade("RISK_ON", "LONG") is True


# ---------------------------------------------------------------------------
# 4. Bootstrap stage no daily_pipeline
# ---------------------------------------------------------------------------

def test_bootstrap_iotausdt_registrado_no_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que bootstrap_iotausdt aparece nos stages quando IOTAUSDT
    esta na lista de simbolos."""
    source_db = tmp_path / "db" / "crypto_agent.db"
    model2_db = tmp_path / "db" / "modelo2.db"
    legacy_db = tmp_path / "db" / "legacy.db"
    output_dir = tmp_path / "results"
    source_db.parent.mkdir(parents=True, exist_ok=True)

    from data.database import DatabaseManager
    DatabaseManager(str(source_db))

    stages_called: list[str] = []

    def _fake_stage(name: str):  # type: ignore[no-untyped-def]
        def _runner(**kwargs: Any) -> dict[str, Any]:
            stages_called.append(name)
            return {"status": "ok", "stage": name}
        return _runner

    def _fake_sync(**kwargs: Any) -> dict[str, Any]:
        stages_called.append("sync_ohlcv")
        DatabaseManager(str(kwargs["source_db_path"]))
        return {"status": "ok", "stage": "sync_ohlcv"}

    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_sync)
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage("migrate"))
    monkeypatch.setattr(
        daily_pipeline, "_run_bootstrap_iotausdt", _fake_stage("bootstrap_iotausdt")
    )
    monkeypatch.setattr(daily_pipeline, "run_scan", _fake_stage("scan"))
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage("track"))
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage("validate"))
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage("resolve"))
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage("bridge"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_persist_training_episodes",
        _fake_stage("persist_training_episodes"),
    )
    monkeypatch.setattr(
        daily_pipeline,
        "flush_deferred_rewards",
        _fake_stage("flush_deferred_rewards"),
    )
    monkeypatch.setattr(
        daily_pipeline, "run_train_entry_agents", _fake_stage("train_entry_agents")
    )
    monkeypatch.setattr(
        daily_pipeline, "run_entry_rl_filter", _fake_stage("entry_rl_filter")
    )
    monkeypatch.setattr(
        daily_pipeline, "run_order_layer", _fake_stage("order_layer")
    )
    monkeypatch.setattr(
        daily_pipeline, "run_export_signals", _fake_stage("export_signals")
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_rl_signal_generation",
        _fake_stage("rl_signal_generation"),
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_ensemble_signal_generation",
        _fake_stage("ensemble_signal_generation"),
    )
    monkeypatch.setattr(
        daily_pipeline, "run_export_dashboard", _fake_stage("export_dashboard")
    )

    summary = daily_pipeline.run_daily_pipeline(
        source_db_path=source_db,
        model2_db_path=model2_db,
        legacy_db_path=legacy_db,
        symbols=["IOTAUSDT"],
        timeframe="M5",
        scan_candles_limit=30,
        validation_candles_limit=30,
        resolution_candles_limit=30,
        limit=20,
        dry_run=False,
        continue_on_error=False,
        retention_days=30,
        output_dir=output_dir,
    )

    assert summary["status"] == "ok", (
        f"pipeline falhou: {summary.get('stage_errors')}"
    )
    assert "bootstrap_iotausdt" in stages_called, (
        "stage 'bootstrap_iotausdt' deve ser executado quando IOTAUSDT "
        "esta na lista de simbolos"
    )


def test_bootstrap_iotausdt_nao_executado_sem_simbolo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bootstrap_iotausdt nao deve ser executado quando IOTAUSDT nao
    esta na lista de simbolos."""
    source_db = tmp_path / "db" / "crypto_agent.db"
    model2_db = tmp_path / "db" / "modelo2.db"
    legacy_db = tmp_path / "db" / "legacy.db"
    output_dir = tmp_path / "results"
    source_db.parent.mkdir(parents=True, exist_ok=True)

    from data.database import DatabaseManager
    DatabaseManager(str(source_db))

    stages_called: list[str] = []

    def _fake_stage(name: str):  # type: ignore[no-untyped-def]
        def _runner(**kwargs: Any) -> dict[str, Any]:
            stages_called.append(name)
            return {"status": "ok", "stage": name}
        return _runner

    def _fake_sync(**kwargs: Any) -> dict[str, Any]:
        stages_called.append("sync_ohlcv")
        DatabaseManager(str(kwargs["source_db_path"]))
        return {"status": "ok", "stage": "sync_ohlcv"}

    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_sync)
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage("migrate"))
    monkeypatch.setattr(daily_pipeline, "run_scan", _fake_stage("scan"))
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage("track"))
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage("validate"))
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage("resolve"))
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage("bridge"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_persist_training_episodes",
        _fake_stage("persist_training_episodes"),
    )
    monkeypatch.setattr(
        daily_pipeline,
        "flush_deferred_rewards",
        _fake_stage("flush_deferred_rewards"),
    )
    monkeypatch.setattr(
        daily_pipeline, "run_train_entry_agents", _fake_stage("train_entry_agents")
    )
    monkeypatch.setattr(
        daily_pipeline, "run_entry_rl_filter", _fake_stage("entry_rl_filter")
    )
    monkeypatch.setattr(
        daily_pipeline, "run_order_layer", _fake_stage("order_layer")
    )
    monkeypatch.setattr(
        daily_pipeline, "run_export_signals", _fake_stage("export_signals")
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_rl_signal_generation",
        _fake_stage("rl_signal_generation"),
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_ensemble_signal_generation",
        _fake_stage("ensemble_signal_generation"),
    )
    monkeypatch.setattr(
        daily_pipeline, "run_export_dashboard", _fake_stage("export_dashboard")
    )

    summary = daily_pipeline.run_daily_pipeline(
        source_db_path=source_db,
        model2_db_path=model2_db,
        legacy_db_path=legacy_db,
        symbols=["BTCUSDT"],
        timeframe="M5",
        scan_candles_limit=30,
        validation_candles_limit=30,
        resolution_candles_limit=30,
        limit=20,
        dry_run=False,
        continue_on_error=False,
        retention_days=30,
        output_dir=output_dir,
    )

    assert "bootstrap_iotausdt" not in stages_called, (
        "bootstrap_iotausdt nao deve rodar quando IOTAUSDT nao esta "
        "na lista de simbolos"
    )


# ---------------------------------------------------------------------------
# 5. _run_bootstrap_iotausdt skipa quando dados suficientes existem
# ---------------------------------------------------------------------------

def test_run_bootstrap_iotausdt_skipa_quando_d1_suficiente(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_run_bootstrap_iotausdt deve retornar 'skipped' quando ja existem
    240+ candles D1 no banco, sem chamar run_bootstrap_algousdt."""
    from data.database import DatabaseManager

    source_db = tmp_path / "source.db"
    model2_db = tmp_path / "model2.db"

    # Criar 241 candles D1 fake para IOTAUSDT
    for path in (source_db, model2_db):
        db = DatabaseManager(str(path))
        db.init_db()
        candles = [
            {
                "timestamp": 1700000000000 + i * 86400000,
                "symbol": "IOTAUSDT",
                "open": 0.2,
                "high": 0.21,
                "low": 0.19,
                "close": 0.205,
                "volume": 1000.0,
                "quote_volume": 200.0,
                "trades_count": 10,
            }
            for i in range(241)
        ]
        db.insert_ohlcv("d1", candles)

    bootstrap_called = False

    def _fake_bootstrap(**kwargs: Any) -> list[dict[str, Any]]:
        nonlocal bootstrap_called
        bootstrap_called = True
        return []

    monkeypatch.setattr(daily_pipeline, "run_bootstrap_algousdt", _fake_bootstrap)

    result = daily_pipeline._run_bootstrap_iotausdt(
        source_db_path=source_db,
        model2_db_path=model2_db,
        symbols=["IOTAUSDT"],
        output_dir=tmp_path,
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "iotausdt_d1_ready"
    assert not bootstrap_called, (
        "run_bootstrap_algousdt nao deve ser chamado quando dados ja existem"
    )
