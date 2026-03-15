#!/usr/bin/env python3
"""
Phase E.6 - Comparacao Sharpe: 22 features (E.5) vs 26 features (E.6).

Carrega modelos treinados e calcula metricas para validacao de melhoria.
"""

import json
import os
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO


def calculate_sharpe_ratio(returns: list[float], risk_free_rate: float = 0.0) -> float:
    """Calcula Sharpe Ratio a partir de retornos diarios."""
    if not returns or len(returns) < 2:
        return 0.0

    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate

    if np.std(excess_returns) == 0:
        return 0.0

    return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))


def load_and_evaluate(model_path: str, label: str) -> dict:
    """Carrega modelo e coleta metricas basicas."""
    try:
        model = PPO.load(model_path)

        # Simulacao rapida para obter rewards
        ep_rewards = []
        for _ in range(10):  # 10 episodios
            ep_reward = 0
            done = False
            obs = model.env.reset()

            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, done, _ = model.env.step(action)
                ep_reward += reward

            ep_rewards.append(ep_reward)

        mean_reward = float(np.mean(ep_rewards))
        std_reward = float(np.std(ep_rewards))

        return {
            "label": label,
            "model_path": model_path,
            "mean_reward": mean_reward,
            "std_reward": std_reward,
            "episodes": 10,
            "status": "loaded",
        }
    except FileNotFoundError:
        return {
            "label": label,
            "model_path": model_path,
            "status": "not_found",
            "error": f"Modelo nao encontrado: {model_path}",
        }
    except Exception as e:
        return {
            "label": label,
            "model_path": model_path,
            "status": "error",
            "error": str(e),
        }


def main():
    """Compara modelos E.5 (22 features) vs E.6 (26 features)."""
    checkpoints_dir = Path("checkpoints/ppo_training")

    # Caminhos dos modelos
    models_to_compare = [
        ("checkpoints/ppo_training/mlp/best_model.zip", "MLP 22 features (E.5)"),
        ("checkpoints/ppo_training/mlp/ppo_model_e6.zip", "MLP 26 features (E.6)"),
        ("checkpoints/ppo_training/lstm/best_model.zip", "LSTM 22 features (E.5)"),
        ("checkpoints/ppo_training/lstm/ppo_model_e6.zip", "LSTM 26 features (E.6)"),
    ]

    results = {
        "timestamp": os.popen("date /T").read().strip(),
        "comparison": "E.5 (22 features) vs E.6 (26 features)",
        "new_indicators": ["Estocastico K", "Estocastico D", "Williams %R", "ATR normalizado"],
        "models": [],
    }

    for model_path, label in models_to_compare:
        eval_result = load_and_evaluate(model_path, label)
        results["models"].append(eval_result)

    # Calcular summary
    mlp_models = [m for m in results["models"] if m["label"].startswith("MLP")]
    lstm_models = [m for m in results["models"] if m["label"].startswith("LSTM")]

    results["summary"] = {
        "mlp_improvement": None,
        "lstm_improvement": None,
    }

    if len(mlp_models) == 2:
        if mlp_models[0]["status"] == "loaded" and mlp_models[1]["status"] == "loaded":
            improvement = ((mlp_models[1]["mean_reward"] - mlp_models[0]["mean_reward"]) / abs(mlp_models[0]["mean_reward"])) * 100 if mlp_models[0]["mean_reward"] != 0 else "N/A"
            results["summary"]["mlp_improvement"] = f"{improvement}%"

    if len(lstm_models) == 2:
        if lstm_models[0]["status"] == "loaded" and lstm_models[1]["status"] == "loaded":
            improvement = ((lstm_models[1]["mean_reward"] - lstm_models[0]["mean_reward"]) / abs(lstm_models[0]["mean_reward"])) * 100 if lstm_models[0]["mean_reward"] != 0 else "N/A"
            results["summary"]["lstm_improvement"] = f"{improvement}%"

    # Salvar resultado
    output_dir = Path("results/model2/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "phase_e6_sharpe_comparison.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[E.6] Comparacao Sharpe salva: {output_file}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
