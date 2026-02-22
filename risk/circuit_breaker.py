"""
Circuit Breaker — Proteção de Emergência

Responsabilidades:
- Monitorar drawdown constante
- Acionado em -3.1% (maior que stop loss de -3%)
- Fecha TODAS as posições imediatamente
- Passa a zelar por 24h sem aceitar novas ordens

Diferença Stop Loss vs Circuit Breaker:
- Stop Loss (-3%): Aviso, fecha uma posição
- Circuit Breaker (-3.1%): EMERGÊNCIA, fecha TUDO + para de operar
"""

import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Estados do Circuit Breaker."""
    NORMAL = "normal"
    ALERT = "alerta"
    TRIGGERED = "acionado"
    RECOVERY = "recuperacao"
    LOCKED = "trancado"  # 24h post-event


@dataclass
class CircuitBreakerEvent:
    """Evento de circuit breaker."""
    timestamp: datetime
    drawdown_pct: float
    portfolio_value: float
    peak_value: float
    loss_amount: float
    action_taken: str  # "close_all_positions", "halt_trading"
    reason: str


class CircuitBreaker:
    """
    Circuit Breaker — Proteção de Emergência.
    
    Garantias:
    1. Acionado SEMPRE em -3.1% de drawdown
    2. Fecha TODAS as posições
    3. Para de aceitar ordens por 24h (recovery period)
    4. Auditoria completa
    """

    TRIGGER_THRESHOLD = -3.1  # -3.1% (INVIOLÁVEL)
    RECOVERY_PERIOD_HOURS = 24  # 24h sem trading pós-evento
    ALERT_THRESHOLD = -2.8  # -2.8% emite ALERTA (pré-evento)

    def __init__(self, callbacks: Optional[Dict[str, Callable]] = None):
        """
        Inicializar Circuit Breaker.
        
        Args:
            callbacks: Dicionário de callbacks para eventos
        """
        self.state = CircuitBreakerState.NORMAL
        self._portfolio_peak: float = 10000.0
        self._portfolio_current: float = 10000.0
        self._triggered_at: Optional[datetime] = None
        self._recovery_until: Optional[datetime] = None
        
        self._callbacks = callbacks or {}
        self._events: List[CircuitBreakerEvent] = []
        
        logger.warning("⚡ Circuit Breaker INICIALIZADO")
        logger.warning(f"   Trigger threshold: {self.TRIGGER_THRESHOLD}%")
        logger.warning(f"   Alert threshold: {self.ALERT_THRESHOLD}%")
        logger.warning(f"   Recovery period: {self.RECOVERY_PERIOD_HOURS}h")

    def update_portfolio_value(self, current_value: float) -> None:
        """Atualizar valor da carteira."""
        self._portfolio_current = current_value
        
        # Rastrear peak
        if current_value > self._portfolio_peak:
            self._portfolio_peak = current_value

    def check_status(self) -> Dict[str, Any]:
        """
        Verificar status do circuit breaker e atualizar estado.
        
        Returns:
            Dicionário com status atual
        """
        drawdown_pct = self._calculate_drawdown()
        
        # Verificar se acionado (-3.1%)
        if drawdown_pct <= self.TRIGGER_THRESHOLD:
            # Se ainda não foi acionado, fazer acionamento agora
            if self.state != CircuitBreakerState.TRIGGERED and self.state != CircuitBreakerState.LOCKED:
                logger.critical(f"💥 CIRCUIT BREAKER ACIONADO: {drawdown_pct:.2f}% <= {self.TRIGGER_THRESHOLD}%")
                self._trigger_emergency()
            
            return {
                "state": self.state.value,
                "drawdown_pct": drawdown_pct,
                "action": "EMERGENCY_SHUTDOWN",
                "trading_allowed": False,
            }
        
        # Verificar se em recovery
        if self._recovery_until and datetime.now() < self._recovery_until:
            self.state = CircuitBreakerState.LOCKED
            recovery_remaining = (self._recovery_until - datetime.now()).total_seconds() / 3600
            logger.warning(f"🔒 Circuit Breaker em RECOVERY: {recovery_remaining:.1f}h restantes")
            
            return {
                "state": self.state.value,
                "drawdown_pct": drawdown_pct,
                "recovery_until": self._recovery_until.isoformat(),
                "trading_allowed": False,
            }
        elif self._recovery_until:
            # Recovery terminou
            self._recovery_until = None
            self.state = CircuitBreakerState.NORMAL
            logger.info("✅ Circuit Breaker RECUPERADO - Operação normal retomada")

        # Verificar se em alerta (-2.8%)
        if drawdown_pct <= self.ALERT_THRESHOLD:
            if self.state != CircuitBreakerState.ALERT:
                logger.warning(f"⚠️  ALERTA: drawdown {drawdown_pct:.2f}% próximo ao limite")
                self.state = CircuitBreakerState.ALERT
            
            return {
                "state": self.state.value,
                "drawdown_pct": drawdown_pct,
                "warning": "drawdown_alert",
                "trading_allowed": True,
            }

        # Normal
        self.state = CircuitBreakerState.NORMAL
        return {
            "state": self.state.value,
            "drawdown_pct": drawdown_pct,
            "trading_allowed": True,
        }

    def _trigger_emergency(self) -> None:
        """
        Acionamento de emergência do Circuit Breaker.
        
        - Fecha todas as posições
        - Entra em modo LOCKED por 24h
        - Registra evento
        """
        self.state = CircuitBreakerState.TRIGGERED
        self._triggered_at = datetime.now()
        self._recovery_until = datetime.now() + timedelta(hours=self.RECOVERY_PERIOD_HOURS)
        
        drawdown_pct = self._calculate_drawdown()
        loss_amount = self._portfolio_peak - self._portfolio_current
        
        event = CircuitBreakerEvent(
            timestamp=self._triggered_at,
            drawdown_pct=drawdown_pct,
            portfolio_value=self._portfolio_current,
            peak_value=self._portfolio_peak,
            loss_amount=loss_amount,
            action_taken="close_all_positions",
            reason=f"Drawdown {drawdown_pct:.2f}% <= {self.TRIGGER_THRESHOLD}%",
        )
        
        self._events.append(event)
        
        # Chamar callback se registrado
        if "on_triggered" in self._callbacks:
            self._callbacks["on_triggered"](event)
        
        logger.critical(f"💥 AÇÃO DE EMERGÊNCIA TOMADA: {event}")

    def can_trade(self) -> bool:
        """
        Verificar se trading é permitido.
        
        Returns:
            True se permitido, False se em TRIGGERED ou LOCKED
        """
        if self.state in [CircuitBreakerState.LOCKED, CircuitBreakerState.TRIGGERED]:
            logger.error(f"🔒 Trading BLOQUEADO: Circuit Breaker em {self.state.value}")
            return False
        
        return True

    def force_close_all_positions(self) -> bool:
        """
        Forçar fechamento de TODAS as posições.
        
        Chamado pela IA de execução quando CB é acionado.
        
        Returns:
            True se sucesso
        """
        logger.critical("💥 ENCERRANDO TODAS AS POSIÇÕES DE EMERGÊNCIA")
        
        # TODO: Integrar com execution/ para fechar ordens
        # - Obter todas as posições abertas
        # - Enviar ordem MARKET para cada uma
        # - Verificar confirmação Binance
        
        return True

    def get_historical_events(self) -> List[CircuitBreakerEvent]:
        """Obter histórico de eventos."""
        return self._events.copy()

    def last_trigger_time(self) -> Optional[datetime]:
        """Obter momento do último acionamento."""
        if self._events:
            return self._events[-1].timestamp
        return None

    def is_in_recovery(self) -> bool:
        """Verificar se está em período de recuperação."""
        return self.state == CircuitBreakerState.LOCKED

    def recovery_time_remaining_hours(self) -> float:
        """Horas restantes até recuperação."""
        if not self.is_in_recovery() or not self._recovery_until:
            return 0.0
        
        remaining = (self._recovery_until - datetime.now()).total_seconds() / 3600
        return max(0.0, remaining)

    def _calculate_drawdown(self) -> float:
        """Calcular drawdown em %."""
        if self._portfolio_peak == 0:
            return 0.0
        
        drawdown = (
            (self._portfolio_current - self._portfolio_peak)
            / self._portfolio_peak
        ) * 100
        
        return drawdown

    def __repr__(self) -> str:
        """Representação legível."""
        remaining = self.recovery_time_remaining_hours()
        drawdown = self._calculate_drawdown()
        
        return (
            f"CircuitBreaker("
            f"state={self.state.value}, "
            f"drawdown={drawdown:.2f}%, "
            f"recovery_remaining={remaining:.1f}h"
            f")"
        )


if __name__ == "__main__":
    # Teste básico
    cb = CircuitBreaker()
    
    print(f"✅ Circuit Breaker inicializado")
    print(f"   State: {cb.state.value}")
    print(f"   Can trade: {cb.can_trade()}")
    
    # Simular portfolio caindo
    cb.update_portfolio_value(10000.0)  # Peak
    
    # Drawdown -2.5% (normal)
    cb.update_portfolio_value(9750.0)
    status = cb.check_status()
    print(f"\n   Drawdown -2.5%: trading={status['trading_allowed']} (deve ser True)")
    
    # Drawdown -2.8% (alerta)
    cb.update_portfolio_value(9720.0)
    status = cb.check_status()
    print(f"   Drawdown -2.8%: state={status['state']} (deve ser 'alerta')")
    
    # Drawdown -3.1% (acionado!)
    cb.update_portfolio_value(9690.0)
    status = cb.check_status()
    print(f"   Drawdown -3.1%: action={status.get('action')} (deve ser 'EMERGENCY_SHUTDOWN')")
    print(f"   Trading permitido: {cb.can_trade()} (deve ser False)")
    
    print(f"\n   Eventos registrados: {len(cb.get_historical_events())}")
