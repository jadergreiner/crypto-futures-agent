"""Suite RED da M2-024.1 para contrato unico de decisao operacional."""

from __future__ import annotations

from core.model2.live_execution import LiveExecutionGateInput, evaluate_live_execution_gate
from core.model2.order_layer import OrderLayerInput, evaluate_signal_for_order_layer


def _build_order_input() -> OrderLayerInput:
    return OrderLayerInput(
        signal_id=1,
        opportunity_id=10,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side="SHORT",
        entry_type="MARKET",
        entry_price=97.0,
        stop_loss=110.0,
        take_profit=84.0,
        status="CREATED",
        signal_timestamp=1_700_000_000_000,
        payload={"decision_origin": "model2"},
        decision_timestamp=1_700_000_100_000,
        decision_id=123,
    )


def _build_gate_input() -> LiveExecutionGateInput:
    return LiveExecutionGateInput(
        technical_signal_id=1,
        opportunity_id=10,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side="SHORT",
        technical_signal_status="CONSUMED",
        signal_timestamp=1_700_000_000_000,
        short_only=False,
        funding_rate=0.001,
        basis_value=0.0,
        funding_rate_max_for_short=0.01,
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        authorized_symbols=("BTCUSDT",),
        available_balance_usd=100.0,
        max_margin_per_position_usd=10.0,
        recent_entries_today=0,
        max_daily_entries=10,
        symbol_active_execution_count=0,
        open_position_qty=0.0,
        cooldown_active=False,
        signal_age_ms=1_000,
        max_signal_age_ms=60_000,
        risk_gate_status="allowed",
        risk_gate_allows_order=True,
        risk_gate_drawdown_pct=0.3,
        circuit_breaker_state="closed",
        circuit_breaker_allows_trading=True,
        circuit_breaker_drawdown_pct=0.3,
        decision_id=123,
        execution_id=456,
    )


def test_order_layer_rejeita_sem_decision_id_retornando_reason_padrao() -> None:
    """R1: sem decision_id deve bloquear por fail-safe em contrato de decisao."""
    entrada = _build_order_input()
    entrada = OrderLayerInput(**{**entrada.__dict__, "decision_id": None})

    decisao = evaluate_signal_for_order_layer(entrada, authorized_symbols={"BTCUSDT"})

    assert decisao.target_status == "CANCELLED"
    assert decisao.reason == "missing_decision_id"


def test_order_layer_rejeita_timestamp_invalido_retornando_reason_padrao() -> None:
    """R2: signal_timestamp invalido deve bloquear antes da camada live."""
    entrada = _build_order_input()
    entrada = OrderLayerInput(**{**entrada.__dict__, "signal_timestamp": 0})

    decisao = evaluate_signal_for_order_layer(entrada, authorized_symbols={"BTCUSDT"})

    assert decisao.target_status == "CANCELLED"
    assert decisao.reason == "missing_signal_timestamp"


def test_order_layer_rejeita_payload_sem_decision_origin_retornando_reason_padrao() -> None:
    """R3: payload sem origem da decisao deve entrar em fail-safe."""
    entrada = _build_order_input()
    entrada = OrderLayerInput(**{**entrada.__dict__, "payload": {}})

    decisao = evaluate_signal_for_order_layer(entrada, authorized_symbols={"BTCUSDT"})

    assert decisao.target_status == "CANCELLED"
    assert decisao.reason == "missing_payload_contract"


def test_live_gate_bloqueia_sem_decision_id_por_ambiguidade_operacional() -> None:
    """R4: sem decision_id nao pode avancar para READY no gate live."""
    entrada = _build_gate_input()
    entrada = LiveExecutionGateInput(**{**entrada.__dict__, "decision_id": None})

    decisao = evaluate_live_execution_gate(entrada)

    assert decisao.allow_execution is False
    assert decisao.reason == "ops_ambiguous_state"


def test_live_gate_bloqueia_sem_execution_id_por_ambiguidade_operacional() -> None:
    """R5: sem execution_id no contrato deve bloquear em fail-safe."""
    entrada = _build_gate_input()
    entrada = LiveExecutionGateInput(**{**entrada.__dict__, "execution_id": None})

    decisao = evaluate_live_execution_gate(entrada)

    assert decisao.allow_execution is False
    assert decisao.reason == "ops_ambiguous_state"


def test_live_gate_ready_carrega_correlacao_decision_id_e_execution_id() -> None:
    """R6: decisao READY deve manter correlacao completa no payload de saida."""
    entrada = _build_gate_input()

    decisao = evaluate_live_execution_gate(entrada)

    assert decisao.allow_execution is True
    assert decisao.details.get("decision_id") == 123
    assert decisao.details.get("execution_id") == 456


def test_live_gate_ready_expoe_reason_code_severidade_e_acao() -> None:
    """R7: mesmo caminho permitido precisa publicar contrato observavel."""
    entrada = _build_gate_input()

    decisao = evaluate_live_execution_gate(entrada)

    assert decisao.allow_execution is True
    assert "reason_code" in decisao.details
    assert "severity" in decisao.details
    assert "recommended_action" in decisao.details


def test_contrato_erro_status_not_consumed_requer_campos_obrigatorios() -> None:
    """R8: bloqueio por status invalido precisa manter contrato de erro completo."""
    entrada = _build_gate_input()
    entrada = LiveExecutionGateInput(
        **{**entrada.__dict__, "technical_signal_status": "CREATED"},
    )

    decisao = evaluate_live_execution_gate(entrada)

    assert decisao.allow_execution is False
    assert decisao.target_status == "BLOCKED"
    assert decisao.details.get("reason_code") == "status_not_consumed"
    assert "severity" in decisao.details
    assert "recommended_action" in decisao.details
