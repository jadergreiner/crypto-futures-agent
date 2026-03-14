
import json
from pathlib import Path

class PPOModelWrapper:
    def __init__(self, config_path):
        with open(config_path) as f:
            self.config = json.load(f)
        self.model_type = "PPO"
        
    def predict(self, observation, deterministic=True):
        # Predição baseada em heurística simples
        import numpy as np
        if isinstance(observation, (list, tuple)):
            obs = np.array(observation)
        else:
            obs = observation
        
        # Usar primeira feature (log close) para decisão
        close_log = float(obs[0]) if len(obs) > 0 else 10.5
        
        # Heurística: alto preço -> SHORT, baixo -> LONG
        if close_log > 11.2:
            action = 2  # SHORT
            prob = 0.75
        elif close_log < 10.5:
            action = 1  # LONG
            prob = 0.75
        else:
            action = 0  # HOLD
            prob = 0.6
        
        # _states é tuple requirement de SB3 compatibility
        return action, None
