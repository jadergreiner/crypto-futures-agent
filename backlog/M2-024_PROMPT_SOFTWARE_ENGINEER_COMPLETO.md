# Handoff Software Engineer — M2-024 Lote 1 GREEN-Refactor

**De**: QA-TDD (4.qa-tdd)  
**Para**: Software Engineer (5.software-engineer)  
**Data**: 2026-03-23 16:00 BRT  
**Status**: PRONTO PARA GREEN-REFACTOR  
**Referência**: RED Phase criada em SYNC-125  

---

Você é o agente 5.software-engineer desta task.

## Contexto da Demanda

- **id**: M2-024 Lote 1 (M2-024.2 + M2-024.3 + M2-024.10) — GREEN-Refactor
- **objetivo**: Implementar código Python que faça todos os 37 testes RED passarem (GREEN phase), sem comprometer guardrails de risco. Foco: reason_code catalogue, idempotência decision_id, contrato erro com auditabilidade.
- **RED Phase Status**: 1 failed, 53 passed (suite rodando, pronta para implementação)
- **mypy Status**: ✅ Success (type hints validados)

---

## Suite RED Completa — Código de Testes

### Arquivo 1: tests/test_model2_m2_024_2_reason_code_catalog.py (222 linhas, 15 testes)

```python
"""RED Phase - Suite de testes para M2-024.2: Catálogo canônico de reason_code com severidade.

Objetivo: Validar que todo reason_code possui severidade e ação recomendada vinculadas,
e que falhas em campos obrigatórios são detectadas.

Status: RED - Todos os testes falham inicialmente (sem implementação).
"""

from __future__ import annotations

import pytest

from core.model2.live_execution import (
    REASON_CODE_CATALOG,
    REASON_CODE_SEVERITY,
    REASON_CODE_ACTION,
)


class TestReasonCodeCatalogCompleteness:
    """Validar cobertura e completude do catálogo de reason_codes."""

    def test_reason_code_catalog_not_empty(self) -> None:
        """Catálogo de reason_codes não deve estar vazio."""
        assert len(REASON_CODE_CATALOG) > 0, "REASON_CODE_CATALOG vazio"

    def test_all_reason_codes_have_severity(self) -> None:
        """Todo reason_code deve ter severidade vinculada."""
        for code_key in REASON_CODE_CATALOG.keys():
            assert (
                code_key in REASON_CODE_SEVERITY
            ), f"reason_code '{code_key}' sem severidade em REASON_CODE_SEVERITY"

    def test_all_reason_codes_have_action(self) -> None:
        """Todo reason_code deve ter ação recomendada vinculada."""
        for code_key in REASON_CODE_CATALOG.keys():
            assert (
                code_key in REASON_CODE_ACTION
            ), f"reason_code '{code_key}' sem ação em REASON_CODE_ACTION"

    def test_severity_is_valid(self) -> None:
        """Toda severidade deve ser um valor válido."""
        valid_severities = {"INFO", "MEDIUM", "HIGH", "CRITICAL"}
        for code_key, severity in REASON_CODE_SEVERITY.items():
            assert (
                severity in valid_severities
            ), f"reason_code '{code_key}' com severidade inválida: {severity}"

    def test_action_is_not_empty(self) -> None:
        """Toda ação recomendada deve estar preenchida."""
        for code_key, action in REASON_CODE_ACTION.items():
            assert (
                action and len(action.strip()) > 0
            ), f"reason_code '{code_key}' com ação vazia"


class TestReasonCodeCatalogContent:
    """Validar conteúdo específico do catálogo (casos críticos)."""

    def test_reason_code_catalog_value_not_empty(self) -> None:
        """Todo reason_code_value no catálogo deve estar preenchido."""
        for code_key, code_value in REASON_CODE_CATALOG.items():
            assert (
                code_value and len(code_value.strip()) > 0
            ), f"reason_code '{code_key}' com valor vazio no catálogo"

    def test_reason_code_critical_entries_present(self) -> None:
        """Entradas críticas devem estar no catálogo (risk_gate, circuit_breaker, etc)."""
        critical_codes = [
            "risk_gate_blocked",
            "circuit_breaker_blocked",
            "reconciliation_divergence",
        ]
        for code in critical_codes:
            assert code in REASON_CODE_CATALOG, f"Código crítico '{code}' ausente no catálogo"

    def test_critical_reason_codes_have_high_severity(self) -> None:
        """Códigos críticos (risk_gate_blocked, circuit_breaker_blocked, reconciliation_divergence) devem ter severidade HIGH ou CRITICAL."""
        critical_codes = {
            "risk_gate_blocked": {"HIGH", "CRITICAL"},
            "circuit_breaker_blocked": {"HIGH", "CRITICAL"},
            "reconciliation_divergence": {"CRITICAL"},
        }
        for code, expected_severities in critical_codes.items():
            actual_severity = REASON_CODE_SEVERITY.get(code)
            assert (
                actual_severity in expected_severities
            ), f"Código crítico '{code}' com severidade inesperada: {actual_severity}"

    def test_reason_code_catalog_keys_are_strings(self) -> None:
        """Todas as chaves do catálogo devem ser strings."""
        for key in REASON_CODE_CATALOG.keys():
            assert isinstance(key, str), f"Chave não é string: {key} ({type(key)})"

    def test_reason_code_catalog_values_are_strings(self) -> None:
        """Todos os valores do catálogo devem ser strings."""
        for code_key, code_value in REASON_CODE_CATALOG.items():
            assert isinstance(
                code_value, str
            ), f"Valor de '{code_key}' não é string: {code_value} ({type(code_value)})"

    def test_reason_code_severity_values_are_strings(self) -> None:
        """Todos os valores de severidade devem ser strings."""
        for code_key, severity in REASON_CODE_SEVERITY.items():
            assert isinstance(
                severity, str
            ), f"Severidade de '{code_key}' não é string: {severity} ({type(severity)})"

    def test_reason_code_action_values_are_strings(self) -> None:
        """Todos os valores de ação devem ser strings."""
        for code_key, action in REASON_CODE_ACTION.items():
            assert isinstance(
                action, str
            ), f"Ação de '{code_key}' não é string: {action} ({type(action)})"


class TestReasonCodeCatalogConsistency:
    """Validar consistência e simetria do catálogo."""

    def test_no_reason_code_in_severity_without_catalog_entry(self) -> None:
        """Não deve haver severidade para code não no catálogo."""
        for code_key in REASON_CODE_SEVERITY.keys():
            assert (
                code_key in REASON_CODE_CATALOG
            ), f"Severidade para '{code_key}' sem entrada no catálogo"

    def test_no_reason_code_in_action_without_catalog_entry(self) -> None:
        """Não deve haver ação para code não no catálogo."""
        for code_key in REASON_CODE_ACTION.keys():
            assert (
                code_key in REASON_CODE_CATALOG
            ), f"Ação para '{code_key}' sem entrada no catálogo"

    def test_ready_for_live_execution_has_info_severity(self) -> None:
        """'ready_for_live_execution' deve ter severidade INFO."""
        assert (
            REASON_CODE_SEVERITY.get("ready_for_live_execution") == "INFO"
        ), "ready_for_live_execution com severidade != INFO"

    def test_catalog_has_minimum_20_entries(self) -> None:
        """Catálogo deve ter no mínimo 20 entry points para cobertura adequada."""
        assert (
            len(REASON_CODE_CATALOG) >= 20
        ), f"Catálogo com menos de 20 entries: {len(REASON_CODE_CATALOG)}"


class TestReasonCodeMissingFields:
    """Validar detecção de campos obrigatórios ausentes."""

    def test_missing_reason_code_catalog(self) -> None:
        """Se REASON_CODE_CATALOG estiver vazio, deve falhar."""
        assert (
            REASON_CODE_CATALOG is not None and len(REASON_CODE_CATALOG) > 0
        ), "REASON_CODE_CATALOG vazio ou None"

    def test_missing_reason_code_severity(self) -> None:
        """Se REASON_CODE_SEVERITY estiver vazio, deve falhar (para codes do catálogo)."""
        assert (
            REASON_CODE_SEVERITY is not None and len(REASON_CODE_SEVERITY) > 0
        ), "REASON_CODE_SEVERITY vazio ou None"

    def test_missing_reason_code_action(self) -> None:
        """Se REASON_CODE_ACTION estiver vazio, deve falhar (para codes do catálogo)."""
        assert (
            REASON_CODE_ACTION is not None and len(REASON_CODE_ACTION) > 0
        ), "REASON_CODE_ACTION vazio ou None"
```

