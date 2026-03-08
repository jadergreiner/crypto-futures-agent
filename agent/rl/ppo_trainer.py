"""
PPO Trainer para TASK-005 — Configuração e treinamento do agente PPO.

Responsabilidades:
- Inicializar o modelo PPO com parâmetros otimizados
- Configurar callbacks e logging
- Implementar gates de treinamento validação

Módulos:
    stable_baselines3: Framework PPO
    gymnasium: Ambiente RL
    torch: PyTorch (backend de deep learning)
    logging: Logging de execução
"""

import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict

from agent.rl.metrics_utils import compute_performance_metrics


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SharpeGateCallback(BaseCallback):
    """
    Callback para monitorar e aplicar gates Sharpe diários durante treinamento.

    Gates:
    - Dia 1: Sharpe ≥ 0.40 (ramp up phase)
    - Dia 2: Sharpe ≥ 0.70 (convergence phase)
    - Dia 3: Sharpe ≥ 1.0 (target achieved)
    """

    def __init__(
        self,
        eval_env,
        eval_freq: int = 10000,
        n_eval_episodes: int = 10,
        day_threshold: int = 300000,  # ~32h em timesteps
    ):
        """
        Inicializa o callback.

        Args:
            eval_env: Ambiente para avaliação
            eval_freq: Frequência de avaliação (timesteps)
            n_eval_episodes: Número de episódios para evaluar
            day_threshold: Timesteps por "dia"
        """
        super().__init__()
        self.eval_env = eval_env
        self.eval_freq = eval_freq
        self.n_eval_episodes = n_eval_episodes
        self.day_threshold = day_threshold
        self.last_eval_step = 0
        self.best_sharpe = -np.inf
        self.daily_sharpies = {}

    def _on_step(self) -> bool:
        """Chamado a cada step de treinamento."""
        # Avalia a cada eval_freq steps
        if self.num_timesteps - self.last_eval_step >= self.eval_freq:
            self.last_eval_step = self.num_timesteps

            metrics = self._evaluate_metrics()
            sharpe = metrics['sharpe_ratio']

            # Determina qual dia (0, 1, 2, 3+)
            day = self.num_timesteps // self.day_threshold

            # Armazena Sharpe do dia
            if day not in self.daily_sharpies:
                self.daily_sharpies[day] = []
            self.daily_sharpies[day].append(sharpe)

            # Calcula Sharpe médio do dia
            avg_sharpe = np.mean(self.daily_sharpies[day])

            # Aplica gates
            gate_passed = self._check_daily_gate(day, avg_sharpe)

            logger.info(
                f"[Step {self.num_timesteps}] Day {day} | "
                f"Sharpe: {avg_sharpe:.4f} | Gate: {'✅ PASS' if gate_passed else '⚠️  WARN'}"
            )

            # ============================================================
            # EARLY STOP V2: MUITO MENOS AGRESSIVO
            # ============================================================
            # v1: Sharpe >= 1.0 → early stop (muito agressivo, abortava em 22min)
            # v2: Sharpe >= 20.0 (very high, only stops on obvious anomaly)
            #     OU timesteps >= 500k (deixa completar 96h / 500k steps)
            # v2.4: Increased from 10.0 to 20.0 to allow full training
            # Resultado: Deixa treinamento rodar completo por padrão
            # ============================================================
            if not metrics.get('metric_sanity_passed', False):
                logger.warning("⚠️ Sanity check de métricas falhou. Parando treinamento.")
                return False

            if avg_sharpe >= 20.0:
                logger.warning(
                    f"⚠️  Sharpe anormalmente alto: {avg_sharpe:.4f}. "
                    f"Possível overfitting. Parando treinamento."
                )
                return False  # Para treinamento por suspeita de overfitting

            # Caso contrário, continua treinamento
            # (Deixa 96h / 500k steps rodar até completar)

        return True  # Continua treinamento

    def _evaluate_metrics(self, n_episodes: Optional[int] = None) -> Dict:
        """
        Avalia o modelo atual e calcula métricas de performance.

        Args:
            n_episodes: Número de episódios (usa padrão se None)

        Returns:
            dict: métricas calculadas
        """
        if n_episodes is None:
            n_episodes = self.n_eval_episodes

        all_trade_results = []

        for _ in range(n_episodes):
            obs, _ = self.eval_env.reset()
            terminated = False

            while not terminated:
                action, _states = self.model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = self.eval_env.step(action)
                if info.get('trade_closed') and info.get('closed_trade'):
                    all_trade_results.append(info['closed_trade'])

        return compute_performance_metrics(
            trade_results=all_trade_results,
            initial_capital=getattr(self.eval_env, 'initial_capital', 10000.0),
        )

    def _check_daily_gate(self, day: int, sharpe: float) -> bool:
        """
        Verifica se o gate Sharpe diário foi alcançado.

        Args:
            day (int): Número do dia (0, 1, 2)
            sharpe (float): Sharpe ratio do dia

        Returns:
            bool: True se passou no gate
        """
        gates = {
            0: 0.40,  # Dia 1
            1: 0.70,  # Dia 2
            2: 1.0,   # Dia 3
        }

        gate = gates.get(day, 1.0)  # Dias 3+ requerem Sharpe ≥ 1.0

        return sharpe >= gate


