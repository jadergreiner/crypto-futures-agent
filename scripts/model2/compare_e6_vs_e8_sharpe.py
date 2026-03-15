"""
BLID-066: Comparacao E.6 (Baseline) vs E.8 (Optuna) — Phase E.8

Carrega modelos MLP/LSTM de E.6 (26 features, hyperparams padrao) e
E.8 (26 features, hyperparams otimizados) e compara performance em dados historicos.

Execucao:
    python scripts/model2/compare_e6_vs_e8_sharpe.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# Stable Baselines 3
from stable_baselines3 import PPO

# Project modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agent.lstm_environment import LSTMSignalEnvironment


def load_model(checkpoint_path):
    """Carregar modelo PPO de checkpoint."""
    if not Path(checkpoint_path).exists():
        raise FileNotFoundError(f"Checkpoint nao encontrado: {checkpoint_path}")
    return PPO.load(checkpoint_path)


def evaluate_model(model, env, n_eval_episodes=10):
    """
    Avaliar modelo em ambiente e retornar metricas.

    Returns:
        dict com mean_reward, win_rate, max_drawdown, etc.
    """
    all_rewards = []
    all_returns = []
    all_drawdowns = []

    for episode in range(n_eval_episodes):
        obs, info = env.reset()
        episode_reward = 0
        episode_trades = 0
        episode_wins = 0
        peak = 0
        drawdown = 0

        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            episode_reward += reward

            # Simular win/drawdown metrics
            if reward > 0:
                episode_wins += 1

            peak = max(peak, episode_reward)
            current_dd = peak - episode_reward
            drawdown = max(drawdown, current_dd)

        all_rewards.append(episode_reward)
        all_returns.append(episode_reward)

        if episode_trades > 0:
            all_drawdowns.append(drawdown)

    # Calcular Sharpe ratio (simplificado)
    returns = np.array(all_rewards)
    sharpe = np.mean(returns) / (np.std(returns) + 1e-8) if len(returns) > 1 else 0

    metrics = {
        'mean_reward': float(np.mean(all_rewards)),
        'std_reward': float(np.std(all_rewards)),
        'sharpe_ratio': float(sharpe),
        'max_reward': float(np.max(all_rewards)),
        'min_reward': float(np.min(all_rewards)),
        'max_drawdown': float(np.max(all_drawdowns)) if all_drawdowns else 0,
    }

    return metrics


def find_model_paths():
    """
    Localizar caminhos de modelos E.6 e E.8.

    Estrutura esperada:
    - E.6 baseline: checkpoints/ppo_training/{mlp,lstm}/ppo_*.zip
    - E.8 optuna: checkpoints/ppo_training/{mlp,lstm}/optuna/ppo_*_e8_optuna.zip
    """
    checkpoint_base = Path('checkpoints/ppo_training')

    models = {}

    for model_type in ['mlp', 'lstm']:
        model_type_path = checkpoint_base / model_type

        # E.6 baseline (mais recente em pasta raiz)
        e6_files = sorted(model_type_path.glob('ppo_*.zip'))
        e6_path = None
        for f in e6_files:
            if 'optuna' not in f.name and 'e8' not in f.name:
                e6_path = f
                break

        # E.8 optuna (em pasta optuna)
        optuna_path = model_type_path / 'optuna'
        e8_files = sorted(optuna_path.glob('ppo_*_e8_optuna.zip')) if optuna_path.exists() else []
        e8_path = e8_files[0] if e8_files else None

        if e6_path or e8_path:
            models[model_type] = {
                'e6_path': str(e6_path) if e6_path else None,
                'e8_path': str(e8_path) if e8_path else None,
            }

    return models


def compare_models():
    """Executar comparacao E.6 vs E.8 para ambos os modelos."""
    print("\n" + "="*70)
    print("[E.8] Comparacao E.6 (Baseline) vs E.8 (Optuna)")
    print("="*70)

    model_paths = find_model_paths()

    if not model_paths:
        print("[E.8] ERRO: Nenhum modelo encontrado em checkpoints/")
        return None

    print(f"[E.8] Modelos encontrados: {list(model_paths.keys())}")

    comparison_results = {
        'phase': 'E.8',
        'timestamp': datetime.now().isoformat(),
        'objective': 'Compare E.6 baseline vs E.8 Optuna hyperparams',
        'models': [],
    }

    env = LSTMSignalEnvironment()

    for model_type, paths in model_paths.items():
        print(f"\n[E.8] Avaliando {model_type.upper()}...")

        e6_path = paths.get('e6_path')
        e8_path = paths.get('e8_path')

        if not e6_path:
            print(f"[E.8] AVISO: E.6 baseline nao encontrado para {model_type}")
            continue

        if not e8_path:
            print(f"[E.8] AVISO: E.8 optuna nao encontrado para {model_type}")
            continue

        # Carregar modelos
        try:
            model_e6 = load_model(e6_path)
            model_e8 = load_model(e8_path)
            print(f"[E.8] Modelos carregados: {model_type}")
        except Exception as e:
            print(f"[E.8] ERRO ao carregar modelos: {e}")
            continue

        # Avaliar
        print(f"[E.8] Avaliando E.6 baseline ({e6_path})...")
        metrics_e6 = evaluate_model(model_e6, env, n_eval_episodes=5)

        print(f"[E.8] Avaliando E.8 optuna ({e8_path})...")
        metrics_e8 = evaluate_model(model_e8, env, n_eval_episodes=5)

        # Calcular melhoria
        sharpe_improvement = (
            (metrics_e8['sharpe_ratio'] - metrics_e6['sharpe_ratio'])
            / (metrics_e6['sharpe_ratio'] + 1e-8) * 100
        ) if metrics_e6['sharpe_ratio'] != 0 else 0

        reward_improvement = (
            (metrics_e8['mean_reward'] - metrics_e6['mean_reward'])
            / (abs(metrics_e6['mean_reward']) + 1e-8) * 100
        )

        result = {
            'model_type': model_type,
            'e6_baseline': {
                'path': e6_path,
                'metrics': metrics_e6,
            },
            'e8_optuna': {
                'path': e8_path,
                'metrics': metrics_e8,
            },
            'improvement': {
                'sharpe_ratio_pct': round(sharpe_improvement, 2),
                'mean_reward_pct': round(reward_improvement, 2),
                'max_drawdown_reduction_pct': round(
                    (metrics_e6['max_drawdown'] - metrics_e8['max_drawdown'])
                    / (metrics_e6['max_drawdown'] + 1e-8) * 100,
                    2
                ) if metrics_e6['max_drawdown'] > 0 else 0,
            },
        }

        comparison_results['models'].append(result)

        # Imprimir resultado
        print(f"\n[E.8] === RESULTADO PARA {model_type.upper()} ===")
        print(f"[E.8] E.6 Sharpe: {metrics_e6['sharpe_ratio']:.4f}")
        print(f"[E.8] E.8 Sharpe: {metrics_e8['sharpe_ratio']:.4f}")
        print(f"[E.8] Melhoria Sharpe: {sharpe_improvement:.2f}%")
        print(f"[E.8] Melhoria Reward: {reward_improvement:.2f}%")

    env.close()

    # Determinar melhor modelo
    if comparison_results['models']:
        best_model = max(
            comparison_results['models'],
            key=lambda x: x['e8_optuna']['metrics']['sharpe_ratio']
        )
        comparison_results['best_model'] = best_model['model_type']
        comparison_results['best_sharpe'] = best_model['e8_optuna']['metrics']['sharpe_ratio']

        print(f"\n[E.8] Melhor modelo (E.8 Optuna): {best_model['model_type'].upper()}")
        print(f"[E.8] Melhor Sharpe: {best_model['e8_optuna']['metrics']['sharpe_ratio']:.4f}")

    # Salvar resultado
    output_dir = Path('results/model2/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'phase_e8_comparison_e6_vs_e8_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump(comparison_results, f, indent=2)

    print(f"\n[E.8] Resultado salvo em: {output_file}")

    return comparison_results


if __name__ == '__main__':
    compare_models()
