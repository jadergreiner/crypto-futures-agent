"""
Análise multi-timeframe e agregação de dados.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MultiTimeframeAnalysis:
    """
    Agrega e analisa dados de múltiplos timeframes (D1, H4, H1).
    Fornece bias direcional e regime de mercado.
    """
    
    @staticmethod
    def get_d1_bias(d1_indicators: pd.DataFrame) -> str:
        """
        Determina bias D1: BULLISH, BEARISH ou NEUTRO.
        
        Args:
            d1_indicators: DataFrame com indicadores D1
            
        Returns:
            "BULLISH", "BEARISH" ou "NEUTRO"
        """
        if d1_indicators.empty:
            return "NEUTRO"
        
        # Pegar última linha
        last = d1_indicators.iloc[-1]
        
        # Verificar se temos todos os dados necessários
        required_cols = ['ema_alignment_score', 'adx_14', 'di_plus', 'di_minus', 'rsi_14']
        if not all(col in d1_indicators.columns for col in required_cols):
            logger.warning("Missing required columns for D1 bias")
            return "NEUTRO"
        
        if pd.isna(last['ema_alignment_score']) or pd.isna(last['adx_14']):
            return "NEUTRO"
        
        # Critérios para BULLISH
        bullish_conditions = [
            last['ema_alignment_score'] >= 4,  # EMAs alinhadas para cima
            last['adx_14'] > 25,  # Tendência forte
            last['di_plus'] > last['di_minus'],  # DI+ dominante
            45 <= last['rsi_14'] <= 75  # RSI em zona bullish
        ]
        
        # Critérios para BEARISH
        bearish_conditions = [
            last['ema_alignment_score'] <= -4,  # EMAs alinhadas para baixo
            last['adx_14'] > 25,  # Tendência forte
            last['di_minus'] > last['di_plus'],  # DI- dominante
            25 <= last['rsi_14'] <= 55  # RSI em zona bearish
        ]
        
        if sum(bullish_conditions) >= 3:
            return "BULLISH"
        elif sum(bearish_conditions) >= 3:
            return "BEARISH"
        else:
            return "NEUTRO"
    
    @staticmethod
    def get_market_regime(d1_indicators: pd.DataFrame, macro_data: Dict[str, Any]) -> str:
        """
        Determina regime de mercado: RISK_ON, RISK_OFF ou NEUTRO.
        
        Args:
            d1_indicators: Indicadores D1
            macro_data: Dados macroeconômicos
            
        Returns:
            "RISK_ON", "RISK_OFF" ou "NEUTRO"
        """
        if d1_indicators.empty or not macro_data:
            return "NEUTRO"
        
        risk_on_score = 0
        risk_off_score = 0
        
        # Fear & Greed Index
        fgi = macro_data.get('fear_greed_value', 50)
        if fgi >= 60:  # Greed
            risk_on_score += 1
        elif fgi <= 40:  # Fear
            risk_off_score += 1
        
        # DXY
        dxy_change = macro_data.get('dxy_change_pct', 0)
        if dxy_change < -0.5:  # DXY caindo = risk on
            risk_on_score += 1
        elif dxy_change > 0.5:  # DXY subindo = risk off
            risk_off_score += 1
        
        # BTC Dominance
        btc_dom = macro_data.get('btc_dominance', 50)
        if btc_dom < 45:  # Baixa dominância = altseason = risk on
            risk_on_score += 1
        elif btc_dom > 55:  # Alta dominância = risk off
            risk_off_score += 1
        
        # Tendência D1
        if not d1_indicators.empty:
            last = d1_indicators.iloc[-1]
            if not pd.isna(last.get('ema_alignment_score')):
                if last['ema_alignment_score'] >= 3:
                    risk_on_score += 1
                elif last['ema_alignment_score'] <= -3:
                    risk_off_score += 1
        
        if risk_on_score > risk_off_score:
            return "RISK_ON"
        elif risk_off_score > risk_on_score:
            return "RISK_OFF"
        else:
            return "NEUTRO"
    
    @staticmethod
    def calculate_correlation(symbol_data: pd.Series, btc_data: pd.Series, 
                             lookback: int = 30) -> float:
        """
        Calcula correlação com BTC.
        
        Args:
            symbol_data: Série de preços do símbolo
            btc_data: Série de preços do BTC
            lookback: Período de lookback
            
        Returns:
            Correlação (-1 a 1)
        """
        if len(symbol_data) < lookback or len(btc_data) < lookback:
            return 0.0
        
        # Pegar últimos N períodos
        symbol_recent = symbol_data.tail(lookback)
        btc_recent = btc_data.tail(lookback)
        
        # Alinhar índices
        common_idx = symbol_recent.index.intersection(btc_recent.index)
        if len(common_idx) < lookback // 2:
            return 0.0
        
        symbol_aligned = symbol_recent.loc[common_idx]
        btc_aligned = btc_recent.loc[common_idx]
        
        # Calcular retornos
        symbol_returns = symbol_aligned.pct_change().dropna()
        btc_returns = btc_aligned.pct_change().dropna()
        
        if len(symbol_returns) < 10 or len(btc_returns) < 10:
            return 0.0
        
        correlation = symbol_returns.corr(btc_returns)
        
        return float(correlation) if not pd.isna(correlation) else 0.0
    
    @staticmethod
    def calculate_beta(symbol_data: pd.Series, btc_data: pd.Series, 
                      lookback: int = 30) -> float:
        """
        Calcula beta em relação ao BTC.
        
        Args:
            symbol_data: Série de preços do símbolo
            btc_data: Série de preços do BTC
            lookback: Período de lookback
            
        Returns:
            Beta (sensibilidade ao BTC)
        """
        if len(symbol_data) < lookback or len(btc_data) < lookback:
            return 1.0
        
        # Pegar últimos N períodos
        symbol_recent = symbol_data.tail(lookback)
        btc_recent = btc_data.tail(lookback)
        
        # Alinhar índices
        common_idx = symbol_recent.index.intersection(btc_recent.index)
        if len(common_idx) < lookback // 2:
            return 1.0
        
        symbol_aligned = symbol_recent.loc[common_idx]
        btc_aligned = btc_recent.loc[common_idx]
        
        # Calcular retornos
        symbol_returns = symbol_aligned.pct_change().dropna()
        btc_returns = btc_aligned.pct_change().dropna()
        
        if len(symbol_returns) < 10 or len(btc_returns) < 10:
            return 1.0
        
        # Beta = Cov(symbol, btc) / Var(btc)
        covariance = symbol_returns.cov(btc_returns)
        btc_variance = btc_returns.var()
        
        if btc_variance == 0:
            return 1.0
        
        beta = covariance / btc_variance
        
        return float(beta) if not pd.isna(beta) else 1.0
    
    @classmethod
    def aggregate(cls, h1_data: pd.DataFrame, h4_data: pd.DataFrame, 
                  d1_data: pd.DataFrame, symbol: str, 
                  macro_data: Optional[Dict[str, Any]] = None,
                  btc_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Agrega análise multi-timeframe.
        
        Args:
            h1_data: DataFrame H1 com indicadores
            h4_data: DataFrame H4 com indicadores
            d1_data: DataFrame D1 com indicadores
            symbol: Símbolo sendo analisado
            macro_data: Dados macro
            btc_data: Dados do BTC para correlação (opcional)
            
        Returns:
            Dicionário com análise agregada
        """
        result = {
            'symbol': symbol,
            'd1_bias': "NEUTRO",
            'market_regime': "NEUTRO",
            'correlation_btc': 0.0,
            'beta_btc': 1.0
        }
        
        # D1 Bias
        if not d1_data.empty:
            result['d1_bias'] = cls.get_d1_bias(d1_data)
        
        # Market Regime
        if macro_data:
            result['market_regime'] = cls.get_market_regime(d1_data, macro_data)
        
        # Correlação e Beta com BTC
        if btc_data is not None and not btc_data.empty and not h4_data.empty:
            if symbol != "BTCUSDT":
                try:
                    result['correlation_btc'] = cls.calculate_correlation(
                        h4_data['close'], btc_data['close'], lookback=30
                    )
                    result['beta_btc'] = cls.calculate_beta(
                        h4_data['close'], btc_data['close'], lookback=30
                    )
                except Exception as e:
                    logger.warning(f"Failed to calculate correlation/beta: {e}")
            else:
                result['correlation_btc'] = 1.0
                result['beta_btc'] = 1.0
        
        logger.info(f"Multi-timeframe analysis for {symbol}: "
                   f"D1={result['d1_bias']}, Regime={result['market_regime']}")
        
        return result
