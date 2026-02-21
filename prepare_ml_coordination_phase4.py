#!/usr/bin/env python
"""
TASK 3: Comunicação com ML Team

Define interfaces de treinamento, formato de dados esperado,
hooks de monitoramento e thresholds de alerta para o treinamento PPO.

Entrega documento formal de handoff para ML  team.
"""
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, field, asdict

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DataFormat:
    """Especificação de formato de dados esperado pelo ML."""

    input_specs: Dict[str, Any] = field(default_factory=lambda: {
        "observation_space": {
            "type": "Box",
            "shape": [104],
            "dtype": "float32",
            "low": -np.inf,
            "high": np.inf,
            "description": "104 features normalizadas: OHLC, indicadores técnicos, SMC, sentimento, macro"
        },
        "action_space": {
            "type": "Discrete",
            "n": 5,
            "actions": {
                0: "HOLD",
                1: "OPEN_LONG",
                2: "OPEN_SHORT",
                3: "CLOSE_POSITION",
                4: "REDUCE_50_PERCENT"
            }
        },
        "episode_length": {
            "min": 100,
            "max": 250,
            "recommended": 200,
            "description": "Quantidade máxima de timesteps por episódio"
        }
    })

    training_data_specs: Dict[str, Any] = field(default_factory=lambda: {
        "format": "Parquet (Apache Parquet)",
        "location": "backtest/cache/",
        "symbols": ["OGNUSDT", "1000PEPEUSDT"],
        "timeframe": "4h",
        "candles_per_symbol": 1000,
        "columns": ["timestamp", "open", "high", "low", "close", "volume"],
        "split": {
            "train": "80%",
            "validation": "20%",
            "test": "None (use validation para avaliar)"
        },
        "dataset_metadata": "data/training_datasets/dataset_info.json"
    })

    environment_specs: Dict[str, Any] = field(default_factory=lambda: {
        "class": "BacktestEnvironment",
        "location": "backtest/backtest_environment.py",
        "key_features": [
            "Determinístico (seed=42)",
            "Sem randomização de start_step",
            "Trade State Machine com PnL preciso",
            "6 métricas de risk clearance"
        ],
        "initialization": {
            "data": "dict com {h4, h1, d1, symbol, sentiment, macro, smc}",
            "initial_capital": "10000 USDT",
            "episode_length": "200 timesteps recomendado",
            "deterministic": True,
            "seed": 42
        }
    })


@dataclass
class MonitoringConfig:
    """Configuração de monitoramento durante treinamento."""

    csv_logging: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "path": "logs/ppo_training/training_metrics.csv",
        "frequency": "every episode",
        "metrics": [
            "episode_number",
            "timesteps_total",
            "episode_reward",
            "episode_length",
            "success_rate",
            "win_rate",
            "profit_factor",
            "sharpe_ratio",
            "max_drawdown",
            "learning_rate"
        ]
    })

    tensorboard_logging: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "path": "logs/ppo_training/tensorboard",
        "scalars": [
            "policy_loss",
            "value_loss",
            "entropy",
            "episode_reward",
            "episode_length",
            "exploration_rate"
        ]
    })

    checkpoint_saving: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "path": "checkpoints/ppo_training",
        "frequency": "every 10,000 timesteps",
        "keep_last_n": 5,
        "naming_convention": "{symbol}_ppo_steps_{timesteps}.zip"
    })

    alert_thresholds: Dict[str, Any] = field(default_factory=lambda: {
        "performance": {
            "episode_reward_too_low": {
                "threshold": -5000,
                "action": "Log warning + check environment",
                "frequency": "per episode"
            },
            "win_rate_below_threshold": {
                "threshold": 0.4,
                "action": "Log warning + review reward function",
                "frequency": "every 100 episodes"
            },
            "max_drawdown_exceeded": {
                "threshold": 0.25,
                "action": "Log warning + check risk parameters",
                "frequency": "every 100 episodes"
            }
        },
        "training": {
            "loss_diverging": {
                "check": "policy_loss > 1000 OR value_loss > 10000",
                "action": "Log critical + reduce learning rate",
                "frequency": "per step"
            },
            "learning_rate_too_high": {
                "threshold": "> 1e-2",
                "action": "Warn: may cause instability",
                "frequency": "on init"
            }
        }
    })


