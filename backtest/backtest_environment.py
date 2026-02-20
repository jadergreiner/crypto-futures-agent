"""
BacktestEnvironment — Wrapper determinístico para CryptoFuturesEnv.

Reutiliza ~99% da lógica de CryptoFuturesEnv, adicionando determinismo.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

from agent.environment import CryptoFuturesEnv

logger = logging.getLogger(__name__)


class BacktestEnvironment(CryptoFuturesEnv):
    """
    Subclass mínima de CryptoFuturesEnv para backtesting determinístico.
    
    Apenas garante que seed é aplicado para reproducibilidade.
    Toda a lógica vem de CryptoFuturesEnv.
    """
    
    def __init__(self,
                 data: Dict[str, pd.DataFrame],
                 initial_capital: float = 10000,
                 risk_params: Optional[Dict[str, Any]] = None,
                 episode_length: Optional[int] = None,
                 seed: int = 42):
        """
        Inicializa BacktestEnvironment.
        
        Args:
            data: Dictionário com {h1, h4, d1, symbol, sentiment, macro, smc}
            initial_capital: Capital inicial em USD
            risk_params: Parâmetros de risco opcionais
            episode_length: Comprimento máximo do episódio
            seed: Seed para reprodutibilidade (DEFAULT: 42)
        """
        # Inferir episode_length se não fornecido
        if episode_length is None:
            h4_data = data.get('h4', pd.DataFrame())
            episode_length = len(h4_data) - 1 if len(h4_data) > 1 else 100
        
        # Chamar super().__init__()
        super().__init__(
            data=data,
            initial_capital=initial_capital,
            risk_params=risk_params,
            episode_length=episode_length
        )
        
        # Aplicar seed determinístico
        self.seed_value = seed
        np.random.seed(seed)
        
        logger.info(f"BacktestEnvironment: {data.get('symbol', 'UNKNOWN')}, "
                   f"seed={seed}, episode_length={episode_length}")
    
    def reset(self, 
              seed: Optional[int] = None,
              options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reseta com seed determinístico."""
        if seed is None:
            seed = self.seed_value
        np.random.seed(seed)
        return super().reset(seed=seed, options=options)
    
    def get_backtest_summary(self) -> Dict[str, Any]:
        """Retorna sumário de performance."""
        closed_trades = [t for t in self.trades_history if t.get('exit_price')]
        total_trades = len(self.trades_history)
        
        if total_trades == 0:
            return {
                'symbol': self.symbol,
                'total_trades': 0,
                'final_capital': self.capital,
                'return_pct': 0,
            }
        
        winning = sum(1 for t in closed_trades if t.get('pnl', 0) > 0)
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        return_pct = (self.capital - self.initial_capital) / self.initial_capital * 100 if self.initial_capital > 0 else 0
        
        return {
            'symbol': self.symbol,
            'total_trades': total_trades,
            'closed_trades': len(closed_trades),
            'winning_trades': winning,
            'losing_trades': len(closed_trades) - winning,
            'win_rate_pct': (winning / len(closed_trades) * 100) if closed_trades else 0,
            'total_pnl': total_pnl,
            'final_capital': self.capital,
            'return_pct': return_pct,
        }

        
        if start_index >= len(self.data_df):
            raise ValueError(f"start_index {start_index} >= dados "
                           f"{len(self.data_df)}")
        
        # Resetar estado
        self.current_index = start_index
        self.capital = self.initial_capital
        self.position_size = 0
        self.entry_price = 0
        self.trade_history = []
        self.peak_capital = self.initial_capital
        self.pnl_history = []
        
        # Gerar primeira observação
        obs = self._get_observation()
        
        current_candle = self.data_df.iloc[self.current_index]
        info = {
            'timestamp': current_candle.get('open_time', self.current_index),
            'current_price': current_candle['close'],
            'balance': self.capital,
            'position_size': self.position_size,
            'trade_id': None,
        }
        
        logger.debug(f"Reset: index={self.current_index}, "
                    f"price={current_candle['close']}")
        
        return obs, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Executa um passo (1 candle) no backtest.
        
        Args:
            action: 0=HOLD, 1=OPEN_LONG, 2=OPEN_SHORT, 3=CLOSE, 4=REDUCE_50
            
        Returns:
            obs: Próxima observação (104 features)
            reward: Recompensa do step
            terminated: True se atingiu limite de episódio
            truncated: False (não usado em backtest)
            info: Metadata do passo (price, PnL, trade_id)
        """
        # Verificar se chegou ao final
        if self.current_index >= len(self.data_df) - 1:
            obs = self._get_observation()
            return (obs, 0.0, True, False,
                   {'message': 'Backtest completado',
                    'total_trades': len(self.trade_history)})
        
        # Avançar índice
        self.current_index += 1
        current_candle = self.data_df.iloc[self.current_index]
        current_price = float(current_candle['close'])
        
        # Processar SL/TP se houver posição aberta
        reward = 0.0
        if self.position_size != 0:
            # LONG
            if self.position_size > 0:
                if current_price <= self.stop_loss:
                    self._close_position(current_price, 'STOP_LOSS')
                elif current_price >= self.take_profit:
                    self._close_position(current_price, 'TP_HIT')
            # SHORT
            else:
                if current_price >= self.stop_loss:
                    self._close_position(current_price, 'STOP_LOSS')
                elif current_price <= self.take_profit:
                    self._close_position(current_price, 'TP_HIT')
        
        # Processar nova ação
        if action == 1 and self.position_size == 0:  # OPEN_LONG
            size, sl, tp = self.risk_manager.calculate_position(
                balance=self.capital,
                current_price=current_price,
                direction='LONG',
                leverage=self.leverage
            )
            self.position_size = size
            self.entry_price = current_price
            self.stop_loss = sl
            self.take_profit = tp
            self._add_trade_entry('LONG', current_price,
                                 current_candle.get('open_time'))
        
        elif action == 2 and self.position_size == 0:  # OPEN_SHORT
            size, sl, tp = self.risk_manager.calculate_position(
                balance=self.capital,
                current_price=current_price,
                direction='SHORT',
                leverage=self.leverage
            )
            self.position_size = -size
            self.entry_price = current_price
            self.stop_loss = sl
            self.take_profit = tp
            self._add_trade_entry('SHORT', current_price,
                                 current_candle.get('open_time'))
        
        elif action == 3 and self.position_size != 0:  # CLOSE
            self._close_position(current_price, 'MANUAL_CLOSE')
        
        elif action == 4 and self.position_size != 0:  # REDUCE_50
            # Reduzir metade da posição
            exit_size = abs(self.position_size) * 0.5
            if self.position_size > 0:
                self._close_position(current_price, 'REDUCE_50',
                                    exit_size=exit_size)
                self.position_size *= 0.5
            else:
                self._close_position(current_price, 'REDUCE_50',
                                    exit_size=exit_size)
                self.position_size *= 0.5
        
        # Próxima observação
        obs = self._get_observation()
        
        # Info dict para auditoria
        info = {
            'timestamp': current_candle.get('open_time', self.current_index),
            'current_price': current_price,
            'balance': self.capital,
            'position_size': self.position_size,
            'trade_id': (self.trade_history[-1].get('trade_id')
                        if self.trade_history else None),
        }
        
        return obs, reward, False, False, info
    
    def _get_observation(self) -> np.ndarray:
        """
        Gera observação de 104 features usando dados históricos.
        
        Reutiliza FeatureEngineer de CryptoFuturesEnv.
        """
        # Buscar janela histórica (últimos 200 candles)
        start_idx = max(0, self.current_index - 200)
        window = self.data_df.iloc[start_idx:self.current_index + 1]
        
        try:
            obs = self.feature_engineer.calculate_all_features(
                window_df=window,
                current_position=self.position_size,
                current_balance=self.capital
            )
            return obs.astype(np.float32)
        except Exception as e:
            logger.warning(f"Erro ao gerar features: {e}, retornando zeros")
            return np.zeros(104, dtype=np.float32)
    
    def _close_position(self,
                       exit_price: float,
                       reason: str,
                       exit_size: Optional[float] = None):
        """
        Fecha posição aberta e registra no histórico.
        
        Args:
            exit_price: Preço de saída
            reason: Motivo do fechamento (TP_HIT, STOP_LOSS, MANUAL_CLOSE, etc)
            exit_size: Tamanho a fechar (default: tudo)
        """
        if self.position_size == 0:
            return
        
        if exit_size is None:
            exit_size = abs(self.position_size)
        
        # Calcular PnL
        if self.position_size > 0:  # LONG
            pnl_abs = (exit_price - self.entry_price) * exit_size
        else:  # SHORT
            pnl_abs = (self.entry_price - exit_price) * exit_size
        
        # Aplicar fees (0.04% taker)
        fees = exit_size * exit_price * 0.0004
        net_pnl = pnl_abs - fees
        
        # Atualizar capital
        self.capital += net_pnl
        self.peak_capital = max(self.peak_capital, self.capital)
        self.pnl_history.append(net_pnl / self.initial_capital * 100)
        
        # Registrar no histórico
        if self.trade_history:
            last_trade = self.trade_history[-1]
            last_trade['exit_price'] = exit_price
            last_trade['exit_reason'] = reason
            last_trade['pnl_abs'] = pnl_abs
            last_trade['pnl_pct'] = (pnl_abs / (self.entry_price *
                                               abs(self.position_size))
                                    * 100)
            last_trade['net_pnl'] = net_pnl
            last_trade['fees'] = fees
        
        logger.debug(f"Posição fechada: {reason}, PnL={net_pnl:.2f}")
    
    def _add_trade_entry(self, side: str, entry_price: float, entry_time):
        """Adiciona entrada de trade ao histórico."""
        trade_id = (f"{self.symbol}_{self.current_index:06d}_"
                   f"{len(self.trade_history):03d}")
        
        self.trade_history.append({
            'trade_id': trade_id,
            'symbol': self.symbol,
            'side': side,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'entry_size': abs(self.position_size),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            # exit_* preenchidos em _close_position()
        })
        
        logger.debug(f"Trade aberto: {trade_id}, {side} @ {entry_price}")
    
    def get_trade_history(self) -> list:
        """Retorna histórico completo de trades para auditoria."""
        return self.trade_history.copy()
    
    def get_backtest_summary(self) -> Dict[str, Any]:
        """Retorna sumário do backtest para análise."""
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for t in self.trade_history
                            if t.get('pnl_abs', 0) > 0)
        losing_trades = total_trades - winning_trades
        
        return {
            'symbol': self.symbol,
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return_pct': ((self.capital - self.initial_capital) /
                                self.initial_capital * 100),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate_pct': (winning_trades / total_trades * 100
                            if total_trades > 0 else 0),
            'max_capital': self.peak_capital,
            'max_drawdown_pct': ((self.peak_capital - self.capital) /
                                self.peak_capital * 100),
        }