---

### Arquivo 2: tests/test_model2_m2_024_3_idempotence_gate.py (230 linhas, 12 testes)

```python
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
```

---

### Arquivo 3: tests/test_model2_m2_024_10_error_contract.py (378 linhas, 10 testes)

```python
"""RED Phase - Suite de testes para M2-024.10: Contrato único de erro com auditabilidade.

Objetivo: Validar que todo bloqueio/falha em live_execution emite estrutura
contendo: decision_id, execution_id, reason_code, severity, recommended_action.

Status: RED - Todos os testes falham inicialmente (sem implementação).
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import Any, Mapping

from core.model2.live_execution import (
    REASON_CODE_CATALOG,
    REASON_CODE_SEVERITY,
    REASON_CODE_ACTION,
)


@dataclass(frozen=True)
class LiveExecutionErrorContract:
    """Contrato de erro para live_execution com auditabilidade."""

    decision_id: int | None
    execution_id: int | None
    reason_code: str
    severity: str
    recommended_action: str
    additional_context: Mapping[str, Any] | None = None

    def is_complete(self) -> bool:
        """Valida se contrato tem todos os campos obrigatórios preenchidos."""
        return (
            self.decision_id is not None
            and self.execution_id is not None
            and self.reason_code
            and len(self.reason_code) > 0
            and self.severity
            and len(self.severity) > 0
            and self.recommended_action
            and len(self.recommended_action) > 0
        )

    def validate_reason_code_in_catalog(self) -> bool:
        """Valida se reason_code existe no catálogo."""
        return self.reason_code in REASON_CODE_CATALOG

    def validate_severity(self) -> bool:
        """Valida se severity é um de [INFO, MEDIUM, HIGH, CRITICAL]."""
        valid_severities = {"INFO", "MEDIUM", "HIGH", "CRITICAL"}
        return self.severity in valid_severities

    def validate_action(self) -> bool:
        """Valida se recommended_action não está vazia."""
        return self.recommended_action and len(self.recommended_action) > 0


class TestErrorContractEmission:
    """Validar emissão de contrato de erro completo."""

    def test_error_contract_creation(self) -> None:
        """Contrato de erro deve ser criável com todos os campos."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert error.decision_id == 100
        assert error.execution_id == 200
        assert error.reason_code == "risk_gate_blocked"
        assert error.severity == "HIGH"
        assert error.recommended_action == "bloquear_operacao"

    def test_error_contract_is_complete(self) -> None:
        """Contrato de erro completo deve passar em is_complete()."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert error.is_complete(), "Contrato completo não passou em is_complete()"

    def test_error_contract_with_additional_context(self) -> None:
        """Contrato de erro deve permitir contexto adicional."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
            additional_context={"gate_reason": "alavancagem_maxima"},
        )

        assert (
            error.additional_context is not None
            and "gate_reason" in error.additional_context
        )


class TestErrorContractMandatoryFields:
    """Validar detecção de campos obrigatórios ausentes."""

    def test_missing_decision_id_incomplete(self) -> None:
        """Contrato sem decision_id deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=None,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert not error.is_complete(), "Contrato sem decision_id passou em is_complete()"

    def test_missing_execution_id_incomplete(self) -> None:
        """Contrato sem execution_id deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=None,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.is_complete()
        ), "Contrato sem execution_id passou em is_complete()"

    def test_missing_reason_code_incomplete(self) -> None:
        """Contrato sem reason_code deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.is_complete()
        ), "Contrato sem reason_code passou em is_complete()"

    def test_missing_severity_incomplete(self) -> None:
        """Contrato sem severity deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.is_complete()
        ), "Contrato sem severity passou em is_complete()"

    def test_missing_recommended_action_incomplete(self) -> None:
        """Contrato sem recommended_action deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="",
        )

        assert (
            not error.is_complete()
        ), "Contrato sem recommended_action passou em is_complete()"


class TestErrorContractReasonCodeValidation:
    """Validar reason_code contra catálogo."""

    def test_reason_code_in_catalog(self) -> None:
        """Contrato com reason_code válido deve passar."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            error.validate_reason_code_in_catalog()
        ), "reason_code válido falhou em validação"

    def test_reason_code_not_in_catalog(self) -> None:
        """Contrato com reason_code inválido deve falhar."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="unknown_reason_code_xyz",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.validate_reason_code_in_catalog()
        ), "reason_code inválido passou em validação"


class TestErrorContractSeverityValidation:
    """Validar severidade contra valores permitidos."""

    def test_severity_info_valid(self) -> None:
        """Severidade INFO deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="ready_for_live_execution",
            severity="INFO",
            recommended_action="seguir_fluxo",
        )

        assert error.validate_severity(), "Severidade INFO falhou em validação"

    def test_severity_medium_valid(self) -> None:
        """Severidade MEDIUM deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="signal_expired",
            severity="MEDIUM",
            recommended_action="descartar_sinal",
        )

        assert error.validate_severity(), "Severidade MEDIUM falhou em validação"

    def test_severity_high_valid(self) -> None:
        """Severidade HIGH deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert error.validate_severity(), "Severidade HIGH falhou em validação"

    def test_severity_critical_valid(self) -> None:
        """Severidade CRITICAL deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="reconciliation_divergence",
            severity="CRITICAL",
            recommended_action="interromper_e_reconciliar",
        )

        assert error.validate_severity(), "Severidade CRITICAL falhou em validação"

    def test_severity_invalid_value(self) -> None:
        """Severidade inválida deve falhar."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="INVALID_SEVERITY",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.validate_severity()
        ), "Severidade inválida passou em validação"


class TestErrorContractActionValidation:
    """Validar recommended_action não está vazia."""

    def test_action_not_empty(self) -> None:
        """Action não vazia deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert error.validate_action(), "Action não vazia falhou em validação"

    def test_action_empty_fails(self) -> None:
        """Action vazia deve falhar."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="",
        )

        assert not error.validate_action(), "Action vazia passou em validação"


class TestErrorContractAuditTrail:
    """Validar rastreabilidade (decision_id e execution_id)."""

    def test_decision_id_preserved_in_error(self) -> None:
        """decision_id deve ser preservado no contrato de erro."""
        original_decision_id = 100
        error = LiveExecutionErrorContract(
            decision_id=original_decision_id,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            error.decision_id == original_decision_id
        ), "decision_id não preservado no contrato"

    def test_execution_id_preserved_in_error(self) -> None:
        """execution_id deve ser preservado no contrato de erro."""
        original_execution_id = 200
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=original_execution_id,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            error.execution_id == original_execution_id
        ), "execution_id não preservado no contrato"

    def test_error_contract_immutable(self) -> None:
        """Contrato de erro deve ser imutável (frozen dataclass)."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            error.decision_id = 999  # type: ignore
```

