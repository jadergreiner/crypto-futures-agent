#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script base para treinamento PPO com BacktestEnvironment.

Configuracao PPO:
- Model: PPO (Proximal Policy Optimization)
- Framework: Stable-Baselines3 + PyTorch
- Environment: BacktestEnvironment (deterministico)
- Data: OGNUSDT + 1000PEPEUSDT H4 (800 treino + 200 validacao)
"""

import logging
import os
import json
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from typing import Optional

# Imports ML
try:
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from gymnasium import Env
    HAS_ML = True
except ImportError as e:
    print(f"[ERROR] Erro ao importar bibliotecas ML: {e}")
    HAS_ML = False

# Imports locais
from backtest.backtest_environment import BacktestEnvironment
from backtest.data_cache import ParquetCache
from config.symbols import SYMBOLS
from config.ppo_config import get_ppo_config, PPOConfig

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)


class PPOTrainer:
    """Treinador PPO para agente de trading."""

    def __init__(self, config: Optional[PPOConfig] = None,
                 checkpoint_dir: str = 'checkpoints/ppo_training',
                 log_dir: str = 'logs/ppo_training'):
        """
        Inicializa treinador.

        Args:
            config: PPOConfig (opcional, usa phase4 default)
            checkpoint_dir: Diretorio para salvar checkpoints
            log_dir: Diretorio para logs
        """
        self.config = config or get_ppo_config("phase4")
        self.checkpoint_dir = Path(checkpoint_dir)
        self.log_dir = Path(log_dir)
        self.cache = ParquetCache(db_path='crypto_agent.db', cache_dir='backtest/cache')

        # Criar diretorios
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"PPOTrainer inicializado com config Phase 4")
        logger.info(f"  Learning Rate: {self.config.learning_rate}")
        logger.info(f"  Batch Size: {self.config.batch_size}")
        logger.info(f"  N Steps: {self.config.n_steps}")
        logger.info(f"  N Epochs: {self.config.n_epochs}")
        logger.info(f"  Entropy Coef: {self.config.ent_coef}")
        logger.info(f"  Checkpoints: {self.checkpoint_dir}")
        logger.info(f"  Logs: {self.log_dir}")

    def prepare_environment(self, symbol: str) -> tuple:
        """
        Prepara ambiente para simbolo com VecNormalize.

        Args:
            symbol: Simbolo (ex: 'OGNUSDT')

        Returns:
            Tupla (BacktestEnvironment, VecNormalize)
        """
        logger.info(f"Preparando ambiente para {symbol}...")

        try:
            # Carregar dados do cache
            h4_data = self.cache.load_ohlcv_for_symbol(symbol, timeframe='4h')

            if h4_data is None or h4_data.empty:
                raise ValueError(f"Dados nao encontrados para {symbol}")

            logger.info(f"Carregados {len(h4_data)} candles H4 para {symbol}")

            # Preparar observation space com features
            env_data = {
                'h4': h4_data,
                'h1': pd.DataFrame(),  # Placeholder
                'd1': pd.DataFrame(),  # Placeholder
                'symbol': symbol,
                'sentiment': pd.DataFrame(),
                'macro': pd.DataFrame(),
                'smc': pd.DataFrame()
            }

            # Criar ambiente base
            env = BacktestEnvironment(
                data=env_data,
                initial_capital=self.config.initial_capital,
                episode_length=self.config.episode_length,
                deterministic=True,
                seed=42
            )

            # Encapsular com DummyVecEnv
            vec_env = DummyVecEnv([lambda: env])

            # Aplicar VecNormalize para estabilidade
            vec_env = VecNormalize(
                vec_env,
                norm_obs=self.config.norm_obs,
                norm_reward=self.config.norm_reward,
                clip_obs=self.config.clip_obs,
                clip_reward=self.config.clip_reward,
                gamma=self.config.gamma
            )

            logger.info(f"[OK] Ambiente preparado para {symbol}")
            return env, vec_env

        except Exception as e:
            logger.error(f"[ERROR] Erro ao preparar ambiente: {e}")
            raise

    def train(self, symbol: str = 'OGNUSDT') -> dict:
        """
        Treina modelo PPO com config Phase 4.

        Args:
            symbol: Simbolo para treinar

        Returns:
            dict com resultado do treinamento
        """
        if not HAS_ML:
            logger.error("Bibliotecas ML nao disponiveis")
            return {"error": "ML libraries missing"}

        logger.info(f"\n[TRAINING] Iniciando treinamento para {symbol}")
        logger.info(f"  Total timesteps: {self.config.total_timesteps:,}")
        logger.info(f"  Learning rate: {self.config.learning_rate}")
        logger.info(f"  Batch size: {self.config.batch_size}")
        logger.info(f"  Device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")

        try:
            # 1. Preparar ambiente
            env, vec_env = self.prepare_environment(symbol)

            # 2. Criar modelo PPO com config
            logger.info("Criando modelo PPO com config Phase 4...")
            model = PPO(
                policy="MlpPolicy",
                env=vec_env,
                learning_rate=self.config.learning_rate,
                n_steps=self.config.n_steps,
                batch_size=self.config.batch_size,
                n_epochs=self.config.n_epochs,
                gamma=self.config.gamma,
                gae_lambda=self.config.gae_lambda,
                clip_range=self.config.clip_range,
                ent_coef=self.config.ent_coef,
                vf_coef=self.config.vf_coef,
                max_grad_norm=self.config.max_grad_norm,
                device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
                verbose=self.config.verbose
            )

            # 3. Callbacks
            checkpoint_callback = CheckpointCallback(
                save_freq=self.config.save_interval,
                save_path=str(self.checkpoint_dir),
                name_prefix=f"{symbol}_ppo"
            )

            # 4. Treinar
            logger.info(f"Iniciando treinamento para {symbol}...")

            model.learn(
                total_timesteps=self.config.total_timesteps,
                callback=checkpoint_callback
            )

            # 5. Salvar modelo final e stats
            model_path = self.checkpoint_dir / f"{symbol}_ppo_final.zip"
            model.save(str(model_path))
            logger.info(f"[OK] Modelo salvo: {model_path}")

            # Salvar VecNormalize stats
            vecnorm_path = self.checkpoint_dir / f"{symbol}_ppo_vecnorm.pkl"
            vec_env.save(str(vecnorm_path))
            logger.info(f"[OK] VecNormalize stats salvo: {vecnorm_path}")

            return {
                "status": "SUCCESS",
                "symbol": symbol,
                "model_path": str(model_path),
                "vecnorm_path": str(vecnorm_path),
                "timesteps": self.config.total_timesteps,
                "config": self.config.to_dict()
            }

        except Exception as e:
            logger.error(f"[ERROR] Erro durante treinamento: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "ERROR",
                "symbol": symbol,
                "error": str(e)
            }


if __name__ == '__main__':
    if not HAS_ML:
        print("Bibliotecas ML nao instaladas. Execute: pip install -r requirements.txt")
        exit(1)

    logger.info("="*70)
    logger.info("PPO TRAINING - SKELETON SCRIPT")
    logger.info("="*70)

    trainer = PPOTrainer()

    # Treinar para OGNUSDT
    result = trainer.train(symbol='OGNUSDT')

    # Resumo
    logger.info(f"\n{'='*70}")
    logger.info("RESULTADO DO TREINAMENTO")
    logger.info(f"{'='*70}")
    print(json.dumps(result, indent=2))
