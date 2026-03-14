"""
Criar checkpoint PPO dummy para teste de RL enhancement.

Simula um modelo PPO treinado para validação de integração.
Usa TensorFlow backend (leve) em vez de PyTorch.
"""

import sys
import json
import pickle
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def create_dummy_ppo_model():
    """Criar modelo PPO dummy para teste."""
    try:
        import os
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TF warnings

        from stable_baselines3 import PPO
        from stable_baselines3.ppo import MlpPolicy
        import gymnasium as gym
        import numpy as np

        print("[PPO] Criando ambiente dummy...")
        # Criar ambiente fake (5 obs, 3 ações = Discrete)
        class FakeEnv(gym.Env):
            def __init__(self):
                self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32)
                self.action_space = gym.spaces.Discrete(3)
                self.step_count = 0

            def reset(self, seed=None):
                return np.random.randn(5).astype(np.float32), {}

            def step(self, action):
                self.step_count += 1
                obs = np.random.randn(5).astype(np.float32)
                reward = float(np.random.randn()) * 0.1
                terminated = self.step_count > 100
                truncated = False
                return obs, reward, terminated, truncated, {}

        env = FakeEnv()

        print("[PPO] Treinando model PPO com 10k steps...")
        # Treinar modelo real (rápido com 10k steps)
        model = PPO(
            MlpPolicy,
            env,
            learning_rate=3e-4,
            n_steps=128,
            batch_size=32,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            verbose=0,
        )

        model.learn(total_timesteps=10000)

        # Salvar modelo
        checkpoint_path = REPO_ROOT / "checkpoints" / "ppo_training" / "ppo_model"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        model.save(str(checkpoint_path))

        print("[PPO] Modelo salvo: {}".format(checkpoint_path))

        # Also create a .pkl wrapper for compatibility
        model_dict = {
            "model": model,
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "timesteps": 10000,
                "timeframe": "H4",
            }
        }

        pkl_path = checkpoint_path.parent / "ppo_model.pkl"
        with open(pkl_path, 'wb') as f:
            pickle.dump(model_dict, f)

        print("[PPO] Pickle salvo: {}".format(pkl_path))

        # Verify can load
        print("[PPO] Testando carregamento...")
        loaded_model = PPO.load(str(checkpoint_path))
        print("[PPO] OK - Modelo carregado com sucesso")

        # Test prediction
        obs, _ = env.reset()
        action, _ = loaded_model.predict(obs, deterministic=True)
        print("[PPO] OK - Teste de predicao: action={}".format(action))
    except ImportError as e:
        print(f"[PPO] ⚠️ Dependência não disponível: {e}")
        print("[PPO] Usando fallback: criar modelo fake via pickle")

        # Fallback: criar wrapper fake que funciona como modelo
        checkpoint_path = REPO_ROOT / "checkpoints" / "ppo_training"
        checkpoint_path.mkdir(parents=True, exist_ok=True)

        class FakePPOModel:
            """Modelo PPO fake para fallback."""
            def predict(self, obs, deterministic=False):
                # Retorna ação determinística baseada em features
                # Se close (log) > 11 (preço alto), sugere SHORT
                # Se close < 10 (preço baixo), sugere LONG
                # Senão HOLD
                import numpy as np
                close_log = obs[0] if isinstance(obs, (list, np.ndarray)) else 0
                if close_log > 11:
                    return 2, None  # SHORT
                elif close_log < 10:
                    return 1, None  # LONG
                else:
                    return 0, None  # HOLD

        fake_model = FakePPOModel()
        pkl_path = checkpoint_path / "ppo_model.pkl"
        with open(pkl_path, 'wb') as f:
            pickle.dump(fake_model, f)

        print("[PPO] OK - Modelo fake criado: {}".format(pkl_path))

        return {
            "status": "ok_fallback",
            "pkl_path": str(pkl_path),
            "message": "Modelo PPO fake criado (sem SB3)"
        }


if __name__ == '__main__':
    print("=" * 60)
    print("CREATE PPO CHECKPOINT FOR RL ENHANCEMENT TESTING")
    print("=" * 60)

    result = create_dummy_ppo_model()

    print("\nResultado:")
    print(json.dumps(result, indent=2))

    sys.exit(0 if result['status'].startswith('ok') else 1)
