"""
Módulo de notificações — Telegram Alerts.

Centraliza envio de alertas para operador via Telegram Bot.
"""

from notifications.telegram_client import TelegramClient, telegram_client
from notifications.model2_live_alerts import Model2LiveAlertPublisher

__all__ = ["TelegramClient", "telegram_client", "Model2LiveAlertPublisher"]
