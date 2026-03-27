from __future__ import annotations

from typing import Any, Mapping


def compact_handoff_payload(
    *,
    payload: Mapping[str, Any],
    limit_chars: int,
    preserve_fields: list[str],
) -> dict[str, Any]:
    if limit_chars <= 0:
        raise ValueError("limit_chars_invalido")

    compacted = dict(payload)
    text_size = len(str(compacted))
    if text_size <= limit_chars:
        return compacted

    for key, value in list(compacted.items()):
        if len(str(compacted)) <= limit_chars:
            break
        if key in preserve_fields:
            continue
        as_text = str(value)
        if len(as_text) <= 32:
            continue
        compacted[key] = as_text[:29] + "..."

    if len(str(compacted)) > limit_chars:
        compacted["_compaction_warning"] = "payload_acima_do_limite_apos_compactacao"
    return compacted
