"""
Final Validation para TASK-005 — Validação final do modelo treinado.

Responsabilidades:
- Executar modelo treinado em backtest completo
- Calcular métricas finais contra success criteria
- Gerar relatório de validação
- Determinar GO/NO-GO para produção

Módulos:
    json: Salvamento de resultados
    pathlib: Manipulação de caminhos
    numpy: Computação numérica
    logging: Logging estruturado
"""

import json
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Tuple
from stable_baselines3 import PPO

from agent.rl.training_env import CryptoTradingEnv
from agent.rl.data_loader import TradeHistoryLoader
from agent.rl.metrics_utils import compute_performance_metrics

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Task005FinalValidator:
    """
    Valida modelo treinado contra success criteria de TASK-005.

    Success Criteria:
    1. Sharpe Ratio ≥ 0.80
    2. Max Drawdown ≤ 12%
    3. Win Rate ≥ 45%
    4. Profit Factor ≥ 1.5
    5. Consecutive Losses ≤ 5
    6. Model serialized
    """

    # Gates de sucesso
    SUCCESS_CRITERIA = {
        'sharpe_ratio': 0.80,
        'max_drawdown': 0.12,
        'win_rate': 0.45,
        'profit_factor': 1.5,
        'consecutive_losses': 5,
    }

    def __init__(
        self,
        model_path: str,
        trades_filepath: str = "data/trades_history.json",
        output_dir: str = "validation/",
    ):
        """
        Inicializa o validador.

        Args:
            model_path: Caminho do modelo treinado
            trades_filepath: Caminho do histórico de trades
            output_dir: Diretório para resultados
        """
        self.model_path = model_path
        self.trades_filepath = trades_filepath
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.env = None
        self.validation_results = {}

    def validate(self) -> Tuple[bool, Dict]:
        """
        Executa validação completa.

        Returns:
            tuple: (is_valid, results_dict)
        """
        logger.info("🔍 Iniciando validação final de TASK-005...")

        try:
            # Carrega model e environment
            if not self._load_model_and_env():
                return False, {}

            # Executa modelo em backtest completo
            if not self._run_backtest():
                return False, {}

            # Calcula métricas
            if not self._calculate_metrics():
                return False, {}

            # Verifica success criteria
            is_valid = self._check_success_criteria()

            # Salva resultados
            self._save_results(is_valid)

            return is_valid, self.validation_results

        except Exception as e:
            logger.error(f"❌ Erro na validação: {e}")
            return False, {}

    def _load_model_and_env(self) -> bool:
        """Carrega modelo e ambiente."""
        try:
            # Carrega dados de trades
            loader = TradeHistoryLoader(self.trades_filepath)
            trades = loader.load()

            # Cria environment
            self.env = CryptoTradingEnv(trade_data=trades)

            # Carrega modelo PPO
            self.model = PPO.load(self.model_path)

            logger.info("✅ Modelo e ambiente carregados")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            return False

    def _run_backtest(self) -> bool:
        """Executa modelo em backtest completo."""
        try:
            logger.info("📊 Executando backtest...")

            obs, _ = self.env.reset()
            trades = []
            terminated = False

            while not terminated:
                action, _states = self.model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = self.env.step(action)
                if info.get('trade_closed') and info.get('closed_trade'):
                    trades.append(info['closed_trade'])

            # Salva trades do backtest
            self.validation_results['trades'] = trades
            self.validation_results['backtest_trades_count'] = len(trades)

            logger.info(f"✅ Backtest completo ({len(trades)} trades)")
            return True

        except Exception as e:
            logger.error(f"❌ Erro no backtest: {e}")
            return False

    def _calculate_metrics(self) -> bool:
        """Calcula métricas finais com a mesma fonte de verdade do treino."""
        try:
            trades = self.validation_results.get('trades', [])
            if len(trades) == 0:
                logger.error("❌ Nenhum trade no backtest")
                return False

            metrics = compute_performance_metrics(
                trade_results=trades,
                initial_capital=self.env.initial_capital,
            )
            metrics['total_return'] = metrics['total_pnl']
            self.validation_results['metrics'] = metrics

            logger.info("✅ Métricas calculadas com validação de sanidade")
            return True

        except Exception as e:
            logger.error(f"❌ Erro no cálculo de métricas: {e}")
            return False

    def _check_success_criteria(self) -> bool:
        """Verifica se atende aos success criteria."""
        metrics = self.validation_results.get('metrics', {})

        criteria_results = {}
        all_passed = True

        for criterion, threshold in self.SUCCESS_CRITERIA.items():
            actual = metrics.get(criterion, 0)

            # Compara com threshold (maior é melhor para sharpe/win_rate/pf,
            # menor é melhor para drawdown/consecutive_losses)
            if criterion in ['max_drawdown', 'consecutive_losses']:
                passed = actual <= threshold
            else:
                passed = actual >= threshold

            criteria_results[criterion] = {
                'threshold': threshold,
                'actual': actual,
                'passed': passed,
            }

            all_passed = all_passed and passed

        self.validation_results['criteria_check'] = criteria_results
        self.validation_results['is_valid'] = all_passed and metrics.get('metric_sanity_passed', False)

        return self.validation_results['is_valid']

    def _save_results(self, is_valid: bool) -> None:
        """Salva resultados de validação."""
        # Salva JSON
        results_file = self.output_dir / "task005_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)

        # Imprime relatório
        self._print_validation_report(is_valid)

    def _print_validation_report(self, is_valid: bool) -> None:
        """Imprime relatório de validação."""
        metrics = self.validation_results.get('metrics', {})
        criteria = self.validation_results.get('criteria_check', {})

        print("\n" + "="*70)
        print("📋 TASK-005 FINAL VALIDATION REPORT")
        print("="*70)

        print("\n🎯 Success Criteria Check:")
        for criterion, check in criteria.items():
            status = "✅ PASS" if check['passed'] else "❌ FAIL"
            print(
                f"  {status} {criterion}: {check['actual']:.4f} "
                f"(gate: {check['threshold']:.4f})"
            )

        print(f"\n📊 Backtest Results:")
        print(f"  Total Trades:    {metrics.get('total_trades', 0)}")
        print(f"  Total PnL:       {metrics.get('total_pnl', 0):.4f}")
        print(f"  Sharpe Ratio:    {metrics.get('sharpe_ratio', 0):.4f}")
        print(f"  Win Rate:        {metrics.get('win_rate', 0)*100:.1f}%")
        print(f"  Max Drawdown:    {metrics.get('max_drawdown', 0)*100:.1f}%")
        print(f"  Profit Factor:   {metrics.get('profit_factor', 0):.2f}")
        print(f"  Vol Floor:       {metrics.get('vol_floor', 0):.4f}")
        print(f"  Metric Sanity:   {'PASS' if metrics.get('metric_sanity_passed') else 'FAIL'}")
        if metrics.get('sanity_issues'):
            print(f"  Sanity Issues:   {', '.join(metrics.get('sanity_issues', []))}")

        print(f"\n{'='*70}")
        if is_valid:
            print("✅ VALIDATION: GO — All criteria passed!")
        else:
            print("❌ VALIDATION: NO-GO — Some criteria failed!")
        print("="*70 + "\n")


def validate_task005_model(model_path: str) -> bool:
    """
    Função convenience para validar modelo.

    Args:
        model_path: Caminho do modelo

    Returns:
        bool: True se validação passou
    """
    validator = Task005FinalValidator(model_path)
    is_valid, results = validator.validate()
    return is_valid


if __name__ == "__main__":
    # Teste: espera modelo em models/ppo_v0_final.pkl
    from pathlib import Path

    model_path = "models/ppo_v0_final.pkl"
    if Path(model_path).exists():
        validate_task005_model(model_path)
    else:
        print(f"❌ Modelo não encontrado: {model_path}")
