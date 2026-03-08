"""Canonical state contract for Model 2.0 thesis lifecycle."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Mapping


class ThesisStatus(str, Enum):
    """Official states for a Model 2.0 thesis."""

    IDENTIFICADA = "IDENTIFICADA"
    MONITORANDO = "MONITORANDO"
    VALIDADA = "VALIDADA"
    INVALIDADA = "INVALIDADA"
    EXPIRADA = "EXPIRADA"


OFFICIAL_THESIS_STATUSES: tuple[str, ...] = tuple(status.value for status in ThesisStatus)
INITIAL_THESIS_STATUS: ThesisStatus = ThesisStatus.IDENTIFICADA
FINAL_THESIS_STATUSES: frozenset[ThesisStatus] = frozenset(
    {
        ThesisStatus.VALIDADA,
        ThesisStatus.INVALIDADA,
        ThesisStatus.EXPIRADA,
    }
)

ALLOWED_TRANSITIONS: Mapping[ThesisStatus | None, FrozenSet[ThesisStatus]] = {
    None: frozenset({ThesisStatus.IDENTIFICADA}),
    ThesisStatus.IDENTIFICADA: frozenset({ThesisStatus.MONITORANDO}),
    ThesisStatus.MONITORANDO: frozenset(
        {
            ThesisStatus.VALIDADA,
            ThesisStatus.INVALIDADA,
            ThesisStatus.EXPIRADA,
        }
    ),
    ThesisStatus.VALIDADA: frozenset(),
    ThesisStatus.INVALIDADA: frozenset(),
    ThesisStatus.EXPIRADA: frozenset(),
}


def _coerce_status(value: ThesisStatus | str | None) -> ThesisStatus | None:
    if value is None:
        return None

    if isinstance(value, ThesisStatus):
        return value

    if isinstance(value, str):
        try:
            return ThesisStatus(value)
        except ValueError:
            return None

    return None


def is_valid_transition(from_status: ThesisStatus | str | None, to_status: ThesisStatus | str) -> bool:
    """Return True when the transition belongs to the official transition matrix."""

    source = _coerce_status(from_status)
    target = _coerce_status(to_status)

    if source is None and from_status is not None:
        return False

    if target is None:
        return False

    return target in ALLOWED_TRANSITIONS.get(source, frozenset())
