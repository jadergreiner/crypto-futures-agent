"""E.2: LSTM Policy Architecture for Stable Baselines 3.

Provides a custom feature extractor and policy class that uses an LSTM
to process sequences of observations shaped (seq_len, n_features).
"""

import gymnasium as gym
import torch
from torch import nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.policies import ActorCriticPolicy

class CustomLSTMFeaturesExtractor(BaseFeaturesExtractor):
    """Custom feature extractor that processes continuous state observation sequences through an LSTM.
    
    Expected input shape: (batch_size, seq_len, n_features)
    Output shape: (batch_size, features_dim)
    """
    def __init__(
        self,
        observation_space: gym.spaces.Box,
        features_dim: int = 128,
        lstm_hidden_size: int = 64,
        lstm_num_layers: int = 1,
    ):
        super().__init__(observation_space, features_dim)
        
        # Determine sequence characteristics from the observation space shape
        # In our LSTMSignalEnvironment, shape could be (seq_len, n_features)
        if len(observation_space.shape) == 2:
            self.seq_len, self.n_features = observation_space.shape
        else:
            raise ValueError(
                f"CustomLSTMFeaturesExtractor requires a 2D observation space shape (seq_len, n_features). "
                f"Got shape: {observation_space.shape}."
            )

        # Build LSTM layer (64 units context)
        self.lstm = nn.LSTM(
            input_size=self.n_features,
            hidden_size=lstm_hidden_size,
            num_layers=lstm_num_layers,
            batch_first=True
        )
        
        # Final fully connected layer
        self.linear = nn.Sequential(
            nn.Linear(lstm_hidden_size, features_dim),
            nn.ReLU()
        )

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        """Process observation sequence to extract final latent state.
        
        Args:
            observations: Tensor of shape (batch_size, seq_len, n_features).
        
        Returns:
            Tensor of shape (batch_size, features_dim).
        """
        # LSTM module expects float32
        observations = observations.float()

        # Output shape is (batch_size, seq_len, lstm_hidden_size)
        lstm_out, _ = self.lstm(observations)
        
        # We only care about the last output in the sequence
        last_out = lstm_out[:, -1, :]
        
        # Pass the last LSTM state through our linear layers
        features = self.linear(last_out)
        
        return features


class LSTMPolicy(ActorCriticPolicy):
    """Actor Critic Policy subclass pre-configured to utilize the CustomLSTMFeaturesExtractor.
    
    Simplifies policy instantiation during training setup by avoiding verbose policy_kwargs defaults.
    """
    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule,
        net_arch=None,
        activation_fn=nn.Tanh,
        *args,
        **kwargs,
    ):
        # Inject the custom LSTM feature extractor if no other was provided
        policy_kwargs = kwargs.get("policy_kwargs", {})
        if "features_extractor_class" not in policy_kwargs:
            kwargs["features_extractor_class"] = CustomLSTMFeaturesExtractor
            
        super().__init__(
            observation_space,
            action_space,
            lr_schedule,
            net_arch=net_arch,
            activation_fn=activation_fn,
            *args,
            **kwargs,
        )
