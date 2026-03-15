#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BLID-067: Avaliacao Ensemble E.9

Compara performance de ensemble (MLP+LSTM votacao) vs modelos individuais.
Calcula Sharpe ratio, Win Rate, Max Drawdown e outras metricas.

Saida: JSON com resultados comparativos.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

import numpy as np
import pandas as pd
from stable_baselines3 import PPO

# Imports do projeto
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.lstm_environment import LSTMSignalEnvironment
from scripts.model2.ensemble_voting_ppo import EnsembleVotingPPO

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def load_model(checkpoint_path: str) -> PPO:
    """Carrega modelo PPO de checkpoint."""
    logger.info(f"Carregando modelo: {checkpoint_path}")
    return PPO.load(checkpoint_path)


def evaluate_model(
    model: PPO,
    env: LSTMSignalEnvironment,
    n_eval_episodes: int = 10,
    deterministic: bool = True
) -> Dict[str, float]:
    """
    Avalia modelo individual.

    Returns:
        Dicionario com metricas (mean_reward, sharpe, win_rate, max_drawdown)
    """
    episode_rewards = []
    episode_sharpes = []
    wins = 0
    total_episodes = 0

    for ep in range(n_eval_episodes):
        obs, info = env.reset()
        done = False
        episode_returns = []

        while not done:
            action, _ = model.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            episode_returns.append(reward)

        ep_reward = np.sum(episode_returns)
        episode_rewards.append(ep_reward)

        # Sharpe ratio
        if len(episode_returns) > 1:
            ep_sharpe = np.mean(episode_returns) / (np.std(episode_returns) + 1e-8)
        else:
            ep_sharpe = 0.0
        episode_sharpes.append(ep_sharpe)

        # Win rate (50% threshold)
        if ep_reward > 0:
            wins += 1
        total_episodes += 1

    # Calcular drawdown maximo
    cumsum_rewards = np.cumsum(episode_rewards)
    running_max = np.maximum.accumulate(cumsum_rewards)
    drawdown = (cumsum_rewards - running_max)
    max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0

    metrics = {
        'n_episodes': n_eval_episodes,
        'mean_reward': float(np.mean(episode_rewards)),
        'std_reward': float(np.std(episode_rewards)),
        'min_reward': float(np.min(episode_rewards)),
        'max_reward': float(np.max(episode_rewards)),
        'mean_sharpe': float(np.mean(episode_sharpes)),
        'std_sharpe': float(np.std(episode_sharpes)),
        'win_rate': float(wins / total_episodes),
        'max_drawdown': float(max_drawdown)
    }

    return metrics


def evaluate_ensemble_model(
    ensemble: EnsembleVotingPPO,
    env: LSTMSignalEnvironment,
    n_eval_episodes: int = 10,
    deterministic: bool = True
) -> Dict[str, float]:
    """Avalia ensemble."""
    episode_rewards = []
    episode_sharpes = []
    wins = 0
    total_episodes = 0

    for ep in range(n_eval_episodes):
        obs, info = env.reset()
        done = False
        episode_returns = []

        while not done:
            action, _ = ensemble.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            episode_returns.append(reward)

        ep_reward = np.sum(episode_returns)
        episode_rewards.append(ep_reward)

        if len(episode_returns) > 1:
            ep_sharpe = np.mean(episode_returns) / (np.std(episode_returns) + 1e-8)
        else:
            ep_sharpe = 0.0
        episode_sharpes.append(ep_sharpe)

        if ep_reward > 0:
            wins += 1
        total_episodes += 1

    cumsum_rewards = np.cumsum(episode_rewards)
    running_max = np.maximum.accumulate(cumsum_rewards)
    drawdown = (cumsum_rewards - running_max)
    max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0

    metrics = {
        'n_episodes': n_eval_episodes,
        'mean_reward': float(np.mean(episode_rewards)),
        'std_reward': float(np.std(episode_rewards)),
        'min_reward': float(np.min(episode_rewards)),
        'max_reward': float(np.max(episode_rewards)),
        'mean_sharpe': float(np.mean(episode_sharpes)),
        'std_sharpe': float(np.std(episode_sharpes)),
        'win_rate': float(wins / total_episodes),
        'max_drawdown': float(max_drawdown)
    }

    return metrics


