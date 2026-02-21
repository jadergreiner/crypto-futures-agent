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
        self.daily_returns = daily_returns or np.array([])
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
        - [ ] Verificar que daily_returns tem dados
        - [ ] mean_return = media dos retornos
        - [ ] std_return = desvio padrão dos retornos
        - [ ] sharpe = (mean - risk_free) / std
        - [ ] Handle edge case: std == 0
        """
        # TODO: Implementar
        logger.debug("Calculating Sharpe Ratio...")
        return 0.0

    def calculate_max_drawdown(self) -> float:
        """
        Calcula Max Drawdown.

        Formula: max(peak - current) / peak

        Returns:
            Max Drawdown como fração (ex: 0.12 = 12%)

        TODO:
        - [ ] Build equity curve a partir de daily_returns
        - [ ] Para cada point: encontrar peak até aquele ponto
        - [ ] Calcular drawdown = (peak - current) / peak
        - [ ] Retornar máximo drawdown
        """
        # TODO: Implementar
        logger.debug("Calculating Max Drawdown...")
        return 0.0

    def calculate_win_rate(self) -> float:
        """
        Calcula Win Rate.

        Formula: winning_trades / total_trades

        Returns:
            Win Rate como fração (ex: 0.50 = 50%)

        TODO:
        - [ ] Count trades com pnl_abs > 0
        - [ ] Dividir pelo total
        """
        # TODO: Implementar
        logger.debug("Calculating Win Rate...")
        return 0.0

    def calculate_profit_factor(self) -> float:
        """
        Calcula Profit Factor.

        Formula: sum(wins) / abs(sum(losses))

        Returns:
            Profit Factor (ex: 1.5 = 150%)

        TODO:
        - [ ] Sum de todos os PnLs positivos
        - [ ] Sum de todos os PnLs negativos (em valor absoluto)
        - [ ] Dividir
        - [ ] Handle division by zero
        """
        # TODO: Implementar
        logger.debug("Calculating Profit Factor...")
        return 0.0

    def calculate_consecutive_losses(self) -> int:
        """
        Encontra máxima sequência de trades perdedores.

        Returns:
            Número máximo de losses consecutivos

        TODO:
        - [ ] Iterar trade_history
        - [ ] Contar sequências de pnl_abs < 0
        - [ ] Retornar máximo
        """
        # TODO: Implementar
        logger.debug("Calculating Consecutive Losses...")
        return 0

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
        - [ ] Check sharpe >= 0.80
        - [ ] Check max_dd <= 0.12
        - [ ] Check win_rate >= 0.45
        - [ ] Check profit_factor >= 1.5
        - [ ] Check consec_losses <= 5
        - [ ] Log cada check
        """
        # TODO: Implementar
        logger.info("Validating metrics against thresholds...")
        return True


# TODO: Helper functions
def daily_returns_from_trade_history(trade_history: List[Dict],
                                     initial_capital: float) -> np.ndarray:
    """
    Construir array de daily returns a partir de trade_history.

    Assume cada trade = 1 dia.
    Returns % do capital.
    """
    # TODO: Implementar
    pass


def build_equity_curve(daily_returns: np.ndarray,
                       initial_capital: float = 10000) -> np.ndarray:
    """Build equity curve array a partir de daily returns."""
    # TODO: Implementar
    pass
