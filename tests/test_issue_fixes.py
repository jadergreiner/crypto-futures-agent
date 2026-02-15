"""
Testes para validar as correções dos 4 problemas restantes após PRs #14 e #15.
"""

import pytest
import time
import logging
from unittest.mock import Mock, MagicMock, patch
from monitoring.position_monitor import PositionMonitor
from monitoring.logger import AgentLogger


class TestBinanceTimestampFix:
    """Testes para Problema 1: Erro de timestamp Binance (-1021)"""
    
    def test_fetch_account_balance_with_recv_window(self):
        """Verifica que recv_window=10000 é passado para a chamada da API"""
        mock_client = Mock()
        mock_db = Mock()
        
        # Configurar mock para retornar resposta válida
        # O monitor usa _extract_data que retorna o objeto data
        # e então usa _safe_get para buscar available_balance
        mock_data = {'available_balance': 1000.0}
        mock_response = Mock()
        mock_response.data = mock_data
        mock_client.rest_api.account_information_v2.return_value = mock_response
        
        monitor = PositionMonitor(mock_client, mock_db)
        balance = monitor.fetch_account_balance()
        
        # Verificar que recv_window foi passado
        mock_client.rest_api.account_information_v2.assert_called_with(recv_window=10000)
        assert balance == 1000.0
    
    def test_fetch_account_balance_retry_on_timestamp_error(self):
        """Verifica retry automático em caso de erro -1021"""
        mock_client = Mock()
        mock_db = Mock()
        
        # Primeira chamada: erro -1021
        # Segunda chamada (retry): sucesso
        mock_data_success = {'available_balance': 500.0}
        mock_response_success = Mock()
        mock_response_success.data = mock_data_success
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("(-1021, \"Timestamp for this request was 1000ms ahead of the server's time.\")")
            return mock_response_success
        
        mock_client.rest_api.account_information_v2.side_effect = side_effect
        
        monitor = PositionMonitor(mock_client, mock_db)
        balance = monitor.fetch_account_balance()
        
        # Verificar que houve 2 chamadas (original + retry)
        assert mock_client.rest_api.account_information_v2.call_count == 2
        assert balance == 500.0


class TestRiskScoreWhenBalanceFails:
    """Testes para Problema 2: Risk score 10.0 quando saldo da conta falha"""
    
    def test_risk_score_penalty_when_balance_fails(self):
        """Verifica que penalidade é pequena (0.5) quando account_balance == 0"""
        mock_client = Mock()
        mock_db = Mock()
        
        # Simular falha no fetch_account_balance
        monitor = PositionMonitor(mock_client, mock_db)
        monitor.fetch_account_balance = Mock(return_value=0)
        
        # Posição LONG lucrativa (+90% PnL) em CROSS margin
        position = {
            'symbol': 'C98USDT',
            'direction': 'LONG',
            'entry_price': 0.10,
            'mark_price': 0.19,  # +90% PnL
            'liquidation_price': 0.05,
            'unrealized_pnl': 90.0,
            'unrealized_pnl_pct': 90.0,
            'margin_type': 'CROSS',
            'margin_invested': 100.0,
            'position_size_qty': 1000
        }
        
        indicators = {
            'rsi_14': 65,
            'ema_17': 0.18,
            'ema_72': 0.15,
            'atr': 0.005,
            'market_structure': 'bullish',
            'choch_recent': 0
        }
        
        sentiment = {}
        
        decision = monitor.evaluate_position(position, indicators, sentiment)
        
        # Verificar que risk_score NÃO é 10.0
        assert decision['risk_score'] < 10.0, "Risk score não deveria ser 10.0 para posição lucrativa"
        
        # Verificar que há uma pequena penalidade por conta indisponível
        # Risk base para cross = 2.0, penalidade = 0.5 = 2.5 antes do multiplicador
        # Com multiplicador 1.5 = 3.75
        assert decision['risk_score'] < 6.0, "Risk score deveria ser baixo para posição lucrativa"
        
        # Verificar que reasoning contém a mensagem sobre saldo indisponível
        reasoning = decision['decision_reasoning']
        # O reasoning é um JSON string, então vamos decodificar
        import json
        reasoning_list = json.loads(reasoning) if isinstance(reasoning, str) else reasoning
        reasoning_text = ' '.join(reasoning_list)
        assert 'Saldo da conta' in reasoning_text and 'indisponível' in reasoning_text


class TestCountdownTimer:
    """Testes para Problema 3: Countdown timer para próximo ciclo"""
    
    @patch('time.sleep')
    def test_countdown_shows_progress(self, mock_sleep):
        """Verifica que o countdown mostra progresso a cada 30 segundos"""
        mock_client = Mock()
        mock_db = Mock()
        
        # Mock para fetch_open_positions retornar lista vazia (sem posições)
        monitor = PositionMonitor(mock_client, mock_db)
        monitor.fetch_open_positions = Mock(return_value=[])
        
        # Simular 1 ciclo apenas
        call_count = 0
        def stop_after_one_cycle(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 2:  # Parar após primeiro sleep
                monitor.stop()  # Usar método público ao invés de manipular _running
        
        mock_sleep.side_effect = stop_after_one_cycle
        
        # Executar com intervalo de 90 segundos (deve gerar 3 sleeps de 30s cada)
        try:
            monitor.run_continuous(interval_seconds=90)
        except:
            pass  # Ignorar exceções de mock
        
        # Verificar que sleep foi chamado múltiplas vezes (não apenas 1x)
        assert mock_sleep.call_count >= 2, "Sleep deveria ser chamado múltiplas vezes para countdown"


class TestLoggerPropagation:
    """Testes para Problema 4: Mensagens de log duplicadas"""
    
    def test_logger_propagate_is_false(self):
        """Verifica que logger.propagate é False para evitar duplicação"""
        logger = AgentLogger.setup_logger('test_logger_propagation')
        
        # Verificar que propagate está False
        assert logger.propagate is False, "Logger propagate deveria ser False para evitar mensagens duplicadas"
    
    def test_no_duplicate_handlers(self):
        """Verifica que chamar setup_logger múltiplas vezes não duplica handlers"""
        logger1 = AgentLogger.setup_logger('test_logger_duplicate')
        handler_count_1 = len(logger1.handlers)
        
        # Chamar novamente
        logger2 = AgentLogger.setup_logger('test_logger_duplicate')
        handler_count_2 = len(logger2.handlers)
        
        # Verificar que são o mesmo logger e não há handlers duplicados
        assert logger1 is logger2
        assert handler_count_1 == handler_count_2
