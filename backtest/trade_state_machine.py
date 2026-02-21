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
        """
        if self.current_state != PositionState.IDLE:
            logger.warning(f"Cannot open: state={self.current_state}")
            return False

        # Criar Trade object
        self.current_trade = Trade(
            symbol=self.symbol,
            direction=direction,
            entry_price=entry_price,
            entry_size=entry_size,
            entry_time=entry_time,
            initial_stop=initial_stop,
            take_profit=take_profit
        )

        # Atualizar estado
        new_state = PositionState.LONG if direction == "LONG" else PositionState.SHORT
        self.current_state = new_state

        logger.debug(f"✅ Opening {direction} position: price={entry_price}, size={entry_size}")
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
        """
        if self.current_state == PositionState.IDLE or not self.current_trade:
            logger.warning("Cannot close: no position open")
            return None

        trade = self.current_trade

        # Calcular PnL bruto (sem fees)
        if trade.direction == "LONG":
            gross_pnl = (exit_price - trade.entry_price) * trade.entry_size
        else:  # SHORT
            gross_pnl = (trade.entry_price - exit_price) * trade.entry_size

        # Calcular fees (entrada + saída, 0.075% maker + 0.1% taker)
        entry_cost = trade.entry_price * trade.entry_size
        exit_value = exit_price * trade.entry_size
        entry_fee = entry_cost * 0.00075  # 0.075% maker
        exit_fee = exit_value * 0.001      # 0.1% taker
        total_fees = entry_fee + exit_fee

        # PnL líquido
        net_pnl = gross_pnl - total_fees

        # PnL em percentual do capital
        pnl_pct = (net_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0

        # R-multiple (risco inicial é diferença entre entry e stop)
        initial_risk = abs(trade.entry_price - trade.initial_stop) * trade.entry_size
        r_multiple = (gross_pnl / initial_risk) if initial_risk > 0 else 0

        # Preencher campos de fechamento
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = reason
        trade.gross_pnl = gross_pnl
        trade.pnl_pct = pnl_pct
        trade.r_multiple = r_multiple
        trade.fees = total_fees
        trade.net_pnl = net_pnl

        # Atualizar consecutive losses
        self._update_consecutive_losses(net_pnl)

        # Adicionar ao histórico
        self.trade_history.append(trade)

        # Resetar estado
        self.current_state = PositionState.IDLE
        self.current_trade = None

        logger.debug(
            f"✅ Closed {trade.direction} position: "
            f"entry={trade.entry_price}, exit={exit_price}, "
            f"pnl={net_pnl:.2f}, reason={reason}"
        )
        return trade

    def check_exit_conditions(self, current_price: float, ohlc: Dict) -> Optional[str]:
        """
        Verificar se SL ou TP foi atingido.

        Args:
            current_price: Preço atual
            ohlc: Dict com {'open', 'high', 'low', 'close', 'volume'}

        Returns:
            None se nada, ou string 'SL_HIT' / 'TP_HIT'
        """
        if not self.current_trade:
            return None

        trade = self.current_trade
        candle_high = ohlc.get('high', current_price)
        candle_low = ohlc.get('low', current_price)

        if trade.direction == "LONG":
            # LONG: SL hit se low < stop, TP hit se high > target
            if candle_low <= trade.initial_stop:
                return 'SL_HIT'
            if candle_high >= trade.take_profit:
                return 'TP_HIT'
        else:  # SHORT
            # SHORT: SL hit se high > stop, TP hit se low < target
            if candle_high >= trade.initial_stop:
                return 'SL_HIT'
            if candle_low <= trade.take_profit:
                return 'TP_HIT'

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

    # Helper methods
    def _calculate_pnl(self, direction: str, entry: float,
                      exit: float, size: float) -> float:
        """Calculate gross PnL (sem fees)."""
        if direction == "LONG":
            return (exit - entry) * size
        else:  # SHORT
            return (entry - exit) * size

    def _calculate_r_multiple(self, pnl: float, initial_risk: float) -> float:
        """Calculate R-multiple (PnL / initial_risk)."""
        if initial_risk == 0:
            return 0.0
        return pnl / initial_risk

    def _apply_fees(self, size: float, price: float) -> float:
        """Calculate fees: 0.075% maker + 0.1% taker = 0.175% total."""
        return size * price * 0.00175

    def _update_consecutive_losses(self, pnl: float) -> None:
        """Update consecutive losses counter."""
        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses
        else:
            self.consecutive_losses = 0
