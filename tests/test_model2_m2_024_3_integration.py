"""RED Phase - Integração order_layer com gate de idempotência (M2-024.3).

Objetivo: Validar que order_layer chama o gate real de signal_bridge para
bloquear decision_ids duplicados no ciclo live.

Status: RED - Testes falham ate implementacao em order_layer.py.
"""

from __future__ import annotations

from typing import Generator

import pytest

from core.model2.order_layer import (
    OrderLayerInput,
    evaluate_signal_for_order_layer,
    TECHNICAL_SIGNAL_STATUS_CREATED,
    TECHNICAL_SIGNAL_STATUS_CANCELLED,
    TECHNICAL_SIGNAL_STATUS_CONSUMED,
)
from core.model2.signal_bridge import (
    is_decision_id_duplicate,
    mark_decision_id_processed,
    reset_idempotence_gate,
)


def _sinal_valido(decision_id: int | None = 100) -> OrderLayerInput:
    """Cria sinal valido com contrato estrito."""
    return OrderLayerInput(
        signal_id=1,
        opportunity_id=10,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side="LONG",
        entry_type="MARKET",
        entry_price=97.0,
        stop_loss=90.0,
        take_profit=110.0,
        status=TECHNICAL_SIGNAL_STATUS_CREATED,
        signal_timestamp=1_700_000_100_000,
        payload={"decision_origin": "signal_bridge"} if decision_id else {},
        decision_timestamp=1_700_000_200_000,
        decision_id=decision_id,
    )


@pytest.fixture(autouse=True)
def limpar_gate() -> Generator[None, None, None]:
    """Reseta gate antes de cada teste para isolamento."""
    reset_idempotence_gate()
    yield
    reset_idempotence_gate()


class TestOrderLayerBloqueaDuplicata:
    """order_layer deve bloquear sinais com decision_id duplicado."""

    def test_primeiro_sinal_accepted(self) -> None:
        """Primeiro sinal com decision_id valido deve ser CONSUMED."""
        sinal = _sinal_valido(decision_id=200)
        decisao = evaluate_signal_for_order_layer(sinal, authorized_symbols={"BTCUSDT"})

        assert decisao.target_status == TECHNICAL_SIGNAL_STATUS_CONSUMED, (
            f"Esperado CONSUMED, obtido {decisao.target_status}"
        )

    def test_segundo_sinal_duplicado_cancelled(self) -> None:
        """Segundo sinal com mesmo decision_id deve ser CANCELLED."""
        decision_id = 300
        sinal = _sinal_valido(decision_id=decision_id)

        # Primeira chamada - deve ser aceita
        evaluate_signal_for_order_layer(sinal, authorized_symbols={"BTCUSDT"})

        # Segunda chamada - mesmo decision_id, deve ser CANCELLED
        decisao2 = evaluate_signal_for_order_layer(sinal, authorized_symbols={"BTCUSDT"})

        assert decisao2.target_status == TECHNICAL_SIGNAL_STATUS_CANCELLED, (
            f"Duplicata nao bloqueada: obtido {decisao2.target_status}"
        )

    def test_segundo_sinal_reason_duplicate_decision_id(self) -> None:
        """Reason code do sinal duplicado deve ser 'duplicate_decision_id'."""
        decision_id = 400
        sinal = _sinal_valido(decision_id=decision_id)

        evaluate_signal_for_order_layer(sinal, authorized_symbols={"BTCUSDT"})
        decisao2 = evaluate_signal_for_order_layer(sinal, authorized_symbols={"BTCUSDT"})

        assert decisao2.reason == "duplicate_decision_id", (
            f"Reason esperado 'duplicate_decision_id', obtido '{decisao2.reason}'"
        )

    def test_sinal_accepted_marca_decision_id_no_gate(self) -> None:
        """Apos CONSUMED, decision_id deve estar marcado no gate de signal_bridge."""
        decision_id = 500
        sinal = _sinal_valido(decision_id=decision_id)

        assert not is_decision_id_duplicate(decision_id), "decision_id ja marcado antes do sinal"

        evaluate_signal_for_order_layer(sinal, authorized_symbols={"BTCUSDT"})

        assert is_decision_id_duplicate(decision_id), (
            "decision_id nao marcado no gate apos CONSUMED"
        )

    def test_decision_ids_diferentes_nao_bloqueados(self) -> None:
        """decision_ids distintos nao devem bloquear entre si."""
        sinal1 = _sinal_valido(decision_id=600)
        sinal2 = _sinal_valido(decision_id=601)

        d1 = evaluate_signal_for_order_layer(sinal1, authorized_symbols={"BTCUSDT"})
        d2 = evaluate_signal_for_order_layer(sinal2, authorized_symbols={"BTCUSDT"})

        assert d1.target_status == TECHNICAL_SIGNAL_STATUS_CONSUMED
        assert d2.target_status == TECHNICAL_SIGNAL_STATUS_CONSUMED, (
            "decision_id diferente bloqueado incorretamente"
        )


class TestOrderLayerRetrocompatSemDecisionId:
    """Fluxo legado sem decision_id nao deve ser afetado pelo gate."""

    def test_legado_sem_decision_id_aceito(self) -> None:
        """Sinal legado sem decision_id deve ser aceito normalmente."""
        sinal_legado = OrderLayerInput(
            signal_id=2,
            opportunity_id=20,
            symbol="BTCUSDT",
            timeframe="H4",
            signal_side="LONG",
            entry_type="MARKET",
            entry_price=97.0,
            stop_loss=90.0,
            take_profit=110.0,
            status=TECHNICAL_SIGNAL_STATUS_CREATED,
            signal_timestamp=1_700_000_100_000,
            payload={},
            decision_timestamp=1_700_000_200_000,
            decision_id=None,
        )
        decisao = evaluate_signal_for_order_layer(sinal_legado, authorized_symbols={"BTCUSDT"})

        assert decisao.target_status == TECHNICAL_SIGNAL_STATUS_CONSUMED, (
            f"Legado sem decision_id bloqueado: {decisao.target_status}"
        )

    def test_legado_duplicado_sem_decision_id_nao_bloqueado_por_gate(self) -> None:
        """Dois sinais legados (decision_id=None) nao devem ser bloqueados pelo gate."""
        sinal_legado = OrderLayerInput(
            signal_id=3,
            opportunity_id=30,
            symbol="BTCUSDT",
            timeframe="H4",
            signal_side="LONG",
            entry_type="MARKET",
            entry_price=97.0,
            stop_loss=90.0,
            take_profit=110.0,
            status=TECHNICAL_SIGNAL_STATUS_CREATED,
            signal_timestamp=1_700_000_100_000,
            payload={},
            decision_timestamp=1_700_000_200_000,
            decision_id=None,
        )
        d1 = evaluate_signal_for_order_layer(sinal_legado, authorized_symbols={"BTCUSDT"})
        d2 = evaluate_signal_for_order_layer(sinal_legado, authorized_symbols={"BTCUSDT"})

        assert d1.target_status == TECHNICAL_SIGNAL_STATUS_CONSUMED
        assert d2.target_status == TECHNICAL_SIGNAL_STATUS_CONSUMED