def main():
    """Avalia ensemble vs modelos individuais."""

    # Paths
    mlp_e8_path = 'checkpoints/ppo_training/mlp/optuna/ppo_mlp_e8_optuna.zip'
    lstm_e8_path = 'checkpoints/ppo_training/lstm/optuna/ppo_lstm_e8_optuna.zip'
    output_dir = Path('results/model2/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("BLID-067: Avaliacao Ensemble E.9")
    logger.info("=" * 70)

    # Criar environment
    env = LSTMSignalEnvironment(mode='paper')
    n_episodes = 10

    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'phase': 'E.9_ensemble_voting',
        'n_eval_episodes': n_episodes,
        'models': {}
    }

    # 1. MLP individual (E.8)
    logger.info("\n[1/4] Avaliando MLP (E.8 Optuna)...")
    mlp_model = load_model(mlp_e8_path)
    mlp_metrics = evaluate_model(mlp_model, env, n_episodes)
    results['models']['mlp_e8'] = mlp_metrics
    logger.info(f"  Mean Sharpe: {mlp_metrics['mean_sharpe']:.4f}")
    logger.info(f"  Win Rate: {mlp_metrics['win_rate']:.2%}")

    # 2. LSTM individual (E.8)
    logger.info("\n[2/4] Avaliando LSTM (E.8 Optuna)...")
    lstm_model = load_model(lstm_e8_path)
    lstm_metrics = evaluate_model(lstm_model, env, n_episodes)
    results['models']['lstm_e8'] = lstm_metrics
    logger.info(f"  Mean Sharpe: {lstm_metrics['mean_sharpe']:.4f}")
    logger.info(f"  Win Rate: {lstm_metrics['win_rate']:.2%}")

    # 3. Ensemble Soft voting
    logger.info("\n[3/4] Avaliando Ensemble (Soft Voting)...")
    ensemble_soft = EnsembleVotingPPO(
        mlp_e8_path,
        lstm_e8_path,
        mlp_weight=0.48,
        lstm_weight=0.52,
        voting_method='soft'
    )
    ensemble_soft_metrics = evaluate_ensemble_model(
        ensemble_soft,
        env,
        n_episodes
    )
    results['models']['ensemble_soft_e9'] = ensemble_soft_metrics
    logger.info(f"  Mean Sharpe: {ensemble_soft_metrics['mean_sharpe']:.4f}")
    logger.info(f"  Win Rate: {ensemble_soft_metrics['win_rate']:.2%}")

    # 4. Ensemble Hard voting
    logger.info("\n[4/4] Avaliando Ensemble (Hard Voting)...")
    ensemble_hard = EnsembleVotingPPO(
        mlp_e8_path,
        lstm_e8_path,
        mlp_weight=0.48,
        lstm_weight=0.52,
        voting_method='hard'
    )
    ensemble_hard_metrics = evaluate_ensemble_model(
        ensemble_hard,
        env,
        n_episodes
    )
    results['models']['ensemble_hard_e9'] = ensemble_hard_metrics
    logger.info(f"  Mean Sharpe: {ensemble_hard_metrics['mean_sharpe']:.4f}")
    logger.info(f"  Win Rate: {ensemble_hard_metrics['win_rate']:.2%}")

    env.close()

    # Comparacao
    logger.info("\n" + "=" * 70)
    logger.info("COMPARACAO DE METRICAS")
    logger.info("=" * 70)

    comparison_data = {
        'MLP (E.8)': mlp_metrics,
        'LSTM (E.8)': lstm_metrics,
        'Ensemble Soft (E.9)': ensemble_soft_metrics,
        'Ensemble Hard (E.9)': ensemble_hard_metrics
    }

    # Sharpe comparison
    logger.info("\nSharpe Ratio:")
    for name, m in comparison_data.items():
        sharpe = m['mean_sharpe']
        logger.info(f"  {name:25s}: {sharpe:7.4f}")

    # Win Rate comparison
    logger.info("\nWin Rate:")
    for name, m in comparison_data.items():
        wr = m['win_rate']
        logger.info(f"  {name:25s}: {wr:6.2%}")

    # Melhoria do ensemble vs individuais
    avg_individual_sharpe = (mlp_metrics['mean_sharpe'] + lstm_metrics['mean_sharpe']) / 2
    ensemble_soft_sharpe = ensemble_soft_metrics['mean_sharpe']
    ensemble_hard_sharpe = ensemble_hard_metrics['mean_sharpe']

    improvement_soft = ((ensemble_soft_sharpe - avg_individual_sharpe) / (abs(avg_individual_sharpe) + 1e-8)) * 100
    improvement_hard = ((ensemble_hard_sharpe - avg_individual_sharpe) / (abs(avg_individual_sharpe) + 1e-8)) * 100

    logger.info(f"\nMelhoria de Sharpe vs media individual:")
    logger.info(f"  Soft Voting:  {improvement_soft:+.2f}%")
    logger.info(f"  Hard Voting:  {improvement_hard:+.2f}%")

    results['comparison'] = {
        'avg_individual_sharpe': float(avg_individual_sharpe),
        'ensemble_soft_sharpe': float(ensemble_soft_sharpe),
        'ensemble_hard_sharpe': float(ensemble_hard_sharpe),
        'improvement_soft_pct': float(improvement_soft),
        'improvement_hard_pct': float(improvement_hard)
    }

    # Salvar resultados
    output_file = output_dir / f"evaluate_ensemble_e9_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n✓ Resultados salvos em {output_file}")

    return results


if __name__ == '__main__':
    main()
