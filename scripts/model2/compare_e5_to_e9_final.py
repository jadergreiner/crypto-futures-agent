#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BLID-067: Comparacao Final E.5 -> E.9

Benchmark completo comparando todas as fases de evolucao:
  E.5: MACD features (22 features)
  E.6: Advanced indicators (26 features)
  E.7: Optuna hyperparameter search
  E.8: Retrain com best hyperparams
  E.9: Ensemble voting (MLP + LSTM)

Saida: Diagrama de melhoria + JSON com resultados finais.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import numpy as np
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


def evaluate_checkpoint(
    checkpoint_path: str,
    env: LSTMSignalEnvironment,
    n_episodes: int = 5
) -> Optional[Dict[str, float]]:
    """
    Avalia checkpoint PPO individual.

    Returns:
        Metricas ou None se checkpoint nao existir.
    """
    if not Path(checkpoint_path).exists():
        logger.warning(f"Checkpoint nao encontrado: {checkpoint_path}")
        return None

    try:
        model = PPO.load(checkpoint_path)
    except Exception as e:
        logger.error(f"Erro ao carregar {checkpoint_path}: {e}")
        return None

    episode_rewards = []
    episode_sharpes = []

    for _ in range(n_episodes):
        obs, info = env.reset()
        done = False
        episode_returns = []

        while not done:
            action, _ = model.predict(obs, deterministic=True)
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

    return {
        'mean_reward': float(np.mean(episode_rewards)),
        'std_reward': float(np.std(episode_rewards)),
        'mean_sharpe': float(np.mean(episode_sharpes)),
        'std_sharpe': float(np.std(episode_sharpes)),
        'win_rate': float(sum(1 for r in episode_rewards if r > 0) / len(episode_rewards))
    }


def evaluate_ensemble(
    checkpoint_mlp: str,
    checkpoint_lstm: str,
    env: LSTMSignalEnvironment,
    n_episodes: int = 5,
    voting_method: str = 'soft'
) -> Optional[Dict[str, float]]:
    """Avalia ensemble."""
    if not Path(checkpoint_mlp).exists() or not Path(checkpoint_lstm).exists():
        logger.warning(f"Checkpoints ensemble nao encontrados")
        return None

    try:
        ensemble = EnsembleVotingPPO(
            checkpoint_mlp,
            checkpoint_lstm,
            mlp_weight=0.48,
            lstm_weight=0.52,
            voting_method=voting_method
        )
    except Exception as e:
        logger.error(f"Erro ao criar ensemble: {e}")
        return None

    episode_rewards = []
    episode_sharpes = []

    for _ in range(n_episodes):
        obs, info = env.reset()
        done = False
        episode_returns = []

        while not done:
            action, _ = ensemble.predict(obs, deterministic=True)
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

    return {
        'mean_reward': float(np.mean(episode_rewards)),
        'std_reward': float(np.std(episode_rewards)),
        'mean_sharpe': float(np.mean(episode_sharpes)),
        'std_sharpe': float(np.std(episode_sharpes)),
        'win_rate': float(sum(1 for r in episode_rewards if r > 0) / len(episode_rewards))
    }


def create_progression_chart(phases: Dict[str, Dict]) -> str:
    """Cria diagrama ASCII de progresso."""
    chart = "\n╔════════════════════════════════════════════════════════════════════════╗\n"
    chart += "║           EVOLUCAO DE METRICAS E.5 -> E.9 (Sharpe Ratio)              ║\n"
    chart += "╚════════════════════════════════════════════════════════════════════════╝\n\n"

    # Extrair Sharpe de cada fase
    sharpes = {}
    for phase, metrics in phases.items():
        if metrics is not None:
            sharpes[phase] = metrics['mean_sharpe']
        else:
            sharpes[phase] = 0.0

    # Find baseline (E.5) para comparacao
    baseline = sharpes.get('E.5 (MACD+22F)', 0.0)

    for phase, sharpe in sharpes.items():
        if baseline > 0:
            improvement = ((sharpe - baseline) / baseline) * 100
            bar_length = int(max(0, improvement / 2))  # Scale para visualizacao
            bar = '█' * bar_length if improvement > 0 else '▓' * (-bar_length)
            direction = '↑' if improvement > 0 else '↓' if improvement < 0 else '='
        else:
            improvement = 0
            bar = ''
            direction = '='

        chart += f"{phase:25s} │ {sharpe:7.4f} │ {direction} {improvement:+6.2f}% │ {bar}\n"

    return chart


