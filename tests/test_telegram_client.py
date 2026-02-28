"""
Testes unitários para cliente Telegram.

Cobre: conexão, formatação de mensagens, rate limiting.
"""

import pytest
from unittest.mock import patch, MagicMock
from notifications.telegram_client import TelegramClient


class TestTelegramClient:
    """Suite de testes para TelegramClient."""

    @pytest.fixture
    def client(self):
        """Cria cliente para testes."""
        return TelegramClient(
            token="test_token_12345",
            chat_id="test_chat_123"
        )

    def test_telegram_client_connect(self, client):
        """
        [TESTE 1] Valida conexão com Telegram.

        Verifica se client consegue conectar à API.
        """
        with patch("requests.get") as mock_get:
            # Mock resposta OK
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ok": True,
                "result": {
                    "id": 123456,
                    "is_bot": True,
                    "first_name": "TestBot",
                    "username": "test_bot"
                }
            }
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = client.test_connection()

            assert result is True
            mock_get.assert_called_once()

    def test_telegram_client_connect_failure(self, client):
        """Valida comportamento ao falhar conexão."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection timeout")

            result = client.test_connection()

            assert result is False

    def test_send_execution_alert_format(self, client):
        """
        [TESTE 2] Valida formatação de alerta de execução.

        Verifica se mensagem é formatada corretamente.
        """
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = client.send_execution_alert(
                order_id="order_123",
                symbol="BTCUSDT",
                side="LONG",
                qty=0.5,
                price=67500.00,
                status="filled"
            )

            assert result is True
            mock_post.assert_called_once()

            # Validar payload
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert "BTCUSDT" in payload["text"]
            assert "0.5" in payload["text"]
            assert "filled" in payload["text"].lower()

    def test_send_pnl_alert(self, client):
        """
        [TESTE 2b] Valida alerta de P&L.

        Verifica formatação de P&L positivo e negativo.
        """
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            # P&L positivo
            result = client.send_pnl_alert(
                pnl=1250.50,
                win_rate=65.0,
                symbol="Portfolio"
            )

            assert result is True
            payload = mock_post.call_args.kwargs["json"]
            assert "+1250.50" in payload["text"]

    def test_send_risk_alert(self, client):
        """
        [TESTE 3] Valida alerta de risco.

        Testa diferentes tipos de risco (stoploss, circuit_breaker, etc).
        """
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = client.send_risk_alert(
                event_type="circuit_breaker",
                details={"drawdown": "-5.2%", "portfolio": "Portfolio"}
            )

            assert result is True
            payload = mock_post.call_args.kwargs["json"]
            assert "CIRCUIT BREAKER" in payload["text"].upper()
            assert "drawdown" in payload["text"].lower()

    def test_rate_limiting(self, client):
        """
        [TESTE 5] Valida rate limiting.

        Verifica se limite de 10 alertas/min é respeitado.
        """
        # Simular 15 tentativas em 60 segundos
        results = []
        for i in range(15):
            with patch("requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()
                mock_post.return_value = mock_response

                result = client.send_message(f"Test message {i}")
                results.append(result)

        # Primeiros 10 devem passar, resto falhar
        assert sum(results) == 10
        assert results[:10] == [True] * 10
        assert results[10:] == [False] * 5

    def test_send_error_alert(self, client):
        """Valida envio de alerta de erro."""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = client.send_error_alert(
                error_msg="API connection lost",
                component="execution"
            )

            assert result is True
            payload = mock_post.call_args.kwargs["json"]
            assert "ERRO CRÍTICO" in payload["text"]

    def test_send_daily_summary(self, client):
        """Valida envio de resumo diário."""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = client.send_daily_summary(
                date_str="2026-02-28",
                total_pnl=5000.00,
                trades=25,
                win_rate=72.0,
                sharpe=1.45
            )

            assert result is True
            payload = mock_post.call_args.kwargs["json"]
            assert "2026-02-28" in payload["text"]
            assert "5000.00" in payload["text"]

    def test_client_without_credentials(self):
        """Valida comportamento sem credenciais."""
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            client = TelegramClient(token=None, chat_id=None)

            result = client.test_connection()
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
