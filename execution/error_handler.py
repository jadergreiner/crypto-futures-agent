"""
Tratamento de erros e retry strategy para execução de ordens.

Implementa:
- Retry automático com backoff exponencial
- Fallback de quantidade quando há erros de saldo ou tamanho
- Logging estruturado de erros em JSON
"""

import time
import logging
import json
from typing import Callable, Any, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


# Constantes
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # 1 segundo
MAX_BACKOFF = 30  # 30 segundos
BACKOFF_MULTIPLIER = 2


class ExecutionError(Exception):
    """Erro base para execução de ordens."""
    pass


class RetryExhaustedError(ExecutionError):
    """Erro quando retries são esgotados."""
    pass


class RetryStrategy:
    """
    Estratégia de retry com backoff exponencial.
    
    Configuração:
    - Max 3 retries automáticos
    - Incrementa delay entre tentativos
    - Delays: [1s, 2s, 4s, 8s, 16s, 30s]
    """
    
    def __init__(self, max_retries: int = MAX_RETRIES,
                 initial_backoff: float = INITIAL_BACKOFF,
                 max_backoff: float = MAX_BACKOFF):
        """
        Inicializar estratégia de retry.
        
        Args:
            max_retries: Número máximo de tentativas (padrão: 3)
            initial_backoff: Delay inicial em segundos (padrão: 1)
            max_backoff: Delay máximo em segundos (padrão: 30)
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executar função com retry automático e backoff exponencial.
        
        Args:
            func: Função a executar
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados
            
        Returns:
            Resultado da função
            
        Raises:
            RetryExhaustedError: Se todos os retries falharem
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Tentativa {attempt + 1} de {self.max_retries + 1}")
                return func(*args, **kwargs)
            except (TimeoutError, ConnectionError, OSError) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # Calcular delay com backoff exponencial
                    delay = min(
                        self.initial_backoff * (BACKOFF_MULTIPLIER ** attempt),
                        self.max_backoff
                    )
                    logger.warning(
                        f"Erro transitório (tentativa {attempt + 1}): {str(e)}. "
                        f"Aguardando {delay:.1f}s antes da próxima tentativa..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Todas as {self.max_retries + 1} tentativas falharam. "
                        f"Último erro: {str(e)}"
                    )
                    raise RetryExhaustedError(
                        f"Falha após {self.max_retries + 1} tentativas. "
                        f"Último erro: {str(e)}"
                    ) from e
        
        # Nunca deve chegar aqui, mas segurança
        raise RetryExhaustedError("Retries esgotados (caso inesperado)")


class FallbackStrategy:
    """
    Estratégia de fallback quando ordem falha por tamanho/saldo.
    
    Comportamentos:
    - Se timeout: reduz quantidade em 50%
    - Se saldo insuficiente: reduz quantidade para máx disponível
    - Log estruturado de cada tentativa
    """
    
    def __init__(self, min_qty: float = 0.001):
        """
        Inicializar estratégia de fallback.
        
        Args:
            min_qty: Quantidade mínima permitida (padrão: 0.001 BTC)
        """
        self.min_qty = min_qty
    
    def reduce_quantity(self, original_qty: float, 
                       reduction_factor: float = 0.5) -> float:
        """
        Reduzir quantidade mantendo mínimo.
        
        Args:
            original_qty: Quantidade original
            reduction_factor: Fator de redução (padrão: 0.5 para 50%)
            
        Returns:
            Quantidade reduzida (nunca negativa, nunca < min_qty)
        """
        reduced = original_qty * reduction_factor
        result = max(reduced, self.min_qty)
        
        if result < original_qty:
            logger.info(
                f"Quantidade reduzida: {original_qty} → {result:.6f} "
                f"({reduction_factor:.0%})"
            )
        
        return result
    
    def handle_insufficient_balance(self, 
                                   original_qty: float,
                                   available_balance: float) -> float:
        """
        Lidar com saldo insuficiente reduzindo quantidade.
        
        Args:
            original_qty: Quantidade solicitada
            available_balance: Saldo disponível
            
        Returns:
            Quantidade ajustada (máximo do saldo disponível)
        """
        if available_balance <= 0:
            logger.error(f"Saldo insuficiente: {available_balance:.2f} USDT")
            raise ExecutionError(f"Saldo insuficiente: {available_balance:.2f}")
        
        if original_qty > available_balance:
            adjusted = min(available_balance, original_qty)
            logger.warning(
                f"Saldo insuficiente: original={original_qty:.6f}, "
                f"disponível={available_balance:.2f}. "
                f"Ajustado para {adjusted:.6f}"
            )
            return adjusted
        
        return original_qty
    
    def handle_invalid_order_qty(self, original_qty: float,
                                 min_notional: float = 10.0) -> float:
        """
        Lidar com tamanho de ordem inválido (muito pequeno).
        
        Args:
            original_qty: Quantidade solicitada
            min_notional: Valor mínimo em USDT (padrão: 10 USDT)
            
        Returns:
            Quantidade ajustada
            
        Raises:
            ExecutionError: Se não puder ajustar para o mínimo
        """
        if original_qty < self.min_qty:
            logger.error(
                f"Quantidade menor que mínimo permitido: "
                f"{original_qty:.6f} < {self.min_qty}"
            )
            raise ExecutionError(
                f"Quantidade menor que mínimo: {self.min_qty}"
            )
        
        return original_qty


class ErrorLogger:
    """
    Logger estruturado de erros para auditoria.
    
    Registra em JSON:
    - timestamp
    - tipo de erro
    - retry count
    - quantidade ajustada
    - resultado final
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Inicializar logger de erros.
        
        Args:
            log_file: Caminho opcional para arquivo de log JSON
        """
        self.log_file = log_file
        self.audit_trail: list[Dict[str, Any]] = []
    
    def log_retry_attempt(self, symbol: str, attempt: int,
                         error: str, delay: float,
                         qty: float) -> None:
        """
        Registrar tentativa de retry.
        
        Args:
            symbol: Símbolo da moeda
            attempt: Número da tentativa
            error: Mensagem de erro
            delay: Delay antes próxima tentativa (segundos)
            qty: Quantidade envolvida
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "RETRY_ATTEMPT",
            "symbol": symbol,
            "attempt": attempt,
            "error": error,
            "delay_seconds": delay,
            "quantity": qty,
        }
        self.audit_trail.append(entry)
        
        logger.info(f"[RETRY] {symbol} tentativa {attempt}: {error}")
        self._write_to_file(entry)
    
    def log_fallback_applied(self, symbol: str, original_qty: float,
                            adjusted_qty: float, reason: str) -> None:
        """
        Registrar aplicação de fallback.
        
        Args:
            symbol: Símbolo da moeda
            original_qty: Quantidade original
            adjusted_qty: Quantidade ajustada
            reason: Razão do fallback
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "FALLBACK_APPLIED",
            "symbol": symbol,
            "original_quantity": original_qty,
            "adjusted_quantity": adjusted_qty,
            "reduction_factor": adjusted_qty / original_qty if original_qty > 0 else 0,
            "reason": reason,
        }
        self.audit_trail.append(entry)
        
        logger.warning(
            f"[FALLBACK] {symbol}: {original_qty:.6f} → {adjusted_qty:.6f} "
            f"({reason})"
        )
        self._write_to_file(entry)
    
    def log_execution_result(self, symbol: str, success: bool,
                            qty: float, order_id: Optional[str] = None,
                            final_error: Optional[str] = None) -> None:
        """
        Registrar resultado final de execução.
        
        Args:
            symbol: Símbolo da moeda
            success: Se foi bem-sucedida
            qty: Quantidade final
            order_id: ID da ordem (se bem-sucedida)
            final_error: Erro final (se falhou)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "EXECUTION_RESULT",
            "symbol": symbol,
            "success": success,
            "quantity": qty,
            "order_id": order_id,
            "error": final_error,
        }
        self.audit_trail.append(entry)
        
        if success:
            logger.info(
                f"[SUCESSO] {symbol} executado: qty={qty:.6f}, "
                f"order_id={order_id}"
            )
        else:
            logger.error(
                f"[FALHA] {symbol}: {final_error}"
            )
        
        self._write_to_file(entry)
    
    def get_audit_trail(self) -> list[Dict[str, Any]]:
        """Retornar trail de auditoria completo."""
        return self.audit_trail.copy()
    
    def _write_to_file(self, entry: Dict[str, Any]) -> None:
        """Escrever entry em arquivo JSON se configurado."""
        if not self.log_file:
            return
        
        try:
            # Append ao arquivo JSON (array of objects)
            with open(self.log_file, 'a') as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            logger.error(f"Erro ao escrever log em arquivo: {e}")
