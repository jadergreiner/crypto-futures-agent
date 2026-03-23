"""Cache OHLCV read-through para fluxo Model 2.0."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time
from typing import Any, Callable, Mapping, Sequence


def _utc_now_ms() -> int:
    return int(time() * 1000)


def build_cache_key(symbol: str, timeframe: str, limit: int) -> str:
    """Gera chave canonica de cache por simbolo/timeframe/limite."""
    return f"{str(symbol).upper()}:{str(timeframe).upper()}:{int(limit)}"


class CacheFallbackReason(str, Enum):
    """Motivos de fallback do cache para trilha operacional."""

    CACHE_BACKEND_ERROR = "cache_backend_error"
    CACHE_STALE = "cache_stale"


@dataclass(frozen=True)
class OhlcvFetchResult:
    """Contrato de retorno da camada de cache OHLCV."""

    candles: list[dict[str, Any]]
    source: str
    fetched_at_ms: int
    fallback_reason: str | None = None


class OhlcvCacheProvider:
    """Provider read-through com TTL por timeframe."""

    def __init__(
        self,
        default_ttl_seconds: int = 30,
        ttl_by_timeframe: Mapping[str, int] | None = None,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        self._default_ttl_ms = max(1, int(default_ttl_seconds)) * 1000
        self._ttl_by_timeframe = {
            str(k).upper(): max(1, int(v)) * 1000
            for k, v in (ttl_by_timeframe or {}).items()
        }
        self._now_ms = now_ms or _utc_now_ms
        self._cache: dict[str, tuple[int, list[dict[str, Any]]]] = {}
        self._hits = 0
        self._misses = 0

    def _ttl_ms_for_timeframe(self, timeframe: str) -> int:
        return self._ttl_by_timeframe.get(str(timeframe).upper(), self._default_ttl_ms)

    def invalidate(self, symbol: str | None = None, timeframe: str | None = None) -> None:
        """Invalida cache completo ou recorte por simbolo/timeframe."""
        if symbol is None and timeframe is None:
            self._cache.clear()
            return

        symbol_upper = str(symbol).upper() if symbol is not None else None
        timeframe_upper = str(timeframe).upper() if timeframe is not None else None

        keys_to_remove: list[str] = []
        for key in self._cache:
            key_symbol, key_timeframe, _ = key.split(":", 2)
            if symbol_upper is not None and key_symbol != symbol_upper:
                continue
            if timeframe_upper is not None and key_timeframe != timeframe_upper:
                continue
            keys_to_remove.append(key)

        for key in keys_to_remove:
            self._cache.pop(key, None)

    def stats(self) -> dict[str, float]:
        """Retorna telemetria minima de hit/miss do cache."""
        total = self._hits + self._misses
        return {
            "hits": float(self._hits),
            "misses": float(self._misses),
            "hit_rate": float(self._hits / total) if total else 0.0,
        }

    def get_many(
        self,
        requests: Sequence[tuple[str, str, int]],
        loader: Callable[[str, str, int], list[dict[str, Any]]],
    ) -> dict[str, OhlcvFetchResult]:
        """Busca multiplas chaves em cache com fallback para loader."""
        now_ms = self._now_ms()
        results: dict[str, OhlcvFetchResult] = {}

        for symbol, timeframe, limit in requests:
            key = build_cache_key(symbol=symbol, timeframe=timeframe, limit=limit)
            cached = self._cache.get(key)
            ttl_ms = self._ttl_ms_for_timeframe(timeframe)
            stale = False

            if cached is not None:
                cached_at_ms, cached_candles = cached
                if now_ms - cached_at_ms <= ttl_ms:
                    self._hits += 1
                    results[key] = OhlcvFetchResult(
                        candles=list(cached_candles),
                        source="cache",
                        fetched_at_ms=now_ms,
                    )
                    continue
                stale = True

            self._misses += 1
            fallback_reason: str | None = (
                CacheFallbackReason.CACHE_STALE.value if stale else None
            )
            try:
                candles = list(loader(symbol, timeframe, limit))
            except Exception:
                fallback_reason = CacheFallbackReason.CACHE_BACKEND_ERROR.value
                candles = []

            self._cache[key] = (now_ms, candles)
            results[key] = OhlcvFetchResult(
                candles=candles,
                source="live",
                fetched_at_ms=now_ms,
                fallback_reason=fallback_reason,
            )

        return results
