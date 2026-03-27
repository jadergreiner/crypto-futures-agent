"""Suite RED para M2-025.7: RetryPolicy em market_reader.py com fallback conservador.

Testa:
- RetryPolicy executa N tentativas antes de falhar
- Fallback conservador retornado quando todas tentativas esgotadas
- Erros transientes sao tratados com backoff
- Erros permanentes nao sao retentados
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call, patch

# Importacoes RED - modulo ainda nao existe
from core.model2.market_reader import MarketReader, RetryPolicy, MarketReaderResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def policy() -> RetryPolicy:
    """Politica de retry: 3 tentativas, sem backoff real."""
    return RetryPolicy(max_attempts=3, base_delay_ms=0, backoff_factor=1.0)


@pytest.fixture
def reader(policy: RetryPolicy) -> MarketReader:
    """MarketReader com policy de teste."""
    return MarketReader(retry_policy=policy)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_retry_policy_sucesso_na_primeira_tentativa(reader: MarketReader) -> None:
    """Deve retornar dados na primeira tentativa sem retries."""
    candles_mock = [{"close": 97000.0, "ts": 1700000000000}]
    source = MagicMock(return_value=candles_mock)

    resultado: MarketReaderResult = reader.fetch_candles(
        symbol="BTCUSDT",
        timeframe="4h",
        source_fn=source,
    )

    assert resultado.success is True
    assert resultado.candles == candles_mock
    assert source.call_count == 1


def test_retry_policy_retenta_em_erro_transiente(reader: MarketReader) -> None:
    """Deve retentar em erros transientes e ter sucesso na segunda tentativa."""
    candles_mock = [{"close": 97000.0, "ts": 1700000000000}]
    source = MagicMock(side_effect=[ConnectionError("timeout"), candles_mock])

    resultado: MarketReaderResult = reader.fetch_candles(
        symbol="BTCUSDT",
        timeframe="4h",
        source_fn=source,
    )

    assert resultado.success is True
    assert source.call_count == 2


def test_retry_policy_fallback_conservador_quando_esgotado(reader: MarketReader) -> None:
    """Deve retornar fallback conservador quando todas as tentativas falham."""
    source = MagicMock(side_effect=ConnectionError("timeout"))

    resultado: MarketReaderResult = reader.fetch_candles(
        symbol="BTCUSDT",
        timeframe="4h",
        source_fn=source,
    )

    assert resultado.success is False
    assert resultado.is_fallback is True
    assert resultado.candles == []
    assert source.call_count == 3  # max_attempts


def test_retry_policy_nao_retenta_erro_permanente(reader: MarketReader) -> None:
    """Erros permanentes (ex: simbolo invalido) nao devem ser retentados."""
    source = MagicMock(side_effect=ValueError("simbolo invalido"))

    resultado: MarketReaderResult = reader.fetch_candles(
        symbol="INVALID",
        timeframe="4h",
        source_fn=source,
    )

    assert resultado.success is False
    assert source.call_count == 1  # sem retry em erro permanente


def test_retry_policy_resultado_inclui_tentativas_realizadas(reader: MarketReader) -> None:
    """MarketReaderResult deve expor numero de tentativas realizadas."""
    source = MagicMock(side_effect=[ConnectionError("t1"), ConnectionError("t2"), []])

    resultado: MarketReaderResult = reader.fetch_candles(
        symbol="BTCUSDT",
        timeframe="4h",
        source_fn=source,
    )

    assert hasattr(resultado, "attempts")
    assert resultado.attempts == 3


def test_retry_policy_fallback_nao_bloqueia_pipeline(reader: MarketReader) -> None:
    """Fallback conservador deve ter campo indicativo para pipeline ignorar ciclo."""
    source = MagicMock(side_effect=ConnectionError("timeout"))

    resultado: MarketReaderResult = reader.fetch_candles(
        symbol="BTCUSDT",
        timeframe="4h",
        source_fn=source,
    )

    # Pipeline deve poder verificar se deve pular processamento
    assert hasattr(resultado, "skip_cycle")
    assert resultado.skip_cycle is True
