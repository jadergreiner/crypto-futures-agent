"""Cobertura adicional para validator e live_execution no item M2-028.9."""

from __future__ import annotations

from types import SimpleNamespace

from core.model2.live_execution import (
    LiveExecutionGateInput,
    REASON_CODE_ACTION,
    REASON_CODE_SEVERITY,
    evaluate_live_execution_gate,
)
from core.model2.scanner import (
    _extract_zone_fields,
    _latest_valid_bearish_zone,
    _market_structure_label,
)
from core.model2.validator import (
    ValidationInput,
    _find_trigger_break_after_monitoring,
    _visible_rejection,
    evaluate_monitoring_validation,
)


def _validation_input(
    *,
    side: str = "SHORT",
    monitoring_started_at: int | None = 50,
    metadata: dict | None = None,
    candles: list[dict] | None = None,
) -> ValidationInput:
    return ValidationInput(
        opportunity_id=10,
        symbol="BTCUSDT",
        timeframe="H4",
        side=side,
        trigger_price=97.0,
        zone_low=100.0,
        monitoring_started_at=monitoring_started_at,
        metadata=metadata
        if metadata is not None
        else {
            "rejection_candle": {
                "timestamp": 40,
                "open": 100.0,
                "high": 111.0,
                "low": 97.0,
                "close": 98.0,
            }
        },
        candles=candles if candles is not None else [{"timestamp": 51, "low": 96.5}],
        validation_timestamp=1_000,
    )


def _live_gate_input(**overrides: object) -> LiveExecutionGateInput:
    base = LiveExecutionGateInput(
        technical_signal_id=1,
        opportunity_id=1,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side="SHORT",
        technical_signal_status="CONSUMED",
        signal_timestamp=1_700_000_000_000,
        short_only=False,
        funding_rate=-0.0001,
        basis_value=0.001,
        funding_rate_max_for_short=0.0005,
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        authorized_symbols=("BTCUSDT",),
        available_balance_usd=100.0,
        max_margin_per_position_usd=1.0,
        recent_entries_today=0,
        max_daily_entries=3,
        symbol_active_execution_count=0,
        open_position_qty=0.0,
        open_position_side="",
        cooldown_active=False,
        signal_age_ms=1_000,
        max_signal_age_ms=240_000,
        risk_gate_status="ativo",
        risk_gate_allows_order=True,
        risk_gate_drawdown_pct=0.0,
        circuit_breaker_state="normal",
        circuit_breaker_allows_trading=True,
        circuit_breaker_drawdown_pct=0.0,
        decision_id=10,
        execution_id=20,
    )
    return LiveExecutionGateInput(**{**base.__dict__, **overrides})


def test_visible_rejection_retains_fail_safe_with_campos_invalidos() -> None:
    assert _visible_rejection({"open": None, "close": 98.0}, zone_low=100.0) is False


def test_extract_zone_fields_aceita_status_objeto_e_zone_id_convertivel() -> None:
    status = SimpleNamespace(value="tested")
    zone = SimpleNamespace(
        zone_low=100.0,
        zone_high=110.0,
        type="bearish",
        status=status,
        timestamp="1700000000000",
        zone_id="12",
    )

    parsed = _extract_zone_fields(zone)

    assert parsed is not None
    assert parsed["status"] == "TESTED"
    assert parsed["zone_id"] == 12


def test_latest_valid_bearish_zone_faz_fallback_para_fvg_quando_order_block_rejeitado() -> None:
    smc = {
        "order_blocks": [
            {
                "zone_low": 100.0,
                "zone_high": 110.0,
                "type": "bearish",
                "status": "MITIGATED",
                "timestamp": 100,
            }
        ],
        "fvgs": [
            {
                "zone_low": 90.0,
                "zone_high": 95.0,
                "type": "bearish",
                "status": None,
                "timestamp": None,
            }
        ],
    }

    parsed = _latest_valid_bearish_zone(smc)

    assert parsed is not None
    assert parsed["source"] == "fvg"
    assert parsed["status"] == ""


def test_market_structure_label_le_objeto_com_value() -> None:
    structure = SimpleNamespace(type=SimpleNamespace(value="Range"))

    label = _market_structure_label({"market_structure": structure})

    assert label == "range"


def test_visible_rejection_long_rejeita_fechamento_abaixo_da_zona() -> None:
    rejection = {
        "open": 109.0,
        "close": 100.0,
        "high": 110.0,
        "low": 95.0,
    }

    assert _visible_rejection(rejection, zone_low=105.0, side="LONG") is False


def test_find_trigger_break_long_ignora_candles_sem_high_e_anteriores() -> None:
    trigger_break = _find_trigger_break_after_monitoring(
        [
            {"timestamp": 49, "high": 110.0},
            {"timestamp": 51},
            {"timestamp": 55, "high": 120.0},
        ],
        trigger_price=115.0,
        monitoring_started_at=50,
        side="LONG",
    )

    assert trigger_break == {"timestamp": 55, "high": 120.0}


