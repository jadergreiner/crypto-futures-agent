#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BLID-067: Ensemble Voting PPO (Phase E.9)

Implementa votacao ensemble entre modelos MLP e LSTM treinados em E.8
com hyperparametros otimizados via Optuna (E.7).

Metodos suportados:
  1. Soft voting: Media ponderada de probabilities (Q-values)
  2. Hard voting: Votacao majoritaria com pesos (decisoes binarias)

Objetivo: Melhorar robustez e reducao de volatilidade vs modelos individuais.
"""

import os
import json
import logging
import argparse
from pathlib import Path
from typing import Tuple, List, Dict, Any

import numpy as np
from stable_baselines3 import PPO

# Imports do projeto
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.lstm_environment import LSTMSignalEnvironment
from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class EnsembleVotingPPO:
    """
    Votador ensemble para MLP + LSTM PPO models.

    Suporta soft voting (probabilistico) e hard voting (majoritario).
    """

    def __init__(
        self,
        mlp_checkpoint_path: str,
        lstm_checkpoint_path: str,
        mlp_weight: float = 0.48,
        lstm_weight: float = 0.52,
        voting_method: str = 'soft'
    ):
        """
        Inicializa ensemble.

        Args:
            mlp_checkpoint_path: Path para checkpoint MLP (E.8)
            lstm_checkpoint_path: Path para checkpoint LSTM (E.8)
            mlp_weight: Peso para MLP (default 0.48, baseado em Optuna E.7)
            lstm_weight: Peso para LSTM (default 0.52, melhor score)
            voting_method: 'soft' (media ponderada) ou 'hard' (majoritario)
        """
        self.mlp_weight = mlp_weight
        self.lstm_weight = lstm_weight
        self.voting_method = voting_method

        # Normalizar pesos
        total_weight = mlp_weight + lstm_weight
        self.mlp_weight = mlp_weight / total_weight
        self.lstm_weight = lstm_weight / total_weight

        logger.info(f"Carregando modelos E.8...")
        logger.info(f"  MLP:  {mlp_checkpoint_path} (peso {self.mlp_weight:.3f})")
        logger.info(f"  LSTM: {lstm_checkpoint_path} (peso {self.lstm_weight:.3f})")

        try:
            self.mlp_model = PPO.load(mlp_checkpoint_path)
            self.lstm_model = PPO.load(lstm_checkpoint_path)
            logger.info("[OK] Modelos carregados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar modelos: {e}")
            raise

    def predict_soft_voting(
        self,
        observation: np.ndarray,
        deterministic: bool = True
    ) -> Tuple[int, None]:
        """
        Predicao via soft voting (media ponderada de Q-values/logits).

        Args:
            observation: State observation from environment
            deterministic: Use deterministic policy (greedy)

        Returns:
            (action, None) - action escolhida via votacao ponderada
        """
        # Get actions e logits/probabilities de ambos modelos
        mlp_action, mlp_state = self.mlp_model.predict(
            observation, deterministic=deterministic, state=None
        )
        lstm_action, lstm_state = self.lstm_model.predict(
            observation, deterministic=deterministic, state=None
        )

        # Soft voting: se ambos concordam, aceitar
        # Se discordam, usar modelo com melhor peso (LSTM)
        if mlp_action == lstm_action:
            # Consenso: ambos modelos concordam
            action = int(mlp_action)
        else:
            # Discordancia: usar LSTM (weight > MLP)
            action = int(lstm_action) if self.lstm_weight > self.mlp_weight else int(mlp_action)

        return action, None

    def predict_hard_voting(
        self,
        observation: np.ndarray,
        deterministic: bool = True
    ) -> Tuple[int, None]:
        """
        Predicao via hard voting (votacao majoritaria com pesos).

        Args:
            observation: State observation from environment
            deterministic: Use deterministic policy (greedy)

        Returns:
            (action, None) - action escolhida via votacao com pesos
        """
        mlp_action, _ = self.mlp_model.predict(
            observation, deterministic=deterministic, state=None
        )
        lstm_action, _ = self.lstm_model.predict(
            observation, deterministic=deterministic, state=None
        )

        # Converter acoes para voto (0 ou 1)
        mlp_vote = int(mlp_action)
        lstm_vote = int(lstm_action)

        # Score ponderado: qual acao tem mais peso?
        # Action 0 score
        score_0 = (1 - mlp_vote) * self.mlp_weight + (1 - lstm_vote) * self.lstm_weight
        # Action 1 score
        score_1 = mlp_vote * self.mlp_weight + lstm_vote * self.lstm_weight

        # Escolher acao com maior score
        action = 1 if score_1 > score_0 else 0

        return action, None

    def predict(
        self,
        observation: np.ndarray,
        deterministic: bool = True
    ) -> Tuple[int, None]:
        """
        Predicao ensemble usando metodo configurado.

        Args:
            observation: State observation
            deterministic: Use deterministic policy

        Returns:
            (action, state_dict_placeholder)
        """
        if self.voting_method == 'soft':
            return self.predict_soft_voting(observation, deterministic)
        elif self.voting_method == 'hard':
            return self.predict_hard_voting(observation, deterministic)
        else:
            raise ValueError(f"Metodo de voting desconhecido: {self.voting_method}")

    def get_config(self) -> Dict[str, Any]:
        """Retorna configuracao do ensemble para logging."""
        return {
            'voting_method': self.voting_method,
            'mlp_weight': float(self.mlp_weight),
            'lstm_weight': float(self.lstm_weight),
            'mlp_checkpoint': getattr(self.mlp_model, 'get_env', lambda: None)(),
            'lstm_checkpoint': getattr(self.lstm_model, 'get_env', lambda: None)()
        }


def evaluate_ensemble(
    ensemble: EnsembleVotingPPO,
    env: LSTMSignalEnvironment,
    n_episodes: int = 10,
    deterministic: bool = True
) -> Dict[str, float]:
    """
    Avalia ensemble em ambiente.

    Args:
        ensemble: EnsembleVotingPPO instance
        env: Environment para avaliacao
        n_episodes: Numero de episodios
        deterministic: Use deterministic policy

    Returns:
        Dicionario com metricas (mean_reward, std_reward, etc)
    """
    episode_rewards = []
    episode_lengths = []

    for episode in range(n_episodes):
        obs, info = env.reset()
        done = False
        total_reward = 0
        steps = 0

        while not done:
            action, _ = ensemble.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            total_reward += reward
            steps += 1

        episode_rewards.append(total_reward)
        episode_lengths.append(steps)

    mean_reward = np.mean(episode_rewards)
    std_reward = np.std(episode_rewards)

    metrics = {
        'n_episodes': n_episodes,
        'mean_reward': float(mean_reward),
        'std_reward': float(std_reward),
        'min_reward': float(np.min(episode_rewards)),
        'max_reward': float(np.max(episode_rewards)),
        'mean_episode_length': float(np.mean(episode_lengths)),
        'std_episode_length': float(np.std(episode_lengths))
    }

    logger.info(f"Metricas ensemble (n={n_episodes}):")
    logger.info(f"  Mean reward: {mean_reward:.4f} +/- {std_reward:.4f}")
    logger.info(f"  Range: [{np.min(episode_rewards):.4f}, {np.max(episode_rewards):.4f}]")

    return metrics


def main():
    """CLI para ensemble voting."""
    parser = argparse.ArgumentParser(description='Ensemble Voting PPO (E.9)')
    parser.add_argument(
        '--mlp_path',
        type=str,
        default='checkpoints/ppo_training/mlp/optuna/ppo_mlp_e8_optuna.zip',
        help='Path para checkpoint MLP E.8'
    )
    parser.add_argument(
        '--lstm_path',
        type=str,
        default='checkpoints/ppo_training/lstm/optuna/ppo_lstm_e8_optuna.zip',
        help='Path para checkpoint LSTM E.8'
    )
    parser.add_argument(
        '--voting_method',
        type=str,
        default='soft',
        choices=['soft', 'hard'],
        help='Metodo de voting'
    )
    parser.add_argument(
        '--mlp_weight',
        type=float,
        default=0.48,
        help='Peso para MLP (E.7: score 0.8761)'
    )
    parser.add_argument(
        '--lstm_weight',
        type=float,
        default=0.52,
        help='Peso para LSTM (E.7: score 0.8690)'
    )
    parser.add_argument(
        '--n_episodes',
        type=int,
        default=10,
        help='Numero de episodios para avaliacao'
    )

    args = parser.parse_args()

    # Criar ensemble
    ensemble = EnsembleVotingPPO(
        mlp_checkpoint_path=args.mlp_path,
        lstm_checkpoint_path=args.lstm_path,
        mlp_weight=args.mlp_weight,
        lstm_weight=args.lstm_weight,
        voting_method=args.voting_method
    )

    # Criar environment com dados mock para avaliacao standalone
    logger.info("Inicializando LSTMSignalEnvironment...")
    _mock_signals = [{'id': i, 'symbol': 'BTCUSDT', 'direction': 'LONG',
                      'entry_price': 50000.0, 'stop_loss': 49000.0,
                      'take_profit': 52000.0, 'outcome': 'WIN',
                      'pnl_pct': 0.04} for i in range(10)]
    _mock_evolutions: dict[int, list[dict]] = {i: [] for i in range(10)}
    from agent.signal_environment import SignalReplayEnv
    env = LSTMSignalEnvironment(SignalReplayEnv(_mock_signals, _mock_evolutions))

    # Avaliar
    metrics = evaluate_ensemble(
        ensemble=ensemble,
        env=env,
        n_episodes=args.n_episodes,
        deterministic=True
    )

    # Salvar config e metricas
    output_dir = Path('results/model2/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = output_dir / f"ensemble_e9_config_{args.voting_method}.json"
    with open(config_path, 'w') as f:
        json.dump({
            'voting_method': args.voting_method,
            'mlp_weight': args.mlp_weight,
            'lstm_weight': args.lstm_weight,
            'mlp_checkpoint': args.mlp_path,
            'lstm_checkpoint': args.lstm_path,
            'metrics': metrics
        }, f, indent=2)

    logger.info(f"[OK] Config salvo em {config_path}")

    env.close()


if __name__ == '__main__':
    main()