@dataclass
class HookInterface:
    """Especificação de hooks para integração durante treinamento."""

    pre_training_hooks: List[str] = field(default_factory=lambda: [
        "env_validation()",
        "data_integrity_check()",
        "model_initialization_check()",
        "checkpoint_dir_ready()"
    ])

    per_step_hooks: List[str] = field(default_factory=lambda: [
        "log_episode_metrics()",
        "check_alert_thresholds()",
        "save_tensorboard_scalar()"
    ])

    per_checkpoint_hooks: List[str] = field(default_factory=lambda: [
        "save_checkpoint(model, timesteps)",
        "evaluate_on_validation_set()",
        "update_best_model_metrics()"
    ])

    post_training_hooks: List[str] = field(default_factory=lambda: [
        "save_final_model()",
        "generate_training_summary()",
        "export_metrics_csv()",
        "cleanup_old_checkpoints(keep_last_n=5)"
    ])


@dataclass
class MLCoordinationSpec:
    """Especificação completa de coordenação com ML team."""

    project: str = "Crypto Futures Agent - PPO Training Phase 4"
    version: str = "1.0"
    deadline: str = "2026-02-23 14:00 UTC"

    data_format: DataFormat = field(default_factory=DataFormat)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    hooks: HookInterface = field(default_factory=HookInterface)

    ppo_hyperparameters: Dict[str, Any] = field(default_factory=lambda: {
        "learning_rate": {
            "value": 3e-4,
            "recommended_range": [1e-5, 1e-3],
            "notes": "Usar learning rate schedule se divergência"
        },
        "n_steps": {
            "value": 2048,
            "notes": "Número de passos antes de atualizar policy"
        },
        "batch_size": {
            "value": 64,
            "notes": "Deve dividir n_steps evenly"
        },
        "n_epochs": {
            "value": 10,
            "notes": "Epochs de treinamento por experência"
        },
        "gamma": {
            "value": 0.99,
            "notes": "Fator de desconto (0.99 = valor long-term)"
        },
        "gae_lambda": {
            "value": 0.95,
            "notes": "GAE lambda para redução de variância"
        },
        "clip_range": {
            "value": 0.2,
            "notes": "Range para clipping de policy ratio"
        },
        "ent_coef": {
            "value": 0.01,
            "notes": "Coeficiente de entropia (regularização)"
        },
        "vf_coef": {
            "value": 0.5,
            "notes": "Coeficiente de value function loss"
        }
    })

    training_spec: Dict[str, Any] = field(default_factory=lambda: {
        "total_timesteps": 1_000_000,
        "eval_frequency": 10_000,
        "n_eval_episodes": 5,
        "device": "cuda (if available) else cpu",
        "mixed_precision": False,
        "gradient_clipping": 0.5
    })

    expected_deliverables: List[str] = field(default_factory=lambda: [
        "Trained model weights (checkpoints/ppo_training/SYMBOL_ppo_final.zip)",
        "Training metrics CSV (logs/ppo_training/training_metrics.csv)",
        "TensorBoard logs (logs/ppo_training/tensorboard/)",
        "Training summary report (models/trained/SYMBOL_training_summary.json)",
        "Performance curves (win_rate, sharpe_ratio over time)",
        "Validation results on hold-out testset"
    ])

    success_criteria: Dict[str, Any] = field(default_factory=lambda: {
        "minimum": {
            "win_rate": ">= 45%",
            "profit_factor": ">= 1.0",
            "max_consecutive_losses": "<= 5",
            "training_stability": "No divergence in loss"
        },
        "target": {
            "sharpe_ratio": ">= 1.0",
            "max_drawdown": "<= 15%",
            "profit_factor": ">= 1.5",
            "calmar_ratio": ">= 2.0"
        }
    })

    edge_cases_and_risks: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            "risk": "Model divergence (loss explodes)",
            "mitigation": "Early stopping + learning rate schedule",
            "monitor": "Check policy_loss per 100 steps"
        },
        {
            "risk": "Overfitting ao treino (win_rate 90% treino, 45% validação)",
            "mitigation": "Aumentar regularização (ent_coef), dropout, data augmentation",
            "monitor": "Track train/val win_rate separately"
        },
        {
            "risk": "Imbalance entre exploração e exploração",
            "mitigation": "Ajustar ent_coef + annealing schedule",
            "monitor": "Check entropy e rewards ao longo do time"
        },
        {
            "risk": "Dados stale (parquets não atualizados)",
            "mitigation": "Validar timestamps e volume no setup",
            "monitor": "Log data range em init"
        }
    ])

    support_contact: Dict[str, str] = field(default_factory=lambda: {
        "data_questions": "SWE - Backend (data extraction, ParquetCache)",
        "env_questions": "SWE - Backtest (BacktestEnvironment API)",
        "infrastructure": "SWE - DevOps (hardware, storage, compute)",
        "deadline_extensions": "CTO (Phase 4 owner)"
    })


