"""
Engine de backtesting.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

logger = logging.getLogger(__name__)


class Backtester:
    """Engine de backtesting com dados históricos."""
    
    def __init__(self, initial_capital: float = 10000):
        """Inicializa backtester."""
        self.initial_capital = initial_capital
        self.trades = []
        self.equity_curve = []
        logger.info("Backtester initialized")
    
    def run(
        self, 
        start_date: str, 
        end_date: str, 
        model: Any, 
        data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Executa backtest.
        
        Args:
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)
            model: Modelo treinado (PPO)
            data: Dados históricos
            
        Returns:
            Resultados do backtest
        """
        from agent.environment import CryptoFuturesEnv
        
        logger.info(f"Running backtest: {start_date} to {end_date}")
        
        # Criar environment com os dados
        env = CryptoFuturesEnv(
            data=data,
            initial_capital=self.initial_capital,
            episode_length=len(data.get('h4', [])) - 1
        )
        
        # Reset environment
        obs, info = env.reset()
        done = False
        
        # Executar modelo step by step
        step_count = 0
        self.equity_curve = [self.initial_capital]
        
        while not done:
            # Predizer ação
            action, _states = model.predict(obs, deterministic=True)
            
            # Executar ação
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            # Registrar equity
            self.equity_curve.append(env.capital)
            
            step_count += 1
            
            if step_count % 100 == 0:
                logger.info(f"Backtest step {step_count}: capital=${env.capital:.2f}")
        
        # Coletar trades
        self.trades = env.trades_history
        
        # Calcular métricas
        metrics = self._calculate_metrics(
            self.trades, 
            self.equity_curve, 
            self.initial_capital
        )
        
        results = {
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': self.initial_capital,
            'final_capital': env.capital,
            'total_trades': len(self.trades),
            'metrics': metrics,
            'equity_curve': self.equity_curve,
            'trades': self.trades
        }
        
        logger.info(f"Backtest completed: {len(self.trades)} trades, "
                   f"final capital=${env.capital:.2f}")
        return results
    
    def _calculate_metrics(
        self, 
        trades: List[Dict[str, Any]], 
        equity_curve: List[float],
        initial_capital: float
    ) -> Dict[str, float]:
        """
        Calcula métricas de performance do backtest.
        
        Args:
            trades: Lista de trades executados
            equity_curve: Curva de equity
            initial_capital: Capital inicial
            
        Returns:
            Dicionário com métricas
        """
        if not trades:
            return {
                'total_return_pct': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown_pct': 0.0,
                'avg_r_multiple': 0.0,
                'total_trades': 0
            }
        
        # Return total
        final_capital = equity_curve[-1]
        total_return = (final_capital - initial_capital) / initial_capital * 100
        
        # Win rate
        winners = [t for t in trades if t['pnl'] > 0]
        win_rate = len(winners) / len(trades)
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in winners)
        losers = [t for t in trades if t['pnl'] <= 0]
        gross_loss = abs(sum(t['pnl'] for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio (assumindo daily returns)
        returns = []
        for i in range(1, len(equity_curve)):
            daily_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(daily_return)
        
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Anualizado
        else:
            sharpe_ratio = 0
        
        # Max drawdown
        peak = initial_capital
        max_dd = 0
        for capital in equity_curve:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak
            if dd > max_dd:
                max_dd = dd
        
        # Avg R-multiple
        r_multiples = [t['r_multiple'] for t in trades if 'r_multiple' in t]
        avg_r = np.mean(r_multiples) if r_multiples else 0
        
        return {
            'total_return_pct': total_return,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_dd * 100,
            'avg_r_multiple': avg_r,
            'total_trades': len(trades)
        }
    
    def compare_models(self, model_a: Any, model_b: Any, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Compara dois modelos.
        
        Args:
            model_a: Primeiro modelo
            model_b: Segundo modelo
            data: Dados de teste
            
        Returns:
            Comparação de métricas
        """
        logger.info("Comparing models...")
        
        results_a = self.run("2024-01-01", "2024-12-31", model_a, data)
        results_b = self.run("2024-01-01", "2024-12-31", model_b, data)
        
        comparison = {
            'model_a': results_a['metrics'],
            'model_b': results_b['metrics'],
            'winner': 'model_a'  # Simplificado
        }
        
        return comparison
    
    def generate_report(self, results: Dict[str, Any], save_path: str = "backtest_report.png") -> None:
        """
        Gera relatório visual com gráficos.
        
        Args:
            results: Resultados do backtest
            save_path: Caminho para salvar gráfico
        """
        logger.info(f"Generating report: {save_path}")
        
        if not results.get('equity_curve') or not results.get('trades'):
            logger.warning("Insufficient data to generate report")
            return
        
        # Criar figura com subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Backtest Report', fontsize=16, fontweight='bold')
        
        # 1. Equity Curve
        ax1 = axes[0, 0]
        equity_curve = results['equity_curve']
        ax1.plot(equity_curve, linewidth=2, color='#2E86AB')
        ax1.axhline(y=results['initial_capital'], color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
        ax1.set_title('Equity Curve', fontweight='bold')
        ax1.set_xlabel('Step')
        ax1.set_ylabel('Capital ($)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # 2. Drawdown Chart
        ax2 = axes[0, 1]
        peak = results['initial_capital']
        drawdowns = []
        for capital in equity_curve:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak * 100
            drawdowns.append(dd)
        
        ax2.fill_between(range(len(drawdowns)), drawdowns, color='#A23B72', alpha=0.6)
        ax2.set_title('Drawdown (%)', fontweight='bold')
        ax2.set_xlabel('Step')
        ax2.set_ylabel('Drawdown (%)')
        ax2.grid(True, alpha=0.3)
        ax2.invert_yaxis()
        
        # 3. Trade Distribution (PnL)
        ax3 = axes[1, 0]
        trades = results['trades']
        pnls = [t['pnl'] for t in trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p <= 0]
        
        ax3.hist([winners, losers], bins=20, label=['Winners', 'Losers'], 
                color=['#06A77D', '#D62246'], alpha=0.7)
        ax3.set_title('Trade Distribution (PnL)', fontweight='bold')
        ax3.set_xlabel('PnL ($)')
        ax3.set_ylabel('Count')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Métricas Resumo
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        metrics = results['metrics']
        metrics_text = f"""
        PERFORMANCE METRICS
        
        Total Return: {metrics['total_return_pct']:.2f}%
        Win Rate: {metrics['win_rate']*100:.2f}%
        Profit Factor: {metrics['profit_factor']:.2f}
        Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
        Max Drawdown: {metrics['max_drawdown_pct']:.2f}%
        Avg R-Multiple: {metrics['avg_r_multiple']:.2f}
        Total Trades: {metrics['total_trades']}
        
        Initial Capital: ${results['initial_capital']:.2f}
        Final Capital: ${results['final_capital']:.2f}
        """
        
        ax4.text(0.1, 0.5, metrics_text, fontsize=12, verticalalignment='center',
                family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
        
        plt.tight_layout()
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
        
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Report saved: {save_path}")

