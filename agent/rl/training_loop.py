"""
Training Loop para TASK-005 — Ciclo completo de treinamento PPO com daily gates.

Orquestra:
- Inicialização do ambiente
- Treinamento por 96h wall-time
- Aplicação de daily Sharpe gates
- Salvamento de checkpoints
- Monitoramento contínuo

Módulos:
    datetime: Rastreamento de tempo
    json: Salvamento de métricas
    pathlib: Manipulação de caminhos
    numpy: Computação numérica
    logging: Logging estruturado
"""

import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, Tuple, Optional
import sys
import os

# Add repo root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent.rl.training_env import CryptoTradingEnv
from agent.rl.data_loader import TradeHistoryLoader
from agent.rl.metrics_utils import compute_performance_metrics
from agent.rl.ppo_trainer import PPOTrainer

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Task005TrainingLoop:
    """
    Orquestrador do ciclo de treinamento PPO para TASK-005.

    Responsabilidades:
    - Gerenciar ciclos de treinamento de 96h
    - Aplicar daily Sharpe gates
    - Salvar checkpoints
    - Compilar métricas finais
    """

    # Daily Sharpe gates
    DAILY_GATES = {
        1: 0.40,  # Dia 1: Ramp up (aprendizado inicial)
        2: 0.70,  # Dia 2: Convergence (refinamento)
        3: 1.0,   # Dia 3: Target (sucesso)
    }

    # Timesteps totais: 500k (96h wall-time ÷ 360s/step ≈ 960k, usaremos 500k)
    TOTAL_TIMESTEPS = 500000
    CHECKPOINT_INTERVAL = 50000  # Salva a cada 50k steps (~5h)

    def __init__(
        self,
        trades_filepath: str = "data/trades_history.json",
        initial_capital: float = 10000.0,
        logs_dir: str = "logs/ppo_task005/",
        models_dir: str = "models/",
    ):
        """
        Inicializa o training loop.

        Args:
            trades_filepath: Caminho do arquivo de trades
            initial_capital: Capital inicial
            logs_dir: Diretório para logs
            models_dir: Diretório para modelos salvos
        """
        self.trades_filepath = trades_filepath
        self.initial_capital = initial_capital
        self.logs_dir = Path(logs_dir)
        self.models_dir = Path(models_dir)

        # Criar diretórios
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Estado de treinamento
        self.start_time = None
        self.training_log = {
            'start_time': '',
            'phase': 'not_started',
            'checkpoints': [],
            'daily_gates': {},
            'final_metrics': {},
            'status': 'PENDING',
            'stop_reason': 'not_started',
            'dataset_baseline': {},
        }

        self.env = None
        self.trainer = None
        self.model = None

    def initialize(self) -> bool:
        """
        Inicializa ambiente e trainer.

        Returns:
            bool: True se inicialização bem sucedida
        """
        logger.info("🔧 Inicializando TASK-005 Training Loop...")

        try:
            # Carrega histórico de trades
            loader = TradeHistoryLoader(self.trades_filepath)
            trades = loader.load()
            logger.info(f"💾 {len(trades)} trades carregados")
            baseline = loader.validate_baseline()
            self.training_log['dataset_baseline'] = baseline
            if not baseline.get('baseline_valid', False):
                raise ValueError(
                    f"Dataset baseline inválido: {baseline.get('baseline_issues', [])}"
                )
            logger.info(
                "📈 Baseline válido | "
                f"win_rate={baseline['win_rate']:.2%} "
                f"profit_factor={baseline['profit_factor']:.2f}"
            )

            # Cria ambiente
            self.env = CryptoTradingEnv(
                trade_data=trades,
                initial_capital=self.initial_capital
            )
            logger.info("🎮 Ambiente criado")

            # Cria trainer
            self.trainer = PPOTrainer(
                env=self.env,
                logs_dir=str(self.logs_dir / "tensorboard/"),
            )

            # Cria modelo
            self.model = self.trainer.create_model()
            logger.info("🤖 Modelo PPO criado")

            return True

        except Exception as e:
            logger.error(f"❌ Erro na inicialização: {e}")
            return False

    def run_training(self) -> bool:
        """
        Executa o ciclo de treinamento de 96h com daily gates.

        Returns:
            bool: True se treinamento bem sucedido
        """
        logger.info("🚀 Iniciando ciclo de treinamento de 96h...")

        self.start_time = datetime.utcnow()
        self.training_log['start_time'] = self.start_time.isoformat()
        self.training_log['phase'] = 'training'

        try:
            checkpoint_num = 0
            total_timesteps_trained = 0

            while total_timesteps_trained < self.TOTAL_TIMESTEPS:
                checkpoint_num += 1

                # Treina bloco de steps
                next_checkpoint_steps = min(
                    self.CHECKPOINT_INTERVAL,
                    self.TOTAL_TIMESTEPS - total_timesteps_trained
                )

                logger.info(
                    f"\n📌 Checkpoint {checkpoint_num}: "
                    f"Training {next_checkpoint_steps} steps "
                    f"({total_timesteps_trained}/{self.TOTAL_TIMESTEPS})"
                )

                # Treina
                self.model.learn(total_timesteps=next_checkpoint_steps)
                total_timesteps_trained += next_checkpoint_steps

                # Salva checkpoint
                checkpoint_path = self.models_dir / f"ppo_checkpoint_{checkpoint_num}.pkl"
                self.trainer.save_checkpoint(str(checkpoint_path))

                # Avalia e aplica daily gate
                elapsed_hours = (datetime.utcnow() - self.start_time).total_seconds() / 3600
                day = int(elapsed_hours / 24) + 1

                metrics = self._evaluate_checkpoint()
                sharpe = metrics['sharpe_ratio']

                # Log do checkpoint
                checkpoint_log = {
                    'num': checkpoint_num,
                    'timesteps': total_timesteps_trained,
                    'elapsed_hours': elapsed_hours,
                    'day': day,
                    'metrics': metrics,
                    'path': str(checkpoint_path),
                    'timestamp': datetime.utcnow().isoformat(),
                    'metric_sanity_passed': metrics.get('metric_sanity_passed', False),
                }
                self.training_log['checkpoints'].append(checkpoint_log)

                # Imprime Status
                self._log_checkpoint_status(day, sharpe, metrics)

                # Verifica daily gate
                gate_passed = self._check_daily_gate(day, sharpe)

                # Salva training log intermediário
                self._save_training_log()

                # Early stop apenas se Sharpe ≥ 20.0 (very high threshold, allows full training by default)
                # v2.4: Increased from 10.0 to 20.0 to avoid premature stopping
                if not metrics.get('metric_sanity_passed', False):
                    self.training_log['stop_reason'] = 'metric_sanity_failed'
                    logger.warning("⚠️ Sanity check falhou. Encerrando antes do treino longo.")
                    break

                if sharpe >= 20.0:
                    self.training_log['stop_reason'] = 'anomalous_sharpe_guard'
                    logger.info("🎉 Target Sharpe ≥ 20.0 alcançado! Encerrando treinamento.")
                    break

                # Timeout safety: se > 120h, para mesmo que não tenha atingido target
                if elapsed_hours > 120:
                    self.training_log['stop_reason'] = 'wall_time_timeout'
                    logger.warning("⚠️ Limite de 120h atingido. Encerrando.")
                    break

            # Treinamento completo
            if self.training_log['stop_reason'] == 'not_started':
                self.training_log['stop_reason'] = 'completed_full_cycle'
            self.training_log['status'] = 'TRAINING_COMPLETE'
            logger.info("✅ Ciclo de treinamento completo!")

            return True

        except Exception as e:
            logger.error(f"❌ Erro durante treinamento: {e}")
            self.training_log['status'] = 'TRAINING_FAILED'
            return False

    def _evaluate_checkpoint(self) -> Dict:
        """
        Avalia modelo atual em episódios e calcula métricas.

        Returns:
            dict: Dicionário com métricas (sharpe, win_rate, max_dd, etc)
        """
        n_episodes = 20
        all_trade_results = []

        for _ in range(n_episodes):
            obs, _ = self.env.reset()
            terminated = False

            while not terminated:
                action, _states = self.model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = self.env.step(action)
                if info.get('trade_closed') and info.get('closed_trade'):
                    all_trade_results.append(info['closed_trade'])

        metrics = compute_performance_metrics(
            trade_results=all_trade_results,
            initial_capital=self.initial_capital,
        )
        metrics['num_episodes'] = n_episodes
        metrics['stop_reason'] = self.training_log.get('stop_reason', 'not_started')
        return metrics

    def _check_daily_gate(self, day: int, sharpe: float) -> bool:
        """
        Verifica se o gate Sharpe diário foi alcançado.

        Args:
            day (int): Número do dia (1, 2, 3, ...)
            sharpe (float): Sharpe ratio do dia

        Returns:
            bool: True se passou no gate
        """
        gate = self.DAILY_GATES.get(day, 1.0)
        passed = sharpe >= gate

        # Log do gate
        self.training_log['daily_gates'][day] = {
            'gate_threshold': gate,
            'sharpe_actual': sharpe,
            'passed': passed,
        }

        return passed

    def _log_checkpoint_status(self, day: int, sharpe: float, metrics: Dict) -> None:
        """Imprime status do checkpoint de forma amigável."""
        status = "✅" if sharpe >= self.DAILY_GATES.get(day, 1.0) else "⚠️"

        logger.info(
            f"{status} Day {day} | Sharpe: {sharpe:.4f} | "
            f"Win Rate: {metrics['win_rate']*100:.1f}% | "
            f"PnL: {metrics['total_pnl']:.4f} | "
            f"Trades: {metrics['num_trades_evaluated']}"
        )

    def _save_training_log(self) -> None:
        """Salva log de treinamento em JSON."""
        log_path = self.logs_dir / "training_log.json"

        with open(log_path, 'w') as f:
            json.dump(self.training_log, f, indent=2)

    def finalize(self) -> bool:
        """
        Finaliza treinamento e salva modelo final.

        Returns:
            bool: True se finalização bem sucedida
        """
        logger.info("🏁 Finalizando TASK-005...")

        try:
            # Salva modelo final
            final_model_path = self.models_dir / "ppo_v0_final.pkl"
            self.trainer.save_checkpoint(str(final_model_path))

            # Compila métricas finais
            final_metrics = self._evaluate_checkpoint()
            self.training_log['final_metrics'] = final_metrics
            self.training_log['status'] = 'COMPLETE'
            self.training_log['end_time'] = datetime.utcnow().isoformat()

            # Salva log final
            self._save_training_log()

            # Imprime resumo final
            self._print_final_summary(final_model_path, final_metrics)

            return True

        except Exception as e:
            logger.error(f"❌ Erro durante finalização: {e}")
            return False

    def _print_final_summary(self, model_path: Path, metrics: Dict) -> None:
        """Imprime resumo final de treinamento."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() / 3600

        print("\n" + "="*70)
        print("TASK-005 TRAINING COMPLETE")
        print("="*70)
        print(f"Model Saved:      {model_path}")
        print(f"Elapsed Time:     {elapsed:.1f} hours")
        print(f"\nFinal Metrics:")
        print(f"  - Sharpe Ratio: {metrics['sharpe_ratio']:.4f} (target: >=1.0)")
        print(f"  - Win Rate:     {metrics['win_rate']*100:.1f}% (target: >=45%)")
        print(f"  - Total PnL:    {metrics['total_pnl']:.4f}")
        print(f"  - Trades Eval:  {metrics['num_trades_evaluated']}")
        print(f"  - Checkpoints:  {len(self.training_log['checkpoints'])}")
        print(f"\nDaily Gates:")
        for day, gate_info in self.training_log['daily_gates'].items():
            status = "PASS" if gate_info['passed'] else "WARN"
            print(f"  Day {day}: {status} (Sharpe: {gate_info['sharpe_actual']:.4f})")
        print(f"Stop Reason:      {self.training_log.get('stop_reason', 'unknown')}")
        print("="*70 + "\n")


def run_task005_training() -> bool:
    """
    Função de entrada para executar treinamento TASK-005 completo.

    Returns:
        bool: True se sucesso
    """
    logger.info("🚀 INICIANDO TASK-005 CICLO DE TREINAMENTO")

    # Criar orquestrador
    training_loop = Task005TrainingLoop()

    # Inicializar
    if not training_loop.initialize():
        logger.error("❌ Falha na inicialização")
        return False

    # Treinar
    if not training_loop.run_training():
        logger.error("❌ Falha no treinamento")
        return False

    # Finalizar
    if not training_loop.finalize():
        logger.error("❌ Falha na finalização")
        return False

    logger.info("✅ TASK-005 COMPLETO COM SUCESSO!")
    return True


if __name__ == "__main__":
    run_task005_training()
