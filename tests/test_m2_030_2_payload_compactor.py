"""RED->GREEN suite for M2-030.2 payload compactor."""

from __future__ import annotations

import pytest

from core.dev_cycle_payload_compactor import compact_handoff_payload


def test_compactor_preserves_payload_when_within_limit() -> None:
    payload = {"id": "M2-030.2", "resumo": "curto"}
    compacted = compact_handoff_payload(payload=payload, limit_chars=200, preserve_fields=["id"])
    assert compacted == payload


def test_compactor_truncates_non_preserved_fields_when_above_limit() -> None:
    payload = {
        "id": "M2-030.2",
        "resumo": "x" * 180,
        "detalhes": "y" * 180,
    }
    compacted = compact_handoff_payload(payload=payload, limit_chars=120, preserve_fields=["id"])
    assert compacted["id"] == "M2-030.2"
    assert str(compacted["resumo"]).endswith("...")
    assert str(compacted["detalhes"]).endswith("...")


def test_compactor_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="limit_chars_invalido"):
        compact_handoff_payload(payload={"id": "x"}, limit_chars=0, preserve_fields=["id"])