def main():
    """Benchmark completo E.5->E.9."""

    logger.info("=" * 75)
    logger.info("BLID-067: Benchmark Final E.5 -> E.9")
    logger.info("=" * 75)

    output_dir = Path('results/model2/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Criar environment
    env = LSTMSignalEnvironment(mode='paper')
    n_episodes = 5  # Rapido para benchmark

    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'benchmark': 'e5_to_e9_final',
        'n_eval_episodes': n_episodes,
        'phases': {}
    }

    # E.5: MACD + 22 features
    logger.info("\n[1/5] E.5 - MACD + 22 features...")
    e5_mlp = evaluate_checkpoint(
        'checkpoints/ppo_training/mlp/base/ppo_mlp_before_optuna.zip',
        env,
        n_episodes
    )
    e5_lstm = evaluate_checkpoint(
        'checkpoints/ppo_training/lstm/base/ppo_lstm_before_optuna.zip',
        env,
        n_episodes
    )
    if e5_mlp and e5_lstm:
        e5_avg = {
            'mean_reward': (e5_mlp['mean_reward'] + e5_lstm['mean_reward']) / 2,
            'mean_sharpe': (e5_mlp['mean_sharpe'] + e5_lstm['mean_sharpe']) / 2,
            'win_rate': (e5_mlp['win_rate'] + e5_lstm['win_rate']) / 2
        }
        results['phases']['E.5 (MACD+22F)'] = e5_avg
        logger.info(f"  ✓ Sharpe: {e5_avg['mean_sharpe']:.4f}")
    else:
        logger.warning("  ✗ E.5 checkpoints nao encontrados (esperado em producao)")
        results['phases']['E.5 (MACD+22F)'] = None

    # E.6: Advanced indicators + 26 features
    logger.info("\n[2/5] E.6 - Advanced indicators + 26 features...")
    e6_mlp = evaluate_checkpoint(
        'checkpoints/ppo_training/mlp/e6/ppo_mlp_e6_advanced.zip',
        env,
        n_episodes
    )
    e6_lstm = evaluate_checkpoint(
        'checkpoints/ppo_training/lstm/e6/ppo_lstm_e6_advanced.zip',
        env,
        n_episodes
    )
    if e6_mlp and e6_lstm:
        e6_avg = {
            'mean_reward': (e6_mlp['mean_reward'] + e6_lstm['mean_reward']) / 2,
            'mean_sharpe': (e6_mlp['mean_sharpe'] + e6_lstm['mean_sharpe']) / 2,
            'win_rate': (e6_mlp['win_rate'] + e6_lstm['win_rate']) / 2
        }
        results['phases']['E.6 (26F)'] = e6_avg
        logger.info(f"  ✓ Sharpe: {e6_avg['mean_sharpe']:.4f}")
    else:
        logger.warning("  ✗ E.6 checkpoints nao encontrados")
        results['phases']['E.6 (26F)'] = None

    # E.7/E.8: Optuna optimized (MLP + LSTM individual)
    logger.info("\n[3/5] E.7/E.8 - Optuna Optimized MLP...")
    e8_mlp = evaluate_checkpoint(
        'checkpoints/ppo_training/mlp/optuna/ppo_mlp_e8_optuna.zip',
        env,
        n_episodes
    )
    results['phases']['E.8 (MLP Optuna)'] = e8_mlp
    if e8_mlp:
        logger.info(f"  ✓ Sharpe: {e8_mlp['mean_sharpe']:.4f}")

    logger.info("\n[4/5] E.7/E.8 - Optuna Optimized LSTM...")
    e8_lstm = evaluate_checkpoint(
        'checkpoints/ppo_training/lstm/optuna/ppo_lstm_e8_optuna.zip',
        env,
        n_episodes
    )
    results['phases']['E.8 (LSTM Optuna)'] = e8_lstm
    if e8_lstm:
        logger.info(f"  ✓ Sharpe: {e8_lstm['mean_sharpe']:.4f}")

    # E.9: Ensemble Voting
    logger.info("\n[5/5] E.9 - Ensemble Voting (Soft)...")
    e9_ensemble = evaluate_ensemble(
        'checkpoints/ppo_training/mlp/optuna/ppo_mlp_e8_optuna.zip',
        'checkpoints/ppo_training/lstm/optuna/ppo_lstm_e8_optuna.zip',
        env,
        n_episodes,
        voting_method='soft'
    )
    results['phases']['E.9 (Ensemble Soft)'] = e9_ensemble
    if e9_ensemble:
        logger.info(f"  ✓ Sharpe: {e9_ensemble['mean_sharpe']:.4f}")

    env.close()

    # Print progression chart
    logger.info(create_progression_chart(results['phases']))

    # Summary statistics
    logger.info("\n" + "=" * 75)
    logger.info("SUMMARY")
    logger.info("=" * 75)

    valid_phases = {k: v for k, v in results['phases'].items() if v is not None}
    if valid_phases:
        sharpes = [m['mean_sharpe'] for m in valid_phases.values()]
        logger.info(f"\nFases com metricas: {len(valid_phases)}/{len(results['phases'])}")
        logger.info(f"Sharpe min: {min(sharpes):.4f}")
        logger.info(f"Sharpe max: {max(sharpes):.4f}")
        logger.info(f"Melhoria geral: {((max(sharpes) - min(sharpes)) / (min(sharpes) + 1e-8) * 100):.2f}%")

    # Salvar resultados
    output_file = output_dir / f"compare_e5_to_e9_final_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n✓ Resultados salvos em {output_file}")

    return results


if __name__ == '__main__':
    main()
