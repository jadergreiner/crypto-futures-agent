"""Core contracts for Model 2.0 domain logic."""

from .thesis_state import (
    ALLOWED_TRANSITIONS,
    FINAL_THESIS_STATUSES,
    INITIAL_THESIS_STATUS,
    OFFICIAL_THESIS_STATUSES,
    ThesisStatus,
    is_valid_transition,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "FINAL_THESIS_STATUSES",
    "INITIAL_THESIS_STATUS",
    "OFFICIAL_THESIS_STATUSES",
    "ThesisStatus",
    "is_valid_transition",
]
