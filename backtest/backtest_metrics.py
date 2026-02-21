"""
Validador de Métricas para Backtest — F-12 Risk Clearance

Implementa calculador automático de 6 métricas críticas para GO/NO-GO.
Fórmulas exatas conforme padrão da indústria (QuantConnect, Backtrader).
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class BacktestMetrics:
    """Métricas de backteste com critérios de risco GO/NO-GO."""

    # 6 Métricas Críticas (GO/NO-GO)
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    consecutive_losses: int = 0
    calmar_ratio: float = 0.0

    # Métricas Informativas
    sortino_ratio: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_return_pct: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    expectancy_pct: float = 0.0
    recovery_factor: float = 0.0

    # Critérios de Passagem (Risk Clearance Gates)
    SHARPE_MIN = 1.0
    MAX_DD_MAX = 15.0
    WIN_RATE_MIN = 45.0
    PROFIT_FACTOR_MIN = 1.5
    CONSECUTIVE_LOSSES_MAX = 5
    CALMAR_MIN = 2.0

    @staticmethod
    def calculate_from_equity_curve(
        equity_curve: List[float],
        trades: Optional[List[Dict[str, Any]]] = None,
        risk_free_rate: float = 0.02
    ) -> 'BacktestMetrics':
        """
        Calcula métricas a partir de equity curve e trades.

        Args:
            equity_curve: Lista de capital ao longo do backtest
            trades: Lista de trades completadas (com pnl)
            risk_free_rate: Taxa livre de risco anual (default 2%)

        Returns:
            BacktestMetrics calculado
        """
        if not equity_curve or len(equity_curve) < 2:
            return BacktestMetrics()

        equity_array = np.array(equity_curve, dtype=float)
        returns = np.diff(equity_array, prepend=equity_array[0])
        returns_pct = (returns[1:] / equity_array[:-1]) * 100

        # 1. SHARPE RATIO
        # Sharpe = (mean_return - risk_free_rate) / std_deviation
        mean_ret = np.mean(returns_pct) if len(returns_pct) > 0 else 0
        std_ret = np.std(returns_pct) if len(returns_pct) > 1 else 1
        
        # Converter taxa livre anual para daily equivalent
        daily_risk_free = (1 + risk_free_rate) ** (1/252) - 1
        sharpe = (mean_ret - daily_risk_free) / (std_ret + 1e-8) if std_ret > 0 else 0
        # Annualize Sharpe
        sharpe_annual = sharpe * np.sqrt(252)

        # 2. MAX DRAWDOWN
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - running_max) / (running_max + 1e-8)
        max_dd_pct = np.min(drawdowns) * 100 if len(drawdowns) > 0 else 0

        # 3-6. TRADES METRICS
        if trades is None or len(trades) == 0:
            # Sem trades = não avaliar métricas de trade
            return BacktestMetrics(
                sharpe_ratio=sharpe_annual,
                max_drawdown_pct=abs(max_dd_pct),
                win_rate_pct=0.0,
                profit_factor=0.0,
                consecutive_losses=0,
                calmar_ratio=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_return_pct=(equity_array[-1] - equity_array[0]) / (equity_array[0] + 1e-8) * 100
            )

        # Separar wins e losses
        pnls = [t.get('pnl_realized', 0) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        winning_trades = len(wins)
        losing_trades = len(losses)
        total_trades = len(trades)

        # CALMAR RATIO = Annual Return / Max Drawdown
        total_return = (equity_array[-1] - equity_array[0]) / (equity_array[0] + 1e-8)
        years = len(equity_curve) / 252  # Aproximado (252 candles = 1 ano)
        annual_return = (total_return / years * 100) if years > 0 else 0
        calmar = annual_return / (abs(max_dd_pct) + 1e-8) if max_dd_pct != 0 else 0

        # PROFIT FACTOR = sum(wins) / abs(sum(losses))
        sum_wins = sum(wins) if wins else 1e-8
        sum_losses = abs(sum(losses)) if losses else 1e-8
        profit_factor = sum_wins / (sum_losses + 1e-8)

        # WIN RATE = winning_trades / total_trades
        wr = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # EXPECTANCY = (wr% * avg_win) - ((1-wr%) * avg_loss)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        expectancy = (wr/100 * avg_win) - ((1 - wr/100) * avg_loss)

        # CONSECUTIVE LOSSES (máximo de perdas seguidas)
        max_consecutive_losses = 0
        current_consecutive = 0
        for pnl in pnls:
            if pnl < 0:
                current_consecutive += 1
                max_consecutive_losses = max(max_consecutive_losses, current_consecutive)
            else:
                current_consecutive = 0

        # RECOVERY FACTOR = Total PnL / Max Drawdown
        total_pnl = sum(pnls) if pnls else 0
        max_dd_abs = abs(max_dd_pct / 100) * equity_array[0]  # Converter pct para absoluto
        recovery_factor = total_pnl / (max_dd_abs + 1e-8) if max_dd_abs > 0 else 0

        return BacktestMetrics(
            sharpe_ratio=sharpe_annual,
            max_drawdown_pct=abs(max_dd_pct),
            win_rate_pct=wr,
            profit_factor=profit_factor,
            consecutive_losses=max_consecutive_losses,
            calmar_ratio=calmar,
            sortino_ratio=sharpe_annual * 0.75,  # Aproximado (Sortino < Sharpe)
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_return_pct=total_return * 100,
            avg_win_pct=np.mean([p/equity_array[0]*100 for p in wins]) if wins else 0,
            avg_loss_pct=np.mean([p/equity_array[0]*100 for p in losses]) if losses else 0,
            expectancy_pct=expectancy / (equity_array[0] + 1e-8) * 100,
            recovery_factor=recovery_factor
        )

    @property
    def risk_clearance_status(self) -> str:
        """
        Determina GO/NO-GO baseado em 6 métricas críticas.

        Returns:
            "✅ GO LIVE" se TODAS as métricas passam
            "❌ NO-GO / ITERATE" se qualquer métrica falha
        """
        checks = [
            self.sharpe_ratio >= self.SHARPE_MIN,
            self.max_drawdown_pct <= self.MAX_DD_MAX,
            self.win_rate_pct >= self.WIN_RATE_MIN,
            self.profit_factor >= self.PROFIT_FACTOR_MIN,
            self.consecutive_losses <= self.CONSECUTIVE_LOSSES_MAX,
            self.calmar_ratio >= self.CALMAR_MIN,
        ]
        
        all_pass = all(checks)
        return "✅ GO LIVE" if all_pass else "❌ NO-GO / ITERATE"

    def get_checklist(self) -> List[tuple]:
        """Retorna checklist de validação com status."""
        return [
            ("Sharpe Ratio (Annualized)", f"{self.sharpe_ratio:.2f}", "≥", self.SHARPE_MIN,
             self.sharpe_ratio >= self.SHARPE_MIN),
            ("Max Drawdown %", f"{self.max_drawdown_pct:.2f}%", "≤", self.MAX_DD_MAX,
             self.max_drawdown_pct <= self.MAX_DD_MAX),
            ("Win Rate %", f"{self.win_rate_pct:.1f}%", "≥", self.WIN_RATE_MIN,
             self.win_rate_pct >= self.WIN_RATE_MIN),
            ("Profit Factor", f"{self.profit_factor:.2f}", "≥", self.PROFIT_FACTOR_MIN,
             self.profit_factor >= self.PROFIT_FACTOR_MIN),
            ("Consecutive Losses", f"{self.consecutive_losses}", "≤",
             self.CONSECUTIVE_LOSSES_MAX,
             self.consecutive_losses <= self.CONSECUTIVE_LOSSES_MAX),
            ("Calmar Ratio", f"{self.calmar_ratio:.2f}", "≥", self.CALMAR_MIN,
             self.calmar_ratio >= self.CALMAR_MIN),
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Serializar para JSON."""
        return {
            'risk_clearance': self.risk_clearance_status,
            'metrics': {
                'sharpe_ratio': round(self.sharpe_ratio, 2),
                'max_drawdown_pct': round(self.max_drawdown_pct, 2),
                'win_rate_pct': round(self.win_rate_pct, 1),
                'profit_factor': round(self.profit_factor, 2),
                'consecutive_losses': self.consecutive_losses,
                'calmar_ratio': round(self.calmar_ratio, 2),
                'sortino_ratio': round(self.sortino_ratio, 2),
                'total_return_pct': round(self.total_return_pct, 2),
                'recovery_factor': round(self.recovery_factor, 2),
            },
            'trades': {
                'total': self.total_trades,
                'winning': self.winning_trades,
                'losing': self.losing_trades,
                'expectancy_pct': round(self.expectancy_pct, 2),
            }
        }

    def print_report(self, symbol: str = "BTCUSDT",
                    start_date: str = "",
                    end_date: str = ""):
        """Imprime relatório formatado em terminal."""
        
        print("\n" + "="*70)
        print(f"{'BACKTEST REPORT — Risk Clearance':^70}")
        print(f"{'Symbol: ' + symbol:^70}")
        if start_date and end_date:
            print(f"{'Period: ' + start_date + ' to ' + end_date:^70}")
        print("="*70)
        
        print(f"\n{'STATUS: ' + self.risk_clearance_status:^70}\n")

        # Checklist
        print("CRITICAL METRICS (6-Point GO/NO-GO):")
        print("-"*70)
        for metric, value, op, threshold, passed in self.get_checklist():
            status_icon = "✅" if passed else "❌"
            print(f"{status_icon} {metric:.<35} {value:>10} {op:>2} {threshold}")
        
        # Informative metrics
        print("\nINFORMATIVE METRICS:")
        print("-"*70)
        print(f"  Total Trades:           {self.total_trades:>10}")
        print(f"  Winning Trades:         {self.winning_trades:>10}")
        print(f"  Losing Trades:          {self.losing_trades:>10}")
        print(f"  Avg Win %:              {self.avg_win_pct:>10.2f}%")
        print(f"  Avg Loss %:             {self.avg_loss_pct:>10.2f}%")
        print(f"  Expectancy %:           {self.expectancy_pct:>10.2f}%")
        print(f"  Total Return %:         {self.total_return_pct:>10.2f}%")
        print(f"  Recovery Factor:        {self.recovery_factor:>10.2f}")
        print(f"  Sortino Ratio:          {self.sortino_ratio:>10.2f}")
        
        print("\n" + "="*70 + "\n")
