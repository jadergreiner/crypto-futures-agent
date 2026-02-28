"""
Configuração centralizada para Telegram Alerts.

Este módulo carrega e valida configurações de Telegram
a partir de variáveis de ambiente.
"""

import os
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Níveis de severidade de alertas."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class TelegramConfig:
    """Configuração centralizada de Telegram."""

    def __init__(self):
        """Carrega configuração de variáveis de ambiente."""
        # Credenciais
        self.token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
        self.webhook_secret: str = os.getenv(
            "TELEGRAM_WEBHOOK_SECRET",
            "change_me_in_production"
        )

        # Alert levels
        alert_level = os.getenv("TELEGRAM_ALERT_LEVEL", "INFO")
        try:
            self.alert_level = AlertLevel(alert_level)
        except ValueError:
            logger.warning(f"Alert level inválido: {alert_level}, usando INFO")
            self.alert_level = AlertLevel.INFO

        # Rate limiting
        self.max_alerts_per_minute: int = int(
            os.getenv("TELEGRAM_MAX_ALERTS_PER_MINUTE", "10")
        )

        # Quiet hours (opcional)
        self.quiet_hours_start: int = int(
            os.getenv("TELEGRAM_QUIET_START", "22")
        )
        self.quiet_hours_end: int = int(
            os.getenv("TELEGRAM_QUIET_END", "6")
        )
        self.quiet_hours_enabled: bool = (
            os.getenv("TELEGRAM_QUIET_HOURS_ENABLED", "false").lower() == "true"
        )

        # Webhook
        self.webhook_port: int = int(
            os.getenv("TELEGRAM_WEBHOOK_PORT", "8000")
        )
        self.webhook_host: str = os.getenv(
            "TELEGRAM_WEBHOOK_HOST",
            "127.0.0.1"
        )

        # Alert types habilitados
        self.alerts_enabled = {
            "execution": os.getenv("TELEGRAM_ALERT_EXECUTION", "true").lower() == "true",
            "pnl": os.getenv("TELEGRAM_ALERT_PNL", "true").lower() == "true",
            "risk": os.getenv("TELEGRAM_ALERT_RISK", "true").lower() == "true",
            "error": os.getenv("TELEGRAM_ALERT_ERROR", "true").lower() == "true",
            "daily_summary": os.getenv("TELEGRAM_ALERT_DAILY_SUMMARY", "true").lower() == "true",
        }

        self._validate()

    def _validate(self):
        """Valida configuração."""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN não está configurado")

        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID não está configurado")

        if self.max_alerts_per_minute < 1:
            logger.error("max_alerts_per_minute deve ser >= 1")
            self.max_alerts_per_minute = 10

    def is_enabled(self) -> bool:
        """Verifica se Telegram está habilitado."""
        return bool(self.token and self.chat_id)

    def should_send_alert(self, alert_type: str, alert_level: AlertLevel
                         ) -> bool:
        """
        Verifica se alerta deve ser enviado.

        Args:
            alert_type: Tipo de alerta
            alert_level: Nível de severidade

        Returns:
            True se alerta deve ser enviado
        """
        if not self.is_enabled():
            return False

        if not self.alerts_enabled.get(alert_type, True):
            return False

        # Validar nível de severidade
        level_hierarchy = {
            AlertLevel.DEBUG: 0,
            AlertLevel.INFO: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.CRITICAL: 3
        }

        if level_hierarchy[alert_level] < level_hierarchy[self.alert_level]:
            return False

        # Validar quiet hours
        if self.quiet_hours_enabled:
            from datetime import datetime
            now = datetime.utcnow()
            current_hour = now.hour

            if self.quiet_hours_start < self.quiet_hours_end:
                # Ex: 22-23:59 e 00-05
                if current_hour >= self.quiet_hours_start or \
                   current_hour < self.quiet_hours_end:
                    if alert_level != AlertLevel.CRITICAL:
                        return False

        return True

    def to_dict(self) -> dict:
        """
        Retorna configuração como dicionário.

        Returns:
            Dicionário com configuração (sem credenciais)
        """
        return {
            "enabled": self.is_enabled(),
            "alert_level": self.alert_level.value,
            "max_alerts_per_minute": self.max_alerts_per_minute,
            "quiet_hours_enabled": self.quiet_hours_enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "webhook_port": self.webhook_port,
            "webhook_host": self.webhook_host,
            "alerts_enabled": self.alerts_enabled
        }


# Instância global
config = TelegramConfig()
