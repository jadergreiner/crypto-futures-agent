from enum import Enum


class CircuitBreakerState(Enum):
    """
    Define os estados possíveis de um Circuit Breaker.

    Valores string garantem compatibilidade com model_decisions.input_json no DB.

    CLOSED   — operando normalmente (sem drawdown critico)
    OPEN     — travado por drawdown (nenhuma entrada permitida)
    HALF_OPEN — em periodo de recuperacao; proximo ciclo decide reabertura
    NORMAL   — alias de CLOSED para compatibilidade com live_service legado
    TRANCADO — alias de OPEN para compatibilidade com valores persistidos no DB
    """
    CLOSED = "normal"
    OPEN = "trancado"
    HALF_OPEN = "half_open"

    # Aliases para compatibilidade com live_service e valores gravados no DB
    NORMAL = "normal"
    TRANCADO = "trancado"
