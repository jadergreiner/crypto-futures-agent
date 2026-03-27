"""Suite RED para M2-028.4: DailyDrawdownGate com freeze em drawdown_gate.py.

Testa:
- DailyDrawdownGate bloqueia ordens quando drawdown diario excede limite
- Gate e ativado antes do status CONSUMED na order_layer
- Reset automatico em virada de dia UTC
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

# Importacoes RED - modulos ainda nao existem
from core.model2.drawdown_gate import DailyDrawdownGate, DrawdownGateDecision


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gate() -> DailyDrawdownGate:
    """Cria gate com limite de 2% de drawdown diario."""
    return DailyDrawdownGate(max_daily_drawdown_pct=2.0, initial_equity=10000.0)


# ---------------------------------------------------------------------------
# Testes de caminho feliz
# ---------------------------------------------------------------------------

def test_drawdown_gate_permite_quando_drawdown_abaixo_do_limite(gate: DailyDrawdownGate) -> None:
    """Gate deve liberar operacao quando perda acumulada < limite diario."""
    # Arrange: perda de 1% (< 2% limite)
    gate.register_loss(100.0)  # 1% de 10000

    # Act
    decisao: DrawdownGateDecision = gate.evaluate()

    # Assert
    assert decisao.allowed is True
    assert decisao.reason == "OK"


def test_drawdown_gate_bloqueia_quando_limite_atingido(gate: DailyDrawdownGate) -> None:
    """Gate deve bloquear quando perda acumulada >= limite diario."""
    # Arrange: perda de 2.1% (> 2% limite)
    gate.register_loss(210.0)

    # Act
    decisao: DrawdownGateDecision = gate.evaluate()

    # Assert
    assert decisao.allowed is False
    assert "drawdown" in decisao.reason.lower()


def test_drawdown_gate_frozen_bloqueia_todas_operacoes(gate: DailyDrawdownGate) -> None:
    """Uma vez frozen, gate bloqueia todas as operacoes mesmo sem nova perda."""
    # Arrange
    gate.register_loss(210.0)
    gate.evaluate()  # dispara freeze

    # Act: nova avaliacao sem perda adicional
    decisao: DrawdownGateDecision = gate.evaluate()

    # Assert
    assert decisao.allowed is False
    assert decisao.frozen is True


def test_drawdown_gate_reset_utc_libera_novo_dia(gate: DailyDrawdownGate) -> None:
    """Reset UTC deve zerar acumulado e descongelar o gate."""
    # Arrange: congelar gate
    gate.register_loss(300.0)
    assert gate.evaluate().frozen is True

    # Act: simular virada de dia UTC
    gate.reset_for_new_day_utc()

    # Assert
    decisao: DrawdownGateDecision = gate.evaluate()
    assert decisao.allowed is True
    assert decisao.frozen is False


def test_drawdown_gate_accumulated_loss_inicia_zerado(gate: DailyDrawdownGate) -> None:
    """Perda acumulada deve iniciar em zero."""
    assert gate.accumulated_loss == 0.0


def test_drawdown_gate_register_loss_acumula_corretamente(gate: DailyDrawdownGate) -> None:
    """Multiplas perdas devem ser somadas corretamente."""
    gate.register_loss(50.0)
    gate.register_loss(75.0)
    assert gate.accumulated_loss == pytest.approx(125.0)


def test_drawdown_gate_decision_contem_percentual_atual(gate: DailyDrawdownGate) -> None:
    """DrawdownGateDecision deve expor percentual de drawdown atual."""
    gate.register_loss(150.0)
    decisao = gate.evaluate()
    assert hasattr(decisao, "current_drawdown_pct")
    assert decisao.current_drawdown_pct == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# Integracao com order_layer
# ---------------------------------------------------------------------------

def test_drawdown_gate_integrado_na_order_layer_pre_consumed() -> None:
    """evaluate_signal_for_order_layer deve consultar gate antes de CONSUMED."""
    from core.model2.order_layer import OrderLayerInput, evaluate_signal_for_order_layer

    sinal = OrderLayerInput(
        signal_id=1,
        opportunity_id=10,
        symbol="BTCUSDT",
        timeframe="4h",
        signal_side="SHORT",
        entry_type="MARKET",
        entry_price=97000.0,
        stop_loss=98000.0,
        take_profit=95000.0,
        status="CREATED",
        signal_timestamp=1_700_000_000_000,
        payload={},
        decision_timestamp=1_700_000_000_000,
        decision_id=None,
    )

    gate_frozen = MagicMock(spec=DailyDrawdownGate)
    gate_frozen.evaluate.return_value = DrawdownGateDecision(
        allowed=False,
        reason="Drawdown diario excedido",
        frozen=True,
        current_drawdown_pct=2.5,
    )

    decisao = evaluate_signal_for_order_layer(
        sinal,
        authorized_symbols=["BTCUSDT"],
        drawdown_gate=gate_frozen,
    )

    assert decisao.should_transition is False
    assert decisao.target_status == "CANCELLED"
