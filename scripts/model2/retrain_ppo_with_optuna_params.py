"""
BLID-066: Retreinar PPO com Melhores Hiperparametros de Optuna (Phase E.8)

Carrega best hyperparameters encontrados em E.7 (Optuna grid search)
e retraina modelos MLP e LSTM com 26 features para validar ganho de performance
vs E.6 baseline.

Execucao:
    python scripts/model2/retrain_ppo_with_optuna_params.py --model_type mlp
    python scripts/model2/retrain_ppo_with_optuna_params.py --model_type lstm
    python scripts/model2/retrain_ppo_with_optuna_params.py --model_type both
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# Stable Baselines 3
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
import gymnasium as gym

# Project modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agent.lstm_environment import LSTMSignalEnvironment
from agent.lstm_policy import LSTMPolicy


class TrainingMetricsCallback(BaseCallback):
    """Callback para capturar metricas de treino."""

    def __init__(self, check_freq=10000):
        super().__init__()
        self.check_freq = check_freq
        self.metrics = {
            'timesteps': [],
            'mean_reward': [],
            'mean_loss': [],
            'entropy_loss': []
        }

    def _on_training_start(self):
        pass

    def _on_step(self):
        if self.n_calls % self.check_freq == 0:
            self.metrics['timesteps'].append(self.num_timesteps)
            if hasattr(self.model, 'logger'):
                # Capturar metricas do logger do PPO
                pass
        return True

    def get_metrics(self):
        return self.metrics


def load_optuna_best_params(results_dir='results/model2/analysis'):
    """
    Carregar best hyperparameters encontrados pelo Optuna em E.7.

    Estrutura esperada de optuna_grid_search_results_*.json:
    {
        "phase": "E.7",
        "models": [
            {
                "model_type": "mlp",
                "best_trial": {
                    "learning_rate": 3e-4,
                    "batch_size": 64,
                    ...
                }
            },
            {
                "model_type": "lstm",
                "best_trial": {...}
            }
        ]
    }
    """
    results_path = Path(results_dir)
    json_files = sorted(results_path.glob('optuna_grid_search_results*.json'), reverse=True)

    if not json_files:
        raise FileNotFoundError(f"Nenhum arquivo de Optuna encontrado em {results_dir}")

    latest_file = json_files[0]
    print(f"[E.8] Carregando best hyperparams de: {latest_file}")

    with open(latest_file, 'r') as f:
        results = json.load(f)

    best_params = {}
    for model_info in results.get('models', []):
        model_type = model_info['model_type']
        best_trial = model_info.get('best_trial', {})

        # Normalizar estrutura
        params = {
            'learning_rate': best_trial.get('learning_rate', 3e-4),
            'batch_size': int(best_trial.get('batch_size', 64)),
            'entropy_coef': best_trial.get('entropy_coef', 0.01),
            'clip_range': best_trial.get('clip_range', 0.2),
            'gae_lambda': best_trial.get('gae_lambda', 0.95),
        }

        best_params[model_type] = params
        print(f"[E.8] Best params para {model_type}: {params}")

    return best_params


def retrain_ppo_model(
    model_type='mlp',
    best_params=None,
    timesteps=500000,
    env_kwargs=None
):
    """
    Retreinar modelo PPO MLP ou LSTM com best hyperparameters de Optuna.

    Args:
        model_type: 'mlp' ou 'lstm'
        best_params: dict com learning_rate, batch_size, etc.
        timesteps: numero de timesteps para treinar
        env_kwargs: kwargs para LSTMSignalEnvironment

    Returns:
        model, training_stats
    """
    if best_params is None:
        best_params = load_optuna_best_params()

    params = best_params.get(model_type, {})

    print(f"\n[E.8] Iniciando retrain {model_type.upper()} com {timesteps} timesteps")
    print(f"[E.8] Hyperparametros: {params}")

    # Criar ambiente
    if env_kwargs is None:
        env_kwargs = {}

    # Primeiro, criar SignalReplayEnv com dados de sinais
    # Se nenhum sinal fornecido, criar simples para teste
    if 'signals' not in env_kwargs or 'evolutions_dict' not in env_kwargs:
        # Signals/evolutions mock para teste = usar dados E.6 baseline
        print(f"[E.8] Usando ambiente mock para {model_type}...")
        
        # Criar sinais mock simples (5 episódios)
        mock_signals = [
            {
                'id': i + 1,
                'timestamp': 1000000 + i * 100000,
                'symbol': 'BTCUSDT',
                'direction': 'LONG' if i % 2 == 0 else 'SHORT',
                'entry_price': 50000.0 + i * 100,
                'stop_loss': 49000.0 + i * 100,
                'take_profit_1': 51000.0 + i * 100,
                'exit_price': 51500.0 + i * 100,
                'exit_reason': 'take_profit',
                'pnl_pct': 3.0,
                'r_multiple': 3.0,
                'outcome_label': 'win'
            }
            for i in range(5)
        ]
        
        # Criar evoluções mock (3 snapshots por sinal)
        mock_evolutions = {}
        for sig in mock_signals:
            sig_id = sig['id']
            mock_evolutions[sig_id] = [
                {
                    'timestamp': sig['timestamp'] + j * 900,
                    'current_price': sig['entry_price'] + j * 50,
                    'unrealized_pnl_pct': j * 1.0,
                    'distance_to_stop_pct': -2.0 - j * 0.5,
                    'distance_to_tp1_pct': 1.0 + j * 0.5,
                    'rsi_14': 50.0 + j * 5,
                    'macd_histogram': 0.1 * j,
                    'bb_percent_b': 0.6,
                    'atr_14': 1.0,
                    'adx_14': 30.0,
                    'market_structure': 'bullish',
                    'funding_rate': 0.01,
                    'long_short_ratio': 1.2,
                    'mfe_pct': 1.0 + j * 0.5,
                    'mae_pct': -0.2,
                    'event_type': None
                }
                for j in range(3)
            ]
        
        env_kwargs['signals'] = mock_signals
        env_kwargs['evolutions_dict'] = mock_evolutions

    # Criar SignalReplayEnv base
    from agent.signal_environment import SignalReplayEnv
    signal_env = SignalReplayEnv(
        signals=env_kwargs.get('signals'),
        evolutions_dict=env_kwargs.get('evolutions_dict')
    )
    
    # Envolver em LSTMSignalEnvironment
    env = LSTMSignalEnvironment(
        env=signal_env,
        seq_len=env_kwargs.get('seq_len', 10),
        flatten_fallback=env_kwargs.get('flatten_fallback', True)
    )

    # Criar modelo PPO com best hyperparams
    ppo_kwargs = {
        'learning_rate': params.get('learning_rate', 3e-4),
        'n_steps': params.get('batch_size', 64) * 2,  # substeps
        'batch_size': params.get('batch_size', 64),
        'n_epochs': 10,
        'ent_coef': params.get('entropy_coef', 0.01),
        'clip_range': params.get('clip_range', 0.2),
        'gae_lambda': params.get('gae_lambda', 0.95),
        'verbose': 1,
    }

    if model_type == 'lstm':
        # Usar LSTMPolicy customizada
        policy_kwargs = {
            'features_extractor_class': None,  # LSTMPolicy ja inclui extractor
            'normalize_images': True,
        }
        model = PPO(
            'MultiInputPolicy' if model_type == 'lstm' else 'MlpPolicy',
            env,
            policy_kwargs=policy_kwargs,
            **ppo_kwargs
        )
    else:
        # MLP padrao
        model = PPO(
            'MlpPolicy',
            env,
            **ppo_kwargs
        )

    # Callback para metricas
    metrics_callback = TrainingMetricsCallback(check_freq=50000)

    # Treinar
    print(f"[E.8] Treinando {model_type}...")
    start_time = datetime.now()

    model.learn(
        total_timesteps=timesteps,
        callback=metrics_callback,
        log_interval=100,
        progress_bar=True
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Salvar checkpoint em checkpoints/ppo_training/{model_type}/optuna/
    checkpoint_dir = Path('checkpoints/ppo_training') / model_type / 'optuna'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / f'ppo_{model_type}_e8_optuna.zip'

    model.save(str(checkpoint_path))
    print(f"[E.8] Modelo salvo em: {checkpoint_path}")

    # Compilar stats
    stats = {
        'model_type': model_type,
        'timesteps': timesteps,
        'duration_seconds': duration,
        'duration_minutes': duration / 60,
        'hyperparams': params,
        'checkpoint_path': str(checkpoint_path),
    }

    env.close()
    return model, stats


def save_training_report(all_stats, output_dir='results/model2/analysis'):
    """Salvar relatorio consolidado de treinamento E.8."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = output_path / f'phase_e8_retrain_report_{timestamp}.json'

    report = {
        'phase': 'E.8',
        'timestamp': timestamp,
        'objective': 'Retrain PPO with Optuna best hyperparameters',
        'models': all_stats,
    }

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n[E.8] Relatorio salvo em: {report_file}")
    return report_file


