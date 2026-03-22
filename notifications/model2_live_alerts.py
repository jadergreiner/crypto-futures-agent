"""Publisher de alertas operacionais para fluxo live do Modelo 2.0."""

from __future__ import annotations

import json
import os
from typing import Any

from notifications.telegram_client import telegram_client


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


class Model2LiveAlertPublisher:
    """Envia alertas criticos com no-op seguro quando desabilitado."""

    def __init__(self, *, enabled: bool | None = None) -> None:
        self._enabled = _env_bool("M2_ALERTS_ENABLED", False) if enabled is None else bool(enabled)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def publish_critical(self, event_type: str, details: dict[str, Any]) -> bool:
        if not self._enabled:
            return False

        message = {
            "event_type": str(event_type),
            "details": details,
        }
        return telegram_client.send_error_alert(
            error_msg=json.dumps(message, ensure_ascii=True, default=str)[:3000],
            component="model2_live",
        ) is True
