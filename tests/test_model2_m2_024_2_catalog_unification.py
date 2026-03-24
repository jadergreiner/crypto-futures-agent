"""RED Phase - Suite de testes para M2-024.2: Unificacao do catalogo canonico de reason_code.

Objetivo: Garantir que order_layer importa REASON_CODE_CATALOG de live_execution
(fonte unica), eliminando duplicidade e divergencia entre modulos.

Status: RED - testes falham antes da unificacao de importacao em order_layer.py
"""

from __future__ import annotations

import inspect

import pytest

from core.model2 import live_execution, order_layer
from core.model2.live_execution import (
    REASON_CODE_ACTION,
    REASON_CODE_CATALOG,
    REASON_CODE_SEVERITY,
)


class TestOrderLayerUsesCanonicalCatalog:
    """R4: order_layer deve usar REASON_CODE_CATALOG de live_execution (sem copia local)."""

    def test_order_layer_imports_reason_code_catalog_from_live_execution(self) -> None:
        """order_layer.REASON_CODE_CATALOG deve ser o mesmo objeto de live_execution."""
        # RED: order_layer define catalogo local — identidade de objeto falha
        assert order_layer.REASON_CODE_CATALOG is live_execution.REASON_CODE_CATALOG, (
            "order_layer.REASON_CODE_CATALOG deve ser importado de live_execution, "
            "nao uma copia local"
        )

    def test_order_layer_does_not_define_local_reason_code_catalog(self) -> None:
        """order_layer.py nao deve definir REASON_CODE_CATALOG como literal dict local."""
        source = inspect.getsource(order_layer)
        # RED: order_layer define 'REASON_CODE_CATALOG: dict[str, str] = {' localmente
        assert "REASON_CODE_CATALOG: dict[str, str] = {" not in source, (
            "order_layer define REASON_CODE_CATALOG como dict literal local — "
            "deve importar de live_execution"
        )

    def test_order_layer_catalog_contains_all_canonical_entries(self) -> None:
        """order_layer.REASON_CODE_CATALOG deve ter todos os entries do catalogo canonico."""
        for key in REASON_CODE_CATALOG:
            assert key in order_layer.REASON_CODE_CATALOG, (
                f"Entry '{key}' ausente em order_layer.REASON_CODE_CATALOG"
            )

    def test_order_layer_catalog_includes_order_layer_specific_codes(self) -> None:
        """Codigos especificos do order_layer devem estar no catalogo canonico apos unificacao."""
        order_layer_specific = [
            "decision_recorded_no_real_order",
            "status_not_created",
            "missing_decision_id",
            "symbol_not_authorized",
            "short_only_enforced",
        ]
        for code in order_layer_specific:
            assert code in order_layer.REASON_CODE_CATALOG, (
                f"Codigo '{code}' especifico do order_layer ausente no catalogo unificado"
            )


class TestCatalogSymmetry:
    """R5: SEVERITY e ACTION devem cobrir exatamente os mesmos keys do CATALOG."""

    def test_severity_keys_match_catalog_keys_exactly(self) -> None:
        """REASON_CODE_SEVERITY deve ter exatamente os mesmos keys que REASON_CODE_CATALOG."""
        catalog_keys = set(REASON_CODE_CATALOG.keys())
        severity_keys = set(REASON_CODE_SEVERITY.keys())
        missing_in_severity = catalog_keys - severity_keys
        extra_in_severity = severity_keys - catalog_keys
        assert not missing_in_severity, (
            f"Keys no CATALOG sem SEVERITY: {missing_in_severity}"
        )
        assert not extra_in_severity, (
            f"Keys em SEVERITY sem CATALOG: {extra_in_severity}"
        )

    def test_action_keys_match_catalog_keys_exactly(self) -> None:
        """REASON_CODE_ACTION deve ter exatamente os mesmos keys que REASON_CODE_CATALOG."""
        catalog_keys = set(REASON_CODE_CATALOG.keys())
        action_keys = set(REASON_CODE_ACTION.keys())
        missing_in_action = catalog_keys - action_keys
        extra_in_action = action_keys - catalog_keys
        assert not missing_in_action, (
            f"Keys no CATALOG sem ACTION: {missing_in_action}"
        )
        assert not extra_in_action, (
            f"Keys em ACTION sem CATALOG: {extra_in_action}"
        )

    def test_order_layer_specific_codes_have_severity(self) -> None:
        """Codigos especificos do order_layer devem ter SEVERITY no catalogo canonico."""
        order_layer_codes = [
            "decision_recorded_no_real_order",
            "status_not_created",
            "missing_decision_id",
            "missing_signal_timestamp",
            "missing_payload_contract",
            "symbol_not_authorized",
            "unsupported_signal_side",
            "short_only_enforced",
            "unsupported_entry_type",
            "invalid_price_geometry",
        ]
        for code in order_layer_codes:
            assert code in REASON_CODE_SEVERITY, (
                f"Codigo do order_layer '{code}' sem SEVERITY no catalogo canonico"
            )

    def test_order_layer_specific_codes_have_action(self) -> None:
        """Codigos especificos do order_layer devem ter ACTION no catalogo canonico."""
        order_layer_codes = [
            "decision_recorded_no_real_order",
            "status_not_created",
            "missing_decision_id",
            "symbol_not_authorized",
            "short_only_enforced",
        ]
        for code in order_layer_codes:
            assert code in REASON_CODE_ACTION, (
                f"Codigo do order_layer '{code}' sem ACTION no catalogo canonico"
            )
