"""
Gerenciador de Rate Limiting para Binance API.

Garante que <1200 requisições por minuto sejam respeitadas.
Implementa backoff exponencial e throttling inteligente.
"""

import logging
import time
from datetime import datetime, timedelta
from collections import deque
from typing import Deque, Optional

logger = logging.getLogger(__name__)


class RateLimitManager:
    """
    Gerencia rate limits da Binance API.
    
    Binance Futures limita a 1200 requisições por minuto.
    Este manager implementa janelas deslizantes de 60 segundos.
    """

    def __init__(
        self,
        max_requests_per_minute: int = 1200,
        window_size_seconds: int = 60,
    ):
        """
        Inicializar gerenciador de rate limit.
        
        Args:
            max_requests_per_minute: Limite da Binance (default 1200)
            window_size_seconds: Tamanho da janela de rastreamento (default 60s)
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.window_size_seconds = window_size_seconds
        
        # Janela deslizante: deque com timestamps das requisições
        self._request_timestamps: Deque[float] = deque()
        
        # Rastreamento de período
        self._window_start = datetime.now()
        self._request_count_in_window = 0
        
        # Throttling
        self._throttle_until: Optional[float] = None
        
        logger.info(
            f"RateLimitManager inicializado: {max_requests_per_minute} req/min, "
            f"janela {window_size_seconds}s"
        )

    def get_max_requests_per_second(self) -> float:
        """
        Calcular máximo de requisições por segundo.
        
        Returns:
            Taxa máxima em req/s
        """
        return self.max_requests_per_minute / 60.0

    def record_request(self) -> None:
        """
        Registrar nova requisição.
        
        Adiciona timestamp ao histórico de requisições.
        """
        current_time = time.time()
        self._request_timestamps.append(current_time)
        self._request_count_in_window += 1

    def is_rate_limited(self) -> bool:
        """
        Verificar se sistema está rate limited.
        
        Retorna:
            True se limite foi atingido
        """
        # Limpar timestamps antigos (> 60s)
        current_time = time.time()
        cutoff_time = current_time - self.window_size_seconds
        
        # Remover requisições antigas da janela
        while self._request_timestamps and self._request_timestamps[0] < cutoff_time:
            self._request_timestamps.popleft()
        
        # Verificar se reached limit
        current_requests = len(self._request_timestamps)
        
        if current_requests >= self.max_requests_per_minute:
            logger.warning(
                f"⚠️  Rate limit atingido: {current_requests}/{self.max_requests_per_minute} req/min"
            )
            return True
        
        return False

    def get_current_minute_requests(self) -> int:
        """
        Obter contagem de requisições no minuto atual.
        
        Returns:
            Número de requisições na janela deslizante
        """
        # Limpar timestamps antigos
        current_time = time.time()
        cutoff_time = current_time - self.window_size_seconds
        
        while self._request_timestamps and self._request_timestamps[0] < cutoff_time:
            self._request_timestamps.popleft()
        
        return len(self._request_timestamps)

    def get_wait_time(self) -> float:
        """
        Calcular tempo de espera até desthrottle.
        
        Returns:
            Segundos até poder fazer nova requisição (0 se imediato)
        """
        current_time = time.time()
        
        if not self._request_timestamps:
            return 0.0
        
        # Tempo até a requisição mais antiga sair da janela
        oldest_request = self._request_timestamps[0]
        time_until_clear = (oldest_request + self.window_size_seconds) - current_time
        
        return max(0.0, time_until_clear)

    def wait_if_needed(self) -> None:
        """
        Bloquear se necessário até poder fazer requisição.
        
        Implementa throttling inteligente com backoff.
        """
        if not self.is_rate_limited():
            return
        
        wait_time = self.get_wait_time()
        if wait_time > 0:
            logger.info(f"🚦 Throttling: aguardando {wait_time:.2f}s antes de próxima req...")
            time.sleep(wait_time + 0.1)  # +100ms de margem

    def get_requests_until_limit(self) -> int:
        """
        Obter quantas requisições ainda podem ser feitas antes de atingir limite.
        
        Returns:
            Número de requisições disponíveis
        """
        current_requests = self.get_current_minute_requests()
        remaining = self.max_requests_per_minute - current_requests
        return max(0, remaining)

    def estimate_recovery_time(self) -> float:
        """
        Estimar quanto tempo falta para recuperação (em segundos).
        
        Returns:
            Tempo em segundos até limite resetar
        """
        if not self.is_rate_limited():
            return 0.0
        
        return self.get_wait_time()

    def reset(self) -> None:
        """
        Resetar manualmente o gerenciador (ex: ao mudar de minuto UTC).
        
        Útil para sincronizar com servidor Binance.
        """
        self._request_timestamps.clear()
        self._request_count_in_window = 0
        self._window_start = datetime.now()
        logger.info("RateLimitManager resetado manualmente")


class AdaptiveRateLimiter:
    """
    Rate limiter adaptativo que automaticamente ajusta taxa.
    
    Monitora 429 (Too Many Requests) e reduz taxa automaticamente.
    """

    def __init__(self, initial_max_per_minute: int = 1200):
        """
        Inicializar rate limiter adaptativo.
        
        Args:
            initial_max_per_minute: Taxa inicial
        """
        self.base_manager = RateLimitManager(max_requests_per_minute=initial_max_per_minute)
        self.current_max = initial_max_per_minute
        self.retry_count = 0
        self.max_retries = 3
        
        logger.info(f"AdaptiveRateLimiter inicializado em {self.current_max} req/min")

    def record_success(self) -> None:
        """Registrar sucesso de requisição."""
        self.base_manager.record_request()
        self.retry_count = 0

    def record_rate_limit_hit(self) -> None:
        """Registrar que rate limit foi atingido (429)."""
        self.retry_count += 1
        
        # Reduzir taxa em 10% a cada hit, mínimo 600
        if self.retry_count > 0:
            reduction_factor = 0.9 ** self.retry_count
            self.current_max = max(600, int(1200 * reduction_factor))
            
            logger.warning(
                f"⚠️  Rate limit hit (429). Reduzindo taxa para {self.current_max} req/min "
                f"({self.retry_count}/{self.max_retries} retries)"
            )
            
            # Resetar manager com nova taxa
            self.base_manager = RateLimitManager(max_requests_per_minute=self.current_max)

    def can_retry(self) -> bool:
        """Validar se pode fazer retry."""
        return self.retry_count < self.max_retries

    def wait_exponential_backoff(self) -> None:
        """Implementar backoff exponencial pós rate limit."""
        wait_time = min(2.0 ** self.retry_count, 60.0)  # Max 60s
        logger.info(f"⏳ Backoff exponencial: aguardando {wait_time:.1f}s...")
        time.sleep(wait_time)


if __name__ == "__main__":
    # Exemplo de uso
    limiter = RateLimitManager(max_requests_per_minute=1200)
    
    print(f"Max requests per second: {limiter.get_max_requests_per_second():.2f}")
    
    # Simular 5 requisições
    for i in range(5):
        limiter.record_request()
        print(f"Requisição {i+1}: {limiter.get_current_minute_requests()} no minuto")
    
    print(f"Rate limited: {limiter.is_rate_limited()}")
    print(f"Requisições disponíveis: {limiter.get_requests_until_limit()}")
