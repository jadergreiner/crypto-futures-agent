"""
Módulo de retry I/O com atomicidade para M2 (BLID-0E4).

Fornece:
- retry_with_backoff: decorator com backoff exponencial
- atomic_file_write: context manager para escrita atômica (temp + rename)
- read_json_with_retry: wrapper para leitura JSON com retry+timeout
- write_json_with_retry: wrapper para escrita JSON com retry+timeout
- IoRetryError: exceção customizada

Guardrails:
- Timeout: 5s leitura, 10s escrita (hard limits)
- Backoff: exponencial (1s, 2s, 4s, 8s)
- Fail-safe: retry exaure → log, retorna False, não raise
- Atomicidade: temp + os.replace() (Windows-compatible)
- Logging: por tentativa com contexto
"""

import functools
import time
import logging
import os
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, Tuple, TypeVar, Union
from collections.abc import Callable

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


class IoRetryError(Exception):
    """Exceção customizada para falhas de I/O após retry exaurido."""
    pass


# ============================================================================
# FASE 1: DECORATOR + ATOMIC WRITE
# ============================================================================


def retry_with_backoff(
    retries: int = 3,
    backoff_seconds: Optional[Tuple[float, ...]] = None,
) -> Callable[[F], F]:
    """
    Decorator para retry com backoff exponencial.

    Args:
        retries: número máximo de tentativas
        backoff_seconds: tuple com delays (ex: (0.05, 0.05, 0.05))
                        se None, usa (1, 2, 4, 8) padrão

    Exemplo:
        @retry_with_backoff(retries=3, backoff_seconds=(1, 2, 4))
        def flaky_function():
            ...
    """
    if backoff_seconds is None:
        backoff_seconds = (1, 2, 4, 8)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:
                        # Calcular delay (usar backoff_seconds se disponível)
                        bs = backoff_seconds or (1, 2, 4, 8)
                        delay = (
                            bs[attempt]
                            if attempt < len(bs)
                            else bs[-1]
                        )
                        logger.debug(
                            f"Retry {attempt+1}/{retries} para {func.__name__}: "
                            f"tentaremos em {delay}s. Erro: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.warning(
                            f"Falha final {func.__name__} após {retries} tentativas: {e}"
                        )

            if last_exception:
                raise last_exception
            return None  # unreachable but satisfies mypy

        return wrapper  # type: ignore[return-value]

    return decorator


@contextmanager
def atomic_file_write(target_path: str) -> Generator[Any, None, None]:
    """
    Context manager para escrita atômica de arquivo (temp + rename).

    Garante que o arquivo alvo não é modificado se houver erro durante a escrita.

    Args:
        target_path: caminho alvo do arquivo

    Uso:
        with atomic_file_write("/path/to/file.json") as f:
            json.dump(data, f)

    Raises:
        Exception: propagada para caller (arquivo alvo não é modificado)
    """
    target = Path(target_path)
    # Criar arquivo temporário no mesmo diretório
    # (garante mesmo volume/filesystem para rename atômico)
    temp_path = str(target.parent / f"{target.name}.tmp_{int(time.time() * 1000000)}")

    try:
        # Abrir arquivo temporário em modo texto
        # Usar open() diretamente para permitir mock de builtins.open
        with open(temp_path, "w", encoding="utf-8") as temp_file:
            yield temp_file
            temp_file.flush()

        # Escrita bem-sucedida: rename atômico (Windows-compatible)
        # os.replace() substitui arquivo alvo se existir
        os.replace(temp_path, str(target))
        logger.debug(f"Arquivo escrito atomicamente: {target}")

    except Exception as e:
        # Limpar arquivo temporário em caso de erro
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as cleanup_error:
            logger.warning(
                f"Erro ao limpar temp file {temp_path}: {cleanup_error}"
            )
        # Propagar exceção original
        raise


# ============================================================================
# FASE 2: READ/WRITE WRAPPERS COM TIMEOUT + RETRY
# ============================================================================


