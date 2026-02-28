"""
Módulo de notificações — Telegram Alerts.

Centraliza envio de alertas para operador via Telegram Bot.
"""

from notifications.telegram_client import TelegramClient, telegram_client

__all__ = ["TelegramClient", "telegram_client"]
