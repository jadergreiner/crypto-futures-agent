"""
Testes de integração para Telegram Webhook.

Cobre: signature validation, alert processing, security.
"""

import json
import pytest
import hmac
import hashlib
from flask import Flask
from unittest.mock import MagicMock, patch
from notifications.telegram_webhook import TelegramWebhook


class TestTelegramWebhook:
    """Suite de testes para TelegramWebhook."""

    @pytest.fixture
    def app(self):
        """Cria aplicação Flask para testes."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def webhook(self, app):
        """Cria webhook para testes."""
        return TelegramWebhook(app, secret_key="test_secret")

    @pytest.fixture
    def client(self, app):
        """Cria cliente Flask para testes."""
        return app.test_client()

    def test_webhook_signature_validation_valid(self, webhook):
        """
        [TESTE 4] Valida assinatura HMAC.

        Verifica se payload com assinatura válida é aceito.
        """
        payload_dict = {"type": "pnl", "pnl": 100}
        payload = json.dumps(payload_dict).encode()
        signature = hmac.new(
            "test_secret".encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        assert webhook._validate_signature(payload, signature) is True

    def test_webhook_signature_validation_invalid(self, webhook):
        """Valida rejeição de assinatura inválida."""
        payload = json.dumps({"type": "pnl"}).encode()
        invalid_sig = "0" * 64

        assert webhook._validate_signature(payload, invalid_sig) is False

    def test_webhook_alert_endpoint_execution(self, client):
        """
        [TESTE 2] Processa alerta de execução via webhook.

        Verifica se POST para /alerts/telegram enfileira alerta.
        """
        payload = {
            "type": "execution",
            "order_id": "ord_123",
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0.5,
            "price": 67500.00,
            "status": "filled",
            "timestamp": "2026-02-28T14:30:00Z"
        }

        response = client.post(
            "/alerts/telegram",
            json=payload,
            content_type="application/json"
        )

        assert response.status_code == 202
        assert response.json["status"] == "enqueued"
        assert response.json["alert_type"] == "execution"

    def test_webhook_alert_endpoint_pnl(self, client):
        """Processa alerta de P&L."""
        payload = {
            "type": "pnl",
            "pnl": 1250.00,
            "win_rate": 65.0,
            "symbol": "Portfolio"
        }

        response = client.post(
            "/alerts/telegram",
            json=payload,
            content_type="application/json"
        )

        assert response.status_code == 202

    def test_webhook_alert_endpoint_risk(self, client):
        """Processa alerta de risco."""
        payload = {
            "type": "risk",
            "event_type": "circuit_breaker",
            "details": {
                "drawdown": "-5.2%",
                "stop_price": 50000.00
            }
        }

        response = client.post(
            "/alerts/telegram",
            json=payload,
            content_type="application/json"
        )

        assert response.status_code == 202

    def test_webhook_missing_alert_type(self, client):
        """Rejeita payload sem tipo de alerta."""
        payload = {"pnl": 100}  # Falta "type"

        response = client.post(
            "/alerts/telegram",
            json=payload,
            content_type="application/json"
        )

        assert response.status_code == 400
        assert "Missing alert type" in response.json["error"]

    def test_webhook_empty_payload(self, client):
        """Rejeita payload vazio."""
        response = client.post(
            "/alerts/telegram",
            data="",
            content_type="application/json"
        )

        assert response.status_code == 400

    def test_webhook_invalid_json(self, client):
        """Rejeita JSON inválido."""
        response = client.post(
            "/alerts/telegram",
            data="not valid json",
            content_type="application/json"
        )

        assert response.status_code == 400
        assert "Invalid JSON" in response.json["error"]

    def test_webhook_health_check(self, client):
        """Valida endpoint de health check."""
        response = client.get("/alerts/health")

        assert response.status_code == 200
        assert response.json["status"] == "ok"
        assert "queue_size" in response.json

    def test_webhook_queue_processing(self, webhook):
        """
        [TESTE 2] Processa fila de alertas.

        Verifica se alerts são enfileirados e processados.
        """
        # Enfileirar alguns alertas
        webhook.alert_queue = [
            {
                "type": "execution",
                "data": {
                    "order_id": "ord_1",
                    "symbol": "BTCUSDT",
                    "side": "LONG",
                    "quantity": 0.5,
                    "price": 67500.00,
                    "status": "filled"
                },
                "timestamp": None
            },
            {
                "type": "pnl",
                "data": {
                    "pnl": 100,
                    "win_rate": 50,
                    "symbol": "Portfolio"
                },
                "timestamp": None
            }
        ]

        # Mock do cliente Telegram
        mock_client = MagicMock()
        mock_client.send_execution_alert.return_value = True
        mock_client.send_pnl_alert.return_value = True

        processed = webhook.process_queue(mock_client)

        assert processed == 2
        assert len(webhook.alert_queue) == 0
        assert mock_client.send_execution_alert.called
        assert mock_client.send_pnl_alert.called

    def test_webhook_unknown_alert_type(self, webhook):
        """Gerencia tipo de alerta desconhecido."""
        webhook.alert_queue = [
            {
                "type": "unknown_type",
                "data": {},
                "timestamp": None
            }
        ]

        mock_client = MagicMock()
        processed = webhook.process_queue(mock_client)

        assert processed == 1
        assert len(webhook.alert_queue) == 0

    def test_webhook_queue_status(self, webhook):
        """Retorna status da fila."""
        webhook.alert_queue = [
            {"type": "pnl", "data": {}, "timestamp": "2026-02-28T14:00:00Z"},
            {"type": "risk", "data": {}, "timestamp": "2026-02-28T14:05:00Z"}
        ]

        status = webhook.get_queue_status()

        assert status["queue_size"] == 2
        assert len(status["alerts"]) == 2
        assert status["alerts"][0]["type"] == "pnl"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