class MLCoordinationDocument:
    """Gera documento formal de coordenação com ML team."""

    def __init__(self):
        """Inicializa gerador de documento."""
        self.spec = MLCoordinationSpec()

    def generate_handoff_document(self) -> str:
        """Gera documento de handoff em Markdown."""
        doc = f"""# ML Team Handoff - Phase 4 PPO Training

**Project**: {self.spec.project}
**Version**: {self.spec.version}
**Deadline**: {self.spec.deadline}
**Generated**: {datetime.utcnow().isoformat()}

## 📊 Data Format Specification

### Input Observation Space
- **Type**: Box({self.spec.data_format.input_specs['observation_space']['shape'][0]},)
- **Range**: Normalized features [-∞, +∞] (mostly [-1, 1])
- **Features**: 104
  - Price/OHLC (8): timestamp, open, high, low, close, volume, vwap, returns
  - Technical Indicators (40): EMA, MACD, RSI, Bollinger, ATR, etc
  - Smart Money Concepts (16): Order Blocks, FVGs, BOS, CHoCH, Liquidity Zones
  - Sentiment (10): Social media, fear/greed, funding rates
  - Macro Data (20): DXY, bond yields, BTC dominance, crypto correlation
  - Risk Metrics (10): Drawdown, volatility, Sharpe, max dd, stress level

### Action Space
- **Type**: Discrete(5)
- **Actions**:
  - 0: HOLD (no change)
  - 1: OPEN_LONG (buy)
  - 2: OPEN_SHORT (sell)
  - 3: CLOSE_POSITION (exit trade)
  - 4: REDUCE_50_PERCENT (reduce position size)

### Training Data
- **Location**: `backtest/cache/`
- **Format**: Apache Parquet (.parquet)
- **Symbols**:
  - OGNUSDT: 1000 H4 candles (800 train / 200 validation)
  - 1000PEPEUSDT: 1000 H4 candles (800 train / 200 validation)
- **Metadata**: `data/training_datasets/dataset_info.json`

## 🔧 Environment Specification

```python
from backtest.backtest_environment import BacktestEnvironment

# Load data
data = {{
    'h4': pd.read_parquet('backtest/cache/SYMBOL_4h.parquet'),
    'h1': pd.DataFrame(),  # Not required for Phase 4
    'd1': pd.DataFrame(),  # Not required for Phase 4
    'symbol': 'OGNUSDT',
    'sentiment': pd.DataFrame(),
    'macro': pd.DataFrame(),
    'smc': pd.DataFrame()
}}

# Create environment
env = BacktestEnvironment(
    data=data,
    initial_capital=10000,
    episode_length=200,
    deterministic=True,
    seed=42
)

# Use with stable-baselines3
model = PPO("MlpPolicy", env=env, ...)
model.learn(total_timesteps=1_000_000)
```

## 📈 Monitoring & Logging

### CSV Metrics (per episode)
File: `logs/ppo_training/training_metrics.csv`
Columns: episode, timesteps, reward, length, win_rate, profit_factor, sharpe, max_dd, lr

### TensorBoard
Path: `logs/ppo_training/tensorboard/`
Scalars: policy_loss, value_loss, entropy, episode_reward, episode_length

### Checkpoints
Path: `checkpoints/ppo_training/`
Frequency: Every 10,000 timesteps
Keep last: 5 models

## ⚠️ Alert Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Episode reward | < -5000 | Check environment |
| Win rate | < 40% | Review reward function |
| Max drawdown | > 25% | Check risk parameters |
| Policy loss | > 1000 | Reduce learning rate |
| Value loss | > 10000 | Maybe increase gamma |

## 🎯 PPO Hyperparameters

- **Learning Rate**: 3e-4 (range: 1e-5 to 1e-3)
- **N Steps**: 2048
- **Batch Size**: 64
- **N Epochs**: 10
- **Gamma**: 0.99
- **GAE Lambda**: 0.95
- **Clip Range**: 0.2
- **Entropy Coef**: 0.01
- **Value Func Coef**: 0.5
- **Total Timesteps**: 1,000,000

**Note**: If divergence observed, try:
1. Reduce learning rate to 1e-4
2. Increase entropy coef to 0.02
3. Add gradient clipping with max_norm=0.5

## ✅ Success Criteria

### Minimum Acceptable
- Win Rate ≥ 45%
- Profit Factor ≥ 1.0
- Max Consecutive Losses ≤ 5
- Training stability (no loss explosion)

### Target Performance
- Sharpe Ratio ≥ 1.0
- Max Drawdown ≤ 15%
- Profit Factor ≥ 1.5
- Calmar Ratio ≥ 2.0

## 📋 Known Risks & Mitigations

| Risk | Mitigation | Monitor |
|------|-----------|---------|
| Model divergence | Early stopping | policy_loss per 100 steps |
| Overfitting | Increase regularization | train vs val metrics |
| Exploration/Exploitation | Entropy annealing | entropy + rewards |
| Stale data | Validate timestamps | log data range |

## 🚀 Getting Started

### 1. Load training script
```bash
python scripts/train_ppo_skeleton.py
```

### 2. Custom config (optional)
Edit `config/ml_training_config.json` before training

### 3. Monitor training
```bash
tensorboard --logdir=logs/ppo_training/tensorboard
```

### 4. Export trained model
Models saved automatically to `checkpoints/ppo_training/`

## 📞 Support

- **Data/Cache questions**: SWE - Backend
- **Environment API questions**: SWE - Backtest
- **Infrastructure issues**: SWE - DevOps
- **Deadline changes**: CTO

---

**Status**: Ready for ML Handoff ✅
**Last Updated**: {datetime.utcnow().isoformat()}
"""
        return doc

    def generate_json_spec(self) -> Dict[str, Any]:
        """Gera especificação em formato JSON."""
        import numpy as np  # Para referência

        return {
            "project": self.spec.project,
            "version": self.spec.version,
            "deadline": self.spec.deadline,
            "generated_at": datetime.utcnow().isoformat(),

            "data_format": {
                "input": self.spec.data_format.input_specs,
                "training_data": self.spec.data_format.training_data_specs,
                "environment": self.spec.data_format.environment_specs
            },

            "monitoring": asdict(self.spec.monitoring),
            "hooks": asdict(self.spec.hooks),
            "hyperparameters": self.spec.ppo_hyperparameters,
            "training_spec": self.spec.training_spec,
            "deliverables": self.spec.expected_deliverables,
            "success_criteria": self.spec.success_criteria,
            "edge_cases": self.spec.edge_cases_and_risks,
            "support": self.spec.support_contact
        }


