"""Core contracts for Model 2.0 domain logic."""

from .thesis_state import (
    ALLOWED_TRANSITIONS,
    FINAL_THESIS_STATUSES,
    INITIAL_THESIS_STATUS,
    OFFICIAL_THESIS_STATUSES,
    ThesisStatus,
    is_valid_transition,
)
from .scanner import (
    DetectorInput,
    DetectionResult,
    M2_002_RULE_ID,
    M2_002_RULE_VERSION,
    M2_002_THESIS_TYPE,
    detect_initial_short_failure,
)
from .repository import (
    CreateInitialThesisResult,
    M2_003_1_RULE_ID,
    M2_003_2_RULE_ID,
    M2_003_3_RULE_ID_EXPIRATION,
    M2_003_3_RULE_ID_INVALIDATION,
    Model2ThesisRepository,
    TransitionToExpiredResult,
    TransitionToInvalidatedResult,
    TransitionToMonitoringResult,
    TransitionToValidatedResult,
)
from .resolver import (
    RESOLUTION_ACTION_EXPIRED,
    RESOLUTION_ACTION_INVALIDATED,
    RESOLUTION_ACTION_NONE,
    ResolutionDecision,
    ResolutionInput,
    evaluate_monitoring_resolution,
)
from .validator import (
    ValidationDecision,
    ValidationInput,
    evaluate_monitoring_validation,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "CreateInitialThesisResult",
    "DetectionResult",
    "DetectorInput",
    "FINAL_THESIS_STATUSES",
    "INITIAL_THESIS_STATUS",
    "M2_002_RULE_ID",
    "M2_002_RULE_VERSION",
    "M2_002_THESIS_TYPE",
    "M2_003_1_RULE_ID",
    "M2_003_2_RULE_ID",
    "M2_003_3_RULE_ID_EXPIRATION",
    "M2_003_3_RULE_ID_INVALIDATION",
    "Model2ThesisRepository",
    "OFFICIAL_THESIS_STATUSES",
    "RESOLUTION_ACTION_EXPIRED",
    "RESOLUTION_ACTION_INVALIDATED",
    "RESOLUTION_ACTION_NONE",
    "ResolutionDecision",
    "ResolutionInput",
    "ThesisStatus",
    "TransitionToExpiredResult",
    "TransitionToInvalidatedResult",
    "TransitionToMonitoringResult",
    "TransitionToValidatedResult",
    "ValidationDecision",
    "ValidationInput",
    "detect_initial_short_failure",
    "evaluate_monitoring_resolution",
    "evaluate_monitoring_validation",
    "is_valid_transition",
]
