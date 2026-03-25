from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Any
from risk.states import CircuitBreakerState

@dataclass(frozen=True)
class CircuitBreakerTransition:
    """
    Representa um evento de transição de estado do Circuit Breaker.
    É um registro imutável de uma mudança de estado.
    """
    from_state: CircuitBreakerState
    to_state: CircuitBreakerState
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

class EventRecorder:
    """
    Um simples gravador de eventos em memória, para fins de demonstração.
    Em um sistema real, isso escreveria em um log, banco de dados ou sistema de mensageria.
    """
    def __init__(self, append_only: bool = False):
        self._events: List[Any] = []
        self._append_only = append_only

    def record(self, event: Any) -> None:
        """Registra um novo evento."""
        self._events.append(event)

    def get_events(self) -> List[Any]:
        """Retorna todos os eventos registrados."""
        return self._events.copy()
