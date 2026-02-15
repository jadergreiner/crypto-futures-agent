"""
Data Loader para treinamento do agente RL.
Carrega dados históricos do SQLite ou gera dados sintéticos como fallback.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data.database import DatabaseManager
from indicators.technical import TechnicalIndicators
from indicators.smc import SmartMoneyConcepts

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Carrega e prepara dados para treinamento do agente RL.
    
    Fornece dados históricos em formato apropriado para o CryptoFuturesEnv.
    Inclui fallback para geração de dados sintéticos quando DB está vazio.
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        Inicializa data loader.
        
        Args:
            db: DatabaseManager instance (opcional, usa dados sintéticos se None)
        """
        self.db = db
        self.tech_indicators = TechnicalIndicators()
        self.smc = SmartMoneyConcepts()
        logger.info("DataLoader initialized")
    
    def load_training_data(
        self, 
        symbol: str = "BTCUSDT",
        train_ratio: float = 0.8,
        min_length: int = 1000
    ) -> Dict[str, Any]:
        """
        Carrega dados de treinamento.
        
        Args:
            symbol: Símbolo para carregar
            train_ratio: Proporção de dados para treino (0-1)
            min_length: Comprimento mínimo de dados H4
            
        Returns:
            Dicionário com DataFrames de H1, H4, D1, sentiment, macro, smc
        """
        logger.info(f"Loading training data for {symbol}")
        
        # Tentar carregar do banco
        if self.db:
            try:
                data = self._load_from_database(symbol, train_ratio=train_ratio, is_train=True)
                if data and self._validate_data(data, min_length):
                    logger.info(f"[OK] Loaded {len(data['h4'])} H4 candles from database")
                    return data
                else:
                    logger.warning("Database data insufficient, falling back to synthetic")
            except Exception as e:
                logger.warning(f"Failed to load from database: {e}, using synthetic data")
        
        # Fallback: gerar dados sintéticos
        logger.info("Generating synthetic training data")
        data = self._generate_synthetic_data(length=min_length, symbol=symbol, seed=42)
        
        # Split treino (primeiros 80%)
        split_idx = int(len(data['h4']) * train_ratio)
        data = self._slice_data(data, 0, split_idx)
        
        logger.info(f"[OK] Generated {len(data['h4'])} H4 candles (synthetic)")
        return data
    
    def load_validation_data(
        self, 
        symbol: str = "BTCUSDT",
        train_ratio: float = 0.8,
        min_length: int = 200
    ) -> Dict[str, Any]:
        """
        Carrega dados de validação (out-of-sample).
        
        Args:
            symbol: Símbolo para carregar
            train_ratio: Proporção de dados para treino (usado para split)
            min_length: Comprimento mínimo de dados H4
            
        Returns:
            Dicionário com DataFrames de validação
        """
        logger.info(f"Loading validation data for {symbol}")
        
        # Tentar carregar do banco
        if self.db:
            try:
                data = self._load_from_database(symbol, train_ratio=train_ratio, is_train=False)
                if data and self._validate_data(data, min_length):
                    logger.info(f"[OK] Loaded {len(data['h4'])} H4 candles from database (validation)")
                    return data
                else:
                    logger.warning("Database data insufficient, falling back to synthetic")
            except Exception as e:
                logger.warning(f"Failed to load from database: {e}, using synthetic data")
        
        # Fallback: gerar dados sintéticos
        logger.info("Generating synthetic validation data")
        data = self._generate_synthetic_data(length=min_length + int(min_length*train_ratio), 
                                            symbol=symbol, seed=123)
        
        # Split validação (últimos 20%)
        split_idx = int(len(data['h4']) * train_ratio)
        data = self._slice_data(data, split_idx, len(data['h4']))
        
        logger.info(f"[OK] Generated {len(data['h4'])} H4 candles (synthetic validation)")
        return data
    
    def _load_from_database(
        self, 
        symbol: str,
        train_ratio: float = 0.8,
        is_train: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Carrega dados do banco SQLite.
        
        Args:
            symbol: Símbolo para carregar
            train_ratio: Proporção de dados para treino
            is_train: Se True, retorna split de treino, senão validação
            
        Returns:
            Dicionário com dados ou None se falhar
        """
        if not self.db:
            return None
        
        try:
            # Carregar OHLCV de todos os timeframes
            h1_df = self.db.get_ohlcv('h1', symbol, limit=10000)
            h4_df = self.db.get_ohlcv('h4', symbol, limit=5000)
            d1_df = self.db.get_ohlcv('d1', symbol, limit=365)
            
            if not h4_df or len(h4_df) < 100:
                logger.warning(f"Insufficient H4 data: {len(h4_df) if h4_df else 0} candles")
                return None
            
            # Converter para DataFrames
            h1_data = pd.DataFrame(h1_df) if h1_df else pd.DataFrame()
            h4_data = pd.DataFrame(h4_df)
            d1_data = pd.DataFrame(d1_df) if d1_df else pd.DataFrame()
            
            # Calcular indicadores
            if not h4_data.empty:
                h4_data = self.tech_indicators.calculate_all(h4_data)
            if not h1_data.empty:
                h1_data = self.tech_indicators.calculate_all(h1_data)
            if not d1_data.empty:
                d1_data = self.tech_indicators.calculate_all(d1_data)
            
            # Calcular SMC no H4
            smc_structures = None
            if not h4_data.empty and len(h4_data) >= 50:
                try:
                    smc_structures = self.smc.calculate_all(h4_data, symbol)
                except Exception as e:
                    logger.warning(f"SMC calculation failed: {e}")
                    smc_structures = {'order_blocks': [], 'fvgs': [], 'liquidity': []}
            
            # Carregar sentiment e macro
            sentiment_data = self.db.get_sentiment(symbol, limit=1000)
            macro_data = self.db.get_macro(limit=365)
            
            # Preparar sentiment e macro
            sentiment = sentiment_data[0] if sentiment_data else self._get_default_sentiment(symbol)
            macro = macro_data[0] if macro_data else self._get_default_macro()
            
            # Fazer split treino/validação baseado em tempo
            split_idx = int(len(h4_data) * train_ratio)
            
            if is_train:
                h4_data = h4_data.iloc[:split_idx].reset_index(drop=True)
                if not h1_data.empty:
                    h1_split = int(len(h1_data) * train_ratio)
                    h1_data = h1_data.iloc[:h1_split].reset_index(drop=True)
            else:
                h4_data = h4_data.iloc[split_idx:].reset_index(drop=True)
                if not h1_data.empty:
                    h1_split = int(len(h1_data) * train_ratio)
                    h1_data = h1_data.iloc[h1_split:].reset_index(drop=True)
            
            return {
                'h1': h1_data,
                'h4': h4_data,
                'd1': d1_data,
                'sentiment': sentiment,
                'macro': macro,
                'smc': smc_structures
            }
            
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            return None
    
    def _generate_synthetic_data(
        self, 
        length: int = 1000,
        symbol: str = "BTCUSDT",
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        Gera dados sintéticos para treinamento.
        
        Args:
            length: Número de candles H4 a gerar
            symbol: Símbolo
            seed: Random seed
            
        Returns:
            Dicionário com dados sintéticos
        """
        from tests.test_e2e_pipeline import (
            create_synthetic_ohlcv,
            create_synthetic_macro_data,
            create_synthetic_sentiment_data
        )
        
        # Gerar OHLCV H4
        h4_data = create_synthetic_ohlcv(
            length=length,
            base_price=30000.0,
            volatility=100.0,
            trend=0.0,
            seed=seed
        )
        h4_data['symbol'] = symbol
        
        # Gerar H1 (4x mais candles)
        h1_data = create_synthetic_ohlcv(
            length=length * 4,
            base_price=30000.0,
            volatility=50.0,
            trend=0.0,
            seed=seed + 1
        )
        h1_data['symbol'] = symbol
        
        # Gerar D1 (menos candles)
        d1_data = create_synthetic_ohlcv(
            length=length // 6,
            base_price=30000.0,
            volatility=200.0,
            trend=0.0,
            seed=seed + 2
        )
        d1_data['symbol'] = symbol
        
        # Calcular indicadores
        h4_data = self.tech_indicators.calculate_all(h4_data)
        h1_data = self.tech_indicators.calculate_all(h1_data)
        d1_data = self.tech_indicators.calculate_all(d1_data)
        
        # Calcular SMC no H4
        try:
            smc_structures = self.smc.calculate_all(h4_data, symbol)
        except Exception as e:
            logger.warning(f"SMC calculation failed on synthetic data: {e}")
            smc_structures = {'order_blocks': [], 'fvgs': [], 'liquidity': []}
        
        # Gerar sentiment e macro sintéticos
        sentiment = create_synthetic_sentiment_data()
        sentiment['symbol'] = symbol
        
        macro = create_synthetic_macro_data()
        
        return {
            'h1': h1_data,
            'h4': h4_data,
            'd1': d1_data,
            'sentiment': sentiment,
            'macro': macro,
            'smc': smc_structures
        }
    
    def _slice_data(
        self, 
        data: Dict[str, Any], 
        start_idx: int, 
        end_idx: int
    ) -> Dict[str, Any]:
        """
        Fatia os dados entre índices.
        
        Args:
            data: Dados completos
            start_idx: Índice inicial
            end_idx: Índice final
            
        Returns:
            Dados fatiados
        """
        result = {}
        
        # Fatiar DataFrames
        for key in ['h1', 'h4', 'd1']:
            if key in data and isinstance(data[key], pd.DataFrame) and not data[key].empty:
                if key == 'h1':
                    # H1 tem 4x mais candles
                    h1_start = start_idx * 4
                    h1_end = end_idx * 4
                    result[key] = data[key].iloc[h1_start:h1_end].reset_index(drop=True)
                elif key == 'd1':
                    # D1 tem menos candles
                    d1_start = max(0, start_idx // 6)
                    d1_end = end_idx // 6
                    result[key] = data[key].iloc[d1_start:d1_end].reset_index(drop=True)
                else:
                    result[key] = data[key].iloc[start_idx:end_idx].reset_index(drop=True)
            else:
                result[key] = data.get(key, pd.DataFrame())
        
        # Copiar sentiment, macro e smc (não são time-series no mesmo sentido)
        result['sentiment'] = data.get('sentiment', self._get_default_sentiment())
        result['macro'] = data.get('macro', self._get_default_macro())
        result['smc'] = data.get('smc', {'order_blocks': [], 'fvgs': [], 'liquidity': []})
        
        return result
    
    def _validate_data(self, data: Dict[str, Any], min_length: int) -> bool:
        """
        Valida se os dados têm comprimento suficiente.
        
        Args:
            data: Dados para validar
            min_length: Comprimento mínimo H4
            
        Returns:
            True se válido
        """
        if not data:
            return False
        
        h4_data = data.get('h4')
        if h4_data is None or h4_data.empty:
            return False
        
        if len(h4_data) < min_length:
            logger.warning(f"H4 data too short: {len(h4_data)} < {min_length}")
            return False
        
        # Verificar colunas essenciais
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in h4_data.columns for col in required_cols):
            logger.warning("Missing required OHLCV columns")
            return False
        
        return True
    
    def _get_default_sentiment(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Retorna dados de sentiment padrão."""
        return {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'symbol': symbol,
            'long_short_ratio': 1.0,
            'open_interest': 50000000.0,
            'open_interest_change_pct': 0.0,
            'funding_rate': 0.0001,
            'long_account': 0.50,
            'short_account': 0.50,
            'liquidations_long_vol': 0.0,
            'liquidations_short_vol': 0.0,
        }
    
    def _get_default_macro(self) -> Dict[str, Any]:
        """Retorna dados macro padrão."""
        return {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'fear_greed_value': 50,
            'fear_greed_classification': 'Neutral',
            'btc_dominance': 48.0,
            'dxy': 100.0,
            'dxy_change_pct': 0.0,
            'stablecoin_exchange_flow_net': 0.0,
        }
    
    def get_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retorna resumo dos dados.
        
        Args:
            data: Dados carregados
            
        Returns:
            Dicionário com estatísticas
        """
        summary = {}
        
        for key in ['h1', 'h4', 'd1']:
            df = data.get(key)
            if df is not None and not df.empty:
                summary[key] = {
                    'length': len(df),
                    'start': df['timestamp'].iloc[0] if 'timestamp' in df.columns else 0,
                    'end': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else 0,
                    'columns': len(df.columns)
                }
            else:
                summary[key] = {'length': 0}
        
        summary['has_sentiment'] = data.get('sentiment') is not None
        summary['has_macro'] = data.get('macro') is not None
        summary['has_smc'] = data.get('smc') is not None
        
        return summary