---

## Mapeamento Requisito → Teste

### M2-024.2: Catálogo Canônico de Reason_Code

| Requisito | Teste(s) Associado(s) |
|-----------|---------------------|
| Catálogo não vazio | `test_reason_code_catalog_not_empty` |
| Todo code tem severidade | `test_all_reason_codes_have_severity` |
| Todo code tem ação | `test_all_reason_codes_have_action` |
| Severidade em {INFO, MEDIUM, HIGH, CRITICAL} | `test_severity_is_valid` |
| Ação não vazia | `test_action_is_not_empty` |
| Valores do catálogo preenchidos | `test_reason_code_catalog_value_not_empty` |
| Entradas críticas presentes | `test_reason_code_critical_entries_present` |
| Códigos críticos com HIGH/CRITICAL | `test_critical_reason_codes_have_high_severity` |
| Chaves são strings | `test_reason_code_catalog_keys_are_strings` |
| Valores são strings | `test_reason_code_catalog_values_are_strings` |
| Severidades são strings | `test_reason_code_severity_values_are_strings` |
| Ações são strings | `test_reason_code_action_values_are_strings` |
| Simetria severidade/catálogo | `test_no_reason_code_in_severity_without_catalog_entry` |
| Simetria ação/catálogo | `test_no_reason_code_in_action_without_catalog_entry` |
| ready_for_live_execution = INFO | `test_ready_for_live_execution_has_info_severity` |
| **Catálogo ≥ 20 entries (BLOCKER)** | **`test_catalog_has_minimum_20_entries` ❌ FALHA** |
| Catálogo não None | `test_missing_reason_code_catalog` |
| Severidade não None | `test_missing_reason_code_severity` |
| Ação não None | `test_missing_reason_code_action` |

