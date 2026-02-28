"""
Webhook handler para receber eventos e disparar alertas Telegram.

Gerencia HTTP endpoint POST /alerts/telegram para integração
com sistemas externos e interno.
"""

import json
import logging
import hmac
import hashlib
from typing import Dict, Any, Tuple
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)


class TelegramWebhook:
    """Webhook handler para eventos de trading."""

    def __init__(self, app: Flask, secret_key: str):
        """
        Inicializa webhook.

        Args:
            app: Instância Flask
            secret_key: Chave para validação de assinatura
        """
        self.app = app
        self.secret_key = secret_key
        self.alert_queue = []
        self._register_routes()

    def _register_routes(self):
        """Registra rotas Flask."""
        @self.app.route("/alerts/telegram", methods=["POST"])
        def telegram_alert():
            """Endpoint para receber alertas."""
            return self._handle_alert(request)

        @self.app.route("/alerts/health", methods=["GET"])
        def health_check():
            """Health check do webhook."""
            return jsonify({"status": "ok", "queue_size": len(self.alert_queue)})

    def _validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Valida assinatura HMAC do payload.

        Args:
            payload: Dados do corpo da requisição
            signature: Assinatura fornecida no header

        Returns:
            True se assinatura válida
        """
        expected = hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def _handle_alert(self, req) -> Tuple[Dict[str, Any], int]:
        """
        Processa alerta recebido.

        Args:
            req: Flask request object

        Returns:
            Tupla (JSON response, status code)
        """
        try:
            # Validar assinatura se fornecida
            signature = req.headers.get("X-Signature")
            payload = req.get_data()

            if signature and not self._validate_signature(payload, signature):
                logger.warning("Assinatura inválida no webhook")
                return {"error": "Invalid signature"}, 403

            # Parse JSON
            data = req.get_json()
            if not data:
                return {"error": "Empty payload"}, 400

            # Validar tipo de alerta
            alert_type = data.get("type")
            if not alert_type:
                return {"error": "Missing alert type"}, 400

            # Enfileirar alerta
            self.alert_queue.append({
                "type": alert_type,
                "data": data,
                "timestamp": data.get("timestamp")
            })

            logger.info(f"Alerta enfileirado: tipo={alert_type}")

            return {
                "status": "enqueued",
                "alert_type": alert_type,
                "queue_size": len(self.alert_queue)
            }, 202

        except json.JSONDecodeError:
            logger.error("JSON inválido no webhook")
            return {"error": "Invalid JSON"}, 400
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {e}")
            return {"error": str(e)}, 500

    def process_queue(self, telegram_client) -> int:
        """
        Processa fila de alertas enfileirados.

        Args:
            telegram_client: Instância TelegramClient para envio

        Returns:
            Número de alertas processados
        """
        processed = 0

        while self.alert_queue:
            alert = self.alert_queue.pop(0)
            alert_type = alert["type"]
            data = alert["data"]

            try:
                if alert_type == "execution":
                    telegram_client.send_execution_alert(
                        order_id=data.get("order_id"),
                        symbol=data.get("symbol"),
                        side=data.get("side"),
                        qty=data.get("quantity"),
                        price=data.get("price"),
                        status=data.get("status")
                    )

                elif alert_type == "pnl":
                    telegram_client.send_pnl_alert(
                        pnl=data.get("pnl"),
                        win_rate=data.get("win_rate"),
                        symbol=data.get("symbol", "Portfolio")
                    )

                elif alert_type == "risk":
                    telegram_client.send_risk_alert(
                        event_type=data.get("event_type"),
                        details=data.get("details", {})
                    )

                elif alert_type == "error":
                    telegram_client.send_error_alert(
                        error_msg=data.get("message"),
                        component=data.get("component")
                    )

                elif alert_type == "daily_summary":
                    telegram_client.send_daily_summary(
                        date_str=data.get("date"),
                        total_pnl=data.get("total_pnl"),
                        trades=data.get("trades"),
                        win_rate=data.get("win_rate"),
                        sharpe=data.get("sharpe")
                    )

                else:
                    logger.warning(f"Tipo de alerta desconhecido: {alert_type}")

                processed += 1

            except Exception as e:
                logger.error(f"Erro ao processar alerta {alert_type}: {e}")

        return processed

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Retorna status da fila.

        Returns:
            Dicionário com informações da fila
        """
        return {
            "queue_size": len(self.alert_queue),
            "alerts": [
                {
                    "type": a["type"],
                    "timestamp": a.get("timestamp")
                }
                for a in self.alert_queue
            ]
        }
