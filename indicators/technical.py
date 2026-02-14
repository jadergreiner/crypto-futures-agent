"""
Cálculo de indicadores técnicos.
Inclui EMAs, RSI, MACD, Bollinger Bands, Volume Profile, OBV, ATR, ADX.
"""

import logging
from typing import Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Calcula todos os indicadores técnicos necessários para o agente.
    Usa numpy/pandas para cálculos eficientes.
    """
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """
        Calcula Exponential Moving Average.
        
        Args:
            data: Série de preços (geralmente 'close')
            period: Período da EMA
            
        Returns:
            Série com valores da EMA
        """
        if len(data) < period:
            logger.warning(f"Insufficient data for EMA({period}): {len(data)} < {period}")
            return pd.Series([np.nan] * len(data), index=data.index)
        
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcula Relative Strength Index.
        
        Args:
            data: Série de preços
            period: Período do RSI
            
        Returns:
            Série com valores do RSI (0-100)
        """
        if len(data) < period + 1:
            logger.warning(f"Insufficient data for RSI({period})")
            return pd.Series([np.nan] * len(data), index=data.index)
        
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, 
                       signal: int = 9) -> pd.DataFrame:
        """
        Calcula MACD (Moving Average Convergence Divergence).
        
        Args:
            data: Série de preços
            fast: Período EMA rápida
            slow: Período EMA lenta
            signal: Período da linha de sinal
            
        Returns:
            DataFrame com 'macd_line', 'macd_signal', 'macd_histogram'
        """
        if len(data) < slow:
            logger.warning(f"Insufficient data for MACD")
            return pd.DataFrame({
                'macd_line': [np.nan] * len(data),
                'macd_signal': [np.nan] * len(data),
                'macd_histogram': [np.nan] * len(data)
            }, index=data.index)
        
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        macd_histogram = macd_line - macd_signal
        
        return pd.DataFrame({
            'macd_line': macd_line,
            'macd_signal': macd_signal,
            'macd_histogram': macd_histogram
        })
    
    @staticmethod
    def calculate_bollinger(data: pd.Series, period: int = 20, 
                           std_dev: float = 2.0) -> pd.DataFrame:
        """
        Calcula Bollinger Bands.
        
        Args:
            data: Série de preços
            period: Período da média móvel
            std_dev: Número de desvios padrão
            
        Returns:
            DataFrame com 'bb_upper', 'bb_middle', 'bb_lower', 'bb_bandwidth', 'bb_percent_b'
        """
        if len(data) < period:
            logger.warning(f"Insufficient data for Bollinger Bands")
            return pd.DataFrame({
                'bb_upper': [np.nan] * len(data),
                'bb_middle': [np.nan] * len(data),
                'bb_lower': [np.nan] * len(data),
                'bb_bandwidth': [np.nan] * len(data),
                'bb_percent_b': [np.nan] * len(data)
            }, index=data.index)
        
        bb_middle = data.rolling(window=period).mean()
        bb_std = data.rolling(window=period).std()
        bb_upper = bb_middle + (bb_std * std_dev)
        bb_lower = bb_middle - (bb_std * std_dev)
        bb_bandwidth = (bb_upper - bb_lower) / bb_middle
        bb_percent_b = (data - bb_lower) / (bb_upper - bb_lower)
        
        return pd.DataFrame({
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'bb_bandwidth': bb_bandwidth,
            'bb_percent_b': bb_percent_b
        })
    
    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, lookback: int = 120) -> pd.DataFrame:
        """
        Calcula Volume Profile (POC, VAH, VAL).
        
        Args:
            df: DataFrame com 'high', 'low', 'close', 'volume'
            lookback: Período de lookback
            
        Returns:
            DataFrame com 'vp_poc', 'vp_vah', 'vp_val'
        """
        if len(df) < lookback:
            logger.warning(f"Insufficient data for Volume Profile")
            return pd.DataFrame({
                'vp_poc': [np.nan] * len(df),
                'vp_vah': [np.nan] * len(df),
                'vp_val': [np.nan] * len(df)
            }, index=df.index)
        
        poc_list = []
        vah_list = []
        val_list = []
        
        for i in range(len(df)):
            if i < lookback - 1:
                poc_list.append(np.nan)
                vah_list.append(np.nan)
                val_list.append(np.nan)
                continue
            
            window = df.iloc[i-lookback+1:i+1]
            
            # Simplified Volume Profile calculation
            # Create price bins and aggregate volume
            price_min = window['low'].min()
            price_max = window['high'].max()
            
            if price_max == price_min:
                poc_list.append(window['close'].iloc[-1])
                vah_list.append(price_max)
                val_list.append(price_min)
                continue
            
            bins = np.linspace(price_min, price_max, 50)
            volume_at_price = np.zeros(len(bins) - 1)
            
            for _, row in window.iterrows():
                # Distribute volume across the price range of the candle
                low_idx = np.digitize(row['low'], bins) - 1
                high_idx = np.digitize(row['high'], bins) - 1
                
                if low_idx == high_idx:
                    if 0 <= low_idx < len(volume_at_price):
                        volume_at_price[low_idx] += row['volume']
                else:
                    for j in range(max(0, low_idx), min(len(volume_at_price), high_idx + 1)):
                        volume_at_price[j] += row['volume'] / (high_idx - low_idx + 1)
            
            # POC: Point of Control (price with highest volume)
            poc_idx = np.argmax(volume_at_price)
            poc = (bins[poc_idx] + bins[poc_idx + 1]) / 2
            
            # VAH/VAL: Value Area High/Low (70% of volume)
            total_volume = volume_at_price.sum()
            target_volume = total_volume * 0.7
            
            accumulated = 0
            val_idx = poc_idx
            vah_idx = poc_idx
            
            # Expand from POC until 70% volume
            while accumulated < target_volume:
                if val_idx > 0:
                    accumulated += volume_at_price[val_idx - 1]
                    val_idx -= 1
                if accumulated < target_volume and vah_idx < len(volume_at_price) - 1:
                    accumulated += volume_at_price[vah_idx + 1]
                    vah_idx += 1
                if val_idx == 0 and vah_idx == len(volume_at_price) - 1:
                    break
            
            val = (bins[val_idx] + bins[val_idx + 1]) / 2
            vah = (bins[vah_idx] + bins[vah_idx + 1]) / 2
            
            poc_list.append(poc)
            vah_list.append(vah)
            val_list.append(val)
        
        return pd.DataFrame({
            'vp_poc': poc_list,
            'vp_vah': vah_list,
            'vp_val': val_list
        }, index=df.index)
    
    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """
        Calcula On Balance Volume.
        
        Args:
            df: DataFrame com 'close' e 'volume'
            
        Returns:
            Série com valores do OBV
        """
        obv = [0]
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        return pd.Series(obv, index=df.index)
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calcula Average True Range.
        
        Args:
            df: DataFrame com 'high', 'low', 'close'
            period: Período do ATR
            
        Returns:
            Série com valores do ATR
        """
        if len(df) < period + 1:
            logger.warning(f"Insufficient data for ATR({period})")
            return pd.Series([np.nan] * len(df), index=df.index)
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calcula ADX (Average Directional Index) e DI+/DI-.
        
        Args:
            df: DataFrame com 'high', 'low', 'close'
            period: Período do ADX
            
        Returns:
            DataFrame com 'adx_14', 'di_plus', 'di_minus'
        """
        if len(df) < period * 2:
            logger.warning(f"Insufficient data for ADX({period})")
            return pd.DataFrame({
                'adx_14': [np.nan] * len(df),
                'di_plus': [np.nan] * len(df),
                'di_minus': [np.nan] * len(df)
            }, index=df.index)
        
        # Calculate True Range
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        up_move = df['high'] - df['high'].shift()
        down_move = df['low'].shift() - df['low']
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_dm = pd.Series(plus_dm, index=df.index)
        minus_dm = pd.Series(minus_dm, index=df.index)
        
        # Smooth with EMA
        atr = true_range.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
        
        # Calculate ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return pd.DataFrame({
            'adx_14': adx,
            'di_plus': plus_di,
            'di_minus': minus_di
        })
    
    @staticmethod
    def calculate_ema_alignment_score(df: pd.DataFrame) -> pd.Series:
        """
        Calcula score de alinhamento das EMAs (-6 a +6).
        
        Args:
            df: DataFrame com as colunas 'ema_17', 'ema_34', 'ema_72', 'ema_144', 'ema_305', 'ema_610'
            
        Returns:
            Série com score de alinhamento
        """
        emas = ['ema_17', 'ema_34', 'ema_72', 'ema_144', 'ema_305', 'ema_610']
        
        if not all(col in df.columns for col in emas):
            logger.warning("Not all EMAs present for alignment score")
            return pd.Series([0] * len(df), index=df.index)
        
        scores = []
        
        for i in range(len(df)):
            # Check if all EMAs are aligned in ascending order (bullish)
            bullish = True
            bearish = True
            
            for j in range(len(emas) - 1):
                if pd.isna(df[emas[j]].iloc[i]) or pd.isna(df[emas[j+1]].iloc[i]):
                    bullish = False
                    bearish = False
                    break
                
                if df[emas[j]].iloc[i] <= df[emas[j+1]].iloc[i]:
                    bullish = False
                if df[emas[j]].iloc[i] >= df[emas[j+1]].iloc[i]:
                    bearish = False
            
            if bullish:
                scores.append(6)
            elif bearish:
                scores.append(-6)
            else:
                # Partial alignment - count aligned pairs
                aligned_up = 0
                aligned_down = 0
                for j in range(len(emas) - 1):
                    if pd.isna(df[emas[j]].iloc[i]) or pd.isna(df[emas[j+1]].iloc[i]):
                        continue
                    if df[emas[j]].iloc[i] > df[emas[j+1]].iloc[i]:
                        aligned_up += 1
                    elif df[emas[j]].iloc[i] < df[emas[j+1]].iloc[i]:
                        aligned_down += 1
                
                if aligned_up > aligned_down:
                    scores.append(aligned_up)
                elif aligned_down > aligned_up:
                    scores.append(-aligned_down)
                else:
                    scores.append(0)
        
        return pd.Series(scores, index=df.index)
    
    @classmethod
    def calculate_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula todos os indicadores técnicos.
        
        Args:
            df: DataFrame com OHLCV ('open', 'high', 'low', 'close', 'volume')
            
        Returns:
            DataFrame com todos os indicadores
        """
        if df.empty or len(df) < 2:
            logger.error("DataFrame empty or insufficient for indicators")
            return df
        
        result = df.copy()
        
        # EMAs
        ema_periods = [17, 34, 72, 144, 305, 610]
        for period in ema_periods:
            result[f'ema_{period}'] = cls.calculate_ema(df['close'], period)
        
        # RSI
        result['rsi_14'] = cls.calculate_rsi(df['close'], 14)
        
        # MACD
        macd_df = cls.calculate_macd(df['close'])
        result = pd.concat([result, macd_df], axis=1)
        
        # Bollinger Bands
        bb_df = cls.calculate_bollinger(df['close'])
        result = pd.concat([result, bb_df], axis=1)
        
        # Volume Profile
        vp_df = cls.calculate_volume_profile(df)
        result = pd.concat([result, vp_df], axis=1)
        
        # OBV
        result['obv'] = cls.calculate_obv(df)
        
        # ATR
        result['atr_14'] = cls.calculate_atr(df, 14)
        
        # ADX
        adx_df = cls.calculate_adx(df, 14)
        result = pd.concat([result, adx_df], axis=1)
        
        # EMA Alignment Score
        result['ema_alignment_score'] = cls.calculate_ema_alignment_score(result)
        
        logger.info(f"Calculated all technical indicators for {len(df)} candles")
        
        return result
