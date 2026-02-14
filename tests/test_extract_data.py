"""
Testes isolados para o método _extract_data().
Estes testes não dependem do SDK Binance.
"""

import pytest
from unittest.mock import Mock


class MockBinanceCollector:
    """Mock simplificado do BinanceCollector para testar _extract_data()."""
    
    def _extract_data(self, response):
        """
        Extrai dados do wrapper ApiResponse do SDK.
        
        O SDK Binance encapsula respostas em um objeto ApiResponse.
        O atributo .data pode ser uma property (acesso direto) ou um método (precisa chamar).
        
        Args:
            response: Resposta bruta do SDK (ApiResponse ou dados diretos)
            
        Returns:
            Os dados reais (list, dict, etc.)
        """
        if response is None:
            return None
        
        # ApiResponse tem um atributo .data contendo o payload real
        if hasattr(response, 'data'):
            data = response.data
            # .data pode ser um método que precisa ser chamado
            if callable(data):
                return data()
            return data
        
        # Se já são os dados brutos (list, dict), retorna como está
        return response


class TestExtractDataMethod:
    """Testes para o método _extract_data()."""
    
    def test_extract_data_with_api_response_object(self):
        """Testa extração de dados de um objeto ApiResponse mockado."""
        collector = MockBinanceCollector()
        
        # Mock de ApiResponse com atributo .data
        mock_response = Mock()
        mock_response.data = [
            {'timestamp': 1234567890, 'symbol': 'BTCUSDT', 'price': 50000}
        ]
        
        result = collector._extract_data(mock_response)
        
        assert result == [{'timestamp': 1234567890, 'symbol': 'BTCUSDT', 'price': 50000}]
        assert isinstance(result, list)
    
    def test_extract_data_with_raw_list(self):
        """Testa extração quando a resposta já é uma lista (sem ApiResponse)."""
        collector = MockBinanceCollector()
        
        raw_data = [
            {'open_time': 1609459200000, 'open': '29000.0', 'close': '29200.0'}
        ]
        
        result = collector._extract_data(raw_data)
        
        assert result == raw_data
        assert result is raw_data  # Deve retornar o mesmo objeto
    
    def test_extract_data_with_raw_dict(self):
        """Testa extração quando a resposta já é um dict (sem ApiResponse)."""
        collector = MockBinanceCollector()
        
        raw_data = {'symbol': 'ETHUSDT', 'open_interest': 1000000}
        
        result = collector._extract_data(raw_data)
        
        assert result == raw_data
        assert result is raw_data  # Deve retornar o mesmo objeto
    
    def test_extract_data_with_none(self):
        """Testa extração quando a resposta é None."""
        collector = MockBinanceCollector()
        
        result = collector._extract_data(None)
        
        assert result is None
    
    def test_extract_data_with_empty_list(self):
        """Testa extração quando a resposta é uma lista vazia."""
        collector = MockBinanceCollector()
        
        result = collector._extract_data([])
        
        assert result == []
        assert isinstance(result, list)
    
    def test_extract_data_with_api_response_empty_data(self):
        """Testa extração quando ApiResponse.data está vazio."""
        collector = MockBinanceCollector()
        
        mock_response = Mock()
        mock_response.data = []
        
        result = collector._extract_data(mock_response)
        
        assert result == []
    
    def test_extract_data_with_api_response_dict_data(self):
        """Testa extração quando ApiResponse.data contém um dict."""
        collector = MockBinanceCollector()
        
        mock_response = Mock()
        mock_response.data = {'funding_rate': 0.0001, 'timestamp': 1234567890}
        
        result = collector._extract_data(mock_response)
        
        assert result == {'funding_rate': 0.0001, 'timestamp': 1234567890}
        assert isinstance(result, dict)
    
    def test_extract_data_with_nested_api_response(self):
        """Testa que não faz unwrap duplo quando .data não é callable."""
        collector = MockBinanceCollector()
        
        # Mock de um objeto nested que também tem .data (non-callable)
        inner_object = {'nested': 'data', 'value': 123}
        
        mock_response = Mock()
        # Usando spec para garantir que .data não seja callable
        mock_response.data = inner_object
        
        result = collector._extract_data(mock_response)
        
        # Deve retornar o objeto interno diretamente (não fazer unwrap recursivo)
        assert result == inner_object
        assert result is inner_object
    
    def test_extract_data_with_callable_data_method(self):
        """Testa extração quando .data é um método callable (cenário real do SDK Binance)."""
        collector = MockBinanceCollector()
        
        # Mock de ApiResponse onde .data é um método callable
        mock_response = Mock()
        expected_data = [
            {'timestamp': 1234567890, 'symbol': 'BTCUSDT', 'price': 50000}
        ]
        mock_response.data = Mock(return_value=expected_data)
        
        result = collector._extract_data(mock_response)
        
        # Deve chamar o método .data() e retornar o resultado
        assert result == expected_data
        assert isinstance(result, list)
        mock_response.data.assert_called_once()
    
    def test_extract_data_with_callable_data_returns_dict(self):
        """Testa extração quando .data() retorna um dict."""
        collector = MockBinanceCollector()
        
        mock_response = Mock()
        expected_data = {'funding_rate': 0.0001, 'timestamp': 1234567890}
        mock_response.data = Mock(return_value=expected_data)
        
        result = collector._extract_data(mock_response)
        
        assert result == expected_data
        assert isinstance(result, dict)
        mock_response.data.assert_called_once()
    
    def test_extract_data_with_callable_data_returns_empty_list(self):
        """Testa extração quando .data() retorna lista vazia."""
        collector = MockBinanceCollector()
        
        mock_response = Mock()
        mock_response.data = Mock(return_value=[])
        
        result = collector._extract_data(mock_response)
        
        assert result == []
        assert isinstance(result, list)
        mock_response.data.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