class PPOTrainer:
    """
    Trainer para inicializar e gerenciar modelo PPO.

    Responsabilidades:
    - Criar modelo PPO com hiperparâmetros otimizados
    - Gerenciar checkpoints
    - Coordenar avaliação e gates
    """

    def __init__(
        self,
        env,
        learning_rate: float = 1e-4,
        batch_size: int = 64,
        n_steps: int = 256,
        n_epochs: int = 4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_range: float = 0.2,
        logs_dir: str = "logs/ppo_tensorboard/",
        use_tensorboard: bool = True,
    ):
        """
        Inicializa o trainer PPO.

        Args:
            env: Ambiente Gymnasium
            learning_rate: Taxa de aprendizado
            batch_size: Tamanho do batch
            n_steps: Passos entre atualizações
            n_epochs: Épocas por atualização
            gamma: Fator de desconto
            gae_lambda: Parâmetro GAE
            clip_range: Clipping range para PPO
            logs_dir: Diretório para logs TensorBoard
            use_tensorboard: Se deve usar TensorBoard (padrão: True)
        """
        self.env = env
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.n_steps = n_steps
        self.n_epochs = n_epochs
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_range = clip_range
        self.logs_dir = logs_dir if use_tensorboard else None
        self.model = None

    def create_model(self) -> PPO:
        """
        Cria modelo PPO com arquitetura e parâmetros otimizados.

        Returns:
            PPO: Modelo treinado
        """
        # Arquitetura: 2 camadas hidden com 256 neurônios cada
        policy_kwargs = dict(
            net_arch=[256, 256],
            activation_fn=nn.ReLU,
        )

        # Cria modelo PPO
        self.model = PPO(
            policy="MlpPolicy",
            env=self.env,
            learning_rate=self.learning_rate,
            n_steps=self.n_steps,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            gamma=self.gamma,
            gae_lambda=self.gae_lambda,
            clip_range=self.clip_range,
            policy_kwargs=policy_kwargs,
            verbose=1,
            tensorboard_log=self.logs_dir,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )

        logger.info(
            f"✅ Modelo PPO criado\n"
            f"   Learning Rate: {self.learning_rate}\n"
            f"   Batch Size: {self.batch_size}\n"
            f"   Network: [{self.n_steps}, 256, 256, 3]\n"
            f"   Device: {self.model.device}"
        )

        return self.model

    def save_checkpoint(self, path: str) -> None:
        """
        Salva checkpoint do modelo.

        Args:
            path (str): Caminho para salvar
        """
        if self.model is None:
            logger.warning("Modelo não foi criado ainda!")
            return

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.model.save(path)
        logger.info(f"✅ Checkpoint salvo: {path}")

    def load_checkpoint(self, path: str) -> None:
        """
        Carrega checkpoint do modelo.

        Args:
            path (str): Caminho do checkpoint
        """
        self.model = PPO.load(path, env=self.env)
        logger.info(f"✅ Checkpoint carregado: {path}")


if __name__ == "__main__":
    # Teste básico
    print("✅ Módulo PPO Trainer importado com sucesso")