def read_json_with_retry(
    path: str,
    timeout_seconds: float = 5.0,
    retries: int = 3,
    fail_safe: bool = False,
) -> Union[Dict[str, Any], bool]:
    """
    Lê JSON com retry, backoff e timeout.

    Args:
        path: caminho do arquivo JSON
        timeout_seconds: timeout máximo total (default 5s para leitura)
        retries: número de tentativas
        fail_safe: se True, retorna False em erro; se False, raise

    Returns:
        Dict com conteúdo JSON descerrado, ou False (fail_safe mode)

    Raises:
        IoRetryError: se fail_safe=False e all retries falham
        TimeoutError: se timeout é excedido
    """
    logger.debug(f"Iniciando read_json_with_retry: {path} (timeout={timeout_seconds}s)")

    start_time = time.time()
    last_exception: Optional[Exception] = None

    for attempt in range(retries):
        try:
            # Verificar timeout (early exit)
            elapsed = time.time() - start_time
            remaining = timeout_seconds - elapsed
            if remaining <= 0:
                err = TimeoutError(
                    f"Timeout read {path}: {elapsed:.2f}s >= {timeout_seconds}s"
                )
                logger.error(str(err))
                if fail_safe:
                    return False
                raise err

            # Tentar leitura
            logger.debug(f"Lendo JSON tentativa {attempt+1}/{retries}: {path}")
            with open(path, "r", encoding="utf-8") as f:
                # Validar timeout também durante leitura
                data = json.load(f)
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(f"Timeout durante leitura: {elapsed:.2f}s > {timeout_seconds}s")
            logger.debug(f"Sucesso na leitura JSON: {path}")
            return data  # type: ignore[no-any-return]

        except (IOError, OSError, TimeoutError) as e:
            last_exception = e
            elapsed = time.time() - start_time

            # Timeout absoluto
            if elapsed >= timeout_seconds:
                logger.error(
                    f"Timeout absoluto atingido: {elapsed:.2f}s >= {timeout_seconds}s"
                )
                if fail_safe:
                    return False
                raise TimeoutError(str(e))

            if attempt < retries - 1:
                # Backoff exponencial
                delay = min(2 ** attempt, 8)  # max 8s

                # But check if delay would exceed timeout
                if elapsed + delay > timeout_seconds:
                    logger.error(
                        f"Backoff delay {delay}s would exceed timeout, abandoning"
                    )
                    if fail_safe:
                        return False
                    raise TimeoutError(f"Timeout: {elapsed + delay:.2f}s > {timeout_seconds}s")

                logger.warning(
                    f"Erro read JSON attempt {attempt+1}/{retries} "
                    f"(elapsed {elapsed:.2f}s), retry em {delay}s: {e}"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Falha final read JSON após {retries} tentativas: {e}"
                )

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON decode error: {e}")
            last_exception = e
            if not fail_safe:
                raise

    # Falha exaurida
    if fail_safe:
        logger.warning(f"Read JSON fail-safe: retornando False ({path})")
        return False
    else:
        raise IoRetryError(f"Read JSON falhou após {retries} tentativas: {last_exception}")


def write_json_with_retry(
    data: Any,
    path: str,
    timeout_seconds: float = 10.0,
    retries: int = 4,
    fail_safe: bool = False,
) -> Union[bool, None]:
    """
    Escreve JSON com retry, atomicidade e timeout.

    Args:
        data: dados a escrever (dict, list, etc)
        path: caminho alvo
        timeout_seconds: timeout máximo total (default 10s para escrita)
        retries: número de tentativas
        fail_safe: se True, retorna False em erro; se False, raise

    Returns:
        True se sucesso, False se fail_safe=True e falha, None case contrário

    Raises:
        IoRetryError: se fail_safe=False e all retries falham
        TimeoutError: se timeout é excedido
    """
    logger.debug(
        f"Iniciando write_json_with_retry: {path} (timeout={timeout_seconds}s)"
    )

    start_time = time.time()
    last_exception: Optional[Exception] = None

    for attempt in range(retries):
        try:
            # Verificar timeout (early exit)
            elapsed = time.time() - start_time
            remaining = timeout_seconds - elapsed
            if remaining <= 0:
                err = TimeoutError(
                    f"Timeout write {path}: {elapsed:.2f}s >= {timeout_seconds}s"
                )
                logger.error(str(err))
                if fail_safe:
                    return False
                raise err

            # Criar diretório se não existir
            Path(path).parent.mkdir(parents=True, exist_ok=True)

            # Tentar escrita atômica
            logger.debug(f"Escrevendo JSON tentativa {attempt+1}/{retries}: {path}")
            with atomic_file_write(path) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Sucesso na escrita JSON: {path}")
            return True

        except (IOError, OSError, TimeoutError, PermissionError) as e:
            last_exception = e
            elapsed = time.time() - start_time

            # Timeout absoluto
            if elapsed >= timeout_seconds:
                logger.error(
                    f"Timeout absoluto atingido: {elapsed:.2f}s >= {timeout_seconds}s"
                )
                if fail_safe:
                    return False
                raise TimeoutError(str(e))

            if attempt < retries - 1:
                # Backoff exponencial
                delay = min(2 ** attempt, 8)  # max 8s

                # But check if delay would exceed timeout
                if elapsed + delay > timeout_seconds:
                    logger.error(
                        f"Backoff delay {delay}s would exceed timeout, abandoning"
                    )
                    if fail_safe:
                        return False
                    raise TimeoutError(f"Timeout: {elapsed + delay:.2f}s > {timeout_seconds}s")

                logger.warning(
                    f"Erro write JSON attempt {attempt+1}/{retries} "
                    f"(elapsed {elapsed:.2f}s), retry em {delay}s: {e}"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Falha final write JSON após {retries} tentativas: {e}"
                )

        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization error: {e}")
            last_exception = e
            if not fail_safe:
                raise

    # Falha exaurida
    if fail_safe:
        logger.warning(f"Write JSON fail-safe: retornando False ({path})")
        return False
    else:
        raise IoRetryError(
            f"Write JSON falhou após {retries} tentativas: {last_exception}"
        )


# ============================================================================
# UTILIDADES
# ============================================================================


def reset_for_testing() -> None:
    """Função auxiliar para testes (reset state se necessário)."""
    pass
