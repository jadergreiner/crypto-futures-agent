"""
MetricsCalculator — Calcula 6 métricas de performance para backtester.

Métricas:
1. Sharpe Ratio (≥ 0.80 gate, ≥ 1.20 target)
2. Max Drawdown (≤ 12% gate, ≤ 10% target)
3. Win Rate (≥ 45% gate)
4. Profit Factor (≥ 1.5 gate)
5. Consecutive Losses (≤ 5 gate)
6. (Bonus) Recovery Factor

TODO: ESP-ML implementar métodos
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calcula métricas de performance para backtesting.

    Inputs: trade_history, daily_returns
    Outputs: Dicionário com 6+ métricas
    """

    def __init__(self, trade_history: List[Dict],
                 daily_returns: Optional[np.ndarray] = None):
        """
        Inicializa MetricsCalculator.

        Args:
            trade_history: Lista de trades fechadas (Dict com 'pnl_abs', etc)
            daily_returns: Array de retornos diários (opcional)
        """
        self.trade_history = trade_history
        self.daily_returns = daily_returns if daily_returns is not None else np.array([])
        self.thresholds = {
            'sharpe_min': 0.80,
            'sharpe_target': 1.20,
            'max_dd_min': 0.12,
            'max_dd_target': 0.10,
            'win_rate_min': 0.45,
            'profit_factor_min': 1.5,
            'consec_losses_max': 5,
        }

        logger.info("MetricsCalculator initialized")

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Calcula Sharpe Ratio.

        Formula: (mean_return - risk_free) / std_return

        Args:
            risk_free_rate: Taxa livre de risco (default 0%)

        Returns:
            Sharpe Ratio

        TODO:
        - [x] Verificar que daily_returns tem dados
        - [x] mean_return = media dos retornos
        - [x] std_return = desvio padrão dos retornos
        - [x] sharpe = (mean - risk_free) / std
        - [x] Handle edge case: std == 0
        """
        logger.debug("Calculating Sharpe Ratio...")
        
        if len(self.daily_returns) == 0:
            logger.warning("No daily returns to calculate Sharpe Ratio")
            return 0.0
        
        mean_return = np.mean(self.daily_returns)
        std_return = np.std(self.daily_returns)
        
        if std_return == 0:
            logger.warning("Std Dev = 0, cannot calculate Sharpe Ratio")
            return 0.0
        
        sharpe = (mean_return - risk_free_rate) / std_return
        logger.debug(f"Sharpe Ratio = {sharpe:.4f}")
        return sharpe

    def calculate_max_drawdown(self) -> float:
        """
        Calcula Max Drawdown.

        Formula: max(peak - current) / peak

        Returns:
            Max Drawdown como fração (ex: 0.12 = 12%)

        TODO:
        - [x] Build equity curve a partir de daily_returns
        - [x] Para cada point: encontrar peak até aquele ponto
        - [x] Calcular drawdown = (peak - current) / peak
        - [x] Retornar máximo drawdown
        """
        logger.debug("Calculating Max Drawdown...")
        
        if len(self.daily_returns) == 0:
            logger.warning("No daily returns to calculate Max Drawdown")
            return 0.0
        
        # Build cumulative equity curve (starting at 1.0)
        cumulative_returns = np.cumprod(1 + self.daily_returns)
        
        # Find running maximum
        running_max = np.maximum.accumulate(cumulative_returns)
        
        # Calculate drawdown at each point
        drawdown = (cumulative_returns - running_max) / running_max
        
        # Get maximum drawdown (minimum value, convert to positive)
        max_dd = -np.min(drawdown)
        logger.debug(f"Max Drawdown = {max_dd:.4f}")
        return max_dd

    def calculate_win_rate(self) -> float:
        """
        Calcula Win Rate.

        Formula: winning_trades / total_trades

        Returns:
            Win Rate como fração (ex: 0.50 = 50%)

        TODO:
        - [x] Count trades com pnl_abs > 0
        - [x] Dividir pelo total
        """
        logger.debug("Calculating Win Rate...")
        
        if len(self.trade_history) == 0:
            logger.warning("No trades to calculate Win Rate")
            return 0.0
        
        winning_trades = sum(1 for trade in self.trade_history if trade.get('pnl_abs', 0) > 0)
        total_trades = len(self.trade_history)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        logger.debug(f"Win Rate = {win_rate:.4f} ({winning_trades}/{total_trades})")
        return win_rate

    def calculate_profit_factor(self) -> float:
        """
        Calcula Profit Factor.

        Formula: sum(wins) / abs(sum(losses))

        Returns:
            Profit Factor (ex: 1.5 = 150%)

        TODO:
        - [x] Sum de todos os PnLs positivos
        - [x] Sum de todos os PnLs negativos (em valor absoluto)
        - [x] Dividir
        - [x] Handle division by zero
        """
        logger.debug("Calculating Profit Factor...")
        
        if len(self.trade_history) == 0:
            logger.warning("No trades to calculate Profit Factor")
            return 0.0
        
        total_wins = sum(trade.get('pnl_abs', 0) for trade in self.trade_history 
                        if trade.get('pnl_abs', 0) > 0)
        total_losses = abs(sum(trade.get('pnl_abs', 0) for trade in self.trade_history 
                              if trade.get('pnl_abs', 0) < 0))
        
        if total_losses == 0:
            logger.warning("No losses found, Profit Factor = 0")
            return 0.0
        
        profit_factor = total_wins / total_losses
        logger.debug(f"Profit Factor = {profit_factor:.4f} ({total_wins}/{total_losses})")
        return profit_factor

    def calculate_consecutive_losses(self) -> int:
        """
        Encontra máxima sequência de trades perdedores.

        Returns:
            Número máximo de losses consecutivos

        TODO:
        - [x] Iterar trade_history
        - [x] Contar sequências de pnl_abs < 0
        - [x] Retornar máximo
        """
        logger.debug("Calculating Consecutive Losses...")
        
        if len(self.trade_history) == 0:
            logger.warning("No trades to calculate Consecutive Losses")
            return 0
        
        max_consecutive_losses = 0
        current_consecutive_losses = 0
        
        for trade in self.trade_history:
            if trade.get('pnl_abs', 0) < 0:
                current_consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
            else:
                current_consecutive_losses = 0
        
        logger.debug(f"Max Consecutive Losses = {max_consecutive_losses}")
        return max_consecutive_losses

    def calculate_all(self) -> Dict[str, float]:
        """
        Calcula TODAS as 6 métricas de uma vez.

        Returns:
            Dict com {'sharpe', 'max_dd', 'win_rate', 'profit_factor',
                      'consec_losses', 'recovery_factor'}
        """
        metrics = {
            'sharpe': self.calculate_sharpe_ratio(),
            'max_dd': self.calculate_max_drawdown(),
            'win_rate': self.calculate_win_rate(),
            'profit_factor': self.calculate_profit_factor(),
            'consec_losses': self.calculate_consecutive_losses(),
        }

        logger.info(f"All metrics calculated: {metrics}")
        return metrics

    def validate_against_thresholds(self, metrics: Dict[str, float]) -> bool:
        """
        Valida métricas contra thresholds de aprovação.

        Args:
            metrics: Dict retornado por calculate_all()

        Returns:
            True se todas as métricas >= thresholds, False case contrário

        TODO:
        - [x] Check sharpe >= 0.80
        - [x] Check max_dd <= 0.12
        - [x] Check win_rate >= 0.45
        - [x] Check profit_factor >= 1.5
        - [x] Check consec_losses <= 5
        - [x] Log cada check
        """
        logger.info("Validating metrics against thresholds...")
        all_valid = True
        
        # Check Sharpe Ratio
        sharpe_valid = metrics['sharpe'] >= self.thresholds['sharpe_min']
        logger.info(f"Sharpe Ratio: {metrics['sharpe']:.4f} >= {self.thresholds['sharpe_min']:.2f} ? {sharpe_valid}")
        all_valid &= sharpe_valid
        
        # Check Max Drawdown
        dd_valid = metrics['max_dd'] <= self.thresholds['max_dd_min']
        logger.info(f"Max Drawdown: {metrics['max_dd']:.4f} <= {self.thresholds['max_dd_min']:.2f} ? {dd_valid}")
        all_valid &= dd_valid
        
        # Check Win Rate
        wr_valid = metrics['win_rate'] >= self.thresholds['win_rate_min']
        logger.info(f"Win Rate: {metrics['win_rate']:.4f} >= {self.thresholds['win_rate_min']:.2f} ? {wr_valid}")
        all_valid &= wr_valid
        
        # Check Profit Factor
        pf_valid = metrics['profit_factor'] >= self.thresholds['profit_factor_min']
        logger.info(f"Profit Factor: {metrics['profit_factor']:.4f} >= {self.thresholds['profit_factor_min']:.2f} ? {pf_valid}")
        all_valid &= pf_valid
        
        # Check Consecutive Losses
        cl_valid = metrics['consec_losses'] <= self.thresholds['consec_losses_max']
        logger.info(f"Consecutive Losses: {metrics['consec_losses']} <= {self.thresholds['consec_losses_max']} ? {cl_valid}")
        all_valid &= cl_valid
        
        if all_valid:
            logger.info("✅ ALL METRICS PASSED VALIDATION")
        else:
            logger.warning("❌ SOME METRICS FAILED VALIDATION")
        
        return all_valid


def daily_returns_from_trade_history(trade_history: List[Dict],
                                     initial_capital: float) -> np.ndarray:
    """
    Construir array de daily returns a partir de trade_history.

    Assume cada trade = 1 dia.
    Returns % do capital.
    """
    if not trade_history or initial_capital == 0:
        return np.array([])
    
    returns = []
    for trade in trade_history:
        pnl = trade.get('pnl_abs', 0)
        return_pct = pnl / initial_capital
        returns.append(return_pct)
    
    return np.array(returns)


def build_equity_curve(daily_returns: np.ndarray,
                       initial_capital: float = 10000) -> np.ndarray:
    """Build equity curve array a partir de daily returns."""
    if len(daily_returns) == 0:
        return np.array([initial_capital])
    
    cumulative_returns = np.cumprod(1 + daily_returns)
    equity_curve = initial_capital * cumulative_returns
    
    # Prepend initial capital
    return np.insert(equity_curve, 0, initial_capital)
