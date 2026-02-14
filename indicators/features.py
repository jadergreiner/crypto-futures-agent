"""
Engenharia de features para o modelo RL.
Constrói vetor de observação de ~104 features normalizadas.
"""

import logging
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Constrói observation space para o agente RL.
    ~104 features normalizadas entre [-1, 1] ou [0, 1].
    """
    
    @staticmethod
    def normalize_zscore(values: np.ndarray, window: int = 120) -> np.ndarray:
        """
        Normaliza usando Z-score com janela rolante.
        
        Args:
            values: Array de valores
            window: Janela para cálculo de média e std
            
        Returns:
            Array normalizado
        """
        if len(values) < window:
            window = len(values)
        
        if window < 2:
            return np.zeros_like(values)
        
        recent = values[-window:]
        mean = np.mean(recent)
        std = np.std(recent)
        
        if std == 0:
            return np.zeros_like(values)
        
        return (values - mean) / std
    
    @staticmethod
    def normalize_minmax(values: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
        """Normaliza para range [0, 1]."""
        if max_val == min_val:
            return np.full_like(values, 0.5)
        return (values - min_val) / (max_val - min_val)
    
    @staticmethod
    def build_observation(
        symbol: str,
        h1_data: Optional[pd.DataFrame],
        h4_data: Optional[pd.DataFrame],
        d1_data: Optional[pd.DataFrame],
        sentiment: Optional[Dict[str, Any]],
        macro: Optional[Dict[str, Any]],
        smc: Optional[Dict[str, Any]],
        position_state: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Constrói vetor de observação de 104 features.
        
        Args:
            symbol: Símbolo
            h1_data: DataFrame H1
            h4_data: DataFrame H4
            d1_data: DataFrame D1
            sentiment: Dados de sentimento
            macro: Dados macro
            smc: Estruturas SMC
            position_state: Estado da posição atual
            
        Returns:
            Array numpy de 104 features normalizadas
        """
        features = []
        
        # --- BLOCO 1: Preço (11 features) ---
        if h4_data is not None and not h4_data.empty:
            # Retornos em vários timeframes
            close = h4_data['close'].values
            if len(close) >= 5:
                ret_1h4 = (close[-1] - close[-2]) / close[-2] if close[-2] != 0 else 0
                ret_4h4 = (close[-1] - close[-5]) / close[-5] if close[-5] != 0 else 0
                features.extend([ret_1h4 * 100, ret_4h4 * 100])  # Percentual
            else:
                features.extend([0.0, 0.0])
            
            # Range atual
            if len(h4_data) >= 1:
                last = h4_data.iloc[-1]
                range_pct = ((last['high'] - last['low']) / last['close']) * 100 if last['close'] != 0 else 0
                features.append(range_pct)
            else:
                features.append(0.0)
            
            # EMA alignment score (já normalizado -6 a +6)
            if 'ema_alignment_score' in h4_data.columns:
                ema_score = h4_data['ema_alignment_score'].iloc[-1] / 6.0  # Normalizar para [-1, 1]
                features.append(ema_score)
            else:
                features.append(0.0)
        else:
            features.extend([0.0] * 4)
        
        # Retornos D1
        if d1_data is not None and not d1_data.empty and len(d1_data) >= 2:
            close_d1 = d1_data['close'].values
            ret_1d = (close_d1[-1] - close_d1[-2]) / close_d1[-2] if close_d1[-2] != 0 else 0
            features.append(ret_1d * 100)
        else:
            features.append(0.0)
        
        # Padding para completar 11
        while len(features) < 11:
            features.append(0.0)
        
        # --- BLOCO 2: EMAs (6 features) ---
        # Distância do close para cada EMA
        if h4_data is not None and not h4_data.empty:
            last = h4_data.iloc[-1]
            ema_periods = [17, 34, 72, 144, 305, 610]
            for period in ema_periods:
                col = f'ema_{period}'
                if col in h4_data.columns and not pd.isna(last[col]) and last[col] != 0:
                    dist_pct = ((last['close'] - last[col]) / last[col]) * 100
                    features.append(np.clip(dist_pct, -10, 10) / 10)  # Normalizar [-1, 1]
                else:
                    features.append(0.0)
        else:
            features.extend([0.0] * 6)
        
        # --- BLOCO 3: Indicadores (11 features) ---
        if h4_data is not None and not h4_data.empty:
            last = h4_data.iloc[-1]
            
            # RSI (0-100 -> 0-1)
            rsi = last.get('rsi_14', 50) / 100.0
            features.append(rsi)
            
            # MACD histogram normalizado
            macd_hist = last.get('macd_histogram', 0)
            features.append(np.tanh(macd_hist))  # Tanh para normalizar
            
            # Bollinger %B (já 0-1)
            bb_pct_b = last.get('bb_percent_b', 0.5)
            features.append(np.clip(bb_pct_b, 0, 1))
            
            # Bollinger bandwidth normalizado
            bb_bw = last.get('bb_bandwidth', 0.02)
            features.append(np.clip(bb_bw * 50, 0, 1))  # Scale
            
            # Volume normalizado (vs média)
            if len(h4_data) >= 20:
                vol_mean = h4_data['volume'].tail(20).mean()
                vol_ratio = last['volume'] / vol_mean if vol_mean > 0 else 1.0
                features.append(np.clip(vol_ratio, 0, 3) / 3)
            else:
                features.append(0.5)
            
            # OBV change
            if len(h4_data) >= 2 and 'obv' in h4_data.columns:
                obv_prev = h4_data['obv'].iloc[-2]
                obv_curr = h4_data['obv'].iloc[-1]
                obv_change = (obv_curr - obv_prev) / abs(obv_prev) if obv_prev != 0 else 0
                features.append(np.tanh(obv_change * 10))
            else:
                features.append(0.0)
            
            # ATR normalizado
            atr = last.get('atr_14', 0)
            atr_pct = (atr / last['close']) * 100 if last['close'] != 0 else 0
            features.append(np.clip(atr_pct, 0, 5) / 5)
            
            # ADX (0-100 -> 0-1)
            adx = last.get('adx_14', 20) / 100.0
            features.append(adx)
            
            # DI difference
            di_plus = last.get('di_plus', 20)
            di_minus = last.get('di_minus', 20)
            di_diff = (di_plus - di_minus) / 100.0
            features.append(np.clip(di_diff, -1, 1))
            
            # Volume Profile position
            vp_poc = last.get('vp_poc', last['close'])
            vp_position = (last['close'] - vp_poc) / last['close'] if last['close'] != 0 else 0
            features.append(np.clip(vp_position * 10, -1, 1))
            
            # VAH/VAL spread
            vp_vah = last.get('vp_vah', last['high'])
            vp_val = last.get('vp_val', last['low'])
            vp_spread = (vp_vah - vp_val) / last['close'] if last['close'] != 0 else 0
            features.append(np.clip(vp_spread * 10, 0, 1))
        else:
            features.extend([0.5] * 11)
        
        # --- BLOCO 4: SMC (19 features) ---
        smc_features = [0.0] * 19  # Default
        if smc:
            # Structure (3 features): bullish, bearish, range (one-hot)
            structure = smc.get('structure')
            if structure:
                if structure.type.value == "bullish":
                    smc_features[0:3] = [1, 0, 0]
                elif structure.type.value == "bearish":
                    smc_features[0:3] = [0, 1, 0]
                else:
                    smc_features[0:3] = [0, 0, 1]
            
            # BOS recente (2 features): bullish, bearish
            bos_list = smc.get('bos', [])
            if bos_list:
                recent_bos = bos_list[-1]
                if recent_bos.direction == "bullish":
                    smc_features[3:5] = [1, 0]
                else:
                    smc_features[3:5] = [0, 1]
            
            # CHoCH recente (2 features)
            choch_list = smc.get('choch', [])
            if choch_list:
                recent_choch = choch_list[-1]
                if recent_choch.direction == "bullish":
                    smc_features[5:7] = [1, 0]
                else:
                    smc_features[5:7] = [0, 1]
            
            # Order Blocks (4 features): contagem bullish/bearish FRESH, distância mais próximo
            obs = smc.get('order_blocks', [])
            bullish_obs = [ob for ob in obs if ob.type == "bullish" and ob.status.value == "FRESH"]
            bearish_obs = [ob for ob in obs if ob.type == "bearish" and ob.status.value == "FRESH"]
            
            smc_features[7] = min(len(bullish_obs), 5) / 5.0
            smc_features[8] = min(len(bearish_obs), 5) / 5.0
            
            # Distância para OB mais próximo
            if h4_data is not None and not h4_data.empty:
                current_price = h4_data['close'].iloc[-1]
                if bullish_obs:
                    closest_bull_ob = min(bullish_obs, key=lambda ob: abs(current_price - ob.zone_high))
                    dist_pct = ((current_price - closest_bull_ob.zone_high) / current_price) * 100
                    smc_features[9] = np.clip(dist_pct, -10, 10) / 10
                if bearish_obs:
                    closest_bear_ob = min(bearish_obs, key=lambda ob: abs(current_price - ob.zone_low))
                    dist_pct = ((current_price - closest_bear_ob.zone_low) / current_price) * 100
                    smc_features[10] = np.clip(dist_pct, -10, 10) / 10
            
            # FVGs (4 features): similar aos OBs
            fvgs = smc.get('fvgs', [])
            bullish_fvgs = [fvg for fvg in fvgs if fvg.type == "bullish" and fvg.status.value == "OPEN"]
            bearish_fvgs = [fvg for fvg in fvgs if fvg.type == "bearish" and fvg.status.value == "OPEN"]
            
            smc_features[11] = min(len(bullish_fvgs), 5) / 5.0
            smc_features[12] = min(len(bearish_fvgs), 5) / 5.0
            
            # Liquidity (2 features): sweeps recentes
            sweeps = smc.get('liquidity_sweeps', [])
            if sweeps and len(sweeps) > 0:
                recent_sweep = sweeps[-1]
                if recent_sweep.direction == "up":
                    smc_features[13:15] = [1, 0]
                else:
                    smc_features[13:15] = [0, 1]
            
            # Premium/Discount (4 features): position + zone one-hot
            premium_discount = smc.get('premium_discount')
            if premium_discount:
                smc_features[15] = premium_discount.position
                # Zone encoding simplificado
                zone_map = {
                    "DEEP_DISCOUNT": 0.0,
                    "DISCOUNT": 0.25,
                    "EQUILIBRIUM": 0.5,
                    "PREMIUM": 0.75,
                    "DEEP_PREMIUM": 1.0
                }
                smc_features[16] = zone_map.get(premium_discount.zone.name, 0.5)
        
        features.extend(smc_features[:19])
        
        # --- BLOCO 5: Sentimento (4 features) ---
        if sentiment:
            # Long/Short Ratio (normalizar em torno de 1.0)
            ls_ratio = sentiment.get('long_short_ratio', 1.0)
            features.append(np.clip((ls_ratio - 1.0) * 2, -1, 1))
            
            # OI Change
            oi_change = sentiment.get('open_interest_change_pct', 0)
            features.append(np.clip(oi_change / 10, -1, 1))
            
            # Funding Rate (normalizar -0.01 a 0.01)
            funding = sentiment.get('funding_rate', 0)
            features.append(np.clip(funding * 100, -1, 1))
            
            # Liquidation Imbalance
            liq_long = sentiment.get('liquidations_long_vol', 0)
            liq_short = sentiment.get('liquidations_short_vol', 0)
            total_liq = liq_long + liq_short
            if total_liq > 0:
                liq_imbalance = (liq_long - liq_short) / total_liq
                features.append(liq_imbalance)
            else:
                features.append(0.0)
        else:
            features.extend([0.0] * 4)
        
        # --- BLOCO 6: Macro (4 features) ---
        if macro:
            # DXY change
            dxy_change = macro.get('dxy_change_pct', 0)
            features.append(np.clip(dxy_change, -2, 2) / 2)
            
            # Fear & Greed (0-100 -> -1 a 1, com 50 = 0)
            fgi = macro.get('fear_greed_value', 50)
            features.append((fgi - 50) / 50)
            
            # BTC Dominance (normalizar em torno de 50%)
            btc_dom = macro.get('btc_dominance', 50)
            features.append((btc_dom - 50) / 50)
            
            # Stablecoin flow (normalizar)
            sc_flow = macro.get('stablecoin_exchange_flow_net', 0)
            features.append(np.tanh(sc_flow / 1e9))  # Bilhões
        else:
            features.extend([0.0] * 4)
        
        # --- BLOCO 7: Correlação (3 features) ---
        # Esses viriam de multi_timeframe analysis
        # Por simplicidade, usando placeholders
        features.extend([0.0, 0.0, 1.0])  # btc_return, correlation, beta
        
        # --- BLOCO 8: Contexto D1 (2 features) ---
        # D1 bias e regime (one-hot simplificado)
        d1_bias_score = 0.0  # -1 bearish, 0 neutro, 1 bullish
        regime_score = 0.0  # -1 risk_off, 0 neutro, 1 risk_on
        
        features.extend([d1_bias_score, regime_score])
        
        # --- BLOCO 9: Posição (5 features) ---
        if position_state and position_state.get('has_position', False):
            # Direção (1 long, -1 short, 0 flat)
            direction = 1.0 if position_state.get('direction') == 'LONG' else -1.0
            features.append(direction)
            
            # PnL %
            pnl_pct = position_state.get('pnl_pct', 0)
            features.append(np.clip(pnl_pct / 10, -1, 1))
            
            # Tempo na posição (normalizado 0-1, máx 100 horas)
            time_in_pos = position_state.get('time_in_position_hours', 0)
            features.append(min(time_in_pos / 100, 1.0))
            
            # Distância do stop
            stop_distance = position_state.get('stop_distance_pct', 2)
            features.append(min(stop_distance / 5, 1.0))
            
            # Distância do TP
            tp_distance = position_state.get('tp_distance_pct', 6)
            features.append(min(tp_distance / 10, 1.0))
        else:
            features.extend([0.0] * 5)
        
        # Garantir exatamente 104 features
        if len(features) < 104:
            features.extend([0.0] * (104 - len(features)))
        elif len(features) > 104:
            features = features[:104]
        
        # Converter para numpy array
        observation = np.array(features, dtype=np.float32)
        
        # Clip final para segurança
        observation = np.clip(observation, -10, 10)
        
        logger.debug(f"Built observation with {len(observation)} features")
        
        return observation
    
    @staticmethod
    def get_feature_names() -> List[str]:
        """
        Retorna nomes das features para debugging.
        
        Returns:
            Lista com nomes das 104 features
        """
        names = []
        
        # Bloco 1: Preço (11)
        names.extend(['ret_1h4', 'ret_4h4', 'range_pct', 'ema_score', 'ret_1d'])
        names.extend([f'price_{i}' for i in range(6)])  # Padding
        
        # Bloco 2: EMAs (6)
        names.extend([f'close_vs_ema_{p}' for p in [17, 34, 72, 144, 305, 610]])
        
        # Bloco 3: Indicadores (11)
        names.extend(['rsi', 'macd_hist', 'bb_pct_b', 'bb_bw', 'volume_ratio',
                     'obv_change', 'atr_pct', 'adx', 'di_diff', 'vp_position', 'vp_spread'])
        
        # Bloco 4: SMC (19)
        names.extend(['struct_bull', 'struct_bear', 'struct_range',
                     'bos_bull', 'bos_bear', 'choch_bull', 'choch_bear',
                     'ob_bull_count', 'ob_bear_count', 'ob_bull_dist', 'ob_bear_dist',
                     'fvg_bull_count', 'fvg_bear_count', 'fvg_bull_dist', 'fvg_bear_dist',
                     'sweep_up', 'sweep_down', 'prem_disc_pos', 'prem_disc_zone'])
        
        # Bloco 5: Sentimento (4)
        names.extend(['ls_ratio', 'oi_change', 'funding', 'liq_imbalance'])
        
        # Bloco 6: Macro (4)
        names.extend(['dxy_change', 'fear_greed', 'btc_dom', 'stablecoin_flow'])
        
        # Bloco 7: Correlação (3)
        names.extend(['btc_return', 'correlation', 'beta'])
        
        # Bloco 8: Contexto (2)
        names.extend(['d1_bias', 'market_regime'])
        
        # Bloco 9: Posição (5)
        names.extend(['position_direction', 'position_pnl', 'position_time',
                     'stop_distance', 'tp_distance'])
        
        return names
