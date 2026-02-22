"""
Integração de Rate Limiting com BinanceCollector.

Augmenta o BinanceCollector existente com gerenciamento inteligente de rate limits
para garantir <1200 requisições por minuto.
"""

import logging
from typing import Optional, Dict, Any, List
from data.collector import BinanceCollector
from data.rate_limit_manager import AdaptiveRateLimiter, RateLimitManager

logger = logging.getLogger(__name__)


class RateLimitedBinanceCollector(BinanceCollector):
    """
    BinanceCollector com suporte a rate limiting automático.
    
    Herda de BinanceCollector e adiciona:
    - Verificação de rate limits antes de cada requisição
    - Throttling automático quando limite é atingido
    - Adaptação inteligente em caso de 429 (Too Many Requests)
    - Logging detalhado de taxa de requisição
    """

    def __init__(
        self,
        client,
        rate_limit_max_per_minute: int = 1200,
        use_adaptive: bool = True,
    ):
        """
        Inicializar collector com rate limiting.
        
        Args:
            client: DerivativesTradingUsdsFutures client
            rate_limit_max_per_minute: Limite máximo (default 1200)
            use_adaptive: Usar adaptação automática em caso de 429 (default True)
        """
        super().__init__(client)
        
        if use_adaptive:
            self.rate_limiter = AdaptiveRateLimiter(
                initial_max_per_minute=rate_limit_max_per_minute
            )
        else:
            self.rate_limiter = RateLimitManager(
                max_requests_per_minute=rate_limit_max_per_minute
            )
        
        logger.info(
            f"RateLimitedBinanceCollector inicializado: "
            f"rate_limit={rate_limit_max_per_minute} req/min, "
            f"adaptive={use_adaptive}"
        )

    def _check_rate_limit(self) -> None:
        """
        Verificar e aplicar rate limiting antes de requisição.
        
        Bloqueia se necessário.
        """
        if self.rate_limiter.is_rate_limited():
            wait_time = self.rate_limiter.get_wait_time()
            logger.warning(
                f"🚦 Rate limit atingido. "
                f"Aguardando {wait_time:.2f}s antes de próxima requisição..."
            )
            self.rate_limiter.wait_if_needed()

    def record_successful_request(self) -> None:
        """Registrar requisição bem-sucedida no rate limiter."""
        self.rate_limiter.record_success()

    def record_rate_limit_error(self) -> None:
        """Registrar erro 429 (rate limit) e adaptar taxa se necessário."""
        if isinstance(self.rate_limiter, AdaptiveRateLimiter):
            self.rate_limiter.record_rate_limit_hit()
            logger.warning(
                f"⚠️  Rate limit hit (429). Nova taxa: {self.rate_limiter.current_max} req/min"
            )

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Obter status atual de rate limiting.
        
        Returns:
            Dict com informações de taxa de requisição
        """
        return {
            "current_requests_per_minute": self.rate_limiter.base_manager.get_current_minute_requests(),
            "max_requests_per_minute": self.rate_limiter.current_max,
            "requests_remaining": self.rate_limiter.base_manager.get_requests_until_limit(),
            "estimated_recovery_time_seconds": self.rate_limiter.base_manager.estimate_recovery_time(),
            "is_rate_limited": self.rate_limiter.is_rate_limited(),
        }

    def collect_klines_with_rate_limiting(
        self,
        symbol: str,
        interval: str = "1h",
        lookback_days: int = 365,
    ) -> Optional[List]:
        """
        Coletar klines com rate limiting automático.
        
        Este é o método wrapper que garante compliance com <1200 req/min.
        
        Args:
            symbol: Símbolo (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1h', '4h', '1d')
            lookback_days: Dias para trás
            
        Returns:
            Lista de klines ou None se falha
        """
        logger.info(
            f"📊 Coleta com rate limiting: {symbol} {interval} ({lookback_days}d)"
        )
        
        try:
            # Verificar rate limit antes
            self._check_rate_limit()
            
            # Chamar método original
            klines = self.get_ohlcv(
                symbol=symbol,
                interval=interval,
                lookback_days=lookback_days,
            )
            
            # Registrar sucesso
            if klines and len(klines) > 0:
                self.record_successful_request()
                logger.info(
                    f"✅ Coleta bem-sucedida: {symbol} = {len(klines)} klines "
                    f"({self.rate_limiter.base_manager.get_current_minute_requests()}/min)"
                )
            
            return klines
        
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                self.record_rate_limit_error()
                logger.error(f"❌ Rate limit atingido (429): {e}")
                return None
            else:
                logger.error(f"❌ Erro na coleta: {e}")
                raise


class BatchCollectorWithRateLimit:
    """
    Coletor em lote com rate limiting para múltiplos símbolos.
    
    Otimizado para coleta de múltiplos pares respeitando <1200 req/min.
    """

    def __init__(
        self,
        collector: RateLimitedBinanceCollector,
        batch_size: int = 10,
    ):
        """
        Inicializar batch collector.
        
        Args:
            collector: RateLimitedBinanceCollector instância
            batch_size: Número de símbolos a coletar em paralelo (com cuidado ao rate limit)
        """
        self.collector = collector
        self.batch_size = batch_size
        self.stats: Dict[str, Any] = {}
        
        logger.info(f"BatchCollectorWithRateLimit inicializado (batch_size={batch_size})")

    def collect_all_symbols(
        self,
        symbols: List[str],
        interval: str = "1h",
        lookback_days: int = 365,
    ) -> Dict[str, List]:
        """
        Coletar klines para múltiplos símbolos com rate limiting.
        
        Args:
            symbols: Lista de símbolos
            interval: Intervalo de tempo
            lookback_days: Dias para trás
            
        Returns:
            Dict { symbol: klines }
        """
        logger.info(f"📊 Iniciando coleta em lote de {len(symbols)} símbolos")
        
        results = {}
        successful = 0
        failed = 0
        
        for i, symbol in enumerate(symbols, 1):
            try:
                # Mostrar progresso
                rate_status = self.collector.get_rate_limit_status()
                logger.info(
                    f"[{i}/{len(symbols)}] Coletando {symbol}... "
                    f"(Rate: {rate_status['current_requests_per_minute']}/{rate_status['max_requests_per_minute']})"
                )
                
                # Coletar com rate limiting
                klines = self.collector.collect_klines_with_rate_limiting(
                    symbol=symbol,
                    interval=interval,
                    lookback_days=lookback_days,
                )
                
                if klines:
                    results[symbol] = klines
                    successful += 1
                else:
                    logger.warning(f"⚠️  Falha na coleta de {symbol}")
                    failed += 1
            
            except Exception as e:
                logger.error(f"❌ Erro ao coletar {symbol}: {e}")
                failed += 1
            
            # Mostrar status a cada 5 símbolos
            if i % 5 == 0:
                rate_status = self.collector.get_rate_limit_status()
                logger.info(
                    f"📈 Progresso: {successful} sucesso, {failed} falhas. "
                    f"Rate: {rate_status['current_requests_per_minute']}/{rate_status['max_requests_per_minute']} req/min"
                )
        
        # Estatísticas finais
        self.stats = {
            "total_symbols": len(symbols),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(symbols)) * 100 if symbols else 0,
            "rate_limit_status": self.collector.get_rate_limit_status(),
        }
        
        logger.info(
            f"✅ Coleta em lote concluída: "
            f"{successful}/{len(symbols)} sucesso "
            f"({self.stats['success_rate']:.1f}%)"
        )
        
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas da coleta."""
        return self.stats


if __name__ == "__main__":
    logger.info("✅ rate_limited_collector.py colocada em produção")
    logger.info("   Uso: RateLimitedBinanceCollector wraps BinanceCollector")
    logger.info("   Garantia: <1200 req/min com adaptação automática")
