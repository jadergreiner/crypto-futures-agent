"""
Cliente Telegram para envio de alertas de trading.

Módulo responsável por gerenciar conexão com Telegram Bot
e enviar notificações formatadas para operador.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class TelegramClient:
    """Cliente para Telegram Bot API com suporte a rate limiting."""

    def __init__(self, token: Optional[str] = None,
                 chat_id: Optional[str] = None):
        """
        Inicializa cliente Telegram.

        Args:
            token: API token do bot (default: env TELEGRAM_BOT_TOKEN)
            chat_id: Chat ID alvo (default: env TELEGRAM_CHAT_ID)
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.alert_count = 0
        self.alert_timestamps = []

        if not self.token or not self.chat_id:
            logger.warning("Telegram credentials not configured")

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Envia mensagem de texto ao chat.

        Args:
            text: Texto da mensagem
            parse_mode: Modo de parse (HTML ou Markdown)

        Returns:
            True se enviado com sucesso
        """
        if not self._check_rate_limit():
            logger.warning("Rate limit atingido, mensagem enfileirada")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Mensagem Telegram enviada com sucesso")
            self.alert_count += 1
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao enviar mensagem Telegram: {e}")
            return False

    def send_execution_alert(self, order_id: str, symbol: str,
                            side: str, qty: float, price: float,
                            status: str) -> bool:
        """
        Envia alerta de execução de ordem.

        Args:
            order_id: ID da ordem
            symbol: Par trading (ex: BTCUSDT)
            side: LONG ou SHORT
            qty: Quantidade
            price: Preço de execução
            status: filled, partial, cancelled

        Returns:
            True se enviado com sucesso
        """
        emoji = "🟢" if side == "LONG" else "🔴"
        status_emoji = "✅" if status == "filled" else "⏳"

        text = (
            f"{emoji} <b>Execução de Ordem</b>\n"
            f"{status_emoji} Status: {status.upper()}\n"
            f"📊 {symbol}\n"
            f"💰 {qty} @ ${price:.2f}\n"
            f"#️⃣ ID: {order_id}\n"
            f"🕐 {datetime.utcnow().isoformat()}Z"
        )

        return self.send_message(text)

    def send_pnl_alert(self, pnl: float, win_rate: float,
                      symbol: str = "Portfolio") -> bool:
        """
        Envia alerta de P&L.

        Args:
            pnl: Lucro/prejuízo em USD
            win_rate: Taxa de ganho (0-100%)
            symbol: Par específico ou "Portfolio"

        Returns:
            True se enviado com sucesso
        """
        emoji = "📈" if pnl >= 0 else "📉"
        color = "green" if win_rate >= 50 else "red"

        text = (
            f"{emoji} <b>Relatório P&L</b>\n"
            f"💵 Resultado: ${pnl:+.2f}\n"
            f"📊 Taxa de Ganho: {win_rate:.1f}%\n"
            f"🎯 Ativo: {symbol}\n"
            f"🕐 {datetime.utcnow().isoformat()}Z"
        )

        return self.send_message(text)

    def send_risk_alert(self, event_type: str, details: Dict[str, Any]
                       ) -> bool:
        """
        Envia alerta de risco (Stop Loss, Circuit Breaker, etc).

        Args:
            event_type: Tipo de evento (stoploss, circuit_breaker, etc)
            details: Detalhes do evento

        Returns:
            True se enviado com sucesso
        """
        emoji_map = {
            "stoploss": "🛑",
            "circuit_breaker": "🚨",
            "margin_warning": "⚠️",
            "liquidation_risk": "💀"
        }

        emoji = emoji_map.get(event_type, "⚠️")

        text = (
            f"{emoji} <b>Alerta de Risco</b>\n"
            f"🔴 Tipo: {event_type.replace('_', ' ').upper()}\n"
        )

        for key, value in details.items():
            text += f"  {key}: {value}\n"

        text += f"🕐 {datetime.utcnow().isoformat()}Z"

        return self.send_message(text)

    def send_error_alert(self, error_msg: str, component: str) -> bool:
        """
        Envia alerta de erro crítico.

        Args:
            error_msg: Mensagem de erro
            component: Componente que falhou

        Returns:
            True se enviado com sucesso
        """
        text = (
            f"❌ <b>ERRO CRÍTICO</b>\n"
            f"🔧 Componente: {component}\n"
            f"📝 Mensagem: {error_msg}\n"
            f"🕐 {datetime.utcnow().isoformat()}Z"
        )

        return self.send_message(text)

    def send_daily_summary(self, date_str: str, total_pnl: float,
                          trades: int, win_rate: float,
                          sharpe: float) -> bool:
        """
        Envia resumo diário de operações.

        Args:
            date_str: Data (YYYY-MM-DD)
            total_pnl: P&L total do dia
            trades: Número de trades
            win_rate: Taxa de ganho (%)
            sharpe: Índice de Sharpe

        Returns:
            True se enviado com sucesso
        """
        emoji = "📈" if total_pnl >= 0 else "📉"

        text = (
            f"{emoji} <b>Resumo Diário — {date_str}</b>\n"
            f"💵 P&L: ${total_pnl:+.2f}\n"
            f"📊 Trades: {trades}\n"
            f"✅ Win Rate: {win_rate:.1f}%\n"
            f"📈 Sharpe: {sharpe:.2f}\n"
            f"🕐 {datetime.utcnow().isoformat()}Z"
        )

        return self.send_message(text)

    def _check_rate_limit(self, max_per_minute: int = 10) -> bool:
        """
        Valida limite de taxa (max_per_minute alertas/min).

        Args:
            max_per_minute: Máximo de alertas por minuto

        Returns:
            True se dentro do limite
        """
        now = datetime.utcnow().timestamp()
        minute_ago = now - 60

        # Remove timestamps antigos
        self.alert_timestamps = [ts for ts in self.alert_timestamps
                                 if ts > minute_ago]

        if len(self.alert_timestamps) >= max_per_minute:
            return False

        self.alert_timestamps.append(now)
        return True

    def test_connection(self) -> bool:
        """
        Testa conectividade com Telegram API.

        Returns:
            True se conexão OK
        """
        if not self.token or not self.chat_id:
            logger.error("Telegram credentials missing")
            return False

        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            bot_info = response.json()
            if bot_info.get("ok"):
                logger.info(f"Telegram conectado: {bot_info['result']['username']}")
                return True
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Falha ao testar Telegram: {e}")
            return False


# Instância global
telegram_client = TelegramClient()
