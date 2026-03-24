# -*- coding: utf-8 -*-
"""Módulo de Resiliência para operações críticas."""

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from risk.risk_gate import get_risk_gate, RiskGateStatus

class PermanentFailure(Exception):
    """Exceção para sinalizar falhas permanentes que não devem ser retentadas."""
    pass

F = TypeVar('F', bound=Callable[..., Any])

def resilient_operation(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0) -> Callable[[F], F]:
    """
    Decorador que adiciona resiliência a uma função através de um mecanismo de
    retry com backoff exponencial para falhas transitórias.

    Args:
        max_retries (int): Número máximo de tentativas.
        initial_delay (float): Tempo de espera inicial em segundos.
        backoff_factor (float): Fator multiplicativo para o tempo de espera a cada tentativa.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            delay = initial_delay

            while retries < max_retries:
                try:
                    gate = get_risk_gate()
                    cb_triggered, _ = gate.check_circuit_breaker()
                    if cb_triggered or gate.status in [RiskGateStatus.CIRCUIT_BREAKER_ARMED, RiskGateStatus.FROZEN]:
                        raise PermanentFailure("Circuit breaker is open.")

                    return func(*args, **kwargs)

                except (ConnectionError, TimeoutError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logging.error(
                            "Operação '%s' falhou após %d tentativas devido a um erro transitório.",
                            func.__name__, max_retries, exc_info=True
                        )
                        raise

                    logging.warning(
                        "Operação '%s' falhou com erro transitório. Tentativa %d/%d em %.2fs.",
                        func.__name__, retries, max_retries, delay
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

                except PermanentFailure:
                    logging.error(
                        "Operação '%s' falhou com um erro permanente. Não haverá novas tentativas.",
                        func.__name__, exc_info=True
                    )
                    raise

                except Exception:
                    logging.error(
                        "Operação '%s' falhou com um erro inesperado e tratado como permanente.",
                        func.__name__, exc_info=True
                    )
                    raise

        return cast(F, wrapper)
    return decorator
