"""Suite RED de integracao para M2-019.6, M2-019.7 e M2-019.9."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import scripts.model2.daily_pipeline as daily_pipeline


def _fake_stage(calls: list[str], name: str) -> Callable[..., dict[str, Any]]:
    def _runner(**kwargs: Any) -> dict[str, Any]:
        _ = kwargs
        calls.append(name)
        return {"status": "ok", "stage": name}

    return _runner


def _fake_stage_raise(calls: list[str], name: str) -> Callable[..., dict[str, Any]]:
    def _runner(**kwargs: Any) -> dict[str, Any]:
        _ = kwargs
        calls.append(name)
        raise RuntimeError(f"{name}_boom")

    return _runner


def _base_monkeypatch_pipeline(calls: list[str], monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        daily_pipeline,
        "sync_ohlcv_from_binance",
        _fake_stage(calls, "sync_ohlcv"),
        raising=False,
    )
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage(calls, "migrate"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_scan", _fake_stage(calls, "scan"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage(calls, "track"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage(calls, "validate"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage(calls, "resolve"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage(calls, "bridge"), raising=False)
    monkeypatch.setattr(
        daily_pipeline,
        "run_persist_training_episodes",
        _fake_stage(calls, "persist_training_episodes"),
        raising=False,
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_train_entry_agents",
        _fake_stage(calls, "train_entry_agents"),
        raising=False,
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_entry_rl_filter",
        _fake_stage(calls, "entry_rl_filter"),
        raising=False,
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_order_layer",
        _fake_stage(calls, "order_layer"),
        raising=False,
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_export_signals",
        _fake_stage(calls, "export_signals"),
        raising=False,
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_rl_signal_generation",
        _fake_stage(calls, "rl_signal_generation"),
        raising=False,
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_ensemble_signal_generation",
        _fake_stage(calls, "ensemble_signal_generation"),
        raising=False,
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_export_dashboard",
        _fake_stage(calls, "export_dashboard"),
        raising=False,
    )


def _run_pipeline(tmp_path: Path, *, continue_on_error: bool, dry_run: bool = False) -> dict[str, Any]:
    return daily_pipeline.run_daily_pipeline(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "modelo2.db",
        legacy_db_path=tmp_path / "db" / "legacy.db",
        symbols=["BTCUSDT"],
        timeframe="H4",
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=dry_run,
        continue_on_error=continue_on_error,
        retention_days=30,
        output_dir=tmp_path / "results",
    )


def _idx(calls: list[str], name: str) -> int:
    return calls.index(name)


def test_daily_pipeline_ordena_stages_bridge_persist_train_filter_order_layer(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Requisito: ordem obrigatoria dos novos stages no pipeline."""
    calls: list[str] = []
    _base_monkeypatch_pipeline(calls, monkeypatch)

    _ = _run_pipeline(tmp_path, continue_on_error=False, dry_run=False)

    assert _idx(calls, "bridge") < _idx(calls, "persist_training_episodes")
    assert _idx(calls, "persist_training_episodes") < _idx(calls, "train_entry_agents")
    assert _idx(calls, "train_entry_agents") < _idx(calls, "entry_rl_filter")
    assert _idx(calls, "entry_rl_filter") < _idx(calls, "order_layer")


def test_daily_pipeline_continue_on_error_true_novos_stages_nao_abortam(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Requisito: novos stages devem manter comportamento continue_on_error=True."""
    calls: list[str] = []
    _base_monkeypatch_pipeline(calls, monkeypatch)
    monkeypatch.setattr(
        daily_pipeline,
        "run_train_entry_agents",
        _fake_stage_raise(calls, "train_entry_agents"),
        raising=False,
    )

    summary = _run_pipeline(tmp_path, continue_on_error=True, dry_run=False)

    assert "train_entry_agents" in calls
    assert "entry_rl_filter" in calls
    assert "order_layer" in calls
    assert summary["status"] == "partial"


def test_daily_pipeline_persist_training_episodes_antes_do_treino_no_mesmo_ciclo(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Requisito: episodios devem ser persistidos antes de treinar no mesmo run."""
    calls: list[str] = []
    _base_monkeypatch_pipeline(calls, monkeypatch)

    _ = _run_pipeline(tmp_path, continue_on_error=False, dry_run=False)

    assert _idx(calls, "persist_training_episodes") < _idx(calls, "train_entry_agents")


def test_daily_pipeline_entry_rl_filter_executa_antes_da_order_layer(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Requisito: filtro RL deve preceder consumo da camada de ordem."""
    calls: list[str] = []
    _base_monkeypatch_pipeline(calls, monkeypatch)

    _ = _run_pipeline(tmp_path, continue_on_error=False, dry_run=False)

    assert _idx(calls, "entry_rl_filter") < _idx(calls, "order_layer")


def test_daily_pipeline_output_json_por_run_contem_stages_novos(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Requisito: output de execucao deve expor novos stages no resumo."""
    calls: list[str] = []
    _base_monkeypatch_pipeline(calls, monkeypatch)

    summary = _run_pipeline(tmp_path, continue_on_error=False, dry_run=False)

    output_file = Path(summary["output_file"])
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert "persist_training_episodes" in payload["stages"]
    assert "train_entry_agents" in payload["stages"]
    assert "entry_rl_filter" in payload["stages"]


def test_daily_pipeline_migrate_up_e2e_em_db_novo_e_existente(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Requisito: migracao segue idempotente em banco novo e existente."""
    calls: list[str] = []
    _base_monkeypatch_pipeline(calls, monkeypatch)

    first = _run_pipeline(tmp_path, continue_on_error=False, dry_run=False)
    second = _run_pipeline(tmp_path, continue_on_error=False, dry_run=False)

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert calls.count("migrate") == 2