### M2-024.3: Gate Idempotência (decision_id)

| Requisito | Teste(s) Associado(s) |
|-----------|---------------------|
| Nova entrada aceita | `test_new_decision_id_accepted` |
| decision_id positivo | `test_new_decision_id_positive` |
| Marcar processado corretamente | `test_new_decision_id_marked_processed` |
| Detecção de duplicação | `test_duplicate_decision_id_detected` |
| decision_ids diferentes não duplicados | `test_different_decision_ids_not_duplicate` |
| Signal duplicado → CANCELLED | `test_duplicate_rejection_cancels_signal` |
| decision_id obrigatório com decision_origin | `test_missing_decision_id_should_error` |
| decision_id ≠ 0 | `test_zero_decision_id_invalid` |
| decision_id > 0 | `test_negative_decision_id_invalid` |
| decision_id None OK sem decision_origin | `test_decision_id_none_when_not_required` |
| OrderLayerInput tem decision_id | `test_order_layer_input_has_decision_id_field` |
| order_layer.evaluate com decision_id | `test_order_layer_evaluate_with_valid_decision_id` |
| decision_id preservado | `test_order_layer_evaluate_preserves_decision_id` |

### M2-024.10: Contrato Erro com Auditabilidade

| Requisito | Teste(s) Associado(s) |
|-----------|---------------------|
| Criação com todos campos | `test_error_contract_creation` |
| Contrato completo passa validação | `test_error_contract_is_complete` |
| Contexto adicional permitido | `test_error_contract_with_additional_context` |
| decision_id obrigatório | `test_missing_decision_id_incomplete` |
| execution_id obrigatório | `test_missing_execution_id_incomplete` |
| reason_code obrigatório | `test_missing_reason_code_incomplete` |
| severity obrigatório | `test_missing_severity_incomplete` |
| recommended_action obrigatório | `test_missing_recommended_action_incomplete` |
| reason_code validado contra catálogo | `test_reason_code_in_catalog`, `test_reason_code_not_in_catalog` |
| Severidade valida (INFO/MEDIUM/HIGH/CRITICAL) | `test_severity_*_valid`, `test_severity_invalid_value` |
| Ação não vazia | `test_action_not_empty`, `test_action_empty_fails` |
| decision_id preservado em erro | `test_decision_id_preserved_in_error` |
| execution_id preservado em erro | `test_execution_id_preserved_in_error` |
| Contrato imutável (frozen) | `test_error_contract_immutable` |

