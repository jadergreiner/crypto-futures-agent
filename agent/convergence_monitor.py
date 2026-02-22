"""
Monitor de Convergência e Divergência Treinamento PPO

Módulo responsável por agregar métricas de treinamento em tempo real,
detectar sinais de divergência precoce e exportar histórico para auditoria.
Integra com TensorBoard para visualização e CSV para rastreabilidade.

Responsabilidades:
- Logging de métricas a cada N steps
- Detecção de divergência (KL div, sem melhora)
- Exportação CSV para auditoria
- Geração de sumários diários
- Integração com TensorBoard
"""

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
from collections import deque

try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:
    SummaryWriter = None

logger = logging.getLogger(__name__)


class ConvergenceMonitor:
    """
    Monitora convergência/divergência durante treinamento PPO.

    Responsabilidades:
    - Acumular métricas (reward, loss, env reset, etc)
    - Detectar padrões de divergência
    - Exportar para TensorBoard e CSV
    - Gerar relatórios diários
    """

    def __init__(
        self,
        output_dir: str = "logs/training_metrics",
        tensorboard_log: Optional[str] = None,
        kl_divergence_threshold: float = 0.05,
        no_improve_episodes: int = 100,
        csv_export_interval: int = 10,
    ):
        """
        Inicializa monitor de convergência.

        Args:
            output_dir: Diretório para salvar CSV/logs
            tensorboard_log: Dir para SummaryWriter (se None, SB3 usa default)
            kl_divergence_threshold: Threshold para alerta KL (warn > 0.05)
            no_improve_episodes: Episodes sem melhora antes de flag divergência
            csv_export_interval: Exportar CSV a cada N steps
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tensorboard_log = tensorboard_log
        self.kl_divergence_threshold = kl_divergence_threshold
        self.no_improve_episodes = no_improve_episodes
        self.csv_export_interval = csv_export_interval

        # Buffer de métricas
        self.metrics_buffer: Dict[str, List[float]] = {
            "step": [],
            "episode_reward": [],
            "episode_length": [],
            "loss_policy": [],
            "loss_value": [],
            "entropy": [],
            "kl_divergence": [],
            "gradient_norm": [],
            "sharpe_backtest": [],  # Calculado diariamente
            "max_drawdown": [],
            "win_rate": [],
        }

        # Histórico para detecção de divergência
        self.reward_history = deque(maxlen=max(100, no_improve_episodes))
        self.kl_history = deque(maxlen=50)
        self.step_count = 0

        # CSV writer
        csv_path = self.output_dir / "metrics.csv"
        self.csv_file = open(csv_path, "w", newline="")
        self.csv_writer = csv.DictWriter(
            self.csv_file,
            fieldnames=list(self.metrics_buffer.keys()),
        )
        self.csv_writer.writeheader()

        # TensorBoard
        if SummaryWriter and tensorboard_log:
            self.tb_writer = SummaryWriter(log_dir=tensorboard_log)
            logger.info(f"TensorBoard ativado: {tensorboard_log}")
        else:
            self.tb_writer = None
            logger.debug("TensorBoard desativado (torch não disponível)")

        logger.info(
            f"Monitor de convergência inicializado. "
            f"Threshold KL: {kl_divergence_threshold}, "
            f"Sem melhora limite: {no_improve_episodes} episodes"
        )

    def log_step(
        self,
        step: int,
        episode_reward: Optional[float] = None,
        episode_length: Optional[int] = None,
        loss_policy: Optional[float] = None,
        loss_value: Optional[float] = None,
        entropy: Optional[float] = None,
        kl_divergence: Optional[float] = None,
        gradient_norm: Optional[float] = None,
    ) -> None:
        """
        Registra métrica de um step de treinamento.

        Args:
            step: Número do step
            episode_reward: Recompensa do episódio
            episode_length: Comprimento do episódio
            loss_policy: Perda da policy
            loss_value: Perda do value network
            entropy: Entropia da policy
            kl_divergence: Divergência KL (old vs new policy)
            gradient_norm: Norma do gradiente
        """
        self.step_count = step
        self.metrics_buffer["step"].append(step)
        self.metrics_buffer["episode_reward"].append(episode_reward or 0.0)
        self.metrics_buffer["episode_length"].append(episode_length or 0)
        self.metrics_buffer["loss_policy"].append(loss_policy or 0.0)
        self.metrics_buffer["loss_value"].append(loss_value or 0.0)
        self.metrics_buffer["entropy"].append(entropy or 0.0)
        self.metrics_buffer["kl_divergence"].append(kl_divergence or 0.0)
        self.metrics_buffer["gradient_norm"].append(gradient_norm or 0.0)

        # Adicionar ao histórico para detecção divergência
        if episode_reward is not None:
            self.reward_history.append(episode_reward)
        if kl_divergence is not None:
            self.kl_history.append(kl_divergence)

        # Exportar para TensorBoard
        if self.tb_writer:
            if episode_reward is not None:
                self.tb_writer.add_scalar("train/episode_reward", episode_reward, step)
            if loss_policy is not None:
                self.tb_writer.add_scalar("train/loss_policy", loss_policy, step)
            if kl_divergence is not None:
                self.tb_writer.add_scalar("train/kl_divergence", kl_divergence, step)
            if entropy is not None:
                self.tb_writer.add_scalar("train/entropy", entropy, step)

        # Exportar para CSV periodicamente
        if step % self.csv_export_interval == 0:
            self._export_to_csv()

        logger.debug(
            f"Step {step}: reward={episode_reward:.2f}, kl={kl_divergence:.4f}, "
            f"entropy={entropy:.4f}"
        )

    def compute_moving_average(
        self,
        metric: str,
        window: int = 50,
    ) -> Optional[float]:
        """
        Calcula média móvel de uma métrica.

        Args:
            metric: Nome da métrica ('episode_reward', 'loss_policy', etc)
            window: Tamanho da janela

        Returns:
            Média móvel ou None se não há dados suficientes
        """
        values = self.metrics_buffer.get(metric, [])
        if len(values) < window:
            return None

        return sum(values[-window:]) / window

    def detect_divergence(
        self,
        kl_threshold: Optional[float] = None,
        no_improve_threshold: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Detecta sinais de divergência de training.

        Critérios:
        - KL divergence > threshold por 10+ steps consecutivos
        - Reward estagnado por N episodes
        - Loss explodindo (gradient norm > 10)

        Args:
            kl_threshold: Override do threshold KL
            no_improve_threshold: Override do limite sem melhora

        Returns:
            Tupla (is_diverging, motivo_string)
        """
        kl_thresh = kl_threshold or self.kl_divergence_threshold
        no_improve = no_improve_threshold or self.no_improve_episodes

        # Critério 1: KL divergence alto por steps consecutivos
        if len(self.kl_history) > 10:
            recent_kl = list(self.kl_history)[-10:]
            if all(k > kl_thresh for k in recent_kl):
                return True, f"KL divergence consistently high: {max(recent_kl):.4f}"

        # Critério 2: Sem melhora na recompensa
        if len(self.reward_history) > no_improve:
            recent_rewards = list(self.reward_history)[-no_improve:]
            best_recent = max(recent_rewards)
            older_rewards = list(self.reward_history)[:-no_improve]
            if older_rewards and best_recent < max(older_rewards):
                return True, (
                    f"No reward improvement for {no_improve} episodes: "
                    f"best_recent={best_recent:.2f}"
                )

        # Critério 3: Gradient exploding
        if self.metrics_buffer["gradient_norm"]:
            recent_grad = self.metrics_buffer["gradient_norm"][-1]
            if recent_grad > 10.0:
                return True, f"Gradient explosion: {recent_grad:.2f}"

        return False, None

    def export_metrics_csv(self, output_path: Optional[str] = None) -> str:
        """
        Exporta métricas acumuladas para CSV.

        Args:
            output_path: Caminho de saída (se None, usa metrics.csv por padrão)

        Returns:
            Caminho do arquivo exportado
        """
        if output_path is None:
            output_path = self.output_dir / "metrics_export.csv"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Converter buffers em formato tabular
        num_steps = len(self.metrics_buffer["step"])
        rows = []
        for i in range(num_steps):
            row = {
                key: self.metrics_buffer[key][i] if i < len(self.metrics_buffer[key]) else None
                for key in self.metrics_buffer.keys()
            }
            rows.append(row)

        # Escrever CSV
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.metrics_buffer.keys())
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Métricas exportadas para CSV: {output_path}")
        return str(output_path)

    def generate_daily_summary(self) -> Dict[str, float]:
        """
        Gera sumário diário de treinamento.

        Returns:
            Dict com estatísticas agregadas do dia
            {avg_reward, max_reward, std_reward, avg_loss, etc}
        """
        if not self.metrics_buffer["episode_reward"]:
            return {}

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_steps": self.step_count,
            "mean_reward": sum(self.reward_history) / len(self.reward_history) if self.reward_history else 0,
            "max_reward": max(self.reward_history) if self.reward_history else 0,
            "min_reward": min(self.reward_history) if self.reward_history else 0,
            "std_reward": self._calculate_std(list(self.reward_history)) if self.reward_history else 0,
            "mean_kl_divergence": sum(self.kl_history) / len(self.kl_history) if self.kl_history else 0,
            "max_kl_divergence": max(self.kl_history) if self.kl_history else 0,
            "mean_loss_policy": self.compute_moving_average("loss_policy", 50) or 0,
            "mean_entropy": self.compute_moving_average("entropy", 50) or 0,
        }

        # Salvar sumário em JSON
        summary_file = self.output_dir / f"summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Sumário diário: {summary}")
        return summary

    def _export_to_csv(self) -> None:
        """Exporta buffer atual para CSV (uso interno)."""
        if self.step_count % self.csv_export_interval == 0:
            row = {
                key: self.metrics_buffer[key][-1] if self.metrics_buffer[key] else None
                for key in self.metrics_buffer.keys()
            }
            self.csv_writer.writerow(row)
            self.csv_file.flush()

    @staticmethod
    def _calculate_std(values: List[float]) -> float:
        """Calcula desvio padrão manual."""
        if not values or len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def close(self) -> None:
        """Fecha resources (CSV, TensorBoard)."""
        if self.csv_file:
            self.csv_file.close()
        if self.tb_writer:
            self.tb_writer.close()
        logger.info("Monitor de convergência encerrado")
