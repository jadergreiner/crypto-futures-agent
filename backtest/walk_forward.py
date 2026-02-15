"""
Walk-forward optimization e retreinamento.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class WalkForward:
    """Walk-forward optimization para retreinamento adaptativo."""
    
    def __init__(self, train_window: int = 365, test_window: int = 30):
        """
        Inicializa walk-forward.
        
        Args:
            train_window: Janela de treinamento (dias)
            test_window: Janela de teste (dias)
        """
        self.train_window = train_window
        self.test_window = test_window
        logger.info(f"Walk-Forward initialized: train={train_window}d, test={test_window}d")
    
    def run(self, data: Dict[str, pd.DataFrame], trainer: Any) -> Dict[str, Any]:
        """
        Executa walk-forward optimization.
        
        Args:
            data: Dados históricos completos
            trainer: Trainer do agente
            
        Returns:
            Resultados agregados
        """
        logger.info("Starting walk-forward optimization")
        
        h4_data = data.get('h4')
        if h4_data is None or h4_data.empty:
            logger.error("No H4 data for walk-forward")
            return {'windows': [], 'avg_metrics': {}}
        
        # Calcular número de janelas (H4 = 4h, então 6 candles/dia)
        candles_per_day = 6  # 24h / 4h
        train_candles = self.train_window * candles_per_day
        test_candles = self.test_window * candles_per_day
        window_step = test_candles  # Andar 1 test_window por vez
        
        total_candles = len(h4_data)
        windows_results = []
        
        # Iterar sobre janelas
        start_idx = 0
        window_num = 0
        
        while start_idx + train_candles + test_candles <= total_candles:
            window_num += 1
            train_end = start_idx + train_candles
            test_start = train_end
            test_end = test_start + test_candles
            
            logger.info(f"Window {window_num}: train[{start_idx}:{train_end}], test[{test_start}:{test_end}]")
            
            # Preparar dados de treino e teste para esta janela
            train_data_window = self._slice_data(data, start_idx, train_end)
            test_data_window = self._slice_data(data, test_start, test_end)
            
            # Treinar modelo nesta janela
            try:
                logger.info(f"Training on window {window_num}...")
                trainer.train_phase1_exploration(
                    train_data=train_data_window,
                    total_timesteps=50000,  # Menos timesteps para walk-forward
                    episode_length=min(500, test_candles)
                )
                
                # Avaliar no período de teste
                logger.info(f"Testing on window {window_num}...")
                test_env = trainer.create_env(test_data_window, episode_length=test_candles-1)
                metrics = trainer.evaluate(test_env, n_episodes=10, deterministic=True)
                
                windows_results.append({
                    'window': window_num,
                    'train_start': start_idx,
                    'train_end': train_end,
                    'test_start': test_start,
                    'test_end': test_end,
                    'metrics': metrics
                })
                
                logger.info(f"Window {window_num} results: "
                          f"Sharpe={metrics['sharpe_ratio']:.2f}, "
                          f"WinRate={metrics['win_rate']*100:.2f}%")
                
            except Exception as e:
                logger.error(f"Error in window {window_num}: {e}")
            
            # Avançar para próxima janela
            start_idx += window_step
        
        # Calcular métricas agregadas
        if windows_results:
            avg_sharpe = np.mean([w['metrics']['sharpe_ratio'] for w in windows_results])
            avg_win_rate = np.mean([w['metrics']['win_rate'] for w in windows_results])
            avg_return = np.mean([w['metrics'].get('avg_return', 0) for w in windows_results])
            
            avg_metrics = {
                'avg_sharpe_ratio': avg_sharpe,
                'avg_win_rate': avg_win_rate,
                'avg_return': avg_return,
                'num_windows': len(windows_results)
            }
        else:
            avg_metrics = {}
        
        results = {
            'windows': windows_results,
            'avg_metrics': avg_metrics
        }
        
        logger.info(f"Walk-forward optimization completed: {len(windows_results)} windows")
        if avg_metrics:
            logger.info(f"Average metrics: Sharpe={avg_metrics['avg_sharpe_ratio']:.2f}, "
                       f"WinRate={avg_metrics['avg_win_rate']*100:.2f}%")
        
        return results
    
    def _slice_data(
        self, 
        data: Dict[str, Any], 
        start_idx: int, 
        end_idx: int
    ) -> Dict[str, Any]:
        """
        Fatia dados para uma janela específica.
        
        Args:
            data: Dados completos
            start_idx: Índice inicial (em H4 candles)
            end_idx: Índice final (em H4 candles)
            
        Returns:
            Dados fatiados
        """
        result = {}
        
        # Fatiar H4
        h4_data = data.get('h4')
        if h4_data is not None and not h4_data.empty:
            result['h4'] = h4_data.iloc[start_idx:end_idx].reset_index(drop=True)
        else:
            result['h4'] = pd.DataFrame()
        
        # Fatiar H1 (4x mais candles)
        h1_data = data.get('h1')
        if h1_data is not None and not h1_data.empty:
            h1_start = start_idx * 4
            h1_end = end_idx * 4
            result['h1'] = h1_data.iloc[h1_start:h1_end].reset_index(drop=True)
        else:
            result['h1'] = pd.DataFrame()
        
        # Fatiar D1 (menos candles)
        d1_data = data.get('d1')
        if d1_data is not None and not d1_data.empty:
            d1_start = max(0, start_idx // 6)
            d1_end = end_idx // 6
            result['d1'] = d1_data.iloc[d1_start:d1_end].reset_index(drop=True)
        else:
            result['d1'] = pd.DataFrame()
        
        # Copiar sentiment, macro e smc
        result['sentiment'] = data.get('sentiment', {})
        result['macro'] = data.get('macro', {})
        result['smc'] = data.get('smc', {})
        
        return result
    
    def retrain_monthly(
        self, 
        current_model: Any, 
        new_data: Dict[str, pd.DataFrame], 
        trainer: Any,
        performance_threshold: float = 0.5
    ) -> Any:
        """
        Retreina modelo com novos dados mensalmente.
        
        Args:
            current_model: Modelo atual
            new_data: Novos dados do último mês
            trainer: Trainer do agente
            performance_threshold: Threshold de Sharpe para retreinar
            
        Returns:
            Modelo retreinado ou modelo atual se performance OK
        """
        logger.info("Monthly retrain started")
        
        try:
            # 1. Validar modelo atual com novos dados
            logger.info("Evaluating current model on new data...")
            test_env = trainer.create_env(new_data, episode_length=min(500, len(new_data.get('h4', []))))
            
            # Definir modelo atual no trainer
            trainer.model = current_model
            
            current_metrics = trainer.evaluate(test_env, n_episodes=20, deterministic=True)
            current_sharpe = current_metrics['sharpe_ratio']
            
            logger.info(f"Current model performance: Sharpe={current_sharpe:.2f}")
            
            # 2. Se performance degrada, retreinar
            if current_sharpe < performance_threshold:
                logger.warning(f"Performance degraded (Sharpe={current_sharpe:.2f} < {performance_threshold}), retraining...")
                
                # Retreinar com dados novos
                trainer.train_phase1_exploration(
                    train_data=new_data,
                    total_timesteps=100000,  # Retreino mais curto
                    episode_length=min(500, len(new_data.get('h4', [])))
                )
                
                # 3. Validar novo modelo
                logger.info("Evaluating retrained model...")
                new_metrics = trainer.evaluate(test_env, n_episodes=20, deterministic=True)
                new_sharpe = new_metrics['sharpe_ratio']
                
                logger.info(f"Retrained model performance: Sharpe={new_sharpe:.2f}")
                
                # 4. Retornar melhor modelo
                if new_sharpe > current_sharpe:
                    logger.info("[OK] Retrained model is better, using new model")
                    return trainer.model
                else:
                    logger.info("[OK] Current model still better, keeping it")
                    return current_model
            else:
                logger.info(f"[OK] Current model performance OK (Sharpe={current_sharpe:.2f}), no retrain needed")
                return current_model
                
        except Exception as e:
            logger.error(f"Error during monthly retrain: {e}")
            return current_model
        
        logger.info("Monthly retrain completed")
        return current_model

