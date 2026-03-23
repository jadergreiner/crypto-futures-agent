"""Suite RED da M2-023.1 para contrato unico de erros de execucao live."""

from __future__ import annotations

from core.model2.live_execution import (
    LiveExecutionGateInput,
    REASON_CODE_CATALOG,
    evaluate_live_execution_gate,
)
from core.model2 import live_service
from core.model2.order_layer import OrderLayerInput

_REQUIRED_REASON_CODES = (
    "timeout",
    "insufficient_balance",
    "reconciliation_divergence",
)


def _build_gate_input() -> LiveExecutionGateInput:
    """Cria entrada base para cenarios deterministas do gate live."""
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
        risk_gate_drawdown_pct=0.5,
        circuit_breaker_state="closed",
        circuit_breaker_allows_trading=True,
        circuit_breaker_drawdown_pct=0.5,
    )


def test_live_execution_gate_input_sem_decision_id_deve_falhar_red() -> None:
    """R2: gate live deve carregar decision_id para correlacao auditavel."""
    # Arrange
    campos = set(LiveExecutionGateInput.__dataclass_fields__.keys())

    # Act
    possui_decision_id = "decision_id" in campos

    # Assert
    assert possui_decision_id, "LiveExecutionGateInput precisa de decision_id"


def test_order_layer_input_sem_decision_id_deve_falhar_red() -> None:
    """R2: order layer deve preservar correlacao por decision_id."""
    # Arrange
    campos = set(OrderLayerInput.__dataclass_fields__.keys())

    # Act
    possui_decision_id = "decision_id" in campos

    # Assert
    assert possui_decision_id, "OrderLayerInput precisa de decision_id"


def test_reason_codes_obrigatorios_nao_catalogados_deve_falhar_red() -> None:
    """R1: contrato de erro exige reason codes minimos para timeout/reconciliacao."""
    # Arrange
    chaves_catalogo = set(REASON_CODE_CATALOG.keys())

    # Act
    ausentes = [codigo for codigo in _REQUIRED_REASON_CODES if codigo not in chaves_catalogo]

    # Assert
    assert not ausentes, f"Reason codes ausentes no catalogo: {ausentes}"


def test_mapa_severidade_obrigatorio_ausente_deve_falhar_red() -> None:
    """R1: contrato unico de erro deve definir severidade por reason_code."""
    # Arrange / Act
    possui_mapa = hasattr(__import__("core.model2.live_execution", fromlist=["x"]), "REASON_CODE_SEVERITY")

    # Assert
    assert possui_mapa, "Modulo live_execution deve expor REASON_CODE_SEVERITY"


def test_mapa_acao_recomendada_obrigatorio_ausente_deve_falhar_red() -> None:
    """R1: contrato unico de erro deve definir acao recomendada por reason_code."""
    # Arrange / Act
    possui_mapa = hasattr(__import__("core.model2.live_execution", fromlist=["x"]), "REASON_CODE_ACTION")

    # Assert
    assert possui_mapa, "Modulo live_execution deve expor REASON_CODE_ACTION"


def test_bloqueio_risk_gate_sem_contrato_completo_deve_falhar_red() -> None:
    """R3: bloqueio por risk gate deve trazer reason/severidade/acao/correlacao."""
    # Arrange
    entrada = _build_gate_input()
    entrada = LiveExecutionGateInput(
        **{
            **entrada.__dict__,
            "risk_gate_status": "blocked",
            "risk_gate_allows_order": False,
        }
    )

    # Act
    decisao = evaluate_live_execution_gate(entrada)

    # Assert
    assert decisao.allow_execution is False
    assert "reason_code" in decisao.details
    assert "severity" in decisao.details
    assert "recommended_action" in decisao.details
    assert "decision_id" in decisao.details
    assert "execution_id" in decisao.details


def test_bloqueio_circuit_breaker_sem_contrato_completo_deve_falhar_red() -> None:
    """R3: bloqueio por circuit breaker deve trazer contrato de erro completo."""
    # Arrange
    entrada = _build_gate_input()
    entrada = LiveExecutionGateInput(
        **{
            **entrada.__dict__,
            "circuit_breaker_state": "open",
            "circuit_breaker_allows_trading": False,
        }
    )

    # Act
    decisao = evaluate_live_execution_gate(entrada)

    # Assert
    assert decisao.allow_execution is False
    assert "reason_code" in decisao.details
    assert "severity" in decisao.details
    assert "recommended_action" in decisao.details


def test_live_service_sem_emissor_contrato_erro_deve_falhar_red() -> None:
    """R2: live_service deve expor API de emissao padronizada de erro."""
    # Arrange / Act
    possui_api = hasattr(live_service.Model2LiveExecutionService, "emit_execution_error_contract_event")

    # Assert
    assert possui_api, "Model2LiveExecutionService deve expor emit_execution_error_contract_event"


def test_live_service_sem_classificador_erro_desconhecido_deve_falhar_red() -> None:
    """R3: erro nao classificado deve cair em fail-safe explicito."""
    # Arrange / Act
    possui_api = hasattr(live_service.Model2LiveExecutionService, "classify_unknown_execution_error")

    # Assert
    assert possui_api, "Model2LiveExecutionService deve expor classify_unknown_execution_error"


def test_order_layer_sem_catalogo_compativel_deve_falhar_red() -> None:
    """R5: contrato de reason_code deve ser consistente entre camadas."""
    # Arrange / Act
    catalogo_order_layer = getattr(__import__("core.model2.order_layer", fromlist=["x"]), "REASON_CODE_CATALOG", None)

    # Assert
    assert isinstance(catalogo_order_layer, dict), "order_layer deve expor REASON_CODE_CATALOG"
    assert "insufficient_balance" in catalogo_order_layer
