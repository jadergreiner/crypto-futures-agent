"""
Treinamento PPO LSTM vs MLP — Model 2.0 RL Training Pipeline

Treina modelo PPO com política MLP padrão ou com memória LSTM personalizada.
Faz uso do `LSTMSignalEnvironment` e `LSTMPolicy`.
"""

import argparse
import json
import sqlite3
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from time import perf_counter
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import MODEL2_DB_PATH
from agent.lstm_policy import LSTMPolicy
from agent.lstm_environment import LSTMSignalEnvironment

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class PPOLstmTrainer:
    def __init__(
        self,
        model2_db_path: Path,
        checkpoint_dir: Optional[Path] = None,
        timeframe: str = "H4",
        policy_type: str = "mlp"
    ):
        self.model2_db_path = Path(model2_db_path)
        self.checkpoint_dir = Path(checkpoint_dir or (REPO_ROOT / "checkpoints" / "ppo_training"))
        self.timeframe = timeframe
        self.policy_type = policy_type

        # Crie diretório separado para não sobrescrever
        self.checkpoint_dir = self.checkpoint_dir / policy_type
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.episodes_data: Optional[List[Dict[str, Any]]] = None
        self.obs_data: Optional[List[Any]] = None
        self.rewards_data: Optional[np.ndarray] = None

    def load_episodes_from_db(self) -> Dict[str, Any]:
        """Carregar episódios de treinamento do banco."""
        try:
            conn = sqlite3.connect(str(self.model2_db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id, episode_key, cycle_run_id, execution_id,
                    symbol, timeframe, status, event_timestamp,
                    label, reward_proxy, features_json, target_json,
                    created_at
                FROM training_episodes
                WHERE timeframe = ?
                ORDER BY created_at ASC
            """, (self.timeframe,))
            episodes = cursor.fetchall()
            conn.close()

            symbols_set = set()
            labels_dict: Dict[str, int] = {}

            if episodes:
                self.episodes_data = [dict(row) for row in episodes]
                for ep in episodes:
                    symbols_set.add(ep['symbol'])
                    labels_dict[ep['label']] = labels_dict.get(ep['label'], 0) + 1

            result: Dict[str, Any] = {
                "status": "ok",
                "total_episodes": len(episodes), 
                "timeframe": self.timeframe, 
                "symbols": list(symbols_set), 
                "labels": labels_dict
            }

            logger.info(f"[PPO-{self.policy_type.upper()}] Carregados {len(episodes)} episódios")
            return result
        except Exception as e:
            logger.error(f"[PPO-{self.policy_type.upper()}] Erro DB: {e}")
            return {"status": "error", "error": str(e)}

    def episodes_to_training_dataset(self) -> Dict[str, Any]:
        if not self.episodes_data:
            return {"status": "error", "error": "No episodes loaded"}

        try:
            observations = []
            rewards = []

            for ep in self.episodes_data:
                features = {}
                if ep['features_json']:
                    try:
                        features = json.loads(ep['features_json'])
                    except json.JSONDecodeError:
                        pass

                obs = self._build_observation(features, ep)
                reward = self._compute_reward(ep, features)
                
                if obs is not None:
                    observations.append(obs)
                    rewards.append(reward)

            # Manter observations como lista de dicts ou flat arrays, trataremos no env.
            self.obs_data = observations
            self.rewards_data = np.array(rewards, dtype=np.float32)

            result = {
                "status": "ok",
                "samples_count": len(observations),
                "mean_reward": float(np.mean(self.rewards_data)),
            }
            logger.info(f"[PPO-{self.policy_type.upper()}] Dataset preparado: {len(observations)} samples")
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _build_observation(self, features: Dict[str, Any], episode: Dict[str, Any]) -> Any:
        return features

    def _compute_reward(self, episode: Dict[str, Any], features: Dict[str, Any]) -> float:
        if episode.get('reward_proxy') is not None:
            return float(episode['reward_proxy'])
        label = episode.get('label', 'context')
        if label == 'win': return 1.0
        elif label == 'loss': return -0.5
        return 0.1

    def train(self, timesteps: int = 10000) -> Dict[str, Any]:
        from stable_baselines3 import PPO
        from gymnasium.spaces import Box, Discrete, Dict as GymDict
        import gymnasium as gym

        if not self.obs_data:
            return {"status": "error", "error": "No training data"}

        class HistoricalDataEnv(gym.Env):
            def __init__(self, observations, rewards, max_steps=100):
                self.observations = observations
                self.rewards = rewards
                self.max_steps = max_steps
                self.current_step = 0
                self.start_idx = 0
                
                # Definir Box generico pra satisfazer SB3 se não for enrolado em wrapper especial
                self.observation_space = Box(low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32)
                self.action_space = Discrete(3)
                
            def reset(self, seed=None):
                super().reset(seed=seed)
                self.current_step = 0
                idx = np.random.randint(0, max(1, len(self.observations) - self.max_steps))
                self.start_idx = idx
                return self.observations[idx], {}
                
            def step(self, action):
                self.current_step += 1
                idx = min(self.start_idx + self.current_step, len(self.observations) - 1)
                base_reward = self.rewards[idx] if idx < len(self.rewards) else 0.0
                
                action_bonus = 0.0
                if action == 1 and base_reward > 0.5: action_bonus = 0.1
                elif action == 2 and base_reward < -0.5: action_bonus = 0.1
                
                terminated = self.current_step >= self.max_steps
                truncated = idx >= len(self.observations) - 1
                obs = self.observations[idx] if idx < len(self.observations) else self.observations[-1]
                
                return obs, base_reward + action_bonus, terminated, truncated, {}

        # 1. Base Environment
        env = HistoricalDataEnv(self.obs_data, self.rewards_data, max_steps=100)
        
        # 2. Wrapper
        use_lstm = (self.policy_type == "lstm")
        env = LSTMSignalEnvironment(env, seq_len=10, flatten_fallback=not use_lstm)

        logger.info(f"[PPO-{self.policy_type.upper()}] Usando observacao: {env.observation_space}")

        policy_class = LSTMPolicy if use_lstm else 'MlpPolicy'
        policy_kwargs = {}
        if not use_lstm:
            policy_kwargs = dict(net_arch=dict(pi=[128, 128], vf=[128, 128]))

        model = PPO(
            policy_class,
            env,
            learning_rate=0.0003,
            n_steps=128,
            batch_size=32,
            n_epochs=10,
            gamma=0.99,
            policy_kwargs=policy_kwargs,
            verbose=1,
            seed=42,
            device='cpu'
        )

        logger.info(f"[PPO-{self.policy_type.upper()}] Iniciando treino...")
        start_time = perf_counter()
        model.learn(total_timesteps=timesteps)
        elapsed = perf_counter() - start_time

        model_path = self.checkpoint_dir / f"ppo_model_{self.policy_type}"
        model.save(str(model_path))
        
        return {
            "status": "ok",
            "policy": self.policy_type,
            "timesteps": timesteps,
            "duration_secs": elapsed,
            "model_path": str(model_path)
        }

def main():
    parser = argparse.ArgumentParser(description='Treinamento comparativo PPO LSTM vs MLP')
    parser.add_argument('--policy', type=str, choices=['mlp', 'lstm'], default='mlp', help='Tipos de politica a treinar')
    parser.add_argument('--timesteps', type=int, default=10000, help='Timesteps de treino')
    parser.add_argument('--model2-db-path', type=Path, default=MODEL2_DB_PATH, help='Caminho banco de dados m2')
    
    args = parser.parse_args()
    
    trainer = PPOLstmTrainer(
        model2_db_path=args.model2_db_path,
        policy_type=args.policy
    )
    
    trainer.load_episodes_from_db()
    trainer.episodes_to_training_dataset()
    res = trainer.train(timesteps=args.timesteps)
    
    print(json.dumps(res, indent=2))
    return 0 if res.get('status') == 'ok' else 1

if __name__ == '__main__':
    sys.exit(main())