def test_validate_monitoring_fails_when_monitoring_start_is_missing() -> None:
    decision = evaluate_monitoring_validation(_validation_input(monitoring_started_at=None))

    assert decision.is_validated is False
    assert decision.reason == "missing_monitoring_start"


def test_validate_monitoring_fails_with_invalid_rejection_candle() -> None:
    decision = evaluate_monitoring_validation(
        _validation_input(
            metadata={
                "rejection_candle": {
                    "timestamp": 40,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.5,
                }
            }
        )
    )

    assert decision.is_validated is False
    assert decision.reason == "invalid_rejection_candle"


def test_orphan_position_reason_code_tem_severidade_e_acao() -> None:
    assert REASON_CODE_SEVERITY["orphan_position"] == "HIGH"
    assert REASON_CODE_ACTION["orphan_position"] == "reconciliar_posicao"


def test_live_gate_rejeita_execution_mode_nao_suportado() -> None:
    decision = evaluate_live_execution_gate(_live_gate_input(execution_mode="sandbox"))

    assert decision.allow_execution is False
    assert decision.reason == "unsupported_execution_mode"


def test_live_gate_rejeita_status_diferente_de_consumed() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(technical_signal_status="CREATED")
    )

    assert decision.allow_execution is False
    assert decision.reason == "status_not_consumed"


def test_live_gate_rejeita_contrato_estrito_sem_decision_id_valido() -> None:
    decision = evaluate_live_execution_gate(_live_gate_input(decision_id=0))

    assert decision.allow_execution is False
    assert decision.reason == "ops_ambiguous_state"


def test_live_gate_rejeita_contrato_estrito_sem_execution_id_valido() -> None:
    decision = evaluate_live_execution_gate(_live_gate_input(execution_id=0))

    assert decision.allow_execution is False
    assert decision.reason == "ops_ambiguous_state"


def test_live_gate_rejeita_risk_gate_indisponivel_sem_ordem_liberada() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(risk_gate_status="unknown", risk_gate_allows_order=False)
    )

    assert decision.allow_execution is False
    assert decision.reason == "ops_ambiguous_state"


def test_live_gate_rejeita_risk_gate_indisponivel_mesmo_com_allow_true() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(risk_gate_status="unknown", risk_gate_allows_order=True)
    )

    assert decision.allow_execution is False
    assert decision.reason == "risk_gate_state_unavailable"


def test_live_gate_rejeita_circuit_breaker_indisponivel() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(circuit_breaker_state="unknown")
    )

    assert decision.allow_execution is False
    assert decision.reason == "circuit_breaker_state_unavailable"


def test_live_gate_rejeita_symbol_nao_autorizado() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(authorized_symbols=("ETHUSDT",))
    )

    assert decision.allow_execution is False
    assert decision.reason == "symbol_not_authorized"


def test_live_gate_rejeita_symbol_nao_habilitado_em_live_symbols() -> None:
    decision = evaluate_live_execution_gate(_live_gate_input(live_symbols=("ETHUSDT",)))

    assert decision.allow_execution is False
    assert decision.reason == "symbol_not_enabled"


def test_live_gate_rejeita_sinal_expirado() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(signal_age_ms=500_000, max_signal_age_ms=240_000)
    )

    assert decision.allow_execution is False
    assert decision.reason == "signal_expired"


def test_live_gate_rejeita_execucao_ativa_sem_reversao() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(symbol_active_execution_count=1, open_position_qty=0.0)
    )

    assert decision.allow_execution is False
    assert decision.reason == "active_execution_exists"


def test_live_gate_rejeita_posicao_aberta_mesmo_lado() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(open_position_qty=1.5, open_position_side="SHORT")
    )

    assert decision.allow_execution is False
    assert decision.reason == "open_position_exists"


def test_live_gate_rejeita_cooldown_ativo() -> None:
    decision = evaluate_live_execution_gate(_live_gate_input(cooldown_active=True))

    assert decision.allow_execution is False
    assert decision.reason == "symbol_in_cooldown"


def test_live_gate_rejeita_limite_de_margem_invalido() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(max_margin_per_position_usd=0.0)
    )

    assert decision.allow_execution is False
    assert decision.reason == "invalid_margin_limit"


def test_live_gate_rejeita_saldo_indisponivel_em_live() -> None:
    decision = evaluate_live_execution_gate(_live_gate_input(available_balance_usd=None))

    assert decision.allow_execution is False
    assert decision.reason == "balance_unavailable"


def test_live_gate_rejeita_saldo_insuficiente_em_live() -> None:
    decision = evaluate_live_execution_gate(
        _live_gate_input(available_balance_usd=0.5, max_margin_per_position_usd=1.0)
    )

    assert decision.allow_execution is False
    assert decision.reason == "insufficient_balance"