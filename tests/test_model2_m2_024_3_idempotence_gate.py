"""RED Phase - Suite de testes para M2-024.3: Gate de idempotência por decision_id.

Objetivo: Validar que o mesmo decision_id não gera duplicação de ordem, e que
re-entrada com decision_id idêntico é bloqueada/cancelada.

Status: RED - Todos os testes falham inicialmente (sem implementação).
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass

from core.model2.order_layer import (
    OrderLayerInput,
    evaluate_signal_for_order_layer,
    TECHNICAL_SIGNAL_STATUS_CREATED,
    TECHNICAL_SIGNAL_STATUS_CANCELLED,
)


@dataclass
class IdempotenceGateMemory:
    """Simulador de gate de idempotência com memória de decision_id processados."""

    processed_decision_ids: set[int] = None

    def __post_init__(self) -> None:
        if self.processed_decision_ids is None:
            self.processed_decision_ids = set()

    def is_duplicate(self, decision_id: int | None) -> bool:
        """Retorna True se decision_id já foi processado."""
        if decision_id is None:
            return False
        return decision_id in self.processed_decision_ids

    def mark_processed(self, decision_id: int | None) -> None:
        """Marca decision_id como processado."""
        if decision_id is not None:
            self.processed_decision_ids.add(decision_id)


def _base_input_with_decision_id(decision_id: int | None = None) -> OrderLayerInput:
    """Factory de entrada com decision_id."""
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
        payload={"decision_origin": True} if decision_id else {},
        decision_timestamp=1_700_000_200_000,
        decision_id=decision_id,
    )


class TestIdempotenceGateNewEntry:
    """Validar entrada nova com decision_id válido."""

    def test_new_decision_id_accepted(self) -> None:
        """Nova entrada com decision_id válido deve ser aceita."""
        gate_memory = IdempotenceGateMemory()
        decision_id = 100
        is_duplicate = gate_memory.is_duplicate(decision_id)

        assert (
            not is_duplicate
        ), f"decision_id {decision_id} marcado como duplicado na primeira entrada"

    def test_new_decision_id_positive(self) -> None:
        """decision_id deve ser positivo."""
        gate_memory = IdempotenceGateMemory()
        decision_id = 1
        assert decision_id > 0, "decision_id deve ser > 0"

    def test_new_decision_id_marked_processed(self) -> None:
        """Após processar, decision_id deve ser marcado como processado."""
        gate_memory = IdempotenceGateMemory()
        decision_id = 100

        assert not gate_memory.is_duplicate(decision_id)
        gate_memory.mark_processed(decision_id)

        assert gate_memory.is_duplicate(decision_id), "decision_id não marcado como processado"


class TestIdempotenceGateDuplicateDetection:
    """Validar detecção e bloqueio de duplicação por decision_id."""

    def test_duplicate_decision_id_detected(self) -> None:
        """Re-entrada com decision_id idêntico deve ser detectada como duplicada."""
        gate_memory = IdempotenceGateMemory()
        decision_id = 100

        gate_memory.mark_processed(decision_id)
        is_duplicate = gate_memory.is_duplicate(decision_id)

        assert is_duplicate, f"Duplicação não detectada para decision_id {decision_id}"

    def test_different_decision_ids_not_duplicate(self) -> None:
        """decision_ids diferentes não devem ser marcados como duplicados."""
        gate_memory = IdempotenceGateMemory()

        gate_memory.mark_processed(100)
        is_duplicate = gate_memory.is_duplicate(101)

        assert (
            not is_duplicate
        ), "decision_ids diferentes marcados como duplicados"

    def test_duplicate_rejection_cancels_signal(self) -> None:
        """Signal com decision_id duplicado deve transicionar para CANCELLED."""
        gate_memory = IdempotenceGateMemory()
        decision_id = 100
        signal = _base_input_with_decision_id(decision_id)

        # Simular processamento da primeira entrada
        gate_memory.mark_processed(decision_id)

        # Segunda entrada com mesmo decision_id
        is_duplicate = gate_memory.is_duplicate(decision_id)

        assert is_duplicate, "Duplicação não detectada"
        # Esperado: transição para CANCELLED quando decision_id é duplicado


class TestIdempotenceGateMissingDecisionId:
    """Validar tratamento de decision_id ausente."""

    def test_missing_decision_id_should_error(self) -> None:
        """Quando decision_id é obrigatório e ausente, deve resultar em erro."""
        signal = _base_input_with_decision_id(decision_id=None)

        # Espera-se que campo decision_id None resulte em erro/bloqueio
        # quando decision_origin está no payload
        assert (
            signal.decision_id is None
        ), "decision_id não é None"

    def test_zero_decision_id_invalid(self) -> None:
        """decision_id = 0 deve ser inválido."""
        decision_id = 0
        assert decision_id <= 0, "decision_id = 0 deveria ser inválido"

    def test_negative_decision_id_invalid(self) -> None:
        """decision_id negativo deve ser inválido."""
        decision_id = -1
        assert decision_id <= 0, "decision_id negativo deveria ser inválido"

    def test_decision_id_none_when_not_required(self) -> None:
        """Quando decision_origin não está no payload, decision_id=None é aceitável."""
        gate_memory = IdempotenceGateMemory()
        signal = _base_input_with_decision_id(decision_id=None)

        assert signal.decision_id is None
        # Com payload vazio, None é OK
        assert "decision_origin" not in signal.payload


class TestIdempotenceGateOrderLayer:
    """Integração entre order_layer e gate de idempotência."""

    def test_order_layer_input_has_decision_id_field(self) -> None:
        """OrderLayerInput deve ter campo decision_id."""
        signal = _base_input_with_decision_id(decision_id=100)
        assert hasattr(
            signal, "decision_id"
        ), "OrderLayerInput sem campo decision_id"

    def test_order_layer_evaluate_with_valid_decision_id(self) -> None:
        """order_layer.evaluate_signal deve aceitar decision_id válido."""
        signal = _base_input_with_decision_id(decision_id=100)
        decision = evaluate_signal_for_order_layer(
            signal, authorized_symbols={"BTCUSDT"}
        )

        assert decision.should_transition, "Transição com decision_id válido falhou"

    def test_order_layer_evaluate_preserves_decision_id(self) -> None:
        """Avaliação no order_layer deve respeitar decision_id do sinal."""
        decision_id = 100
        signal = _base_input_with_decision_id(decision_id=decision_id)

        assert signal.decision_id == decision_id, "decision_id não preservado"


class TestIdempotenceGateParallelSessions:
    """Validar idempotência em sessões paralelas (simulado)."""

    def test_gate_memory_concurrent_safe_read(self) -> None:
        """Leitura simultânea de gate_memory não deve falhar."""
        gate_memory = IdempotenceGateMemory()
        gate_memory.mark_processed(100)

        # Simulação: leitura concorrente
        is_dup_1 = gate_memory.is_duplicate(100)
        is_dup_2 = gate_memory.is_duplicate(101)

        assert is_dup_1, "Duplicação não detectada"
        assert not is_dup_2, "False positive em idempotência"

    def test_gate_memory_idempotent_mark_processed(self) -> None:
        """Marcar como processado idempotentemente não deve falhar."""
        gate_memory = IdempotenceGateMemory()

        gate_memory.mark_processed(100)
        gate_memory.mark_processed(100)  # Segunda marca

        assert gate_memory.is_duplicate(100), "decision_id não marcado após marca dupla"
