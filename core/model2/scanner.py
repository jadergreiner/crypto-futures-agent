"""Deterministic detector for Model 2.0 initial short thesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


M2_002_RULE_ID = "M2-002.1-RULE-FAIL-SELL-REGION"
M2_002_RULE_VERSION = "1.0.0"
M2_002_THESIS_TYPE = "FALHA_REGIAO_VENDA"

_VALID_ZONE_STATUSES = {"FRESH", "TESTED", "PARTIALLY_FILLED", "OPEN"}
_REJECTED_ZONE_STATUSES = {"MITIGATED", "FILLED"}
_BULLISH_LABEL = "bullish"


@dataclass(frozen=True)
class DetectorInput:
    """Input payload for the initial short-failure detector."""

    symbol: str
    timeframe: str
    candles: Sequence[Mapping[str, Any]]
    indicators: Sequence[Mapping[str, Any]]
    smc: Mapping[str, Any]
    scan_timestamp: int


@dataclass(frozen=True)
class DetectionResult:
    """Detection payload ready to be persisted as initial thesis."""

    detected: bool
    symbol: str
    timeframe: str
    side: str
    thesis_type: str
    zone_low: float
    zone_high: float
    trigger_price: float
    invalidation_price: float
    metadata: Mapping[str, Any]
    rule_id: str


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _status_to_str(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value).upper()
    return str(value).upper()


def _extract_zone_fields(zone: Any) -> dict[str, Any] | None:
    if zone is None:
        return None

    if isinstance(zone, Mapping):
        raw_zone = zone
    else:
        raw_zone = zone.__dict__

    zone_high = _to_float(raw_zone.get("zone_high"))
    zone_low = _to_float(raw_zone.get("zone_low"))
    if zone_high is None or zone_low is None or zone_low >= zone_high:
        return None

    zone_type = str(raw_zone.get("type", "")).lower()
    if zone_type != "bearish":
        return None

    status = _status_to_str(raw_zone.get("status"))
    if status in _REJECTED_ZONE_STATUSES:
        return None
    if status and status not in _VALID_ZONE_STATUSES:
        return None

    timestamp = _to_int(raw_zone.get("timestamp"))
    zone_id = raw_zone.get("zone_id")
    if zone_id is not None:
        zone_id = _to_int(zone_id)

    return {
        "zone_high": zone_high,
        "zone_low": zone_low,
        "type": zone_type,
        "status": status,
        "timestamp": timestamp,
        "zone_id": zone_id,
    }


def _latest_valid_bearish_zone(smc: Mapping[str, Any]) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []

    for source_key in ("order_blocks", "fvgs"):
        source = smc.get(source_key, [])
        for zone in source:
            parsed = _extract_zone_fields(zone)
            if parsed is None:
                continue
            parsed["source"] = "order_block" if source_key == "order_blocks" else "fvg"
            candidates.append(parsed)

    if not candidates:
        return None

    # Prefer newest zone; timestamps missing fall back to the lowest priority.
    candidates.sort(key=lambda item: item.get("timestamp") or -1, reverse=True)
    return candidates[0]


def _market_structure_label(smc: Mapping[str, Any]) -> str:
    structure = smc.get("structure") or smc.get("market_structure")
    if structure is None:
        return "unknown"

    raw = None
    if isinstance(structure, Mapping):
        raw = structure.get("type")
    else:
        raw = getattr(structure, "type", None)

    if raw is None:
        return "unknown"
    if hasattr(raw, "value"):
        return str(raw.value).lower()
    return str(raw).lower()


def _intersects_zone(candle: Mapping[str, Any], zone_low: float, zone_high: float) -> bool:
    candle_high = _to_float(candle.get("high"))
    candle_low = _to_float(candle.get("low"))
    if candle_high is None or candle_low is None:
        return False
    return candle_high >= zone_low and candle_low <= zone_high


def _is_visible_rejection(candle: Mapping[str, Any], zone_low: float) -> bool:
    open_price = _to_float(candle.get("open"))
    close_price = _to_float(candle.get("close"))
    high_price = _to_float(candle.get("high"))
    low_price = _to_float(candle.get("low"))
    if None in (open_price, close_price, high_price, low_price):
        return False

    if close_price >= zone_low:
        return False

    body = abs(close_price - open_price)
    upper_wick = high_price - max(open_price, close_price)
    lower_wick = min(open_price, close_price) - low_price

    # Upper wick must dominate body and lower wick for a clear rejection.
    return upper_wick > body and upper_wick > lower_wick and upper_wick > 0


def _find_rejection_index(
    candles: Sequence[Mapping[str, Any]],
    zone_low: float,
    zone_high: float,
) -> int | None:
    # Walk backwards to pick the most recent rejection.
    for idx in range(len(candles) - 2, -1, -1):
        candle = candles[idx]
        if not _intersects_zone(candle, zone_low=zone_low, zone_high=zone_high):
            continue
        if _is_visible_rejection(candle, zone_low=zone_low):
            return idx
    return None


def _has_trigger_break(
    candles: Sequence[Mapping[str, Any]],
    rejection_idx: int,
    trigger_price: float,
) -> bool:
    for idx in range(rejection_idx + 1, len(candles)):
        low_value = _to_float(candles[idx].get("low"))
        if low_value is not None and low_value < trigger_price:
            return True
    return False


def detect_initial_short_failure(detector_input: DetectorInput) -> DetectionResult | None:
    """Detect the initial short thesis from deterministic technical rules."""

    candles = list(detector_input.candles)
    if len(candles) < 3:
        return None

    zone = _latest_valid_bearish_zone(detector_input.smc)
    if zone is None:
        return None

    structure_label = _market_structure_label(detector_input.smc)
    if structure_label == _BULLISH_LABEL:
        return None

    zone_low = float(zone["zone_low"])
    zone_high = float(zone["zone_high"])
    rejection_idx = _find_rejection_index(candles, zone_low=zone_low, zone_high=zone_high)
    if rejection_idx is None:
        return None

    rejection_candle = candles[rejection_idx]
    trigger_price = _to_float(rejection_candle.get("low"))
    if trigger_price is None:
        return None

    if not _has_trigger_break(candles, rejection_idx=rejection_idx, trigger_price=trigger_price):
        return None

    rejection_ts = _to_int(rejection_candle.get("timestamp"))
    rejection_payload = {
        "timestamp": rejection_ts,
        "open": _to_float(rejection_candle.get("open")),
        "high": _to_float(rejection_candle.get("high")),
        "low": trigger_price,
        "close": _to_float(rejection_candle.get("close")),
    }
    metadata = {
        "rule_id": M2_002_RULE_ID,
        "rule_version": M2_002_RULE_VERSION,
        "technical_zone": {
            "source": zone["source"],
            "zone_id": zone.get("zone_id"),
            "timestamp": zone.get("timestamp"),
            "zone_low": zone_low,
            "zone_high": zone_high,
            "status": zone.get("status", ""),
        },
        "rejection_candle": rejection_payload,
        "context": {
            "market_structure": structure_label,
            "is_non_bullish_context": structure_label != _BULLISH_LABEL,
        },
        "parameters": {
            "requires_zone_intersection": True,
            "requires_visible_rejection": True,
            "requires_trigger_break": True,
        },
        "scan_timestamp": detector_input.scan_timestamp,
    }

    return DetectionResult(
        detected=True,
        symbol=detector_input.symbol,
        timeframe=detector_input.timeframe,
        side="SHORT",
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=zone_low,
        zone_high=zone_high,
        trigger_price=trigger_price,
        invalidation_price=zone_high,
        metadata=metadata,
        rule_id=M2_002_RULE_ID,
    )
