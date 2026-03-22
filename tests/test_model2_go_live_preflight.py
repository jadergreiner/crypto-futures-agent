import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import patch

from config.settings import M2_MAX_DAILY_ENTRIES
from scripts.model2.go_live_preflight import (
    _check_guardrails_functional,
    _check_model_inference_functional,
    run_go_live_preflight,
)


def _ok_summary(output_file: Path) -> dict:
    return {
        "status": "ok",
        "output_file": str(output_file),
    }


def _stub_migrate(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "stub_migrate.json"
    out.write_text("{}", encoding="utf-8")
    return _ok_summary(out)


def _stub_execute(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    out = output_dir / "stub_execute.json"
    out.write_text("{}", encoding="utf-8")
    return _ok_summary(out)


def _stub_reconcile(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    out = output_dir / "stub_reconcile.json"
    out.write_text("{}", encoding="utf-8")
    return _ok_summary(out)


def _stub_dashboard(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    out = output_dir / "stub_dashboard.json"
    out.write_text("{}", encoding="utf-8")
    return _ok_summary(out)


def _stub_healthcheck(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    out = output_dir / "stub_healthcheck.json"
    out.write_text("{}", encoding="utf-8")
    return _ok_summary(out)


def _create_min_live_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS technical_signals(id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS signal_executions(id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS signal_execution_events(id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS signal_execution_snapshots(id INTEGER PRIMARY KEY);
            """
        )


def test_go_live_preflight_happy_path_writes_summary(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    env_file.write_text("M2_LIVE_SYMBOLS=BTCUSDT\n", encoding="utf-8")

    summary = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=False,
        live_symbols=("BTCUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_migrate,
        live_execute_fn=_stub_execute,
        live_reconcile_fn=_stub_reconcile,
        live_dashboard_fn=_stub_dashboard,
        live_healthcheck_fn=_stub_healthcheck,
    )

    assert summary["status"] == "ok"
    assert len(summary["checks"]) == 10
    assert Path(summary["output_file"]).exists()


def test_go_live_preflight_retries_after_acl_fix(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    env_file.write_text("M2_LIVE_SYMBOLS=BTCUSDT\n", encoding="utf-8")

    attempts = {"count": 0}

    def flaky_write_probe(_: Path) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise PermissionError("denied")

    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr="")

    summary = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=False,
        live_symbols=("BTCUSDT",),
        command_runner=fake_runner,
        db_write_probe=flaky_write_probe,
        migrate_fn=_stub_migrate,
        live_execute_fn=_stub_execute,
        live_reconcile_fn=_stub_reconcile,
        live_dashboard_fn=_stub_dashboard,
        live_healthcheck_fn=_stub_healthcheck,
    )

    check2 = next(item for item in summary["checks"] if item["id"] == "2")
    assert check2["status"] == "ok"
    assert attempts["count"] == 2
    assert any(item["type"] == "windows_acl_fix" for item in summary["applied_fixes"])


def test_no_apply_does_not_run_migration_or_env_fix(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    _create_min_live_schema(db_path)
    env_file = tmp_path / ".env"
    env_file.write_text("M2_EXECUTION_MODE=live\nM2_LIVE_SYMBOLS=\n", encoding="utf-8")

    calls = {"migrate": 0}

    def count_migrate(**kwargs):
        calls["migrate"] += 1
        return _stub_migrate(**kwargs)

    summary = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=False,
        continue_on_error=True,
        live_symbols=(),
        db_write_probe=lambda _: None,
        migrate_fn=count_migrate,
        live_execute_fn=_stub_execute,
        live_reconcile_fn=_stub_reconcile,
        live_dashboard_fn=_stub_dashboard,
        live_healthcheck_fn=_stub_healthcheck,
    )

    assert calls["migrate"] == 0
    assert summary["applied_fixes"] == []
    assert summary["status"] == "alert"


def test_env_auto_fix_updates_required_keys_and_creates_backup(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "M2_EXECUTION_MODE=live\n"
        "M2_MAX_DAILY_ENTRIES=0\n"
        "M2_MAX_MARGIN_PER_POSITION_USD=0\n"
        "M2_MAX_SIGNAL_AGE_MINUTES=-1\n"
        "M2_SYMBOL_COOLDOWN_MINUTES=-5\n",
        encoding="utf-8",
    )

    run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=False,
        live_symbols=("ETHUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_migrate,
        live_execute_fn=_stub_execute,
        live_reconcile_fn=_stub_reconcile,
        live_dashboard_fn=_stub_dashboard,
        live_healthcheck_fn=_stub_healthcheck,
    )

    env_text = env_file.read_text(encoding="utf-8")
    assert "M2_EXECUTION_MODE=shadow" in env_text
    assert "M2_LIVE_SYMBOLS=ETHUSDT" in env_text
    assert f"M2_MAX_DAILY_ENTRIES={M2_MAX_DAILY_ENTRIES}" in env_text
    assert (tmp_path / ".env.bak").exists()


def test_continue_on_error_controls_followup_execution(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    env_file.write_text("M2_LIVE_SYMBOLS=BTCUSDT\n", encoding="utf-8")

    calls = {"reconcile": 0}

    def failing_execute(**kwargs):
        raise RuntimeError("execute failed")

    def count_reconcile(**kwargs):
        calls["reconcile"] += 1
        return _stub_reconcile(**kwargs)

    summary_failfast = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results_failfast",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=False,
        live_symbols=("BTCUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_migrate,
        live_execute_fn=failing_execute,
        live_reconcile_fn=count_reconcile,
        live_dashboard_fn=_stub_dashboard,
        live_healthcheck_fn=_stub_healthcheck,
    )

    check8_failfast = next(item for item in summary_failfast["checks"] if item["id"] == "8")
    assert check8_failfast["status"] == "skipped"
    assert calls["reconcile"] == 0

    summary_continue = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results_continue",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=True,
        live_symbols=("BTCUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_migrate,
        live_execute_fn=failing_execute,
        live_reconcile_fn=count_reconcile,
        live_dashboard_fn=_stub_dashboard,
        live_healthcheck_fn=_stub_healthcheck,
    )

    check8_continue = next(item for item in summary_continue["checks"] if item["id"] == "8")
    assert check8_continue["status"] == "ok"
    assert calls["reconcile"] == 1


def test_check_guardrails_functional_returns_ok_when_modules_available() -> None:
    """M2-020.5: _check_guardrails_functional retorna ok quando RiskGate e CircuitBreaker funcionam."""
    result = _check_guardrails_functional()
    assert result["ok"] is True
    assert result["details"]["risk_gate"]["instantiated"] is True
    assert result["details"]["circuit_breaker"]["instantiated"] is True
    assert "status" in result["details"]["risk_gate"]
    assert "state" in result["details"]["circuit_breaker"]


def test_check_guardrails_functional_fails_when_risk_gate_unavailable(monkeypatch) -> None:
    """M2-020.5: _check_guardrails_functional retorna ok=False quando RiskGate nao pode ser importado."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "risk.risk_gate":
            raise ImportError("modulo indisponivel")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = _check_guardrails_functional()
    assert result["ok"] is False
    assert result["details"]["risk_gate"]["instantiated"] is False
    assert "error" in result["details"]["risk_gate"]


def test_preflight_check6_includes_guardrails_evidence(tmp_path: Path) -> None:
    """M2-020.5: check 6 do preflight inclui evidencia dos guard-rails."""
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    env_file.write_text("M2_LIVE_SYMBOLS=BTCUSDT\n", encoding="utf-8")

    summary = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=True,
        live_symbols=("BTCUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_migrate,
        live_execute_fn=_stub_execute,
        live_reconcile_fn=_stub_reconcile,
        live_dashboard_fn=_stub_dashboard,
        live_healthcheck_fn=_stub_healthcheck,
    )

    check6 = next(item for item in summary["checks"] if item["id"] == "6")
    assert check6["status"] == "ok"
    assert "guardrails" in check6["evidence"]
    assert "model_inference" in check6["evidence"]
    assert "operational_alerts" in check6["evidence"]
    assert check6["evidence"]["guardrails"]["risk_gate"]["instantiated"] is True
    assert check6["evidence"]["guardrails"]["circuit_breaker"]["instantiated"] is True
    assert check6["evidence"]["model_inference"]["instantiated"] is True
    assert check6["evidence"]["model_inference"]["competent"] is True
    assert check6["evidence"]["operational_alerts"]["enabled"] is False


def test_check_model_inference_functional_returns_ok() -> None:
    result = _check_model_inference_functional()
    assert result["ok"] is True
    assert result["details"]["instantiated"] is True
    assert result["details"]["competent"] is True


def test_preflight_check6_blocks_when_alerts_enabled_without_telegram_credentials(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "M2_LIVE_SYMBOLS=BTCUSDT\n"
        "M2_ALERTS_ENABLED=true\n",
        encoding="utf-8",
    )

    summary = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=True,
        live_symbols=("BTCUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_migrate,
        live_execute_fn=_stub_execute,
        live_reconcile_fn=_stub_reconcile,
        live_dashboard_fn=_stub_dashboard,
        live_healthcheck_fn=_stub_healthcheck,
    )

    check6 = next(item for item in summary["checks"] if item["id"] == "6")
    assert check6["status"] == "alert"
    assert check6["evidence"]["operational_alerts"]["enabled"] is True
    assert check6["evidence"]["operational_alerts"]["telegram_bot_token_configured"] is False
    assert check6["evidence"]["operational_alerts"]["telegram_chat_id_configured"] is False
