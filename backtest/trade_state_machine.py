"""
TradeStateMachine — Gerencia estado de posições para backtesting.

State machine: IDLE → LONG/SHORT → CLOSED
Rastreia: entry price, size, SL, TP, fees, PnL, R-multiple

TODO: ESP-ENG implementar métodos depois de F-12a refactor
"""

import logging
from typing import Dict, Optional, Literal
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class PositionState(Enum):
    """Estados da máquina de estados."""
    IDLE = "IDLE"           # Sem posição aberta
    LONG = "LONG"           # Posição LONG aberta
    SHORT = "SHORT"         # Posição SHORT aberta
    CLOSING = "CLOSING"     # Em processo de fechamento


@dataclass
class Trade:
    """Rastreia uma trade completa (aberta + fechada)."""
    symbol: str
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    entry_size: float
    entry_time: int
    initial_stop: float
    take_profit: float

    # Preenchido no fechamento
    exit_price: Optional[float] = None
    exit_time: Optional[int] = None
    exit_reason: Optional[str] = None  # 'TP_HIT', 'SL_HIT', 'MANUAL', etc.

    # Métricas calculadas
    gross_pnl: Optional[float] = None  # Sem fees
    pnl_pct: Optional[float] = None    # % do capital
    r_multiple: Optional[float] = None # PnL / initial_risk
    fees: Optional[float] = None       # 0.04% maker + 0.04% taker
    net_pnl: Optional[float] = None    # gross_pnl - fees


class TradeStateMachine:
    """
    Máquina de estados para gerenciar posições de trading.

    Responsabilidades:
    - Rastrear estado atual (IDLE, LONG, SHORT)
    - Calcular PnL com fees
    - Rastrear consecutive losses
    - Armazenar histórico completo de trades
    """

    def __init__(self, symbol: str = 'BTCUSDT', initial_capital: float = 10000):
        """
        Inicializa TradeStateMachine.

        Args:
            symbol: Símbolo sendo tradado
            initial_capital: Capital inicial (para cálculo de % PnL)
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.current_state = PositionState.IDLE
        self.current_trade: Optional[Trade] = None
        self.trade_history: list[Trade] = []
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0

        logger.info(f"TradeStateMachine initialized: {symbol}")

    def open_position(self, direction: Literal["LONG", "SHORT"],
                     entry_price: float,
                     entry_size: float,
                     initial_stop: float,
                     take_profit: float,
                     entry_time: int) -> bool:
        """
        Abre posição novo.

        Args:
            direction: 'LONG' ou 'SHORT'
            entry_price: Preço de entrada
            entry_size: Tamanho em unidades base
            initial_stop: Preço de stop loss
            take_profit: Preço de take profit
            entry_time: Timestamp de entrada

        Returns:
            True se sucesso, False se fails (posição já aberta)

        TODO:
        - [ ] Validar que current_state == IDLE
        - [ ] Criar Trade object
        - [ ] Set current_state = LONG ou SHORT
        """
        if self.current_state != PositionState.IDLE:
            logger.warning(f"Cannot open: state={self.current_state}")
            return False

        # TODO: Implementar
        logger.debug(f"Opening {direction} position: {entry_price}, size={entry_size}")
        return True

    def close_position(self, exit_price: float, exit_time: int,
                      reason: str = 'MANUAL') -> Optional[Trade]:
        """
        Fecha posição aberta.

        Args:
            exit_price: Preço de saída
            exit_time: Timestamp de saída
            reason: Motivo ('TP_HIT', 'SL_HIT', 'MANUAL', 'REDUCE_50', etc)

        Returns:
            Trade finalizada ou None se não há posição

        TODO:
        - [ ] Validar que current_state != IDLE
        - [ ] Calcular PnL = (exit - entry) * size (ajustar para SHORT)
        - [ ] Aplicar fees: 0.04% maker + 0.04% taker (ambos lados)
        - [ ] Calcular r_multiple = pnl / initial_risk
        - [ ] Atualizar consecutive_losses contador
        - [ ] Set current_state = IDLE
        - [ ] Return Trade preenchida
        """
        if self.current_state == PositionState.IDLE:
            logger.warning("Cannot close: no position open")
            return None

        # TODO: Implementar
        logger.debug(f"Closing {self.current_trade.direction if self.current_trade else 'N/A'} "
                    f"position: {exit_price}, reason={reason}")
        return None

    def check_exit_conditions(self, current_price: float, ohlc: Dict) -> Optional[str]:
        """
        Verificar se SL ou TP foi atingido.

        Args:
            current_price: Preço atual
            ohlc: Dict com {'open', 'high', 'low', 'close', 'volume'}

        Returns:
            None se nada, ou string 'SL_HIT' / 'TP_HIT'

        TODO:
        - [ ] Check high/low do candle vs. SL/TP
        - [ ] Se LONG: SL = low < stop_loss, TP = high > take_profit
        - [ ] Se SHORT: SL = high > stop_loss, TP = low < take_profit
        - [ ] Retornar apropriadamente
        """
        # TODO: Implementar
        return None

    def get_current_state(self) -> Dict:
        """
        Retorna estado atual da máquina.

        Returns:
            Dict com estado, posição aberta (se alguma), métricas
        """
        return {
            'state': self.current_state.value,
            'has_open_position': self.current_state != PositionState.IDLE,
            'current_trade': self.current_trade,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_losses': self.max_consecutive_losses,
        }

    def get_trade_history(self) -> list[Trade]:
        """Retorna histórico completo de trades."""
        return self.trade_history.copy()

    # TODO: Helper methods
    def _calculate_pnl(self, direction: str, entry: float,
                      exit: float, size: float) -> float:
        """Calculate gross PnL (sem fees)."""
        # TODO: Implementar
        pass

    def _calculate_r_multiple(self, pnl: float, initial_risk: float) -> float:
        """Calculate R-multiple (PnL / initial_risk)."""
        # TODO: Implementar
        pass

    def _apply_fees(self, size: float, price: float,
                   entry_fee: bool = False) -> float:
        """Calculate fees: 0.04% maker + 0.04% taker."""
        # TODO: Implementar (0.0004 * size * price)
        pass

    def _update_consecutive_losses(self, pnl: float) -> None:
        """Update consecutive losses counter."""
        # TODO: Implementar
        pass
