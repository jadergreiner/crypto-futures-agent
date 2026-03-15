"""E.2: Tests for the LSTM policy architecture."""

import pytest
import torch
import numpy as np
import gymnasium as gym

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from agent.lstm_policy import CustomLSTMFeaturesExtractor, LSTMPolicy


class DummyLSTMEnv(gym.Env):
    """Dummy environment that outputs a 2D sequence state for testing LSTM."""
    
    def __init__(self, seq_len=10, n_features=20):
        super().__init__()
        self.seq_len = seq_len
        self.n_features = n_features
        
        # 2D Observation Space: (seq_len, n_features)
        self.observation_space = gym.spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(seq_len, n_features), 
            dtype=np.float32
        )
        
        # Simple discrete action space
        self.action_space = gym.spaces.Discrete(2)
        
        self.step_count = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.step_count = 0
        return self.observation_space.sample(), {}

    def step(self, action):
        self.step_count += 1
        obs = self.observation_space.sample()
        reward = float(action)  # Dummy reward
        terminated = self.step_count >= 10
        truncated = False
        return obs, reward, terminated, truncated, {}


def test_custom_lstm_features_extractor_shape():
    """Test if CustomLSTMFeaturesExtractor produces correct output shapes."""
    seq_len, n_features = 10, 20
    batch_size = 32
    features_dim = 128
    
    # Mock observation space structure
    obs_space = gym.spaces.Box(
        low=-np.inf, high=np.inf, shape=(seq_len, n_features), dtype=np.float32
    )
    
    extractor = CustomLSTMFeaturesExtractor(
        observation_space=obs_space,
        features_dim=features_dim,
        lstm_hidden_size=64,
        lstm_num_layers=1
    )
    
    # Dummy batched sequence: (batch_size, seq_len, n_features)
    sample_obs = torch.randn(batch_size, seq_len, n_features)
    
    # Forward pass
    output = extractor(sample_obs)
    
    assert output.shape == (batch_size, features_dim), \
        f"Expected output shape {(batch_size, features_dim)}, got {output.shape}"


def test_lstm_policy_initialization():
    """Test if LSTMPolicy integrates seamlessly with PPO and a sequence environment."""
    
    # Create the dummy batched environment
    env = make_vec_env(lambda: DummyLSTMEnv(seq_len=10, n_features=20), n_envs=1)
    
    try:
        # Pass LSTMPolicy to PPO
        # LSTMPolicy natively sets the features_extractor_class=CustomLSTMFeaturesExtractor
        model = PPO(LSTMPolicy, env, n_steps=64, batch_size=64, verbose=0)
        
        # Perform a minimal training run to ensure forward/backward passes don't crash
        model.learn(total_timesteps=64)
        
    except Exception as e:
        pytest.fail(f"LSTMPolicy integration failed with: {str(e)}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
