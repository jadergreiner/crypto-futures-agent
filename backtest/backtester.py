"""Engine de backtesting com execução determinística e auditável (MVP F-12)."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class Backtester:
    """Engine de backtesting com dados históricos."""

    def __init__(self, initial_capital: float = 10000):
        """Inicializa backtester."""
        if initial_capital <= 0:
            raise ValueError("initial_capital deve ser maior que zero")
        self.initial_capital = initial_capital
        self.trades = []
        self.equity_curve = []
        logger.info("Backtester initialized")

    def run(
        self,
        start_date: str,
        end_date: str,
        model: Any,
        data: Dict[str, pd.DataFrame],
        symbol: str = "BTCUSDT",
        seed: int = 42,
        deterministic: bool = True,
        risk_stop_pct: float = -3.0,
        risk_params: Optional[Dict[str, Any]] = None,
        env_cls: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Executa backtest.

        Args:
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)
            model: Modelo treinado (PPO)
            data: Dados históricos
            symbol: Símbolo da execução
            seed: Seed para reproduzir execução
            deterministic: Se True, usa BacktestEnvironment determinístico
            risk_stop_pct: Hard stop percentual para validação de risco
            risk_params: Parâmetros de risco opcionais para environment
            env_cls: Classe de environment customizada (uso em testes)

        Returns:
            Resultados do backtest
        """
        if env_cls is None:
            if deterministic:
                from backtest.backtest_environment import BacktestEnvironment

                env_cls = BacktestEnvironment
            else:
                from agent.environment import CryptoFuturesEnv

                env_cls = CryptoFuturesEnv

        logger.info(
            "Running backtest: symbol=%s, range=%s..%s, deterministic=%s, seed=%s",
            symbol,
            start_date,
            end_date,
            deterministic,
            seed,
        )

        episode_length = max(1, len(data.get("h4", [])) - 1)

        # Criar environment com os dados
        env_kwargs: Dict[str, Any] = {
            "data": data,
            "initial_capital": self.initial_capital,
            "episode_length": episode_length,
        }
        if risk_params is not None:
            env_kwargs["risk_params"] = risk_params
        if deterministic:
            env_kwargs["seed"] = seed
            env_kwargs["deterministic"] = True

        env = env_cls(**env_kwargs)

        # Reset environment
        obs, _ = env.reset(seed=seed)
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
        self.trades = [self._normalize_trade(t) for t in env.trades_history]

        # Calcular métricas
        metrics = self._calculate_metrics(
            self.trades,
            self.equity_curve,
            self.initial_capital
        )
        risk_gate = self._evaluate_risk_gate(self.trades, risk_stop_pct)
        execution_id = self._build_execution_id(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            seed=seed,
        )
        text_summary = self.generate_text_summary(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            final_capital=env.capital,
            metrics=metrics,
            risk_gate=risk_gate,
        )

        results = {
            "execution_id": execution_id,
            "symbol": symbol,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': self.initial_capital,
            'final_capital': env.capital,
            'total_trades': len(self.trades),
            'metrics': metrics,
            'equity_curve': self.equity_curve,
            'trades': self.trades,
            "risk_gate": risk_gate,
            "deterministic": deterministic,
            "seed": seed,
            "text_summary": text_summary,
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
                'total_trades': 0,
                "gross_pnl_usd": 0.0,
                "total_fees_usd": 0.0,
                "net_pnl_usd": 0.0,
            }

        # Return total
        final_capital = equity_curve[-1]
        total_return = (final_capital - initial_capital) / initial_capital * 100

        # Win rate
        winners = [t for t in trades if t["pnl"] > 0]
        win_rate = len(winners) / len(trades)

        # Profit factor
        gross_profit = sum(t["pnl"] for t in winners)
        losers = [t for t in trades if t["pnl"] <= 0]
        gross_loss = abs(sum(t["pnl"] for t in losers))
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
        gross_pnl = float(sum(t.get("pnl_bruto", t.get("pnl", 0.0)) for t in trades))
        total_fees = float(sum(t.get("fees", 0.0) for t in trades))
        net_pnl = float(sum(t.get("pnl", 0.0) for t in trades))

        return {
            'total_return_pct': total_return,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_dd * 100,
            'avg_r_multiple': avg_r,
            'total_trades': len(trades),
            "gross_pnl_usd": gross_pnl,
            "total_fees_usd": total_fees,
            "net_pnl_usd": net_pnl,
        }

    @staticmethod
    def _build_execution_id(symbol: str, start_date: str, end_date: str, seed: int) -> str:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        return f"bt_{symbol}_{start_date}_{end_date}_s{seed}_{ts}"

    @staticmethod
    def _trade_value(trade: Dict[str, Any], *keys: str, default: float = 0.0) -> float:
        for key in keys:
            if key in trade and trade[key] is not None:
                try:
                    return float(trade[key])
                except (TypeError, ValueError):
                    continue
        return float(default)

    def _normalize_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        pnl_liquido = self._trade_value(trade, "pnl", "net_pnl", "pnl_abs", "pnl_realized")
        pnl_bruto = self._trade_value(trade, "gross_pnl", default=pnl_liquido)
        fees = self._trade_value(trade, "fees", default=0.0)
        if fees == 0.0 and "entry_fee" in trade and "exit_fee" in trade:
            fees = self._trade_value(trade, "entry_fee") + self._trade_value(trade, "exit_fee")
        # Se não houver bruto explícito, inferir bruto como líquido + fees
        if "gross_pnl" not in trade and "pnl_bruto" not in trade:
            pnl_bruto = pnl_liquido + fees

        normalized = dict(trade)
        normalized["pnl"] = pnl_liquido
        normalized["pnl_bruto"] = pnl_bruto
        normalized["fees"] = fees
        return normalized

    @staticmethod
    def _evaluate_risk_gate(trades: List[Dict[str, Any]], risk_stop_pct: float) -> Dict[str, Any]:
        if not trades:
            return {
                "status": "NO_EVIDENCE",
                "risk_stop_pct": risk_stop_pct,
                "triggered_by_stop_loss": 0,
                "triggered_by_threshold": 0,
            }

        triggered_reasons = 0
        triggered_threshold = 0

        for trade in trades:
            exit_reason = str(trade.get("exit_reason", "")).lower()
            pnl_pct = Backtester._trade_value(trade, "pnl_pct")
            if exit_reason == "stop_loss":
                triggered_reasons += 1
            if pnl_pct <= risk_stop_pct:
                triggered_threshold += 1

        status = "TRIGGERED" if (triggered_reasons > 0 or triggered_threshold > 0) else "CLEAR"
        return {
            "status": status,
            "risk_stop_pct": risk_stop_pct,
            "triggered_by_stop_loss": triggered_reasons,
            "triggered_by_threshold": triggered_threshold,
        }

    @staticmethod
    def generate_text_summary(
        symbol: str,
        start_date: str,
        end_date: str,
        final_capital: float,
        metrics: Dict[str, float],
        risk_gate: Dict[str, Any],
    ) -> str:
        return (
            "BACKTEST MVP - RESUMO\n"
            f"Simbolo: {symbol}\n"
            f"Periodo: {start_date} -> {end_date}\n"
            f"Capital Final: ${final_capital:.2f}\n"
            f"PnL Liquido: ${metrics.get('net_pnl_usd', 0.0):.2f}\n"
            f"Fees Totais: ${metrics.get('total_fees_usd', 0.0):.2f}\n"
            f"Drawdown Max: {metrics.get('max_drawdown_pct', 0.0):.2f}%\n"
            f"Win Rate: {metrics.get('win_rate', 0.0) * 100:.2f}%\n"
            f"Risk Gate (-3%): {risk_gate.get('status', 'UNKNOWN')}\n"
            f"StopLoss Trigger: {risk_gate.get('triggered_by_stop_loss', 0)}\n"
            f"Threshold Trigger: {risk_gate.get('triggered_by_threshold', 0)}\n"
        )

    def save_results(
        self,
        results: Dict[str, Any],
        output_dir: str = "tests/output",
        prefix: str = "backtest_mvp",
    ) -> Tuple[str, str]:
        """Salva artefatos padronizados (JSON + resumo textual)."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        execution_id = results.get("execution_id", datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"))
        json_file = output_path / f"{prefix}_{execution_id}.json"
        txt_file = output_path / f"{prefix}_{execution_id}.txt"

        with json_file.open("w", encoding="utf-8") as fp:
            json.dump(results, fp, indent=2, ensure_ascii=False, default=str)

        with txt_file.open("w", encoding="utf-8") as fp:
            fp.write(results.get("text_summary", ""))

        return str(json_file), str(txt_file)

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

    def generate_report(self, results: Dict[str, Any], save_path: str = "backtest_report.png") -> bool:
        """
        Gera relatório visual com gráficos.

        Args:
            results: Resultados do backtest
            save_path: Caminho para salvar gráfico
        """
        logger.info(f"Generating report: {save_path}")

        if not results.get('equity_curve') or not results.get('trades'):
            logger.warning("Insufficient data to generate report")
            return False

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
        pnls = [self._trade_value(t, "pnl", "net_pnl", "pnl_abs", "pnl_realized") for t in trades]
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
        return True

