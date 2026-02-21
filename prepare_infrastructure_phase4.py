#!/usr/bin/env python
"""
TASK 2: Infrastructure Setup para Treinamento PPO

1. Verificar recursos disponíveis (GPU, memória)
2. Preparar diretórios necessários
3. Criar script base de treinamento (skeleton)
"""
import logging
import json
import platform
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)


class InfrastructureSetup:
    """Configuração de infraestrutura para treinamento."""
    
    REQUIRED_DIRS = [
        'checkpoints/ppo_training',
        'logs/ppo_training',
        'models/trained',
        'data/training_datasets'
    ]
    
    def __init__(self):
        """Inicializa setup."""
        self.resources = {}
        self.setup_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "PENDING",
            "checks": {},
            "issues": [],
            "warnings": []
        }
    
    def check_hardware(self) -> Dict[str, Any]:
        """Verifica recursos de hardware disponíveis."""
        logger.info("\n[CHECK 1] Verificando hardware...")
        
        hardware = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_count": 0,
            "memory_gb": 0.0,
            "gpu_available": False,
            "gpu_name": None,
            "gpu_vram_gb": 0.0,
            "cuda_available": False
        }
        
        try:
            if HAS_PSUTIL:
                hardware["cpu_count"] = psutil.cpu_count(logical=True)
                hardware["memory_gb"] = psutil.virtual_memory().total / (1024**3)
                logger.info(f"✅ CPU: {hardware['cpu_count']} cores")
                logger.info(f"✅ RAM: {hardware['memory_gb']:.1f} GB")
            else:
                logger.warning("⚠️  psutil não disponível, pulando RAM check")
        except Exception as e:
            logger.error(f"❌ Erro ao verificar CPU/RAM: {e}")
        
        try:
            if HAS_TORCH:
                hardware["cuda_available"] = torch.cuda.is_available()
                if hardware["cuda_available"]:
                    hardware["gpu_available"] = True
                    hardware["gpu_name"] = torch.cuda.get_device_name(0)
                    hardware["gpu_vram_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    logger.info(f"✅ GPU: {hardware['gpu_name']}")
                    logger.info(f"✅ VRAM: {hardware['gpu_vram_gb']:.1f} GB")
                else:
                    logger.warning("⚠️  GPU/CUDA não disponível - treinamento será CPUonly")
            else:
                logger.warning("⚠️  PyTorch não instalado")
        except Exception as e:
            logger.error(f"❌ Erro ao verificar GPU: {e}")
        
        self.resources = hardware
        self.setup_result["checks"]["hardware"] = hardware
        
        return hardware
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Verifica dependências críticas."""
        logger.info("\n[CHECK 2] Verificando dependências...")
        
        dependencies = {
            "numpy": False,
            "pandas": False,
            "scipy": False,
            "sklearn": False,
            "stable_baselines3": False,
            "gymnasium": False,
            "torch": False
        }
        
        try:
            import numpy
            dependencies["numpy"] = True
            logger.info(f"✅ numpy {numpy.__version__}")
        except:
            logger.warning("⚠️  numpy não encontrado")
        
        try:
            import pandas
            dependencies["pandas"] = True
            logger.info(f"✅ pandas {pandas.__version__}")
        except:
            logger.warning("⚠️  pandas não encontrado")
        
        try:
            import scipy
            dependencies["scipy"] = True
            logger.info(f"✅ scipy {scipy.__version__}")
        except:
            logger.warning("⚠️  scipy não encontrado")
        
        try:
            import sklearn
            dependencies["sklearn"] = True
            logger.info(f"✅ scikit-learn {sklearn.__version__}")
        except:
            logger.warning("⚠️  scikit-learn não encontrado")
        
        try:
            import stable_baselines3
            dependencies["stable_baselines3"] = True
            logger.info(f"✅ stable-baselines3")
        except:
            logger.warning("⚠️  stable-baselines3 não encontrado")
        
        try:
            import gymnasium
            dependencies["gymnasium"] = True
            logger.info(f"✅ gymnasium")
        except:
            logger.warning("⚠️  gymnasium não encontrado")
        
        try:
            import torch
            dependencies["torch"] = True
            logger.info(f"✅ torch {torch.__version__}")
        except:
            logger.warning("⚠️  torch não encontrado")
        
        self.setup_result["checks"]["dependencies"] = dependencies
        
        critical_missing = [k for k, v in dependencies.items() 
                           if not v and k in ['stable_baselines3', 'gymnasium', 'torch']]
        
        if critical_missing:
            self.setup_result["issues"].extend([f"Dependência crítica ausente: {pkg}" for pkg in critical_missing])
        
        return dependencies
    
    def prepare_directories(self) -> Dict[str, str]:
        """Prepara estrutura de diretórios necessária."""
        logger.info("\n[CHECK 3] Preparando diretórios...")
        
        created_dirs = {}
        
        for dir_path in self.REQUIRED_DIRS:
            try:
                path = Path(dir_path)
                path.mkdir(parents=True, exist_ok=True)
                created_dirs[dir_path] = str(path.resolve())
                logger.info(f"✅ {dir_path}")
            except Exception as e:
                logger.error(f"❌ Erro ao criar {dir_path}: {e}")
                self.setup_result["issues"].append(f"Erro ao criar diretório {dir_path}: {e}")
        
        self.setup_result["checks"]["directories"] = created_dirs
        
        return created_dirs
    
    def create_training_skeleton(self) -> str:
        """Cria script base de treinamento."""
        logger.info("\n[CHECK 4] Criando script base de treinamento...")
        
        skeleton_code = '''#!/usr/bin/env python
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
        
        logger.info(f"\\n[TRAINING] Iniciando treinamento para {symbol}")
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
    logger.info(f"\\n{'='*70}")
    logger.info("RESULTADO DO TREINAMENTO")
    logger.info(f"{'='*70}")
    print(json.dumps(result, indent=2))
'''
        
        script_path = Path('scripts/train_ppo_skeleton.py')
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(skeleton_code)
            logger.info(f"✅ Script base criado: {script_path}")
            self.setup_result["checks"]["training_script"] = str(script_path)
            return str(script_path)
        except Exception as e:
            logger.error(f"❌ Erro ao criar script: {e}")
            self.setup_result["issues"].append(f"Erro ao criar script de treinamento: {e}")
            return None
    
    def create_ml_config(self) -> str:
        """Cria arquivo de configuração ML."""
        logger.info("\n[CHECK 5] Criando configuração ML...")
        
        ml_config = {
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
                "vf_coef": 0.5,
                "seed": 42
            },
            "training": {
                "total_timesteps": 1_000_000,
                "eval_freq": 10_000,
                "n_eval_episodes": 5,
                "eval_log_path": "logs/ppo_training/eval_results.csv",
                "verbose": 1,
                "device": "cuda" if HAS_TORCH and torch.cuda.is_available() else "cpu"
            },
            "data": {
                "symbols": ["OGNUSDT", "1000PEPEUSDT"],
                "timeframe": "4h",
                "train_split": 0.8,
                "cache_dir": "backtest/cache",
                "db_path": "crypto_agent.db"
            },
            "logging": {
                "level": "INFO",
                "tensorboard_log": "logs/ppo_training/tensorboard",
                "csv_log": "logs/ppo_training/training_metrics.csv"
            },
            "checkpointing": {
                "save_freq": 10_000,
                "checkpoint_dir": "checkpoints/ppo_training",
                "keep_last_n": 5
            }
        }
        
        config_path = Path('config/ml_training_config.json')
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(ml_config, f, indent=2)
            logger.info(f"✅ Config ML criada: {config_path}")
            self.setup_result["checks"]["ml_config"] = str(config_path)
            return str(config_path)
        except Exception as e:
            logger.error(f"❌ Erro ao criar config: {e}")
            self.setup_result["issues"].append(f"Erro ao criar config ML: {e}")
            return None
    
    def run_all_checks(self) -> dict:
        """Executa todos os checks."""
        logger.info("="*70)
        logger.info("TASK 2: INFRASTRUCTURE SETUP")
        logger.info("="*70)
        
        # Executar checks
        self.check_hardware()
        self.check_dependencies()
        dirs = self.prepare_directories()
        script = self.create_training_skeleton()
        config = self.create_ml_config()
        
        # Finalizar
        self.setup_result["status"] = "READY" if not self.setup_result["issues"] else "PARTIAL"
        self.setup_result["directories_created"] = dirs
        self.setup_result["training_script"] = script
        self.setup_result["ml_config"] = config
        
        # Log resumo
        logger.info("\n" + "="*70)
        logger.info("RESUMO - TASK 2")
        logger.info("="*70)
        
        print(f"\n✅ Hardware: {self.resources['platform']}")
        print(f"  CPU: {self.resources['cpu_count']} cores")
        print(f"  RAM: {self.resources['memory_gb']:.1f} GB")
        print(f"  GPU: {'Sim' if self.resources['gpu_available'] else 'Não'}")
        if self.resources['gpu_available']:
            print(f"       {self.resources['gpu_name']} ({self.resources['gpu_vram_gb']:.1f}GB)")
        
        print(f"\n✅ Diretórios: {len(dirs)} criados")
        print(f"✅ Script de treinamento: {Path(script).name}")
        print(f"✅ Config ML: {Path(config).name}")
        
        if self.setup_result["issues"]:
            print(f"\n⚠️  Issues encontradas:")
            for issue in self.setup_result["issues"]:
                print(f"  - {issue}")
        
        if self.setup_result["warnings"]:
            print(f"\n⚠️  Avisos:")
            for warning in self.setup_result["warnings"]:
                print(f"  - {warning}")
        
        return self.setup_result


def main():
    """TASK 2: Infrastructure Setup."""
    setup = InfrastructureSetup()
    result = setup.run_all_checks()
    
    # Salvar resultado
    result_path = Path('setup_result_task2.json')
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"\n📄 Resultado salvo: {result_path}")
    
    return result


if __name__ == '__main__':
    main()