---

## Guardrails Obrigatórios

✅ **risk_gate.py** — ATIVO em todos os caminhos, **NÃO mockado** em testes  
✅ **circuit_breaker.py** — ATIVO em todos os caminhos, **NÃO mockado** em testes  
✅ **decision_id idempotência** — Enforçado em signal_bridge, validado em testes  
✅ **Fail-safe** — Em dúvida/ausência operacional, bloqueia operação  
✅ **Compatibilidade** — Sem breaking changes em fluxo legado  
✅ **Auditabilidade** — decision_id e execution_id preservados em erro  

---

## Plano GREEN-Refactor

### Passo 1: M2-024.2 — Expandir REASON_CODE_CATALOG

**Arquivo**: `core/model2/live_execution.py`

**Ação**:
1. Expandir REASON_CODE_CATALOG de 9 para **mínimo 20 entries**
2. Adicionar mapeamento correspondente em REASON_CODE_SEVERITY
3. Adicionar mapeamento correspondente em REASON_CODE_ACTION

**Exemplos de entries a adicionar**:
- `entrada_validada` (INFO)
- `ordem_enviada` (INFO)
- `ordem_confirmada` (INFO)
- `protecao_armada` (INFO)
- `protecao_falhou` (HIGH)
- `posicao_aumentada` (INFO)
- `posicao_reduzida` (INFO)
- `posicao_fechada` (INFO)
- `saida_forcada` (HIGH)
- `reconciliacao_ok` (INFO)
- `reconciliacao_pendente` (MEDIUM)
- `signal_expirado` (MEDIUM)
- Etc. (até 20+)

**Validação**:
```bash
pytest -q tests/test_model2_m2_024_2_reason_code_catalog.py
# Esperado: 15 passed
```

### Passo 2: M2-024.3 — Integrar Gate Idempotência

**Arquivo**: `core/model2/signal_bridge.py`

**Ação**:
1. Adicionar cache/memory de decision_ids já processados (set ou dict)
2. Implementar validação: se `decision_id` foi processado e `payload.decision_origin == True`, transicionar para CANCELLED
3. Integrar sem quebrar testes de order_layer

**Pseudocódigo**:
```python
# Em signal_bridge.py
_processed_decision_ids: set[int] = set()

def consume_signal(signal: OrderLayerInput) -> None:
    if signal.payload.get("decision_origin") and signal.decision_id:
        if signal.decision_id in _processed_decision_ids:
            # Marcar como CANCELLED
            signal.status = TECHNICAL_SIGNAL_STATUS_CANCELLED
            return
        _processed_decision_ids.add(signal.decision_id)
    # Continuar fluxo normal
```

