"""RED phase suite for M2-024.12 testnet full-flow contract."""

from __future__ import annotations

import json
from pathlib import Path

from core.model2.live_execution import LiveExecutionConfig
from core.model2.live_service import Model2LiveExecutionService
from scripts.model2.go_live_preflight import run_go_live_preflight
from tests.test_model2_m2_018_2_testnet_integration import (
    _stub_ok,
)


def _write_paper_env_with_credentials(env_file: Path) -> None:
    env_file.write_text(
        "TRADING_MODE=paper\n"
        "M2_EXECUTION_MODE=shadow\n"
        "M2_LIVE_SYMBOLS=BNBUSDT\n"
        "BINANCE_API_KEY=test_key\n"
        "BINANCE_API_SECRET=test_secret\n"
        "M2_MAX_DAILY_ENTRIES=10\n"
        "M2_MAX_MARGIN_PER_POSITION_USD=1.0\n"
        "M2_MAX_SIGNAL_AGE_MINUTES=240\n"
        "M2_SYMBOL_COOLDOWN_MINUTES=240\n"
        "M2_SHORT_ONLY=true\n"
        "M2_CANARY_LEVERAGE=5\n"
        "M2_FUNDING_RATE_MAX_FOR_SHORT=0.0005\n",
        encoding="utf-8",
    )


def test_preflight_paper_with_credentials_check6_includes_ok_testnet_credentials(tmp_path: Path) -> None:
    """R1: check6 must include positive testnet credentials evidence in paper mode."""
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    _write_paper_env_with_credentials(env_file)
    result = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=False,
        continue_on_error=True,
        live_symbols=("BNBUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_ok,
        live_execute_fn=_stub_ok,
        live_reconcile_fn=_stub_ok,
        live_dashboard_fn=_stub_ok,
        live_healthcheck_fn=_stub_ok,
    )
    check6 = next(item for item in result["checks"] if item["id"] == "6")
    creds = check6["evidence"]["testnet_credentials"]
    assert check6["status"] == "ok"
    assert creds["requires_testnet_credentials"] is True
    assert creds["reason"] == "ok"


def test_preflight_paper_with_credentials_persists_testnet_evidence_artifact(tmp_path: Path) -> None:
    """R2 (RED): preflight output must persist a dedicated testnet evidence artifact."""
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    _write_paper_env_with_credentials(env_file)

    summary = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=False,
        continue_on_error=True,
        live_symbols=("BNBUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_ok,
        live_execute_fn=_stub_ok,
        live_reconcile_fn=_stub_ok,
        live_dashboard_fn=_stub_ok,
        live_healthcheck_fn=_stub_ok,
    )

    output_file = Path(str(summary["output_file"]))
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert "testnet_evidence" in payload
    assert "decision_execution_correlation" in payload["testnet_evidence"]


def _build_shadow_service() -> Model2LiveExecutionService:
    service = Model2LiveExecutionService.__new__(Model2LiveExecutionService)
    service.config = LiveExecutionConfig(
        execution_mode="shadow",
        live_symbols=("BNBUSDT",),
        authorized_symbols=("BNBUSDT",),
        short_only=True,
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_ms=240 * 60_000,
        symbol_cooldown_ms=240 * 60_000,
        funding_rate_max_for_short=0.0005,
        leverage=5,
    )
    return service


def test_execute_shadow_item_contains_reason_contract_fields() -> None:
    """R3 (RED): shadow execute return must expose reason contract fields."""
    service = _build_shadow_service()
    output = service._execute_ready_signal(
        {"id": 101, "status": "READY"},
        now_ms=1_700_000_000_000,
    )
    assert "reason_code" in output
    assert "severity" in output
    assert "recommended_action" in output


def test_execute_shadow_item_contains_decision_and_execution_ids() -> None:
    """R4 (RED): shadow execute return must include decision/execution correlation IDs."""
    service = _build_shadow_service()
    output = service._execute_ready_signal(
        {"id": 101, "status": "READY"},
        now_ms=1_700_000_000_000,
    )
    assert int(output["decision_id"]) > 0
    assert int(output["execution_id"]) > 0


def test_execute_shadow_item_reason_code_is_cataloged() -> None:
    """R5 (RED): output reason_code must be canonical and machine-readable."""
    service = _build_shadow_service()
    output = service._execute_ready_signal(
        {"id": 101, "status": "READY"},
        now_ms=1_700_000_000_000,
    )
    assert output["reason_code"].startswith("ops.")


def test_execute_shadow_item_status_reason_contract_is_deterministic() -> None:
    """R6 (RED): repeated shadow execution should preserve contract fields deterministically."""
    service = _build_shadow_service()
    first = service._execute_ready_signal({"id": 101, "status": "READY"}, now_ms=1_700_000_000_000)
    second = service._execute_ready_signal({"id": 101, "status": "READY"}, now_ms=1_700_000_000_001)
    assert first["reason_code"] == second["reason_code"]
    assert first["severity"] == second["severity"]