def main():
    """TASK 3: ML Coordination."""

    logger.info("="*70)
    logger.info("TASK 3: COMUNICAÇÃO COM ML TEAM")
    logger.info("="*70)

    # Gerar documentação
    doc_gen = MLCoordinationDocument()

    # 1. Gerar documento Markdown
    logger.info("\n[STEP 1] Gerando documento de handoff (Markdown)...")
    markdown_doc = doc_gen.generate_handoff_document()

    markdown_path = Path('ML_TEAM_HANDOFF.md')
    try:
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_doc)
        logger.info(f"✅ Documento Markdown salvo: {markdown_path}")
    except Exception as e:
        logger.error(f"❌ Erro ao salvar Markdown: {e}")

    # 2. Gerar especificação JSON
    logger.info("\n[STEP 2] Gerando especificação técnica (JSON)...")
    json_spec = doc_gen.generate_json_spec()

    json_path = Path('config/ml_coordination_spec.json')
    json_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(json_path, 'w') as f:
            json.dump(json_spec, f, indent=2)
        logger.info(f"✅ Especificação JSON salva: {json_path}")
    except Exception as e:
        logger.error(f"❌ Erro ao salvar JSON: {e}")

    # 3. Resumo
    logger.info("\n" + "="*70)
    logger.info("RESUMO - TASK 3")
    logger.info("="*70)

    print(f"\n✅ Coordenação com ML concluída:")
    print(f"   - Documento handoff: {markdown_path}")
    print(f"   - Especificação técnica: {json_path}")
    print(f"\n📊 Dados esperados:")
    print(f"   - OGNUSDT: 1000 candles H4 (800 treino / 200 validação)")
    print(f"   - 1000PEPEUSDT: 1000 candles H4 (800 treino / 200 validação)")
    print(f"\n📈 Monitoramento:")
    print(f"   - CSV metrics: logs/ppo_training/training_metrics.csv")
    print(f"   - TensorBoard: logs/ppo_training/tensorboard/")
    print(f"   - Checkpoints: checkpoints/ppo_training/")
    print(f"\n🎯 Deadline: {doc_gen.spec.deadline}")
    print(f"✅ Status: READY FOR ML HANDOFF")

    return {
        "status": "READY",
        "markdown_doc": str(markdown_path),
        "json_spec": str(json_path),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == '__main__':
    import numpy as np  # Para referência no dataclass
    result = main()
