#!/usr/bin/env python
"""
Script base para treinamento PPO com BacktestEnvironment.

Configuração:
- Model: PPO (Proximal Policy Optimization)
- Framework: Stable-Baselines3 + PyTorch
- Environment: BacktestEnvironment (determinístico)
- Data: OGNUSDT + 1000PEPEUSDT H4 (800 treino + 200 validação)
"""

import logging
import os
import json
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd

# Imports ML
try:
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
    from gymnasium import Env
    HAS_ML = True
except ImportError as e:
    print(f"❌ Erro ao importar bibliotecas ML: {e}")
    HAS_ML = False

# Imports locais
from backtest.backtest_environment import BacktestEnvironment
from backtest.data_cache import ParquetCache
from config.symbols import SYMBOLS

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)


class PPOTrainer:
    """Treinador PPO para agente de trading."""
    
    def __init__(self, config_path: str = 'config/ml_training_config.json',
                 checkpoint_dir: str = 'checkpoints/ppo_training',
                 log_dir: str = 'logs/ppo_training'):
        """
        Inicializa treinador.
        
        Args:
            config_path: Path para arquivo de configuração ML
            checkpoint_dir: Diretório para salvar checkpoints
            log_dir: Diretório para logs
        """
        self.config = self._load_config(config_path)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.log_dir = Path(log_dir)
        self.cache = ParquetCache(db_path='crypto_agent.db', cache_dir='backtest/cache')
        
        # Criar diretórios
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PPOTrainer inicializado")
        logger.info(f"  Config: {self.config}")
        logger.info(f"  Checkpoints: {self.checkpoint_dir}")
        logger.info(f"  Logs: {self.log_dir}")
    
    def _load_config(self, config_path: str) -> dict:
        """Carrega configuração de arquivo ou usa valores default."""
        config_file = Path(config_path)
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"⚠️  Config não encontrada: {config_path}, usando defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """Retorna configuração default para treinamento."""
        return {
            "model": {
                "policy": "MlpPolicy",
                "learning_rate": 3e-4,
                "n_steps": 2048,
                "batch_size": 64,
                "n_epochs": 10,
                "gamma": 0.99,
                "gae_lambda": 0.95,
                "clip_range": 0.2,
                "ent_coef": 0.01,
                "vf_coef": 0.5
            },
            "training": {
                "total_timesteps": 1_000_000,
                "eval_freq": 10_000,
                "n_eval_episodes": 5,
                "verbose": 1,
                "device": "cuda" if torch.cuda.is_available() else "cpu"
            },
            "data": {
                "symbols": ["OGNUSDT", "1000PEPEUSDT"],
                "timeframe": "4h",
                "train_split": 0.8
            }
        }
    
    def prepare_environment(self, symbol: str) -> BacktestEnvironment:
        """
        Prepara ambiente para símbolo.
        
        Args:
            symbol: Símbolo (ex: 'OGNUSDT')
            
        Returns:
            BacktestEnvironment configurado
        """
        logger.info(f"Preparando ambiente para {symbol}...")
        
        try:
            # Carregar dados do cache
            h4_data = self.cache.load_ohlcv_for_symbol(symbol, timeframe='4h')
            
            if h4_data is None or h4_data.empty:
                raise ValueError(f"Dados não encontrados para {symbol}")
            
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
            
            # Criar ambiente
            env = BacktestEnvironment(
                data=env_data,
                initial_capital=10000,
                episode_length=min(200, len(h4_data) - 1),
                deterministic=True,
                seed=42
            )
            
            logger.info(f"✅ Ambiente preparado: {symbol}")
            return env
            
        except Exception as e:
            logger.error(f"❌ Erro ao preparar ambiente: {e}")
            raise
    
    def train(self, symbol: str = 'OGNUSDT') -> dict:
        """
        Treina modelo PPO.
        
        Args:
            symbol: Símbolo para treinar
            
        Returns:
            dict com resultado do treinamento
        """
        if not HAS_ML:
            logger.error("❌ Bibliotecas ML não disponíveis")
            return {"error": "ML libraries missing"}
        
        logger.info(f"\n[TRAINING] Iniciando treinamento para {symbol}")
        logger.info(f"  Total timesteps: {self.config['training']['total_timesteps']:,}")
        logger.info(f"  Device: {self.config['training']['device']}")
        
        try:
            # 1. Preparar ambiente
            env = self.prepare_environment(symbol)
            
            # 2. Criar modelo
            logger.info("Criando modelo PPO...")
            model = PPO(
                policy=self.config['model']['policy'],
                env=env,
                learning_rate=self.config['model']['learning_rate'],
                n_steps=self.config['model']['n_steps'],
                batch_size=self.config['model']['batch_size'],
                n_epochs=self.config['model']['n_epochs'],
                gamma=self.config['model']['gamma'],
                gae_lambda=self.config['model']['gae_lambda'],
                clip_range=self.config['model']['clip_range'],
                ent_coef=self.config['model']['ent_coef'],
                vf_coef=self.config['model']['vf_coef'],
                device=self.config['training']['device'],
                verbose=self.config['training']['verbose']
            )
            
            # 3. Callbacks
            checkpoint_callback = CheckpointCallback(
                save_freq=self.config['training']['eval_freq'],
                save_path=str(self.checkpoint_dir),
                name_prefix=f"{symbol}_ppo"
            )
            
            # 4. Treinar
            logger.info("Iniciando treinamento...")
            model.learn(
                total_timesteps=self.config['training']['total_timesteps'],
                callback=checkpoint_callback
            )
            
            # 5. Salvar modelo final
            model_path = self.checkpoint_dir / f"{symbol}_ppo_final.zip"
            model.save(str(model_path))
            logger.info(f"✅ Modelo salvo: {model_path}")
            
            return {
                "status": "SUCCESS",
                "symbol": symbol,
                "model_path": str(model_path),
                "timesteps": self.config['training']['total_timesteps']
            }
            
        except Exception as e:
            logger.error(f"❌ Erro durante treinamento: {e}")
            return {
                "status": "ERROR",
                "symbol": symbol,
                "error": str(e)
            }


if __name__ == '__main__':
    if not HAS_ML:
        print("❌ Bibliotecas ML não instaladas. Execute: pip install -r requirements.txt")
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
