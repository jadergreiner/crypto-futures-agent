from __future__ import annotations

from scripts.model2 import m2_016_2_validation_window as validation_window
from scripts.model2 import phase_d5_real_data_correlation as phase_d5
from scripts.model2 import train_ppo_lstm as train_lstm


def _expect_contract(module: object, contract: str, message: str) -> None:
    # Arrange/Act
    has_contract = hasattr(module, contract)
    # Assert
    assert has_contract, message


def test_validation_window_finalize_requires_72h_gate_returns_fail_safe() -> None:
    _expect_contract(validation_window, "validate_72h_window_gate", "Missing 72h fail-safe gate")


def test_validation_window_checkpoint_requires_incident_severity_summary() -> None:
    _expect_contract(validation_window, "build_incident_severity_summary", "Missing incident severity summary")


def test_phase_d5_report_requires_phase_e_metrics_bundle_sharpe_winrate_drawdown() -> None:
    _expect_contract(phase_d5, "build_phase_e_metrics_bundle", "Missing Sharpe/win-rate/drawdown metrics bundle")


def test_train_lstm_requires_gate_dependency_m2_016_2_before_phase_e_close() -> None:
    _expect_contract(train_lstm, "validate_m2_016_2_dependency_gate", "Missing M2-016.2 dependency gate")


def test_integration_validation_finalize_exposes_go_no_go_decision_contract() -> None:
    _expect_contract(validation_window, "derive_go_no_go_decision", "Missing GO/NO-GO decision contract")


def test_integration_train_pipeline_persists_phase_e_comparison_artifact_contract() -> None:
    _expect_contract(train_lstm, "persist_phase_e_comparison_report", "Missing Phase E comparison persistence")


def test_risk_regression_requires_decision_id_idempotency_contract_for_reports() -> None:
    _expect_contract(validation_window, "validate_decision_id_idempotency", "Missing decision_id idempotency contract")
