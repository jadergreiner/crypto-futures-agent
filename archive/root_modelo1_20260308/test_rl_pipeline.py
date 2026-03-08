"""
Script de teste simples para o pipeline de treinamento RL.
Testa os componentes principais sem dependências externas.
"""

import logging
import sys
import numpy as np
import pandas as pd
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_data_generation():
    """Testa geração de dados sintéticos."""
    logger.info("="*60)
    logger.info("TESTE 1: Geração de Dados Sintéticos")
    logger.info("="*60)
    
    from tests.test_e2e_pipeline import (
        create_synthetic_ohlcv,
        create_synthetic_macro_data,
        create_synthetic_sentiment_data
    )
    from indicators.technical import TechnicalIndicators
    
    # Gerar dados
    h4_data = create_synthetic_ohlcv(length=500, seed=42)
    logger.info(f"[OK] Gerados {len(h4_data)} candles H4")
    
    # Calcular indicadores
    tech = TechnicalIndicators()
    h4_data = tech.calculate_all(h4_data)
    logger.info(f"[OK] Indicadores calculados: {len(h4_data.columns)} colunas")
    
    # Sentiment e macro
    sentiment = create_synthetic_sentiment_data()
    macro = create_synthetic_macro_data()
    logger.info(f"[OK] Sentiment e macro gerados")
    
    return {
        'h1': pd.DataFrame(),
        'h4': h4_data,
        'd1': pd.DataFrame(),
        'sentiment': sentiment,
        'macro': macro,
        'smc': {'order_blocks': [], 'fvgs': [], 'liquidity': []},
        'symbol': 'BTCUSDT'
    }

def test_environment(data):
    """Testa o environment."""
    logger.info("="*60)
    logger.info("TESTE 2: CryptoFuturesEnv")
    logger.info("="*60)
    
    from agent.environment import CryptoFuturesEnv
    
    # Criar environment
    env = CryptoFuturesEnv(
        data=data,
        initial_capital=10000,
        episode_length=100
    )
    logger.info(f"[OK] Environment criado")
    logger.info(f"    Observation space: {env.observation_space}")
    logger.info(f"    Action space: {env.action_space}")
    
    # Reset
    obs, info = env.reset()
    logger.info(f"[OK] Reset executado")
    logger.info(f"    Observation shape: {obs.shape}")
    logger.info(f"    Initial capital: ${info['capital']:.2f}")
    
    # Executar alguns steps
    total_reward = 0
    for i in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        if terminated or truncated:
            logger.info(f"[INFO] Episode terminou no step {i+1}")
            break
    
    logger.info(f"[OK] 10 steps executados")
    logger.info(f"    Total reward: {total_reward:.4f}")
    logger.info(f"    Final capital: ${info['capital']:.2f}")
    
    return env

def test_trainer(data):
    """Testa o trainer com poucos timesteps."""
    logger.info("="*60)
    logger.info("TESTE 3: Trainer (Mini-Training)")
    logger.info("="*60)
    
    from agent.trainer import Trainer
    
    # Criar trainer
    trainer = Trainer(save_dir="/tmp/test_models")
    logger.info(f"[OK] Trainer criado")
    
    # Treinar com poucos timesteps
    logger.info("[INFO] Iniciando mini-treinamento (10k timesteps)...")
    model = trainer.train_phase1_exploration(
        train_data=data,
        total_timesteps=10000,
        episode_length=50
    )
    logger.info(f"[OK] Mini-treinamento concluído")
    
    # Avaliar
    logger.info("[INFO] Avaliando modelo...")
    test_env = trainer.create_env(data, episode_length=50)
    metrics = trainer.evaluate(test_env, n_episodes=5, deterministic=True)
    
    logger.info(f"[OK] Avaliação concluída")
    logger.info(f"    Win Rate: {metrics['win_rate']*100:.2f}%")
    logger.info(f"    Total Trades: {metrics['total_trades']}")
    logger.info(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    
    return trainer, model

def test_backtester(model, data):
    """Testa o backtester."""
    logger.info("="*60)
    logger.info("TESTE 4: Backtester")
    logger.info("="*60)
    
    from backtest.backtester import Backtester
    
    # Criar backtester
    backtester = Backtester(initial_capital=10000)
    logger.info(f"[OK] Backtester criado")
    
    # Executar backtest
    logger.info("[INFO] Executando backtest...")
    results = backtester.run(
        start_date="2024-01-01",
        end_date="2024-12-31",
        model=model,
        data=data
    )
    
    logger.info(f"[OK] Backtest concluído")
    logger.info(f"    Initial Capital: ${results['initial_capital']:.2f}")
    logger.info(f"    Final Capital: ${results['final_capital']:.2f}")
    logger.info(f"    Total Return: {results['metrics']['total_return_pct']:.2f}%")
    logger.info(f"    Total Trades: {results['total_trades']}")
    logger.info(f"    Win Rate: {results['metrics']['win_rate']*100:.2f}%")
    
    # Gerar relatório
    backtester.generate_report(results, save_path="/tmp/test_backtest_report.png")
    logger.info(f"[OK] Relatório gerado: /tmp/test_backtest_report.png")
    
    return results

def main():
    """Executa todos os testes."""
    try:
        logger.info("="*60)
        logger.info("INICIANDO TESTES DO PIPELINE RL")
        logger.info("="*60)
        
        # Teste 1: Dados
        data = test_data_generation()
        
        # Teste 2: Environment
        env = test_environment(data)
        
        # Teste 3: Trainer
        trainer, model = test_trainer(data)
        
        # Teste 4: Backtester
        results = test_backtester(model, data)
        
        logger.info("="*60)
        logger.info("TODOS OS TESTES PASSARAM COM SUCESSO!")
        logger.info("="*60)
        
        return 0
        
    except Exception as e:
        logger.error("="*60)
        logger.error("ERRO NOS TESTES")
        logger.error("="*60)
        logger.error(f"Erro: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
