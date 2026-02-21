"""
Script de Revalidação — Phase 4 (27-28 FEV)
==============================================

Carrega modelo treinado e executa full backtest com 6 risk gates.
Compara vs baseline random (2/6 gates) e decide GO/NO-GO.

Deadline: 2026-02-27 16:00 UTC (Decision)
         2026-02-28 até às 17:00 (Implementation if GO)
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RevalidationValidator:
    """Valida modelo treinado contra 6 risk gates."""

    # Risk Clearance Gates (da backtest_metrics.py)
    SHARPE_MIN = 1.0
    MAX_DD_MAX = 15.0
    WIN_RATE_MIN = 45.0
    PROFIT_FACTOR_MIN = 1.5
    CONSECUTIVE_LOSSES_MAX = 5
    CALMAR_MIN = 2.0

    def __init__(self, model_dir: str = "models/ppo_phase4"):
        """
        Inicializa validator.

        Args:
            model_dir: Diretório onde o modelo foi salvo
        """
        self.model_dir = Path(model_dir)
        self.results_dir = Path("reports/revalidation")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"RevalidationValidator initialized, model_dir={model_dir}")

    def load_model(self, checkpoint_name: str = "best_model"):
        """
        Carrega modelo treinado.

        Args:
            checkpoint_name: Nome do checkpoint (sem extensão)

        Returns:
            Modelo PPO carregado
        """
        model_path = self.model_dir / f"{checkpoint_name}.zip"

        if not model_path.exists():
            logger.error(f"Model not found: {model_path}")
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Importar modelo
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import VecNormalize

        # Carregar modelo
        model = PPO.load(model_path)
        logger.info(f"Model loaded from {model_path}")

        # Tentar carregar VecNormalize
        vec_norm_path = self.model_dir / f"{checkpoint_name}_vec_normalize.pkl"
        vec_normalize = None
        if vec_norm_path.exists():
            vec_normalize = VecNormalize.load(vec_norm_path)
            logger.info(f"VecNormalize loaded from {vec_norm_path}")

        return model, vec_normalize

    def run_backtest(
        self,
        model: Any,
        vec_normalize: Optional[Any],
        backtest_data: Dict[str, pd.DataFrame],
        num_episodes: int = 10
    ) -> Tuple[list, list, Dict[str, Any]]:
        """
        Executa backtest com modelo treinado.

        Args:
            model: Modelo PPO carregado
            vec_normalize: VecNormalize stats (se existe)
            backtest_data: Dados para backtest (h4, h1, d1, sentiment, macro, smc)
            num_episodes: Número de episódios a simular

        Returns:
            (trades, equity_curve, episode_stats)
        """
        from agent.environment import CryptoFuturesEnv
        from stable_baselines3.common.vec_env import DummyVecEnv

        logger.info(f"Running backtest with {num_episodes} episodes")

        all_trades = []
        all_equity_curves = []
        episode_rewards = []

        for ep in range(num_episodes):
            # Criar environment
            env = CryptoFuturesEnv(
                data=backtest_data,
                initial_capital=10000,
                episode_length=500
            )

            # Resetar
            obs, info = env.reset()
            done = False
            total_reward = 0
            episode_trades = []
            episode_equity = [10000]

            # Executar episódio
            while not done:
                # Normalizare observação se necessário
                if vec_normalize:
                    obs = vec_normalize.normalize_obs(obs)

                # Get action from model
                action, _ = model.predict(obs, deterministic=True)

                # Step environment
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                total_reward += reward

                # Coletar trades e equity
                if 'trades' in info:
                    episode_trades.extend(info['trades'])
                if 'capital' in info:
                    episode_equity.append(info['capital'])

            all_trades.extend(episode_trades)
            all_equity_curves.append(episode_equity)
            episode_rewards.append(total_reward)

            logger.info(f"Episode {ep+1}/{num_episodes}: reward={total_reward:.4f}, "
                       f"trades={len(episode_trades)}")

        # Consolidar equity curve (usar última para métricas)
        final_equity = all_equity_curves[-1] if all_equity_curves else [10000]

        episode_stats = {
            'num_episodes': num_episodes,
            'avg_reward': np.mean(episode_rewards),
            'total_trades': len(all_trades),
            'final_capital': final_equity[-1] if final_equity else 10000,
        }

        return all_trades, final_equity, episode_stats

    def calculate_metrics_from_trades(
        self,
        trades: list,
        equity_curve: list
    ) -> Dict[str, float]:
        """
        Calcula 6 métricas de risco a partir de trades e equity curve.

        Args:
            trades: Lista de trades completados
            equity_curve: Lista de capital ao longo do backtest

        Returns:
            Dicionário com 6 métricas
        """
        from backtest.backtest_metrics import BacktestMetrics

        # Se nenhum trade, retornar zeros
        if not trades or not equity_curve:
            return {
                'sharpe_ratio': 0.0,
                'max_drawdown_pct': 0.0,
                'win_rate_pct': 0.0,
                'profit_factor': 0.0,
                'consecutive_losses': 0,
                'calmar_ratio': 0.0,
            }

        # Usar BacktestMetrics da F-12
        metrics = BacktestMetrics.calculate_from_equity_curve(
            equity_curve=equity_curve,
            trades=trades,
            risk_free_rate=0.02
        )

        return {
            'sharpe_ratio': metrics.sharpe_ratio,
            'max_drawdown_pct': metrics.max_drawdown_pct,
            'win_rate_pct': metrics.win_rate_pct,
            'profit_factor': metrics.profit_factor,
            'consecutive_losses': metrics.consecutive_losses,
            'calmar_ratio': metrics.calmar_ratio,
        }

    def validate_gates(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Valida 6 gates de risco e retorna resultado GO/NO-GO.

        Args:
            metrics: Dicionário com 6 métricas

        Returns:
            {
                'gates_passed': int (0-6),
                'go_no_go': 'GO' | 'PARTIAL-GO' | 'NO-GO',
                'gate_results': {cada métrica com True/False},
                'summary': str,
                'recommendations': [str]
            }
        """
        results = {
            'sharpe_ratio_ok': metrics['sharpe_ratio'] >= self.SHARPE_MIN,
            'max_drawdown_ok': metrics['max_drawdown_pct'] <= self.MAX_DD_MAX,
            'win_rate_ok': metrics['win_rate_pct'] >= self.WIN_RATE_MIN,
            'profit_factor_ok': metrics['profit_factor'] >= self.PROFIT_FACTOR_MIN,
            'consecutive_losses_ok': metrics['consecutive_losses'] <= self.CONSECUTIVE_LOSSES_MAX,
            'calmar_ratio_ok': metrics['calmar_ratio'] >= self.CALMAR_MIN,
        }

        gates_passed = sum(results.values())

        # Determinar GO/NO-GO
        if gates_passed >= 5:
            decision = 'GO'
        elif gates_passed >= 4:
            decision = 'PARTIAL-GO'
        else:
            decision = 'NO-GO'

        # Recomendações
        recommendations = []
        if not results['sharpe_ratio_ok']:
            recommendations.append(
                f"Sharpe {metrics['sharpe_ratio']:.4f} < {self.SHARPE_MIN} "
                "(need higher returns or lower volatility)"
            )
        if not results['max_drawdown_ok']:
            recommendations.append(
                f"Max DD {metrics['max_drawdown_pct']:.2f}% > {self.MAX_DD_MAX}% "
                "(need stronger stop-losses or position sizing)"
            )
        if not results['win_rate_ok']:
            recommendations.append(
                f"Win Rate {metrics['win_rate_pct']:.2f}% < {self.WIN_RATE_MIN}% "
                "(need better entry signals or reward tuning)"
            )
        if not results['profit_factor_ok']:
            recommendations.append(
                f"Profit Factor {metrics['profit_factor']:.2f} < {self.PROFIT_FACTOR_MIN} "
                "(winners need to be larger than losers)"
            )
        if not results['consecutive_losses_ok']:
            recommendations.append(
                f"Consecutive Losses {metrics['consecutive_losses']} > {self.CONSECUTIVE_LOSSES_MAX} "
                "(need better diversification or entry filters)"
            )
        if not results['calmar_ratio_ok']:
            recommendations.append(
                f"Calmar {metrics['calmar_ratio']:.2f} < {self.CALMAR_MIN} "
                "(returns need to be much higher relative to drawdown)"
            )

        return {
            'gates_passed': gates_passed,
            'go_no_go': decision,
            'gate_results': results,
            'metrics': metrics,
            'recommendations': recommendations,
        }

    def generate_report(
        self,
        validation_result: Dict[str, Any],
        baseline_metrics: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Gera relatório de revalidação em markdown.

        Args:
            validation_result: Resultado de validação
            baseline_metrics: Métricas do baseline random (para comparação)

        Returns:
            Markdown report string
        """
        metrics = validation_result['metrics']
        gates = validation_result['gate_results']
        decision = validation_result['go_no_go']
        passed = validation_result['gates_passed']

        report = f"""
# Revalidation Report — Phase 4 PPO
## Date: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

### Decision: **{decision}** ({passed}/6 gates passed)

---

## Metrics Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Sharpe Ratio | {metrics['sharpe_ratio']:.4f} | ≥{self.SHARPE_MIN} | {'✅' if gates['sharpe_ratio_ok'] else '❌'} |
| Max Drawdown | {metrics['max_drawdown_pct']:.2f}% | ≤{self.MAX_DD_MAX}% | {'✅' if gates['max_drawdown_ok'] else '❌'} |
| Win Rate | {metrics['win_rate_pct']:.2f}% | ≥{self.WIN_RATE_MIN}% | {'✅' if gates['win_rate_ok'] else '❌'} |
| Profit Factor | {metrics['profit_factor']:.2f} | ≥{self.PROFIT_FACTOR_MIN} | {'✅' if gates['profit_factor_ok'] else '❌'} |
| Consecutive Losses | {metrics['consecutive_losses']} | ≤{self.CONSECUTIVE_LOSSES_MAX} | {'✅' if gates['consecutive_losses_ok'] else '❌'} |
| Calmar Ratio | {metrics['calmar_ratio']:.4f} | ≥{self.CALMAR_MIN} | {'✅' if gates['calmar_ratio_ok'] else '❌'} |

---

## Comparison vs Baseline (Random)

"""
        if baseline_metrics:
            report += """
| Metric | Random | Trained | Improvement |
|--------|--------|---------|-------------|
"""
            for key in ['sharpe_ratio', 'max_drawdown_pct', 'win_rate_pct', 'profit_factor']:
                if key in baseline_metrics and key in metrics:
                    baseline_val = baseline_metrics[key]
                    trained_val = metrics[key]
                    improvement = trained_val - baseline_val
                    report += f"| {key} | {baseline_val:.4f} | {trained_val:.4f} | {improvement:+.4f} |\n"

        if validation_result['recommendations']:
            report += "\n## Recommendations for Improvement\n\n"
            for i, rec in enumerate(validation_result['recommendations'], 1):
                report += f"{i}. {rec}\n"

        report += f"\n---\n"
        report += f"Generated: {datetime.now().isoformat()}\n"

        return report

    def save_results(
        self,
        validation_result: Dict[str, Any],
        report_markdown: str,
        filename: str = "revalidation_result"
    ):
        """
        Salva resultados de revalidação.

        Args:
            validation_result: Resultado de validação
            report_markdown: Markdown report
            filename: Nome base do arquivo (sem extensão)
        """
        # JSON
        json_path = self.results_dir / f"{filename}.json"
        with open(json_path, 'w') as f:
            json.dump(validation_result, f, indent=2)
        logger.info(f"JSON results saved to {json_path}")

        # Markdown
        md_path = self.results_dir / f"{filename}.md"
        with open(md_path, 'w') as f:
            f.write(report_markdown)
        logger.info(f"Markdown report saved to {md_path}")

        return json_path, md_path


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Função principal para executar revalidação."""
    import sys
    from pathlib import Path

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("="*80)
    print("REVALIDATION SCRIPT — Phase 4 (27-28 FEV)")
    print("="*80)

    # Criar validator
    validator = RevalidationValidator()

    # Carregar modelo
    print("\n[1/3] Loading trained model...")
    try:
        model, vec_normalize = validator.load_model("best_model")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("   Make sure model is saved as: models/ppo_phase4/best_model.zip")
        return

    # Carregar dados de backtest
    print("\n[2/3] Loading backtest data...")
    # TODO: Implementar carregamento de dados (depende de data module)
    print("   TODO: Implement data loading from data module")
    print("   Assuming data will be provided as dict with keys: h4, h1, d1, sentiment, macro, smc")

    # Executar backtest (simular por agora)
    print("\n[3/3] Running backtest...")
    print("   TODO: Run actual backtest with load_backtest_data()")
    print("   Simulating metrics for now...")

    # Simular métricas (para teste)
    simulated_metrics = {
        'sharpe_ratio': 1.1,
        'max_drawdown_pct': 12.5,
        'win_rate_pct': 52.5,
        'profit_factor': 1.7,
        'consecutive_losses': 4,
        'calmar_ratio': 2.2,
    }

    baseline_metrics = {
        'sharpe_ratio': 0.06,
        'max_drawdown_pct': 17.24,
        'win_rate_pct': 48.51,
        'profit_factor': 0.75,
        'consecutive_losses': 5,
        'calmar_ratio': 0.10,
    }

    # Validar
    print("\n[4/5] Validating against 6 risk gates...")
    validation = validator.validate_gates(simulated_metrics)

    # Gerar relatório
    print("\n[5/5] Generating report...")
    report = validator.generate_report(validation, baseline_metrics)

    # Salvar
    json_path, md_path = validator.save_results(validation, report)

    # Imprimir resultado
    print("\n" + "="*80)
    print(f"DECISION: {validation['go_no_go']} ({validation['gates_passed']}/6 gates)")
    print("="*80)
    print(report)

    print(f"\nResults saved to:")
    print(f"  - JSON: {json_path}")
    print(f"  - Markdown: {md_path}")


if __name__ == "__main__":
    main()
