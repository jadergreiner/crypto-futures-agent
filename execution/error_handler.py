"""
Error Handler — Tratamento estruturado de erros em execucao de ordens.

Modulo que implementa:
- Captura de excecoes da Binance API (APIError, NetworkError, TimeoutError)
- Strategy pattern para diferentes tipos de erro
- Logging estruturado em portugues
- Recuperacao inteligente com backoff exponencial
"""

import logging
import time
from typing import Optional, Callable, Any, Dict, Tuple
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Tipos de erro que podem ocorrer durante execucao."""
    API_ERROR = "api_error"  # Erro geral da Binance API
    NETWORK_ERROR = "network_error"  # Problema de conectividade
    TIMEOUT_ERROR = "timeout_error"  # Timeout na requisicao
    RATE_LIMIT_ERROR = "rate_limit_error"  # 429 Too Many Requests
    INSUFFICIENT_BALANCE = "insufficient_balance"  # Saldo insuficiente
    INVALID_ORDER = "invalid_order"  # Ordem invalida
    UNKNOWN_ERROR = "unknown_error"  # Erro desconhecido


class ErrorSeverity(Enum):
    """Niveis de severidade do erro."""
    LOW = "baixa"  # Pode tentar novamente imediatamente
    MEDIUM = "media"  # Aguardar um pouco antes de tentar
    HIGH = "alta"  # Aguardar bastante tempo
    CRITICAL = "critica"  # Nao tentar mais


class ErrorRecoveryStrategy:
    """Estrategia de recuperacao para um tipo de erro."""

    def __init__(
        self,
        error_type: ErrorType,
        severity: ErrorSeverity,
        should_retry: bool,
        max_retries: int,
        initial_backoff_seconds: float,
        max_backoff_seconds: float,
    ):
        """
        Inicializar estrategia de recuperacao.

        Args:
            error_type: Tipo de erro
            severity: Severidade do erro
            should_retry: Se deve tentar novamente
            max_retries: Numero maximo de tentativas
            initial_backoff_seconds: Tempo inicial de espera (segundos)
            max_backoff_seconds: Tempo maximo de espera (segundos)
        """
        self.error_type = error_type
        self.severity = severity
        self.should_retry = should_retry
        self.max_retries = max_retries
        self.initial_backoff_seconds = initial_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds

    def calculate_backoff(self, attempt_number: int) -> float:
        """
        Calcular tempo de backoff exponencial.

        Usa backoff exponencial: initial_backoff * 2^(attempt-1)
        com limite maximo de max_backoff_seconds.

        Args:
            attempt_number: Numero da tentativa (1-indexed)

        Returns:
            Tempo de espera em segundos
        """
        backoff = (
            self.initial_backoff_seconds * (2 ** (attempt_number - 1))
        )
        return min(backoff, self.max_backoff_seconds)


class ErrorHandler:
    """
    Handler central de erros durante execucao de ordens.

    Responsabilidades:
    - Identificar tipo de erro
    - Mapear para estrategia de recuperacao
    - Executar retry com backoff exponencial
    - Fazer log estruturado em portugues
    - Permitir hook customizado de tratamento
    """

    def __init__(self):
        """Inicializar ErrorHandler com estrategias padrao."""
        self._strategies: Dict[ErrorType, ErrorRecoveryStrategy] = {}
        self._error_handlers: Dict[ErrorType, Callable] = {}
        self._initialize_default_strategies()

    def _initialize_default_strategies(self) -> None:
        """Inicializar estrategias padrao para cada tipo de erro."""
        # API Error: pode tentar 3 vezes, aguardando 1-8 segundos
        self.register_strategy(
            ErrorRecoveryStrategy(
                error_type=ErrorType.API_ERROR,
                severity=ErrorSeverity.MEDIUM,
                should_retry=True,
                max_retries=3,
                initial_backoff_seconds=1.0,
                max_backoff_seconds=8.0,
            )
        )

        # Network Error: pode tentar 5 vezes, aguardando 2-16 segundos
        self.register_strategy(
            ErrorRecoveryStrategy(
                error_type=ErrorType.NETWORK_ERROR,
                severity=ErrorSeverity.HIGH,
                should_retry=True,
                max_retries=5,
                initial_backoff_seconds=2.0,
                max_backoff_seconds=16.0,
            )
        )

        # Timeout Error: pode tentar 3 vezes, aguardando 1-4 segundos
        self.register_strategy(
            ErrorRecoveryStrategy(
                error_type=ErrorType.TIMEOUT_ERROR,
                severity=ErrorSeverity.MEDIUM,
                should_retry=True,
                max_retries=3,
                initial_backoff_seconds=1.0,
                max_backoff_seconds=4.0,
            )
        )

        # Rate Limit Error: pode tentar 3 vezes, aguardando muito (60-300s)
        self.register_strategy(
            ErrorRecoveryStrategy(
                error_type=ErrorType.RATE_LIMIT_ERROR,
                severity=ErrorSeverity.CRITICAL,
                should_retry=True,
                max_retries=3,
                initial_backoff_seconds=60.0,
                max_backoff_seconds=300.0,
            )
        )

        # Insufficient Balance: nao tentar novamente
        self.register_strategy(
            ErrorRecoveryStrategy(
                error_type=ErrorType.INSUFFICIENT_BALANCE,
                severity=ErrorSeverity.HIGH,
                should_retry=False,
                max_retries=0,
                initial_backoff_seconds=0.0,
                max_backoff_seconds=0.0,
            )
        )

        # Invalid Order: nao tentar novamente
        self.register_strategy(
            ErrorRecoveryStrategy(
                error_type=ErrorType.INVALID_ORDER,
                severity=ErrorSeverity.HIGH,
                should_retry=False,
                max_retries=0,
                initial_backoff_seconds=0.0,
                max_backoff_seconds=0.0,
            )
        )

        # Unknown Error: pode tentar 2 vezes, aguardando 2-8 segundos
        self.register_strategy(
            ErrorRecoveryStrategy(
                error_type=ErrorType.UNKNOWN_ERROR,
                severity=ErrorSeverity.MEDIUM,
                should_retry=True,
                max_retries=2,
                initial_backoff_seconds=2.0,
                max_backoff_seconds=8.0,
            )
        )

    def register_strategy(
        self, strategy: ErrorRecoveryStrategy
    ) -> None:
        """
        Registrar estrategia de recuperacao customizada.

        Args:
            strategy: Estrategia a registrar
        """
        self._strategies[strategy.error_type] = strategy
        logger.info(
            f"Estrategia registrada: {strategy.error_type.value} "
            f"(severidade={strategy.severity.value}, "
            f"retry={strategy.should_retry}, "
            f"max_retries={strategy.max_retries})"
        )

    def register_error_handler(
        self,
        error_type: ErrorType,
        handler: Callable[[Exception, Dict[str, Any]], Any],
    ) -> None:
        """
        Registrar handler customizado para tipo de erro.

        Args:
            error_type: Tipo de erro
            handler: Funcao que sera chamada quando erro ocorrer
                    Assinatura: handler(exception, context) -> Any
        """
        self._error_handlers[error_type] = handler
        logger.info(
            f"Handler customizado registrado para {error_type.value}"
        )

    def get_strategy(self, error_type: ErrorType) -> ErrorRecoveryStrategy:
        """
        Obter estrategia de recuperacao para tipo de erro.

        Args:
            error_type: Tipo de erro

        Returns:
            Estrategia de recuperacao
        """
        return self._strategies.get(
            error_type, self._strategies[ErrorType.UNKNOWN_ERROR]
        )

    def classify_exception(
        self, exception: Exception
    ) -> Tuple[ErrorType, str]:
        """
        Classificar tipo de excecao e retornar mensagem descritiva.

        Args:
            exception: Excecao capturada

        Returns:
            Tupla (ErrorType, descricao_amigavel)
        """
        exc_name = exception.__class__.__name__
        exc_msg = str(exception)

        # Verificar por 429 (rate limit) primeiro
        if "429" in exc_msg or "too many requests" in exc_msg.lower():
            return (
                ErrorType.RATE_LIMIT_ERROR,
                "Rate limit atingido (429 Too Many Requests)"
            )

        # Verificar por timeout
        if "Timeout" in exc_name or "timeout" in exc_msg.lower():
            return (
                ErrorType.TIMEOUT_ERROR,
                "Timeout na requisicao para Binance"
            )

        # Verificar por network error
        if "Network" in exc_name or "Connection" in exc_name:
            return (
                ErrorType.NETWORK_ERROR,
                f"Erro de conectividade: {exc_msg[:100]}"
            )

        # Verificar por saldo insuficiente (antes de APIError generico)
        if "insufficient balance" in exc_msg.lower():
            return (
                ErrorType.INSUFFICIENT_BALANCE,
                "Saldo insuficiente para executar ordem"
            )

        # Verificar por APIError
        if "APIError" in exc_name or "APIError" in exc_msg or "BinanceAPIError" in exc_name:
            return (
                ErrorType.API_ERROR,
                f"Erro da API Binance: {exc_msg[:100]}"
            )

        # Padrao: erro desconhecido
        return (
            ErrorType.UNKNOWN_ERROR,
            f"Erro desconhecido ({exc_name}): {exc_msg[:100]}"
        )

    def handle_with_retry(
        self,
        operation: Callable[[], Any],
        operation_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Any], Optional[Dict[str, Any]]]:
        """
        Executar operacao com retry automatico em caso de erro.

        Args:
            operation: Funcao a executar (sem argumentos)
            operation_name: Nome descritivo da operacao (para logging)
            context: Contexto adicional para logging (ex: symbol, side, qty)

        Returns:
            Tupla (sucesso, resultado, info_erro)
            - sucesso: True se operacao bem-sucedida
            - resultado: Resultado da operacao ou None se falha
            - info_erro: Dicionario com info de erro ou None se sucesso
        """
        if context is None:
            context = {}

        error_info: Optional[Dict[str, Any]] = None
        last_exception: Optional[Exception] = None

        for attempt in range(1, 10):  # Maximo 10 tentativas globais
            try:
                logger.info(
                    f"[TENTATIVA {attempt}] Executando {operation_name}",
                    extra={"context": context}
                )
                result = operation()
                logger.info(
                    f"[SUCESSO] {operation_name} completada",
                    extra={"context": context}
                )
                return (True, result, None)

            except Exception as e:
                last_exception = e
                error_type, error_msg = self.classify_exception(e)
                strategy = self.get_strategy(error_type)

                error_info = {
                    "error_type": error_type.value,
                    "error_message": error_msg,
                    "error_details": str(e),
                    "attempt": attempt,
                    "timestamp": datetime.utcnow().isoformat(),
                    "context": context,
                }

                # Chamar handler customizado se registrado
                if error_type in self._error_handlers:
                    try:
                        self._error_handlers[error_type](e, context)
                    except Exception as handler_error:
                        logger.warning(
                            f"Erro no handler customizado: {handler_error}"
                        )

                # Decidir se retenta
                if not strategy.should_retry or attempt > strategy.max_retries:
                    logger.error(
                        f"[FALHA] {operation_name} falhou permanentemente",
                        extra={"error_info": error_info}
                    )
                    return (False, None, error_info)

                # Calcular backoff e aguardar
                backoff_seconds = strategy.calculate_backoff(attempt)
                logger.warning(
                    f"[ERRO] {operation_name}: {error_msg}. "
                    f"Tentando novamente em {backoff_seconds:.2f}s "
                    f"(tentativa {attempt}/{strategy.max_retries})",
                    extra={"error_info": error_info}
                )
                time.sleep(backoff_seconds)

        # Se chegou aqui, esgotou todas as tentativas
        logger.critical(
            f"[EXAUSTO] {operation_name} falhou apos multiplas tentativas",
            extra={"error_info": error_info}
        )
        return (False, None, error_info)

    def create_error_summary(
        self, error_info: Dict[str, Any]
    ) -> str:
        """
        Criar resumo legivel do erro para logging.

        Args:
            error_info: Dicionario com info de erro

        Returns:
            String formatada
        """
        return (
            f"[{error_info['error_type']}] "
            f"{error_info['error_message']} "
            f"(tentativa {error_info['attempt']}, "
            f"{error_info['timestamp']})"
        )