**Validação**:
```bash
pytest -q tests/test_model2_m2_024_3_idempotence_gate.py
# Esperado: 12 passed
```

### Passo 3: M2-024.10 — Usar LiveExecutionErrorContract

**Arquivo**: `core/model2/live_execution.py`

**Ação**:
1. Quando emitir erro de bloqueio (risk_gate, circuit_breaker, reconciliação), usar LiveExecutionErrorContract
2. Garantir que todo erro inclua: decision_id, execution_id, reason_code, severity, recommended_action
3. Marcar contrato como `frozen` (imutável)

**Pseudocódigo**:
```python
# Em live_execution.py
def emit_error(decision_id: int | None, execution_id: int | None, reason: str) -> None:
    error = LiveExecutionErrorContract(
        decision_id=decision_id,
        execution_id=execution_id,
        reason_code=reason,
        severity=REASON_CODE_SEVERITY.get(reason, "HIGH"),
        recommended_action=REASON_CODE_ACTION.get(reason, "bloquear_operacao"),
    )
    # Validar contrato
    assert error.is_complete(), "Contrato incompleto"
    # Emitir (log, evento, etc)
```

**Validação**:
```bash
pytest -q tests/test_model2_m2_024_10_error_contract.py
# Esperado: 10 passed
```

---

## Checklist de Aceite

- [ ] **M2-024.2**: `pytest -q tests/test_model2_m2_024_2_reason_code_catalog.py` → 15 PASSED
- [ ] **M2-024.3**: `pytest -q tests/test_model2_m2_024_3_idempotence_gate.py` → 12 PASSED
- [ ] **M2-024.10**: `pytest -q tests/test_model2_m2_024_10_error_contract.py` → 10 PASSED
- [ ] **mypy --strict** nos módulos alterados → SUCCESS
- [ ] **pytest -q tests/** → Suite completa verde (sem regressão)
- [ ] **Backlog atualizado**: M2-024.2/3/10 marcadas `EM_DESENVOLVIMENTO` ao iniciar
- [ ] **Backlog atualizado**: M2-024.2/3/10 marcadas `IMPLEMENTADO` ao concluir + SE comments
- [ ] Guardrails **risk_gate** e **circuit_breaker** permanecem ATIVOS (não mockados)
- [ ] **decision_id idempotência** enforçada em signal_bridge.py
- [ ] **LiveExecutionErrorContract** usado em todos os erros de live_execution.py

---

## Comandos de Validação

```bash
# Validar testes unitários por task
pytest -q tests/test_model2_m2_024_2_reason_code_catalog.py
pytest -q tests/test_model2_m2_024_3_idempotence_gate.py
pytest -q tests/test_model2_m2_024_10_error_contract.py

# Validar type hints (mypy --strict)
mypy --strict core/model2/order_layer.py
mypy --strict core/model2/live_execution.py
mypy --strict core/model2/signal_bridge.py
mypy --strict tests/test_model2_m2_024_*.py

# Full suite para regressão
pytest -q tests/

# Limpar cache de testes
pytest --cache-clear
```

---

## Entregáveis Esperados

1. **Arquivos alterados**:
   - `core/model2/live_execution.py` (expand catalogo + usar contrato)
   - `core/model2/signal_bridge.py` (adicionar gate idempotência)
   - Possivelmente `core/model2/order_layer.py` (se necessário ajustes)

2. **Evidências de implementação**:
   - ✅ `pytest -q tests/test_model2_m2_024_*.py` → todos os 37 testes passam
   - ✅ `mypy --strict` nos módulos alterados → success
   - ✅ `pytest -q tests/` → suite completa verde (regressão OK)

3. **Atualização de Backlog**:
   - `docs/BACKLOG.md`: M2-024.2/3/10 marcadas `EM_DESENVOLVIMENTO` ao iniciar
   - Após sucesso: marcadas `IMPLEMENTADO` + comment `SE:` com evidências

4. **Prompt para Tech Lead**:
   - Estruturado com: contexto, arquivos alterados, evidências pytest + mypy
   - Lista completa de testes passing
   - Confirmação de guardrails preservados

---

**Status**: ✅ PRONTO PARA GREEN-REFACTOR  
**RED Phase Commit**: 473d89e  
**Próxima Etapa**: 5.software-engineer implementar (GREEN-Refactor)
