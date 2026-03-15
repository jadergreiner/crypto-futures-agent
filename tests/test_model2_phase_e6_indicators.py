"""Tests para novos indicadores do Feature Enricher - Fase E.6."""

import pytest
from scripts.model2.feature_enricher import FeatureEnricher


class TestStochasticIndicator:
    """Testes para indicador Estocastico (K e D)."""

    def test_stochastic_basic(self):
        """Valida calculo basico do Estocastico."""
        highs = [100, 102, 104, 103, 105, 106, 105, 107, 108, 106, 105, 104, 103, 102, 101]
        lows = [95, 97, 99, 98, 100, 101, 100, 102, 103, 101, 100, 99, 98, 97, 96]
        closes = [98, 101, 102, 100, 104, 105, 103, 106, 107, 105, 104, 103, 102, 100, 99]

        k, d = FeatureEnricher.calculate_stochastic(highs, lows, closes, period=14)

        assert isinstance(k, float)
        assert isinstance(d, float)
        assert 0.0 <= k <= 100.0
        assert 0.0 <= d <= 100.0

    def test_stochastic_overbot_zone(self):
        """Estocastico deve estar alto em zona de sobrecompra."""
        # Dados com tendencia claramente de alta ate o final
        highs = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]
        lows = [95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        closes = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]

        k, d = FeatureEnricher.calculate_stochastic(highs, lows, closes, period=14)
        assert k > 50.0, f"Estocastico deve estar acima de 50 em tendencia de alta, got {k}"

    def test_stochastic_insufficient_data(self):
        """Estocastico com dados insuficientes deve retornar 50 como padrao."""
        highs = [100, 101, 102]
        lows = [99, 100, 101]
        closes = [100, 101, 102]

        k, d = FeatureEnricher.calculate_stochastic(highs, lows, closes, period=14)
        assert k == 50.0
        assert d == 50.0


class TestWilliamsR:
    """Testes para indicador Williams %R."""

    def test_williams_r_basic(self):
        """Valida calculo basico do Williams %R."""
        highs = [100, 102, 104, 103, 105, 106, 105, 107, 108, 106, 105, 104, 103, 102, 101]
        lows = [95, 97, 99, 98, 100, 101, 100, 102, 103, 101, 100, 99, 98, 97, 96]
        closes = [98, 101, 102, 100, 104, 105, 103, 106, 107, 105, 104, 103, 102, 100, 99]

        williams = FeatureEnricher.calculate_williams_r(highs, lows, closes, period=14)

        assert isinstance(williams, float)
        assert -100.0 <= williams <= 0.0

    def test_williams_r_at_high(self):
        """Williams %R deve estar proximo de 0 quando preco esta no maximo."""
        highs = [100, 101, 102, 103, 104, 105, 106] * 2 + [107, 107, 107, 107, 107, 107, 107]
        lows = [99, 100, 101, 102, 103, 104, 105] * 2 + [100, 100, 100, 100, 100, 100, 100]
        closes = [107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107]

        williams = FeatureEnricher.calculate_williams_r(highs, lows, closes, period=14)
        assert williams > -20.0, "Williams %R deve estar perto de 0 (menos negativo) quando preco no topo"

    def test_williams_r_insufficient_data(self):
        """Williams %R com dados insuficientes deve retornar -50."""
        highs = [100, 101, 102]
        lows = [99, 100, 101]
        closes = [100, 101, 102]

        williams = FeatureEnricher.calculate_williams_r(highs, lows, closes, period=14)
        assert williams == -50.0


class TestATRNormalized:
    """Testes para ATR normalizado."""

    def test_atr_normalized_basic(self):
        """Valida calculo basico do ATR normalizado."""
        highs = [100, 102, 104, 103, 105, 106, 105, 107, 108, 106, 105, 104, 103, 102, 101]
        lows = [95, 97, 99, 98, 100, 101, 100, 102, 103, 101, 100, 99, 98, 97, 96]
        closes = [98, 101, 102, 100, 104, 105, 103, 106, 107, 105, 104, 103, 102, 100, 99]

        atr_norm = FeatureEnricher.calculate_atr_normalized(highs, lows, closes, period=14)

        assert isinstance(atr_norm, float)
        assert atr_norm >= 0.0

    def test_atr_normalized_high_volatility(self):
        """ATR normalizado maior em periodos de alta volatilidade."""
        # Periodo 1: baixa volatilidade
        highs_low = [100] * 14
        lows_low = [99.5] * 14
        closes_low = [100] * 14
        atr_low = FeatureEnricher.calculate_atr_normalized(highs_low, lows_low, closes_low, period=14)

        # Periodo 2: alta volatilidade
        highs_high = [100 + i*2 for i in range(14)]
        lows_high = [98 + i*2 for i in range(14)]
        closes_high = [99 + i*2 for i in range(14)]
        atr_high = FeatureEnricher.calculate_atr_normalized(highs_high, lows_high, closes_high, period=14)

        assert atr_high > atr_low, "ATR normalizado deve ser maior em periodos volateis"


def test_feature_enricher_integration():
    """Teste de integracao: indicadores devem estar no output do enricher."""
    # Mock basico para validacao
    enricher = FeatureEnricher()

    # Testar que os novos metodos sao acessiveis
    assert hasattr(enricher, 'calculate_stochastic')
    assert hasattr(enricher, 'calculate_williams_r')
    assert hasattr(enricher, 'calculate_atr_normalized')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
