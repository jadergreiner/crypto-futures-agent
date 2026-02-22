"""
Stop Loss Manager — Gerenciador de Stop Loss Hardcoded

Responsabilidades:
- Manter stop loss sempre ativo (-3%)
- Integrar com mark price da WebSocket (Binance)
- Validar execução do stop loss
- NUNCA permitir desabilitação

Validação contra critérios S1-2:
✓ Stop Loss ativa em -3% de drawdown
✓ Não pode ser desabilitado (hardcoded)
✓ Auditoria completa de acionamentos
"""

import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StopLossEvent:
    """Evento registrado quando stop loss é acionado."""
    timestamp: datetime
    entry_price: float
    trigger_price: float  # Preço que acionou o stop loss
    loss_amount: float  # Valor perdido
    loss_pct: float  # Percentual de perda
    portfolio_value: float  # Valor da carteira no momento do acionamento


class StopLossManager:
    """
    Gerenciador de Stop Loss — Inviolável.
    
    Garantias:
    1. Stop loss SEMPRE ativo (não pode ser desabilitado)
    2. Threshold SEMPRE -3% (não pode ser alterado)
    3. Qualquer tentativa de mudança é bloqueada + auditada
    """

    HARDCODED_THRESHOLD = -3.0  # -3% (INVIOLÁVEL)

    def __init__(self, callbacks: Optional[Dict[str, Callable]] = None):
        """
        Inicializar Stop Loss Manager.
        
        Args:
            callbacks: Dicionário de callbacks {'on_triggered': func}
        """
        self.threshold = self.HARDCODED_THRESHOLD
        self._is_armed = True  # SEMPRE armado
        self._entry_price: Optional[float] = None
        self._current_price: Optional[float] = None
        self._peak_price: Optional[float] = None
        self._portfolio_peak: float = 10000.0
        self._portfolio_current: float = 10000.0
        
        # Callbacks para reação ao stop loss
        self._callbacks = callbacks or {}
        
        # Histórico de eventos
        self._stop_loss_events: list = []
        
        logger.warning("🛑 Stop Loss Manager INICIALIZADO")
        logger.warning(f"   Threshold HARDCODED: {self.HARDCODED_THRESHOLD}%")
        logger.warning("   Status: SEMPRE ATIVO (não pode ser desabilitado)")

    def arm(self) -> bool:
        """
        Tentar ativar stop loss (já está ativo).
        
        Esta função sempre retorna True mas não muda nada,
        porque stop loss SEMPRE está ativo.
        """
        logger.warning("⚠️  Stop Loss já está SEMPRE ATIVO (hardcoded)")
        return True

    def disarm(self) -> bool:
        """
        Tentar desativar stop loss.
        
        BLOQUEADO INVIOLAVELMENTE.
        """
        logger.critical("❌ TENTATIVA DE DESATIVAR STOP LOSS BLOQUEADA")
        logger.critical("   Stop Loss é INVIOLÁVEL e não pode ser desligado")
        return False  # SEMPRE bloqueado

    def set_threshold(self, threshold: float) -> bool:
        """
        Tentar alterar threshold do stop loss.
        
        BLOQUEADO: Threshold é hardcoded em -3%.
        """
        if threshold != self.HARDCODED_THRESHOLD:
            logger.critical(f"❌ TENTATIVA DE ALTERAR THRESHOLD BLOQUEADA")
            logger.critical(f"   Tentativa: {threshold}%")
            logger.critical(f"   Hardcoded: {self.HARDCODED_THRESHOLD}%")
            return False
        return True

    def open_position(self, entry_price: float, portfolio_value: float) -> bool:
        """
        Registrar abertura de posição.
        
        Stop loss é SEMPRE ativo para nova posição.
        """
        self._entry_price = entry_price
        self._peak_price = entry_price
        self._portfolio_peak = portfolio_value
        self._portfolio_current = portfolio_value
        
        logger.info(f"📍 Posição aberta: entry={entry_price} @ portfolio={portfolio_value}")
        return True

    def update_price(self, current_price: float) -> None:
        """Atualizar preço atual (vem da WebSocket mark price)."""
        self._current_price = current_price
        
        if self._peak_price is None or current_price > self._peak_price:
            self._peak_price = current_price

    def update_portfolio_value(self, current_value: float) -> None:
        """Atualizar valor da carteira."""
        self._portfolio_current = current_value

    def check_triggered(self) -> Optional[StopLossEvent]:
        """
        Verificar se stop loss foi acionado.
        
        Calcula drawdown e compara com -3%.
        
        Returns:
            StopLossEvent se acionado, None caso contrário
        """
        if self._entry_price is None:
            return None

        # Evitar divisão por zero
        if self._portfolio_peak == 0:
            return None

        # Calcular drawdown: (current - peak) / peak * 100
        drawdown_pct = (
            (self._portfolio_current - self._portfolio_peak)
            / self._portfolio_peak
        ) * 100

        # Verificar se acionou stop loss (-3%)
        if drawdown_pct <= self.HARDCODED_THRESHOLD:
            logger.critical(f"🛑 STOP LOSS ACIONADO: {drawdown_pct:.2f}% <= {self.HARDCODED_THRESHOLD}%")
            
            event = StopLossEvent(
                timestamp=datetime.now(),
                entry_price=self._entry_price,
                trigger_price=self._current_price or self._peak_price,
                loss_amount=self._portfolio_peak - self._portfolio_current,
                loss_pct=drawdown_pct,
                portfolio_value=self._portfolio_current,
            )
            
            self._stop_loss_events.append(event)
            
            # Chamar callbacks registrados
            if "on_triggered" in self._callbacks:
                self._callbacks["on_triggered"](event)
            
            return event

        return None

    def get_stop_loss_price(self) -> Optional[float]:
        """
        Obter preço teórico de stop loss.
        
        = entry_price * (1 + threshold/100)
        = entry_price * (1 - 0.03)
        = entry_price * 0.97
        
        Returns:
            Preço de stop loss, ou None se sem posição aberta
        """
        if self._entry_price is None:
            return None

        # Para long: entry * (1 + threshold/100) = entry * 0.97
        sl_price = self._entry_price * (1 + self.HARDCODED_THRESHOLD / 100)
        return sl_price

    def get_historical_events(self) -> list:
        """Obter histórico completo de acionamentos."""
        return self._stop_loss_events.copy()

    def is_active(self) -> bool:
        """Stop Loss é SEMPRE ativo."""
        return True

    def is_position_open(self) -> bool:
        """Verificar se há posição aberta."""
        return self._entry_price is not None

    def close_position(self) -> None:
        """Registrar fechamento de posição."""
        self._entry_price = None
        self._peak_price = None
        logger.info("🔒 Posição fechada")

    def __repr__(self) -> str:
        """Representação legível."""
        sl_price = self.get_stop_loss_price()
        return (
            f"StopLossManager("
            f"threshold={self.threshold}%, "
            f"active={self.is_active()}, "
            f"entry={self._entry_price}, "
            f"sl_price={sl_price:.2f if sl_price else None}"
            f")"
        )


if __name__ == "__main__":
    # Teste básico
    manager = StopLossManager()
    
    print(f"✅ Stop Loss Manager inicializado")
    print(f"   Active: {manager.is_active()}")
    print(f"   Threshold: {manager.threshold}%")
    
    # Teste: tentar desativar (deve falhar)
    result = manager.disarm()
    print(f"   Tentativa de desativar: {result} (deve ser False)")
    
    # Teste: abrir posição
    manager.open_position(50000.0, 10000.0)
    print(f"   Posição aberta @ 50000")
    
    # Teste: preço vai para 48500 (drawdown -3%)
    manager.update_price(48500.0)
    manager.update_portfolio_value(9700.0)  # Drawdown -3%
    
    event = manager.check_triggered()
    print(f"   Stop Loss acionado: {event is not None} (deve ser True)")
