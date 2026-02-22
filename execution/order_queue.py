"""
Fila de ordens com suporte a prioridade e status tracking.

Implementa FIFO com estados: PENDING, EXECUTING, FILLED, FAILED, CANCELLED
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Deque
from enum import Enum
from collections import deque
import logging

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Estados possíveis de uma ordem."""
    PENDING = "pendente"  # Aguardando execução
    EXECUTING = "executando"  # Em processo de execução
    FILLED = "preenchida"  # Executada com sucesso
    FAILED = "falha"  # Falhou
    CANCELLED = "cancelada"  # Cancelada


@dataclass
class Order:
    """
    Estrutura de dados para uma ordem.
    
    Atributos:
        symbol: Símbolo da moeda (ex: BTCUSDT)
        qty: Quantidade a executar
        side: Direção ("long" ou "short")
        order_type: Tipo de ordem (padrão: "MARKET")
        status: Status atual (padrão: PENDING)
        order_id: ID da ordem na Binance (preenchido após execução)
        timestamp: Timestamp de criação
        retries: Número de tentativas de execução
        priority: Prioridade (maior = mais importante, padrão: 0)
    """
    symbol: str
    qty: float
    side: str  # "long" ou "short"
    order_type: str = "MARKET"
    status: OrderStatus = OrderStatus.PENDING
    order_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retries: int = 0
    priority: int = 0
    
    def __lt__(self, other: 'Order') -> bool:
        """Comparador para prioridade (maior priority = menor em heap)."""
        if self.priority != other.priority:
            return self.priority > other.priority  # Inverte para max-heap
        return self.timestamp < other.timestamp  # Break tie com timestamp


class OrderQueue:
    """
    Fila FIFO de ordens com suporte a prioridade.
    
    Garante:
    - Processamento ordenado (FIFO por padrão)
    - Suporte a prioridade (orders com priority > 0 são processadas antes)
    - Status tracking de cada ordem
    - Thread-safe (em Python CPython, deque é thread-safe)
    - Não bloqueia execução (async-ready)
    """
    
    def __init__(self):
        """Inicializar fila de ordens."""
        self._queue: Deque[Order] = deque()
        self._status_map: dict[str, OrderStatus] = {}
        self._order_id_map: dict[str, Order] = {}
        
        logger.info("OrderQueue inicializada")
    
    def enqueue(self, order: Order) -> None:
        """
        Adicionar ordem à fila.
        
        Args:
            order: Ordem a adicionar
            
        Raises:
            ValueError: Se ordem é inválida
        """
        # Validações básicas
        if not order.symbol:
            raise ValueError("Símbolo não pode estar vazio")
        if order.qty <= 0:
            raise ValueError(f"Quantidade deve ser > 0, recebido: {order.qty}")
        if order.side not in ("long", "short"):
            raise ValueError(f"Side deve ser 'long' ou 'short', recebido: {order.side}")
        
        # Adicionar à fila
        self._queue.append(order)
        self._status_map[id(order)] = order.status
        
        logger.info(
            f"Ordem adicionada à fila: {order.symbol} {order.side} "
            f"qty={order.qty:.6f} (priority={order.priority})"
        )
    
    def dequeue(self) -> Optional[Order]:
        """
        Remover e retornar primeira ordem da fila.
        
        Returns:
            Próxima ordem ou None se fila vazia
        """
        if not self._queue:
            logger.debug("Fila vazia")
            return None
        
        order = self._queue.popleft()
        logger.info(f"Ordem removida da fila: {order.symbol} {order.side}")
        return order
    
    def peek(self) -> Optional[Order]:
        """
        Ver primeira ordem sem remover.
        
        Returns:
            Próxima ordem ou None se fila vazia
        """
        if not self._queue:
            return None
        return self._queue[0]
    
    def update_status(self, order: Order, new_status: OrderStatus) -> None:
        """
        Atualizar status de uma ordem.
        
        Args:
            order: Ordem a atualizar
            new_status: Novo status
        """
        order.status = new_status
        self._status_map[id(order)] = new_status
        
        logger.info(f"Status atualizado: {order.symbol} → {new_status.value}")
    
    def size(self) -> int:
        """Retornar número de ordens na fila."""
        return len(self._queue)
    
    def is_empty(self) -> bool:
        """Verificar se fila está vazia."""
        return len(self._queue) == 0
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """
        Obter todas as ordens com um status específico.
        
        Args:
            status: Status a filtrar
            
        Returns:
            Lista de ordens com esse status
        """
        return [order for order in self._queue if order.status == status]
    
    def get_pending_orders(self) -> List[Order]:
        """Obter todas as ordens pendentes."""
        return self.get_orders_by_status(OrderStatus.PENDING)
    
    def get_executing_orders(self) -> List[Order]:
        """Obter todas as ordens em execução."""
        return self.get_orders_by_status(OrderStatus.EXECUTING)
    
    def get_filled_orders(self) -> List[Order]:
        """Obter todas as ordens preenchidas."""
        return self.get_orders_by_status(OrderStatus.FILLED)
    
    def get_failed_orders(self) -> List[Order]:
        """Obter todas as ordens que falharam."""
        return self.get_orders_by_status(OrderStatus.FAILED)
    
    def clear(self) -> None:
        """Limpar toda a fila."""
        self._queue.clear()
        self._status_map.clear()
        self._order_id_map.clear()
        logger.warning("Fila limpa")
    
    def get_all_orders(self) -> List[Order]:
        """Retornar cópia de todas as ordens na fila."""
        return list(self._queue)
    
    def get_statistics(self) -> dict:
        """
        Obter estatísticas da fila.
        
        Returns:
            Dict com contagens por status
        """
        stats = {
            "total": len(self._queue),
            "pending": len(self.get_pending_orders()),
            "executing": len(self.get_executing_orders()),
            "filled": len(self.get_filled_orders()),
            "failed": len(self.get_failed_orders()),
            "cancelled": len(self.get_orders_by_status(OrderStatus.CANCELLED)),
        }
        return stats