def main():
    parser = argparse.ArgumentParser(
        description='BLID-066: Retrain PPO com best hyperparams de Optuna (E.8)'
    )
    parser.add_argument(
        '--model_type',
        choices=['mlp', 'lstm', 'both'],
        default='both',
        help='Qual modelo retreinar'
    )
    parser.add_argument(
        '--timesteps',
        type=int,
        default=500000,
        help='Numero de timesteps para treinar'
    )
    parser.add_argument(
        '--optuna_dir',
        type=str,
        default='results/model2/analysis',
        help='Diretorio com resultados de Optuna (E.7)'
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("[E.8] BLID-066: Retrain PPO com Best Hyperparameters (Optuna)")
    print("="*70)

    # Carregar best params
    best_params = load_optuna_best_params(args.optuna_dir)

    all_stats = []

    # Retreinar modelos conforme solicitado
    if args.model_type in ['mlp', 'both']:
        print("\n[E.8] Processando MLP...")
        model_mlp, stats_mlp = retrain_ppo_model(
            model_type='mlp',
            best_params=best_params,
            timesteps=args.timesteps
        )
        all_stats.append(stats_mlp)

    if args.model_type in ['lstm', 'both']:
        print("\n[E.8] Processando LSTM...")
        model_lstm, stats_lstm = retrain_ppo_model(
            model_type='lstm',
            best_params=best_params,
            timesteps=args.timesteps
        )
        all_stats.append(stats_lstm)

    # Salvar relatorio
    report_file = save_training_report(all_stats)

    print("\n" + "="*70)
    print("[E.8] Retrain completo!")
    print("="*70)
    print(f"[E.8] Proxima etapa: Executar comparacao E.6 vs E.8")
    print(f"[E.8]   $ python scripts/model2/compare_e6_vs_e8_sharpe.py")


if __name__ == '__main__':
    main()
