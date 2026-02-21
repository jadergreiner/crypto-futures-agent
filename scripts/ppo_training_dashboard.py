"""
Dashboard de Convergência PPO — Phase 4
========================================

Monitora treinamento em tempo real com métricas críticas:
- Episode reward (smoothed)
- Policy/Value losses
- Entropy e KL divergence
- Win rate validation
- Sharpe estimate

Saída: logs/ppo_training/convergence_dashboard.csv
       logs/ppo_training/daily_summary.log
"""

import logging
import os
import csv
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


class ConvergenceDashboard:
    """Monitora convergência durante treinamento PPO."""

    def __init__(
        self,
        log_dir: str = "logs/ppo_training",
        window_size: int = 50  # Episodes para rolling average
    ):
        """
        Inicializa dashboard.

        Args:
            log_dir: Diretório para logs
            window_size: Tamanho da janela para rolling average
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.window_size = window_size
        self.csv_path = self.log_dir / "convergence_dashboard.csv"
        self.daily_log_path = self.log_dir / "daily_summary.log"
        self.alerts_path = self.log_dir / "alerts.log"

        # Buffers para rolling averages
        self.episode_rewards = deque(maxlen=window_size)
        self.policy_losses = deque(maxlen=window_size)
        self.value_losses = deque(maxlen=window_size)
        self.entropies = deque(maxlen=window_size)
        self.kl_divergences = deque(maxlen=window_size)

        # Rastrear episódios processados
        self.total_episodes = 0
        self.total_steps = 0
        self.best_reward = -np.inf
        self.best_sharpe = -np.inf
        self.consecutive_no_improve = 0
        self.training_start_time = datetime.now()

        # Métricas para validação
        self.validation_metrics = {
            'win_rate': 0.0,
            'sharpe_estimate': 0.0,
            'consecutive_losses': 0,
            'max_drawdown_pct': 0.0,
        }

        # Alerts & Thresholds
        self.kl_divergence_threshold = 0.05
        self.max_no_improve_threshold = 100  # Episódios

        # Inicializar CSV
        self._init_csv()

        logger.info(f"ConvergenceDashboard initialized at {self.log_dir}")

    def _init_csv(self):
        """Inicializa arquivo CSV com headers."""
        csv_headers = [
            'timestamp',
            'episode',
            'total_steps',
            'episode_reward',
            'reward_ma50',  # Moving average over 50 episodes
            'policy_loss',
            'value_loss',
            'entropy',
            'kl_divergence',
            'win_rate_val',
            'sharpe_estimate',
            'best_reward',
            'consecutive_no_improve',
            'status'  # 'normal', 'warning', 'excellent'
        ]

        # Escrever headers se arquivo não existe
        if not self.csv_path.exists():
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=csv_headers)
                writer.writeheader()
            logger.info(f"Created CSV: {self.csv_path}")

    def log_step(
        self,
        episode: int,
        total_steps: int,
        episode_reward: float,
        policy_loss: Optional[float] = None,
        value_loss: Optional[float] = None,
        entropy: Optional[float] = None,
        kl_divergence: Optional[float] = None,
        win_rate_validation: Optional[float] = None,
        sharpe_estimate: Optional[float] = None,
    ):
        """
        Registra um passo de treinamento.

        Args:
            episode: Número do episódio
            total_steps: Total de environment steps
            episode_reward: Reward do episódio
            policy_loss: Policy loss (do modelo)
            value_loss: Value loss (do modelo)
            entropy: Entropia da política
            kl_divergence: KL divergence da update
            win_rate_validation: Win rate na validation set (se calculado)
            sharpe_estimate: Estimativa de Sharpe (se calculado)
        """
        self.total_episodes = episode
        self.total_steps = total_steps

        # Adicionar aos buffers
        self.episode_rewards.append(episode_reward)
        if policy_loss is not None:
            self.policy_losses.append(policy_loss)
        if value_loss is not None:
            self.value_losses.append(value_loss)
        if entropy is not None:
            self.entropies.append(entropy)
        if kl_divergence is not None:
            self.kl_divergences.append(kl_divergence)

        # Calcular métricas
        reward_ma50 = np.mean(list(self.episode_rewards)) if self.episode_rewards else 0
        policy_loss_mean = np.mean(list(self.policy_losses)) if self.policy_losses else 0
        value_loss_mean = np.mean(list(self.value_losses)) if self.value_losses else 0
        entropy_mean = np.mean(list(self.entropies)) if self.entropies else 0
        kl_mean = np.mean(list(self.kl_divergences)) if self.kl_divergences else 0

        # Verificar melhoria
        if episode_reward > self.best_reward:
            self.best_reward = episode_reward
            self.consecutive_no_improve = 0
        else:
            self.consecutive_no_improve += 1

        # Atualizar métricas de validação
        if win_rate_validation is not None:
            self.validation_metrics['win_rate'] = win_rate_validation
        if sharpe_estimate is not None:
            self.validation_metrics['sharpe_estimate'] = sharpe_estimate

        # Determinar status
        status = self._determine_status(
            kl_mean,
            sharpe_estimate,
            self.consecutive_no_improve
        )

        # Logar para CSV
        csv_row = {
            'timestamp': datetime.now().isoformat(),
            'episode': episode,
            'total_steps': total_steps,
            'episode_reward': f"{episode_reward:.4f}",
            'reward_ma50': f"{reward_ma50:.4f}",
            'policy_loss': f"{policy_loss_mean:.6f}" if policy_loss_mean > 0 else "N/A",
            'value_loss': f"{value_loss_mean:.6f}" if value_loss_mean > 0 else "N/A",
            'entropy': f"{entropy_mean:.6f}" if entropy_mean > 0 else "N/A",
            'kl_divergence': f"{kl_mean:.6f}" if kl_mean > 0 else "N/A",
            'win_rate_val': f"{win_rate_validation:.2f}%" if win_rate_validation else "N/A",
            'sharpe_estimate': f"{sharpe_estimate:.4f}" if sharpe_estimate else "N/A",
            'best_reward': f"{self.best_reward:.4f}",
            'consecutive_no_improve': self.consecutive_no_improve,
            'status': status
        }

        # Escrever para CSV
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_row.keys())
            writer.writerow(csv_row)

        # Checar alertas
        self._check_alerts(kl_mean, sharpe_estimate, status)

    def _determine_status(
        self,
        kl_divergence: float,
        sharpe_estimate: Optional[float],
        no_improve_count: int
    ) -> str:
        """Determina status do treinamento."""
        if sharpe_estimate and sharpe_estimate > 0.7:
            return "excellent"
        elif kl_divergence > self.kl_divergence_threshold:
            return "warning"
        elif no_improve_count > self.max_no_improve_threshold:
            return "degrading"
        else:
            return "normal"

    def _check_alerts(
        self,
        kl_divergence: float,
        sharpe_estimate: Optional[float],
        status: str
    ):
        """Verifica alertas e escreve para log."""
        alerts = []

        if kl_divergence > self.kl_divergence_threshold:
            alerts.append(
                f"⚠️  KL divergence {kl_divergence:.6f} > "
                f"{self.kl_divergence_threshold} (large policy change)"
            )

        if sharpe_estimate and sharpe_estimate > 0.7:
            alerts.append(
                f"✅ EXCELLENT: Sharpe {sharpe_estimate:.4f} > 0.7 (save checkpoint!)"
            )

        if self.consecutive_no_improve > self.max_no_improve_threshold:
            alerts.append(
                f"❌ NO IMPROVEMENT: {self.consecutive_no_improve} episodes "
                f"(consider reducing LR or entropy)"
            )

        if alerts:
            timestamp = datetime.now().isoformat()
            with open(self.alerts_path, 'a') as f:
                for alert in alerts:
                    f.write(f"[{timestamp}] [{status.upper()}] {alert}\n")
                f.flush()

    def print_daily_summary(self, utc_hour: int = 10):
        """
        Imprime resumo diário (10:00 UTC check-in).

        Args:
            utc_hour: Hora UTC para check-in (default 10:00)
        """
        elapsed = datetime.now() - self.training_start_time
        elapsed_hours = elapsed.total_seconds() / 3600

        summary = {
            'timestamp': datetime.now().isoformat(),
            'training_duration_hours': f"{elapsed_hours:.1f}",
            'episodes_trained': self.total_episodes,
            'total_steps': self.total_steps,
            'best_episode_reward': f"{self.best_reward:.4f}",
            'current_reward_ma50': f"{np.mean(list(self.episode_rewards)):.4f}",
            'policy_loss_ma50': f"{np.mean(list(self.policy_losses)):.6f}" if self.policy_losses else "N/A",
            'entropy_ma50': f"{np.mean(list(self.entropies)):.6f}" if self.entropies else "N/A",
            'win_rate_estimate': f"{self.validation_metrics['win_rate']:.2f}%",
            'sharpe_estimate': f"{self.validation_metrics['sharpe_estimate']:.4f}",
            'consecutive_no_improve_episodes': self.consecutive_no_improve,
            'status': 'training normally' if self.consecutive_no_improve < 50 else 'degrading'
        }

        # Log to daily summary
        with open(self.daily_log_path, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"DAILY SUMMARY — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n")
            f.write(f"{'='*80}\n")
            for key, value in summary.items():
                f.write(f"{key:.<40} {value}\n")
            f.write(f"{'='*80}\n\n")
            f.flush()

        # Also print to console
        print(f"\n{'='*80}")
        print(f"DAILY SUMMARY — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*80}")
        for key, value in summary.items():
            print(f"{key:.<40} {value}")
        print(f"{'='*80}\n")

        logger.info(f"Daily summary written to {self.daily_log_path}")

    def get_status_dict(self) -> Dict[str, Any]:
        """Retorna status atual do treinamento como dicionário."""
        return {
            'total_episodes': self.total_episodes,
            'total_steps': self.total_steps,
            'best_reward': float(self.best_reward),
            'current_reward_ma50': float(np.mean(list(self.episode_rewards))) if self.episode_rewards else 0.0,
            'consecutive_no_improve': self.consecutive_no_improve,
            'validation_metrics': self.validation_metrics,
            'elapsed_hours': (datetime.now() - self.training_start_time).total_seconds() / 3600,
        }

    def save_checkpoint_metadata(self, checkpoint_path: str, metadata: Dict[str, Any]):
        """
        Salva metadata associado a um checkpoint.

        Args:
            checkpoint_path: Caminho do modelo salvo
            metadata: Metadata para o checkpoint
        """
        metadata_path = checkpoint_path.replace('.zip', '_metadata.json')
        metadata.update({
            'timestamp': datetime.now().isoformat(),
            'training_status': self.get_status_dict(),
        })

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Checkpoint metadata saved to {metadata_path}")


class ConvergenceMonitor:
    """Monitora e toma decisões de parada baseado em convergência."""

    def __init__(self, dashboard: ConvergenceDashboard):
        """
        Inicializa monitor.

        Args:
            dashboard: Dashboard instance para acessar métricas
        """
        self.dashboard = dashboard

    def should_stop_training(self) -> Tuple[bool, str]:
        """
        Determina se treinamento deve parar.

        Returns:
            (should_stop, reason)
        """
        no_improve = self.dashboard.consecutive_no_improve

        if no_improve > self.dashboard.max_no_improve_threshold:
            return True, (
                f"No improvement for {no_improve} episodes "
                "(exceeded threshold of {self.dashboard.max_no_improve_threshold})"
            )

        return False, ""

    def estimate_time_to_convergence(self) -> timedelta:
        """
        Estima tempo restante de treinamento (baseado em taxa histórica).

        Returns:
            Timedelta estimado
        """
        if self.dashboard.total_steps < 10000:
            return timedelta(days=5)  # Default estimate

        elapsed = datetime.now() - self.dashboard.training_start_time
        steps_per_second = self.dashboard.total_steps / elapsed.total_seconds()
        remaining_steps = 500_000 - self.dashboard.total_steps

        if steps_per_second > 0:
            remaining_seconds = remaining_steps / steps_per_second
            return timedelta(seconds=remaining_seconds)
        else:
            return timedelta(days=5)


if __name__ == "__main__":
    """Teste do dashboard."""
    dashboard = ConvergenceDashboard()

    # Simular alguns episódios
    np.random.seed(42)
    for ep in range(1, 101):
        reward = -100 + ep * 0.5 + np.random.normal(0, 10)
        policy_loss = 0.5 - ep * 0.001 + np.random.normal(0, 0.01)
        value_loss = 0.3 - ep * 0.0005 + np.random.normal(0, 0.01)
        entropy = 1.5 - ep * 0.01 + np.random.normal(0, 0.05)
        kl_div = 0.02 + np.random.normal(0, 0.005)

        dashboard.log_step(
            episode=ep,
            total_steps=ep * 2048,
            episode_reward=reward,
            policy_loss=policy_loss,
            value_loss=value_loss,
            entropy=entropy,
            kl_divergence=kl_div,
            win_rate_validation=45 + ep * 0.01,
            sharpe_estimate=0.1 + ep * 0.005,
        )

    dashboard.print_daily_summary()
    print(f"\nCSV written to {dashboard.csv_path}")
    print(f"Daily summary written to {dashboard.daily_log_path}")
    print(f"Alerts written to {dashboard.alerts_path}")
