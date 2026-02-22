"""
Order Queue — Fila thread-safe para execucao de ordens com retry automatico.

Modulo que implementa:
- Fila thread-safe de ordens (Queue.Queue)
- Observer pattern para notificacoes
- Retry automatico com max 3 tentativas
- Rastreamento de estado de cada ordem
- Worker thread para processamento assincrono
"""

import logging
import threading
import time
import uuid
from queue import Queue, Empty
from typing import (
    Optional, Callable, List, Dict, Any, Set
)
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Estados possiveis de uma ordem."""
    PENDING = "pendente"  # Aguardando processamento
    PROCESSING = "processando"  # Sendo processada
    EXECUTED = "executada"  # Executada com sucesso
    RETRYING = "retentando"  # Tentando novamente
    FAILED = "falha"  # Falha permanente
    CANCELLED = "cancelada"  # Cancelada manualmente


@dataclass
class Order:
    """
    Representa uma ordem a ser executada.

    Atributos:
        order_id: ID unico da ordem (gerado automaticamente)
        symbol: Simbolo (ex: BTCUSDT)
        side: BUY ou SELL
        quantity: Quantidade
        order_type: Tipo de ordem (ex: MARKET)
        timestamp: Timestamp de criacao
        status: Estado atual da ordem
        attempt: Numero de tentativas (1-indexed)
        last_error: Ultimo erro capturado
        result: Resultado da execucao (dict ou None)
    """
    symbol: str
    side: str
    quantity: float
    order_type: str = "MARKET"
    order_id: Optional[str] = None
    timestamp: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    attempt: int = 0
    last_error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Gerar ID e timestamp se nao fornecidos."""
        if self.order_id is None:
            self.order_id = self._generate_order_id()
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    @staticmethod
    def _generate_order_id() -> str:
        """Gerar ID unico para a ordem."""
        # Usar UUID4 para garantir unicidade
        return f"order_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        """Converter ordem para dicionario."""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    def increment_attempt(self) -> None:
        """Incrementar contador de tentativas."""
        self.attempt += 1

    def mark_as_executed(self, result: Dict[str, Any]) -> None:
        """Marcar ordem como executada com sucesso."""
        self.status = OrderStatus.EXECUTED
        self.result = result
        logger.info(
            f"Ordem {self.order_id} marcada como EXECUTADA",
            extra={"order": self.to_dict()}
        )

    def mark_as_failed(self, error: str) -> None:
        """Marcar ordem como falha permanente."""
        self.status = OrderStatus.FAILED
        self.last_error = error
        logger.error(
            f"Ordem {self.order_id} marcada como FALHA: {error}",
            extra={"order": self.to_dict()}
        )

    def mark_as_retrying(self, error: str) -> None:
        """Marcar ordem como retentando."""
        self.status = OrderStatus.RETRYING
        self.last_error = error
        logger.warning(
            f"Ordem {self.order_id} sera retentada "
            f"(tentativa {self.attempt})",
            extra={"error": error}
        )


class OrderObserver:
    """
    Interface para observers de mudancas em ordens.

    Implementadores devem override os metodos de callback.
    """

    def on_order_queued(self, order: Order) -> None:
        """Callback quando ordem eh enfileirada."""
        pass

    def on_order_processing(self, order: Order) -> None:
        """Callback quando ordem comeca processamento."""
        pass

    def on_order_executed(self, order: Order, result: Dict[str, Any]) -> None:
        """Callback quando ordem eh executada."""
        pass

    def on_order_failed(self, order: Order, error: str) -> None:
        """Callback quando ordem falha."""
        pass

    def on_order_retrying(self, order: Order, attempt: int) -> None:
        """Callback quando ordem sera retentada."""
        pass


class OrderQueue:
    """
    Fila thread-safe para execucao de ordens.

    Responsabilidades:
    - Armazenar ordens em fila FIFO thread-safe
    - Executar cada ordem com retry automatico (max 3)
    - Notificar observers sobre mudancas
    - Rastrear estado de todas as ordens
    - Permitir cancelamento de ordens (se ainda nao executadas)
    """

    MAX_RETRIES = 3

    def __init__(self, max_queue_size: int = 100):
        """
        Inicializar fila de ordens.

        Args:
            max_queue_size: Tamanho maximo da fila
        """
        self._queue: Queue = Queue(maxsize=max_queue_size)
        self._observers: List[OrderObserver] = []
        self._lock = threading.RLock()
        self._order_history: Dict[str, Order] = {}
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._executor_fn: Optional[Callable] = None

        logger.info(
            f"OrderQueue inicializado (tamanho maximo: {max_queue_size})"
        )

    def register_executor(
        self, executor_fn: Callable[[Order], Dict[str, Any]]
    ) -> None:
        """
        Registrar funcao executora.

        Args:
            executor_fn: Funcao que executa uma ordem.
                        Assinatura: executor_fn(order: Order) -> dict
                        Deve lancar excecao em caso de erro.
        """
        self._executor_fn = executor_fn
        logger.info("Executor registrado na OrderQueue")

    def subscribe(self, observer: OrderObserver) -> None:
        """
        Registrar observer para notificacoes.

        Args:
            observer: Observer a registrar
        """
        with self._lock:
            self._observers.append(observer)
            logger.info(
                f"Observer registrado: {observer.__class__.__name__}"
            )

    def unsubscribe(self, observer: OrderObserver) -> None:
        """
        Remover observer.

        Args:
            observer: Observer a remover
        """
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)
                logger.info(
                    f"Observer removido: {observer.__class__.__name__}"
                )

    def enqueue(self, order: Order) -> None:
        """
        Enfileirar ordem para execucao.

        Args:
            order: Ordem a enfileirar

        Raises:
            queue.Full: Se fila estiver cheia
        """
        try:
            self._queue.put(order, block=False)
            with self._lock:
                self._order_history[order.order_id] = order
            logger.info(
                f"Ordem {order.order_id} enfileirada",
                extra={"order": order.to_dict()}
            )
            self._notify_observers("on_order_queued", order=order)
        except Exception as e:
            logger.error(f"Erro ao enfileirar ordem: {e}")
            raise

    def start_worker(self) -> None:
        """Iniciar thread worker para processar fila."""
        if self._running:
            logger.warning("Worker ja esta em execucao")
            return

        if self._executor_fn is None:
            raise ValueError(
                "Executor nao foi registrado. "
                "Use register_executor() primeiro."
            )

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True
        )
        self._worker_thread.start()
        logger.info("Worker thread iniciada")

    def stop_worker(self, timeout_seconds: float = 5.0) -> None:
        """
        Parar thread worker.

        Args:
            timeout_seconds: Tempo maximo de espera
        """
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout_seconds)
            logger.info("Worker thread parada")

    def _worker_loop(self) -> None:
        """Loop principal do worker thread."""
        while self._running:
            try:
                # Aguardar ordem com timeout
                order = self._queue.get(timeout=1.0)
                self._process_order(order)
                self._queue.task_done()
            except Empty:
                # Timeout normal, continua o loop
                continue
            except Exception as e:
                logger.error(f"Erro no worker loop: {e}")

    def _process_order(self, order: Order) -> None:
        """
        Processar uma ordem com retry automatico.

        Args:
            order: Ordem a processar
        """
        if self._executor_fn is None:
            raise ValueError("Executor nao foi registrado")

        logger.info(
            f"Processando ordem {order.order_id}",
            extra={"order": order.to_dict()}
        )

        while order.attempt < self.MAX_RETRIES:
            order.increment_attempt()
            self._notify_observers("on_order_processing", order=order)

            try:
                # Executar ordem
                result = self._executor_fn(order)

                # Sucesso
                order.mark_as_executed(result)
                self._notify_observers(
                    "on_order_executed", order=order, result=result
                )
                break

            except Exception as e:
                error_msg = str(e)
                logger.warning(
                    f"Erro na tentativa {order.attempt} "
                    f"da ordem {order.order_id}: {error_msg}"
                )

                # Decidir se retenta
                if order.attempt >= self.MAX_RETRIES:
                    order.mark_as_failed(error_msg)
                    self._notify_observers(
                        "on_order_failed",
                        order=order,
                        error=error_msg
                    )
                else:
                    order.mark_as_retrying(error_msg)
                    backoff = 2 ** (order.attempt - 1)  # 1, 2, 4 segundos
                    logger.info(
                        f"Aguardando {backoff}s antes de retentar..."
                    )
                    time.sleep(backoff)
                    self._notify_observers(
                        "on_order_retrying",
                        order=order,
                        attempt=order.attempt
                    )

    def _notify_observers(
        self, method_name: str, **kwargs
    ) -> None:
        """
        Notificar todos os observers.

        Args:
            method_name: Nome do metodo a chamar
            **kwargs: Argumentos a passar para o metodo
        """
        with self._lock:
            for observer in self._observers:
                try:
                    method = getattr(observer, method_name, None)
                    if method:
                        method(**kwargs)
                except Exception as e:
                    logger.error(
                        f"Erro notificando observer {observer.__class__.__name__}: {e}"
                    )

    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Obter ordem do historico.

        Args:
            order_id: ID da ordem

        Returns:
            Ordem ou None se nao encontrada
        """
        with self._lock:
            return self._order_history.get(order_id)

    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """
        Obter todas as ordens com status especifico.

        Args:
            status: Status desejado

        Returns:
            Lista de ordens
        """
        with self._lock:
            return [
                order for order in self._order_history.values()
                if order.status == status
            ]

    def get_pending_orders(self) -> List[Order]:
        """Obter ordens ainda nao processadas."""
        return self.get_orders_by_status(OrderStatus.PENDING)

    def get_executed_orders(self) -> List[Order]:
        """Obter ordens executadas com sucesso."""
        return self.get_orders_by_status(OrderStatus.EXECUTED)

    def get_failed_orders(self) -> List[Order]:
        """Obter ordens que falharam."""
        return self.get_orders_by_status(OrderStatus.FAILED)

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancelar ordem se ainda estiver pendente.

        Args:
            order_id: ID da ordem

        Returns:
            True se cancelada, False se nao estava em PENDING
        """
        with self._lock:
            order = self._order_history.get(order_id)
            if order and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                logger.info(f"Ordem {order_id} cancelada")
                self._notify_observers(
                    "on_order_cancelled", order=order
                )
                return True
            return False

    def queue_size(self) -> int:
        """Obter tamanho atual da fila."""
        return self._queue.qsize()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Obter estatisticas da fila.

        Returns:
            Dicionario com estatisticas
        """
        with self._lock:
            total = len(self._order_history)
            executed = len(self.get_executed_orders())
            failed = len(self.get_failed_orders())
            pending = len(self.get_pending_orders())

            return {
                "total_orders": total,
                "executed": executed,
                "failed": failed,
                "pending": pending,
                "success_rate": executed / total if total > 0 else 0.0,
                "queue_size": self.queue_size(),
            }
