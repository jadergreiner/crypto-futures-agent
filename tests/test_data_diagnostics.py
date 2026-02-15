"""
Testes para a funcionalidade de diagnóstico de disponibilidade de dados.

Testa o método diagnose_data_readiness() do DataLoader.
"""

import pytest
from unittest.mock import Mock, MagicMock
from agent.data_loader import DataLoader
from datetime import datetime, timedelta


class TestDataDiagnostics:
    """Testes para o diagnóstico de dados."""
    
    def test_diagnose_no_database(self):
        """Testa diagnóstico quando não há database conectado."""
        loader = DataLoader(db=None)
        
        diagnosis = loader.diagnose_data_readiness(
            symbol="BTCUSDT",
            min_length_train=1000,
            min_length_val=200
        )
        
        assert diagnosis is not None
        assert 'ready' in diagnosis
        assert 'summary' in diagnosis
        assert not diagnosis['ready']
        assert "NÃO DISPONÍVEL" in diagnosis['summary']
    
    def test_diagnose_insufficient_h4_data(self):
        """Testa diagnóstico quando há dados H4 insuficientes."""
        # Mock database com poucos candles H4
        mock_db = Mock()
        
        # Simular 500 candles H4 disponíveis (insuficiente para min_length=1000 com split 80/20)
        def mock_get_ohlcv(timeframe, symbol):
            if timeframe == 'h4':
                # Retornar 500 candles (após split 80/20 = 400, menos que 1000)
                return [{'timestamp': i * 14400000} for i in range(500)]
            elif timeframe == 'h1':
                return [{'timestamp': i * 3600000} for i in range(2000)]
            elif timeframe == 'd1':
                return [{'timestamp': i * 86400000} for i in range(300)]
            return []
        
        mock_db.get_ohlcv = mock_get_ohlcv
        
        loader = DataLoader(db=mock_db)
        diagnosis = loader.diagnose_data_readiness(
            symbol="BTCUSDT",
            min_length_train=1000,
            min_length_val=200
        )
        
        assert not diagnosis['ready']
        assert 'h4' in diagnosis['timeframes']
        assert diagnosis['timeframes']['h4']['available'] == 500
        assert diagnosis['timeframes']['h4']['status'] == '❌ INSUFICIENTE'
        assert diagnosis['timeframes']['h4']['gap'] < 0
        assert 'recommendation' in diagnosis['timeframes']['h4']
    
    def test_diagnose_sufficient_data(self):
        """Testa diagnóstico quando há dados suficientes."""
        # Mock database com dados suficientes
        mock_db = Mock()
        
        # 1500 candles H4 = após split 80/20 = 1200 (> 1000) ✅
        # 6000 candles H1 = 1500 * 4 ✅
        # 700 candles D1 = > 610 para EMA_610 ✅
        def mock_get_ohlcv(timeframe, symbol):
            now = datetime.now()
            if timeframe == 'h4':
                return [
                    {'timestamp': int((now - timedelta(hours=i*4)).timestamp() * 1000)}
                    for i in range(1500, 0, -1)
                ]
            elif timeframe == 'h1':
                return [
                    {'timestamp': int((now - timedelta(hours=i)).timestamp() * 1000)}
                    for i in range(6000, 0, -1)
                ]
            elif timeframe == 'd1':
                return [
                    {'timestamp': int((now - timedelta(days=i)).timestamp() * 1000)}
                    for i in range(700, 0, -1)
                ]
            return []
        
        mock_db.get_ohlcv = mock_get_ohlcv
        
        loader = DataLoader(db=mock_db)
        diagnosis = loader.diagnose_data_readiness(
            symbol="BTCUSDT",
            min_length_train=1000,
            min_length_val=200
        )
        
        assert diagnosis['ready']
        assert diagnosis['timeframes']['h4']['status'] == '✅ OK'
        assert diagnosis['timeframes']['h4']['gap'] >= 0
        assert diagnosis['indicators']['ema_610_d1']['status'] == '✅ OK'
        assert "PRONTO" in diagnosis['summary']
    
    def test_diagnose_insufficient_d1_for_ema610(self):
        """Testa diagnóstico quando D1 insuficiente para EMA(610)."""
        mock_db = Mock()
        
        def mock_get_ohlcv(timeframe, symbol):
            now = datetime.now()
            if timeframe == 'h4':
                # Suficiente para treino
                return [
                    {'timestamp': int((now - timedelta(hours=i*4)).timestamp() * 1000)}
                    for i in range(1500, 0, -1)
                ]
            elif timeframe == 'h1':
                return [
                    {'timestamp': int((now - timedelta(hours=i)).timestamp() * 1000)}
                    for i in range(6000, 0, -1)
                ]
            elif timeframe == 'd1':
                # Apenas 365 candles (insuficiente para EMA_610)
                return [
                    {'timestamp': int((now - timedelta(days=i)).timestamp() * 1000)}
                    for i in range(365, 0, -1)
                ]
            return []
        
        mock_db.get_ohlcv = mock_get_ohlcv
        
        loader = DataLoader(db=mock_db)
        diagnosis = loader.diagnose_data_readiness(
            symbol="BTCUSDT",
            min_length_train=1000,
            min_length_val=200
        )
        
        # H4 deve estar OK
        assert diagnosis['timeframes']['h4']['status'] == '✅ OK'
        
        # Mas D1 insuficiente para EMA_610
        assert diagnosis['indicators']['ema_610_d1']['status'] == '❌ INSUFICIENTE'
        assert diagnosis['indicators']['ema_610_d1']['available'] == 365
        assert diagnosis['indicators']['ema_610_d1']['required_candles'] == 610
        
        # Overall não está pronto devido ao problema com EMA_610
        # O diagnóstico marca como não pronto quando indicadores críticos estão insuficientes
        assert not diagnosis['ready']
        assert 'EMA(610)' in diagnosis['indicators']['ema_610_d1']['recommendation']
    
    def test_diagnose_stale_data(self):
        """Testa diagnóstico quando dados estão desatualizados."""
        mock_db = Mock()
        
        # Dados de 3 dias atrás (desatualizados)
        old_time = datetime.now() - timedelta(days=3)
        
        def mock_get_ohlcv(timeframe, symbol):
            if timeframe == 'h4':
                return [
                    {'timestamp': int((old_time - timedelta(hours=i*4)).timestamp() * 1000)}
                    for i in range(1500, 0, -1)
                ]
            elif timeframe == 'h1':
                return [
                    {'timestamp': int((old_time - timedelta(hours=i)).timestamp() * 1000)}
                    for i in range(6000, 0, -1)
                ]
            elif timeframe == 'd1':
                return [
                    {'timestamp': int((old_time - timedelta(days=i)).timestamp() * 1000)}
                    for i in range(700, 0, -1)
                ]
            return []
        
        mock_db.get_ohlcv = mock_get_ohlcv
        
        loader = DataLoader(db=mock_db)
        diagnosis = loader.diagnose_data_readiness(
            symbol="BTCUSDT",
            min_length_train=1000,
            min_length_val=200
        )
        
        # Verificar que detectou dados desatualizados
        assert 'data_freshness' in diagnosis
        assert diagnosis['data_freshness']['is_stale']
        assert diagnosis['data_freshness']['hours_since_last'] > 24
    
    def test_diagnose_return_structure(self):
        """Testa que o diagnóstico retorna a estrutura esperada."""
        mock_db = Mock()
        mock_db.get_ohlcv = Mock(return_value=[])
        
        loader = DataLoader(db=mock_db)
        diagnosis = loader.diagnose_data_readiness(
            symbol="BTCUSDT",
            min_length_train=1000,
            min_length_val=200
        )
        
        # Verificar estrutura do retorno
        assert 'ready' in diagnosis
        assert 'symbol' in diagnosis
        assert 'timeframes' in diagnosis
        assert 'indicators' in diagnosis
        assert 'data_freshness' in diagnosis
        assert 'summary' in diagnosis
        
        assert isinstance(diagnosis['ready'], bool)
        assert isinstance(diagnosis['symbol'], str)
        assert isinstance(diagnosis['timeframes'], dict)
        assert isinstance(diagnosis['indicators'], dict)
        assert isinstance(diagnosis['summary'], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
