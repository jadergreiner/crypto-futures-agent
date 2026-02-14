"""
Performance tracker - Métricas de trading.
"""

import logging
from typing import List, Dict, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Calcula e rastreia métricas de performance do agente."""
    
    @staticmethod
    def calculate_metrics(trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calcula métricas de performance.
        
        Args:
            trades: Lista de trades
            
        Returns:
            Dicionário com métricas
        """
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'avg_r_multiple': 0.0,
                'expectancy': 0.0
            }
        
        # Win Rate
        winners = [t for t in trades if t.get('pnl', 0) > 0]
        losers = [t for t in trades if t.get('pnl', 0) <= 0]
        win_rate = len(winners) / len(trades) if trades else 0
        
        # Profit Factor
        gross_profit = sum(t.get('pnl', 0) for t in winners)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe Ratio
        returns = [t.get('pnl_pct', 0) for t in trades]
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Anualizado
        else:
            sharpe = 0
        
        # Max Drawdown
        cumulative = np.cumsum([t.get('pnl', 0) for t in trades])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_dd = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        # Avg R-Multiple
        r_multiples = [t.get('r_multiple', 0) for t in trades]
        avg_r = np.mean(r_multiples) if r_multiples else 0
        
        # Expectancy
        avg_win = np.mean([t.get('pnl', 0) for t in winners]) if winners else 0
        avg_loss = abs(np.mean([t.get('pnl', 0) for t in losers])) if losers else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        return {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'avg_r_multiple': avg_r,
            'expectancy': expectancy
        }
    
    @staticmethod
    def generate_weekly_report(trades_week: List[Dict[str, Any]]) -> str:
        """Gera relatório semanal."""
        metrics = PerformanceTracker.calculate_metrics(trades_week)
        
        report = f"""
WEEKLY PERFORMANCE REPORT
{"="*60}
Total Trades: {metrics['total_trades']}
Win Rate: {metrics['win_rate']*100:.2f}%
Profit Factor: {metrics['profit_factor']:.2f}
Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
Max Drawdown: {metrics['max_drawdown']*100:.2f}%
Avg R-Multiple: {metrics['avg_r_multiple']:.2f}
Expectancy: ${metrics['expectancy']:.2f}
{"="*60}
"""
        return report
    
    @staticmethod
    def check_degradation(metrics_history: List[Dict[str, float]], 
                         window: int = 14) -> bool:
        """
        Verifica degradação de performance.
        
        Args:
            metrics_history: Histórico de métricas diárias
            window: Janela de análise (dias)
            
        Returns:
            True se há degradação significativa
        """
        if len(metrics_history) < window * 2:
            return False
        
        # Comparar últimas 2 janelas
        recent = metrics_history[-window:]
        previous = metrics_history[-window*2:-window]
        
        recent_wr = np.mean([m.get('win_rate', 0) for m in recent])
        previous_wr = np.mean([m.get('win_rate', 0) for m in previous])
        
        recent_pf = np.mean([m.get('profit_factor', 0) for m in recent])
        previous_pf = np.mean([m.get('profit_factor', 0) for m in previous])
        
        # Degradação se win rate ou profit factor caíram > 20%
        wr_degradation = (previous_wr - recent_wr) / previous_wr > 0.2 if previous_wr > 0 else False
        pf_degradation = (previous_pf - recent_pf) / previous_pf > 0.2 if previous_pf > 0 else False
        
        return wr_degradation or pf_degradation
