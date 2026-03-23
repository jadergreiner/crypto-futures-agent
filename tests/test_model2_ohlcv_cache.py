"""Suite RED da BLID-084 para cache OHLCV read-through."""

from __future__ import annotations

import importlib
import inspect

import pytest


def _get_cache_module():
    """Carrega modulo de cache esperado pela BLID-084."""
    try:
        return importlib.import_module("core.model2.ohlcv_cache")
    except ModuleNotFoundError as exc:
        pytest.fail(
            "Modulo core.model2.ohlcv_cache ausente: BLID-084 requer "
            "provider unico de cache OHLCV.",
            pytrace=False,
        )


def _get_cache_provider_class():
    """Retorna classe canonica do provider de cache da BLID-084."""
    module = _get_cache_module()
    provider_cls = getattr(module, "OhlcvCacheProvider", None)
    if provider_cls is None:
        pytest.fail(
            "Classe OhlcvCacheProvider ausente em core.model2.ohlcv_cache.",
            pytrace=False,
        )
    return provider_cls


def test_ohlcv_cache_provider_existe_com_nome_canonico() -> None:
    """Garante API publica minima para provider unico de candles."""
    # Arrange
    provider_cls = _get_cache_provider_class()

    # Act
    name = provider_cls.__name__

    # Assert
    assert name == "OhlcvCacheProvider"


def test_ohlcv_cache_provider_suporta_ttl_configuravel() -> None:
    """Exige construtor com TTL default e override por chave."""
    # Arrange
    provider_cls = _get_cache_provider_class()
    signature = inspect.signature(provider_cls)

    # Act
    params = set(signature.parameters.keys())

    # Assert
    assert "default_ttl_seconds" in params
    assert "ttl_by_timeframe" in params


def test_ohlcv_cache_provider_expoe_get_many() -> None:
    """Exige operacao batelada para reduzir chamadas redundantes."""
    # Arrange
    provider_cls = _get_cache_provider_class()

    # Act
    get_many = getattr(provider_cls, "get_many", None)

    # Assert
    assert callable(get_many)


def test_ohlcv_cache_provider_expoe_invalidate() -> None:
    """Exige invalidacao explicita para controle de staleness."""
    # Arrange
    provider_cls = _get_cache_provider_class()

    # Act
    invalidate = getattr(provider_cls, "invalidate", None)

    # Assert
    assert callable(invalidate)


def test_ohlcv_cache_provider_expoe_stats_hit_miss() -> None:
    """Exige telemetria minima para hit/miss no cache."""
    # Arrange
    provider_cls = _get_cache_provider_class()

    # Act
    stats = getattr(provider_cls, "stats", None)

    # Assert
    assert callable(stats)


def test_scan_runner_expoe_loader_com_cache() -> None:
    """Exige ponto de extensao de cache no runner de scan."""
    # Arrange
    scan_module = importlib.import_module("scripts.model2.scan")

    # Act
    cached_loader = getattr(scan_module, "_load_candles_cached", None)

    # Assert
    assert callable(cached_loader)


def test_validate_runner_expoe_loader_com_cache() -> None:
    """Exige ponto de extensao de cache no runner de validate."""
    # Arrange
    validate_module = importlib.import_module("scripts.model2.validate")

    # Act
    cached_loader = getattr(validate_module, "_load_candles_cached", None)

    # Assert
    assert callable(cached_loader)


def test_resolve_runner_expoe_loader_com_cache() -> None:
    """Exige ponto de extensao de cache no runner de resolve."""
    # Arrange
    resolve_module = importlib.import_module("scripts.model2.resolve")

    # Act
    cached_loader = getattr(resolve_module, "_load_candles_cached", None)

    # Assert
    assert callable(cached_loader)


def test_run_scan_aceita_cache_provider_injetavel() -> None:
    """Exige injeção de provider para testes determinísticos."""
    # Arrange
    scan_module = importlib.import_module("scripts.model2.scan")
    signature = inspect.signature(scan_module.run_scan)

    # Act
    params = set(signature.parameters.keys())

    # Assert
    assert "cache_provider" in params


def test_run_validation_aceita_cache_provider_injetavel() -> None:
    """Exige injeção de provider para reduzir acoplamento com DB."""
    # Arrange
    validate_module = importlib.import_module("scripts.model2.validate")
    signature = inspect.signature(validate_module.run_validation)

    # Act
    params = set(signature.parameters.keys())

    # Assert
    assert "cache_provider" in params


def test_run_resolution_aceita_cache_provider_injetavel() -> None:
    """Exige injeção de provider para uso unificado de candles."""
    # Arrange
    resolve_module = importlib.import_module("scripts.model2.resolve")
    signature = inspect.signature(resolve_module.run_resolution)

    # Act
    params = set(signature.parameters.keys())

    # Assert
    assert "cache_provider" in params


def test_sync_market_context_expoe_chave_cache_hit_rate() -> None:
    """Exige indicador de hit-rate no resumo operacional de sync."""
    # Arrange
    sync_module = importlib.import_module("scripts.model2.sync_market_context")

    # Act
    summary_fields = getattr(sync_module, "SUMMARY_FIELDS", None)

    # Assert
    assert isinstance(summary_fields, tuple)
    assert "cache_hit_rate" in summary_fields


def test_cache_tem_chave_por_simbolo_timeframe_limite() -> None:
    """Exige granularidade de chave para evitar colisoes de payload."""
    # Arrange
    module = _get_cache_module()
    key_builder = getattr(module, "build_cache_key", None)

    # Act
    assert callable(key_builder)
    key = key_builder(symbol="BTCUSDT", timeframe="H4", limit=240)

    # Assert
    assert key == "BTCUSDT:H4:240"


def test_cache_define_fallback_fail_safe_sem_excecao_vazia() -> None:
    """Exige caminho fail-safe com motivo auditavel."""
    # Arrange
    module = _get_cache_module()
    reason_enum = getattr(module, "CacheFallbackReason", None)

    # Act
    assert reason_enum is not None
    values = {item.value for item in reason_enum}

    # Assert
    assert "cache_backend_error" in values
    assert "cache_stale" in values


def test_cache_expoe_contrato_de_retorno_com_source() -> None:
    """Exige source explicito para auditoria de origem dos candles."""
    # Arrange
    module = _get_cache_module()
    result_type = getattr(module, "OhlcvFetchResult", None)

    # Act
    assert result_type is not None
    fields = getattr(result_type, "__annotations__", {})

    # Assert
    assert "candles" in fields
    assert "source" in fields
    assert "fetched_at_ms" in fields
