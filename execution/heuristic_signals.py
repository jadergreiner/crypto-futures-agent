"""
Heurísticas Conservadoras de Trading — TASK-001 Implementation.

Gera sinais de trading via regras hand-crafted conservadoras:
  - SMC (Smart Money Concepts): Order Blocks, FVG, Break of Structure
  - EMA Alignment: Daily → 4h → 1h confirmation
  - RSI Oversold/Overbought detection
  - ADX Trending confirmation
  - Risk Gates: Drawdown 5%, Circuit breaker -3%
  - Signal confidence threshold: >70%

Módulos:
  logging: Auditoria e rastreamento de sinais
  pandas: Análise de dados de preços
  numpy: Operações numéricas
  indicators: SMC, TechnicalIndicators, MultiTimeframeAnalysis
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np

from indicators.smc import SmartMoneyConcepts
from indicators.technical import TechnicalIndicators
from indicators.multi_timeframe import MultiTimeframeAnalysis

logger = logging.getLogger(__name__)


@dataclass
class SignalComponent:
    """Componente individual de um sinal."""
    name: str  # "smc", "ema_alignment", "rsi", "adx"
    value: float
    threshold: float
    is_valid: bool
    confidence: float  # 0-1


@dataclass
class HeuristicSignal:
    """Sinal gerado por heurísticas."""
    symbol: str
    timestamp: int
    signal_type: str  # "BUY", "SELL" ou "NEUTRAL"
    components: List[SignalComponent]
    confidence: float  # 0-100
    confluence_score: int  # Número de componentes concordando (máx 14)
    market_regime: str  # "RISK_ON", "RISK_OFF", "NEUTRO"
    d1_bias: str  # "BULLISH", "BEARISH", "NEUTRO"
    risk_assessment: str  # "CLEARED", "RISKY", "BLOCKED"
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward_ratio: Optional[float]
    audit_trail: Dict[str, Any]


class RiskGate:
    """
    Gates de risco inline — Protege contra drawdown excessivo e circuit breaker.

    - CLEARED: 0-3% drawdown (aceita trades)
    - RISKY: 3-5% drawdown (reduz volume)
    - BLOCKED: > 5% drawdown (bloqueia tudo)
    """

    def __init__(self, max_drawdown_pct: float = 3.0, circuit_breaker_pct: float = 5.0):
        """
        Inicializa risk gates.

        Args:
            max_drawdown_pct: Máximo drawdown CLEARED (padrão -3%, valor 3.0)
            circuit_breaker_pct: Nível BLOCKED (padrão -5%, valor 5.0)
        """
        self.max_drawdown_pct = max_drawdown_pct  # 3.0 = -3%
        self.circuit_breaker_pct = circuit_breaker_pct  # 5.0 = -5%
        self.peak_capital = None
        self.current_drawdown = 0.0

    def evaluate(self, current_balance: float, session_peak: float) -> Tuple[str, str]:
        """
        Avalia risk gates.

        Args:
            current_balance: Saldo atual
            session_peak: Pico da sessão

        Returns:
            (status: "CLEARED" | "RISKY" | "BLOCKED", message: str)
        """
        if session_peak <= 0:
            return "CLEARED", "Sem histórico de sessão"

        drawdown_pct = ((current_balance - session_peak) / session_peak) * 100
        drawdown_abs = abs(drawdown_pct)
        self.current_drawdown = drawdown_pct

        # Zonas de drawdown magnitude:
        # CLEARED: 0-3% (e.g., -1%, -2.5%)
        # RISKY: 3.0-5.0% (e.g., -3.5%, -4.5%)
        # BLOCKED: > 5.0% (e.g., -5.5%, -6%)

        if drawdown_abs >= self.circuit_breaker_pct:
            return "BLOCKED", f"🚨 Circuit breaker ativado: {drawdown_pct:.2f}% exceeds {-self.circuit_breaker_pct}%"

        if drawdown_abs >= self.max_drawdown_pct:
            return "RISKY", f"⚠️  Drawdown alto: {drawdown_pct:.2f}% (máximo CLEARED: {-self.max_drawdown_pct}%)"

        return "CLEARED", f"✓ Drawdown dentro dos limites: {drawdown_pct:.2f}%"


class HeuristicSignalGenerator:
    """Gerador de sinais heurísticos com validações conservadoras."""

    def __init__(self, risk_gate: Optional[RiskGate] = None):
        """
        Inicializa o gerador de sinais.

        Args:
            risk_gate: Instância de RiskGate (cria uma nova se não fornecida)
        """
        self.risk_gate = risk_gate or RiskGate()
        self.tech_ind = TechnicalIndicators()
        self.mtf = MultiTimeframeAnalysis()

        logger.info("HeuristicSignalGenerator inicializado")

    def generate_signal(
        self,
        symbol: str,
        d1_ohlcv: pd.DataFrame,
        h4_ohlcv: pd.DataFrame,
        h1_ohlcv: pd.DataFrame,
        macro_data: Dict[str, Any],
        current_balance: float,
        session_peak: float,
    ) -> HeuristicSignal:
        """
        Gera sinal heurístico consolidado com validações.

        Args:
            symbol: Símbolo (ex: "BTCUSDT")
            d1_ohlcv: OHLCV DataFrame Daily
            h4_ohlcv: OHLCV DataFrame 4h
            h1_ohlcv: OHLCV DataFrame 1h
            macro_data: Dados macroeconômicos
            current_balance: Saldo atual
            session_peak: Pico de saldo da sessão

        Returns:
            HeuristicSignal object
        """
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        audit = {}
        components = []

        # === RISK GATE ===
        risk_status, risk_msg = self.risk_gate.evaluate(current_balance, session_peak)
        audit["risk_gate"] = {"status": risk_status, "message": risk_msg}
        logger.info(f"{symbol} Risk Gate: {risk_msg}")

        # === SMC VALIDATION ===
        smc_signal, smc_confidence = self._validate_smc(symbol, h1_ohlcv, audit)
        components.append(SignalComponent(
            name="smc",
            value=1.0 if smc_signal != "NEUTRAL" else 0.0,
            threshold=1.0,
            is_valid=smc_signal != "NEUTRAL",
            confidence=smc_confidence
        ))

        # === EMA ALIGNMENT ===
        ema_signal, ema_confidence = self._validate_ema_alignment(symbol, d1_ohlcv, h4_ohlcv, h1_ohlcv, audit)
        components.append(SignalComponent(
            name="ema_alignment",
            value=1.0 if ema_signal != "NEUTRAL" else 0.0,
            threshold=1.0,
            is_valid=ema_signal != "NEUTRAL",
            confidence=ema_confidence
        ))

        # === RSI VALIDATION ===
        rsi_signal, rsi_confidence = self._validate_rsi(symbol, h1_ohlcv, audit)
        components.append(SignalComponent(
            name="rsi",
            value=1.0 if rsi_signal != "NEUTRAL" else 0.0,
            threshold=1.0,
            is_valid=rsi_signal != "NEUTRAL",
            confidence=rsi_confidence
        ))

        # === ADX CONFIRMATION ===
        adx_signal, adx_confidence = self._validate_adx(symbol, h1_ohlcv, audit)
        components.append(SignalComponent(
            name="adx",
            value=1.0 if adx_signal else 0.0,
            threshold=1.0,
            is_valid=adx_signal,
            confidence=adx_confidence
        ))

        # === MARKET REGIME ===
        regime = self.mtf.get_market_regime(d1_ohlcv, macro_data)
        d1_bias = self.mtf.get_d1_bias(d1_ohlcv)
        audit["market_regime"] = regime
        audit["d1_bias"] = d1_bias

        # === CONFLUÊNCIA & DECISÃO ===
        confluence = sum(1 for c in components if c.is_valid)
        overall_confidence = self._calculate_overall_confidence(components, regime, risk_status)

        # Sinalize apenas se confluence >= 3 e confiança > 70
        final_signal = self._determine_final_signal(
            smc_signal, ema_signal, rsi_signal, adx_signal,
            confluence, overall_confidence, regime, risk_status
        )

        # === PREÇOS & R:R ===
        current_price = h1_ohlcv['close'].iloc[-1] if len(h1_ohlcv) > 0 else 0.0
        sl_price, tp_price = self._calculate_sl_tp(symbol, final_signal, h1_ohlcv, audit)
        rr_ratio = self._calculate_rr_ratio(current_price, sl_price, tp_price) if (sl_price and tp_price) else None

        # === SINAL FINAL ===
        signal = HeuristicSignal(
            symbol=symbol,
            timestamp=timestamp,
            signal_type=final_signal,
            components=components,
            confidence=overall_confidence,
            confluence_score=confluence,
            market_regime=regime,
            d1_bias=d1_bias,
            risk_assessment=risk_status,
            entry_price=current_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            risk_reward_ratio=rr_ratio,
            audit_trail=audit
        )

        # === LOGGING ===
        self._log_signal(signal)

        return signal

    def _validate_smc(self, symbol: str, h1_ohlcv: pd.DataFrame, audit: Dict) -> Tuple[str, float]:
        """
        Valida SMC: Estrutura de swings, trends, Order Blocks, e BOS.

        Validações:
        - Volume threshold: 1.5× SMA(20) para Order Blocks válidos
        - Edge cases: gaps noturnos, ranging markets, liquidação sweeps

        Returns: ("BUY" | "SELL" | "NEUTRAL", confidence 0-1)
        """
        try:
            if len(h1_ohlcv) < 50:
                audit["smc"] = {"status": "INSUFFICIENT_DATA", "confidence": 0.0}
                return "NEUTRAL", 0.0

            # Adicionar timestamp e volume se não existirem
            df = h1_ohlcv.copy()
            if 'timestamp' not in df.columns:
                df['timestamp'] = [int(i * 3600 * 1000) for i in range(len(df))]
            if 'volume' not in df.columns:
                df['volume'] = 0.0  # Fallback se volume não disponível
                has_volume = False
            else:
                has_volume = True

            # === EDGE CASE VALIDATIONS ===
            edge_case_flags = {
                "gaps_detected": False,
                "ranging_market": False,
                "low_liquidity": False
            }

            # Detectar gaps noturnos (gap > 1% entre velas)
            if len(df) > 2:
                for i in range(1, len(df)):
                    price_prev_close = df['close'].iloc[i-1]
                    price_curr_open = df['open'].iloc[i]
                    if price_prev_close > 0:
                        gap_pct = abs((price_curr_open - price_prev_close) / price_prev_close) * 100
                        if gap_pct > 1.0:
                            edge_case_flags["gaps_detected"] = True
                            break

            # Validar ranging market (ATR < 0.5%)
            if 'high' in df.columns and 'low' in df.columns:
                atr_range = (df['high'].iloc[-20:].max() - df['low'].iloc[-20:].min()) / df['close'].iloc[-1] * 100
                if atr_range < 0.5:
                    edge_case_flags["ranging_market"] = True

            # Validar low liquidity (volume médio < threshold)
            if has_volume and 'volume' in df.columns:
                vol_mean = df['volume'].tail(20).mean()
                if vol_mean < 100:  # Volume mínimo absoluto
                    edge_case_flags["low_liquidity"] = True

            # Rejeitar sinal se edge case crítico
            if edge_case_flags["gaps_detected"] and edge_case_flags["ranging_market"]:
                audit["smc"] = {
                    "status": "EDGE_CASE_REJECTION",
                    "reason": "Gaps + ranging market detected",
                    "edge_cases": edge_case_flags,
                    "confidence": 0.0
                }
                return "NEUTRAL", 0.0

            # Detectar swing points
            swings = SmartMoneyConcepts.detect_swing_points(df, lookback=5)

            if len(swings) < 4:
                audit["smc"] = {"status": "INSUFFICIENT_SWINGS", "confidence": 0.0}
                return "NEUTRAL", 0.0

            # Detectar market structure
            market_structure = SmartMoneyConcepts.detect_market_structure(swings)

            # Score baseado em estrutura
            smc_score = 0.0
            confidence = 0.0
            signal = "NEUTRAL"

            if market_structure.type.value == "bullish":
                signal = "BUY"
                smc_score = 0.6
                confidence = 0.65  # Reduzido pois precisa confirmação
            elif market_structure.type.value == "bearish":
                signal = "SELL"
                smc_score = -0.6
                confidence = 0.65
            else:  # RANGE
                confidence = 0.3

            # Detectar BOS para aumentar confiança
            bos_list = SmartMoneyConcepts.detect_bos(df, swings)
            bos_count_initial = len(bos_list)

            if bos_list:
                if bos_list[-1].direction == "bullish" and signal == "BUY":
                    confidence = min(confidence + 0.15, 1.0)
                elif bos_list[-1].direction == "bearish" and signal == "SELL":
                    confidence = min(confidence + 0.15, 1.0)

            # === INTEGRAÇÃO ORDER BLOCKS COM VOLUME THRESHOLD ===
            order_blocks = SmartMoneyConcepts.detect_order_blocks(
                df, swings, bos_list,
                max_obs=10,
                lookback=20,
                volume_threshold=1.5  # 1.5× SMA(20) para validar OB
            )

            # Aumentar confiança se order blocks confirmado BOS
            ob_confluence = 0.0
            if order_blocks and bos_list:
                # Validar que OB está "alinhado" com BOS (mesmo timeframe)
                last_ob = order_blocks[-1]
                last_bos = bos_list[-1]

                if last_ob.type == last_bos.direction:
                    ob_confluence = 0.1  # +10% confiança se OB aligned
                    confidence = min(confidence + ob_confluence, 1.0)
                    logger.debug(
                        f"{symbol} OB confluence: {last_ob.type} aligned "
                        f"with BOS {last_bos.direction}"
                    )

            audit["smc"] = {
                "status": "VALID",
                "signal": signal,
                "structure": market_structure.type.value,
                "swing_count": len(swings),
                "bos_count": bos_count_initial,
                "order_block_count": len(order_blocks),
                "edge_cases": edge_case_flags,
                "ob_confluence": ob_confluence,
                "confidence": float(confidence)
            }

            logger.debug(f"{symbol} SMC validated: {signal} (conf={confidence:.2f})")
            return signal, confidence

        except Exception as e:
            logger.error(f"{symbol} SMC validation error: {str(e)}")
            audit["smc"] = {"status": "ERROR", "error": str(e), "confidence": 0.0}
            return "NEUTRAL", 0.0

    def _validate_ema_alignment(
        self, symbol: str, d1: pd.DataFrame, h4: pd.DataFrame, h1: pd.DataFrame, audit: Dict
    ) -> Tuple[str, float]:
        """
        Valida alinhamento EMA: D1 → H4 → H1.

        Returns: ("BUY" | "SELL" | "NEUTRAL", confidence 0-1)
        """
        try:
            if len(d1) < 100 or len(h4) < 50 or len(h1) < 50:
                audit["ema_alignment"] = {"status": "INSUFFICIENT_DATA", "confidence": 0.0}
                return "NEUTRAL", 0.0

            # Calcular EMAs para cada timeframe
            d1_ema_9 = self.tech_ind.calculate_ema(d1['close'], 9).iloc[-1]
            d1_ema_21 = self.tech_ind.calculate_ema(d1['close'], 21).iloc[-1]
            d1_ema_50 = self.tech_ind.calculate_ema(d1['close'], 50).iloc[-1]

            h4_ema_9 = self.tech_ind.calculate_ema(h4['close'], 9).iloc[-1]
            h4_ema_21 = self.tech_ind.calculate_ema(h4['close'], 21).iloc[-1]

            h1_ema_9 = self.tech_ind.calculate_ema(h1['close'], 9).iloc[-1]
            h1_ema_21 = self.tech_ind.calculate_ema(h1['close'], 21).iloc[-1]

            d1_current = d1['close'].iloc[-1]
            h4_current = h4['close'].iloc[-1]
            h1_current = h1['close'].iloc[-1]

            # Score bullish: EMAs em ordem crescente (9 < 21 < 50)
            bullish_score = 0.0
            if d1_ema_9 > d1_ema_21 > d1_ema_50:
                bullish_score += 0.4  # D1 bullish
            if h4_ema_9 > h4_ema_21:
                bullish_score += 0.3  # H4 bullish
            if h1_ema_9 > h1_ema_21:
                bullish_score += 0.3  # H1 bullish

            # Score bearish: EMAs em ordem decrescente
            bearish_score = 0.0
            if d1_ema_9 < d1_ema_21 < d1_ema_50:
                bearish_score += 0.4
            if h4_ema_9 < h4_ema_21:
                bearish_score += 0.3
            if h1_ema_9 < h1_ema_21:
                bearish_score += 0.3

            confidence = max(bullish_score, bearish_score)
            signal = "BUY" if bullish_score > bearish_score and confidence > 0.4 else (
                "SELL" if bearish_score > bullish_score and confidence > 0.4 else "NEUTRAL"
            )

            audit["ema_alignment"] = {
                "status": "VALID",
                "signal": signal,
                "bullish_score": float(bullish_score),
                "bearish_score": float(bearish_score),
                "confidence": float(confidence),
                "d1_ema_9": float(d1_ema_9),
                "d1_ema_21": float(d1_ema_21),
                "d1_ema_50": float(d1_ema_50),
            }

            return signal, confidence

        except Exception as e:
            logger.error(f"{symbol} EMA alignment error: {str(e)}")
            audit["ema_alignment"] = {"status": "ERROR", "error": str(e), "confidence": 0.0}
            return "NEUTRAL", 0.0

    def _validate_rsi(self, symbol: str, h1: pd.DataFrame, audit: Dict) -> Tuple[str, float]:
        """
        Valida RSI: Oversold/Overbought.

        Returns: ("BUY" | "SELL" | "NEUTRAL", confidence 0-1)
        """
        try:
            if len(h1) < 20:
                audit["rsi"] = {"status": "INSUFFICIENT_DATA", "confidence": 0.0}
                return "NEUTRAL", 0.0

            rsi = self.tech_ind.calculate_rsi(h1['close'], 14).iloc[-1]

            # Oversold: RSI < 30 → potencial BUY
            if pd.isna(rsi):
                audit["rsi"] = {"status": "NAN_VALUE", "confidence": 0.0}
                return "NEUTRAL", 0.0

            signal = "NEUTRAL"
            confidence = 0.0

            if rsi < 30:
                signal = "BUY"
                confidence = (30 - rsi) / 30  # Quanto mais oversold, mais confiante
            elif rsi > 70:
                signal = "SELL"
                confidence = (rsi - 70) / 30  # Quanto mais overbought, mais confiante
            else:
                confidence = 0.2  # Mínima confiança

            audit["rsi"] = {
                "status": "VALID",
                "signal": signal,
                "rsi_value": float(rsi),
                "confidence": float(min(confidence, 1.0))
            }

            return signal, min(confidence, 1.0)

        except Exception as e:
            logger.error(f"{symbol} RSI validation error: {str(e)}")
            audit["rsi"] = {"status": "ERROR", "error": str(e), "confidence": 0.0}
            return "NEUTRAL", 0.0

    def _validate_adx(self, symbol: str, h1: pd.DataFrame, audit: Dict) -> Tuple[bool, float]:
        """
        Valida ADX: Confirma se há tendência.

        Returns: (is_trending: bool, confidence 0-1)
        """
        try:
            if len(h1) < 50:
                audit["adx"] = {"status": "INSUFFICIENT_DATA", "confidence": 0.0}
                return False, 0.0

            adx_df = self.tech_ind.calculate_adx(h1, 14)
            adx = adx_df['adx_14'].iloc[-1]

            if pd.isna(adx):
                audit["adx"] = {"status": "NAN_VALUE", "confidence": 0.0}
                return False, 0.0

            # Tendência forte: ADX > 25
            is_trending = adx > 25
            confidence = min(adx / 50, 1.0)  # Normalizar

            audit["adx"] = {
                "status": "VALID",
                "adx_value": float(adx),
                "is_trending": is_trending,
                "confidence": float(confidence)
            }

            return is_trending, confidence

        except Exception as e:
            logger.error(f"{symbol} ADX validation error: {str(e)}")
            audit["adx"] = {"status": "ERROR", "error": str(e), "confidence": 0.0}
            return False, 0.0

    def _calculate_overall_confidence(
        self, components: List[SignalComponent], regime: str, risk_status: str
    ) -> float:
        """Calcula confiança geral do sinal (0-100)."""
        if not components:
            return 0.0

        avg_component_conf = np.mean([c.confidence for c in components]) * 100

        # Ajuste por regime
        regime_multiplier = {
            "RISK_ON": 1.1,
            "RISK_OFF": 0.7,
            "NEUTRO": 1.0
        }.get(regime, 1.0)

        # Ajuste por risk_status
        risk_multiplier = {
            "CLEARED": 1.0,
            "RISKY": 0.6,
            "BLOCKED": 0.0
        }.get(risk_status, 1.0)

        final_conf = avg_component_conf * regime_multiplier * risk_multiplier
        return min(max(final_conf, 0), 100)

    def _determine_final_signal(
        self,
        smc: str, ema: str, rsi: str, adx: bool,
        confluence: int, confidence: float, regime: str, risk_status: str
    ) -> str:
        """Determina sinal final com confluência mínima."""
        # Bloqueia se risk gate falhar
        if risk_status == "BLOCKED":
            return "NEUTRAL"

        # Confluência mínima: 3 componentes concordando
        if confluence < 3 or confidence < 70:
            return "NEUTRAL"

        # Contar votos
        bullish_votes = sum(1 for s in [smc, ema, rsi] if s == "BUY")
        bearish_votes = sum(1 for s in [smc, ema, rsi] if s == "SELL")

        if adx:
            if bullish_votes >= 2:
                return "BUY"
            elif bearish_votes >= 2:
                return "SELL"

        return "NEUTRAL"

    def _calculate_sl_tp(self, symbol: str, signal: str, h1_ohlcv: pd.DataFrame, audit: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Calcula Stop Loss e Take Profit."""
        try:
            if signal == "NEUTRAL" or len(h1_ohlcv) < 20:
                return None, None

            # Usar ATR para dimensionamento
            atr_series = self.tech_ind.calculate_atr(h1_ohlcv, 14)
            atr = atr_series.iloc[-1]
            current = h1_ohlcv['close'].iloc[-1]

            if signal == "BUY":
                sl = current - (2 * atr)  # 2 ATR abaixo
                tp = current + (3 * atr)  # 3 ATR acima (R:R 1:1.5)
            else:  # SELL
                sl = current + (2 * atr)
                tp = current - (3 * atr)

            audit["price_targets"] = {
                "atr": float(atr),
                "stop_loss": float(sl),
                "take_profit": float(tp)
            }

            return sl, tp

        except Exception as e:
            logger.error(f"{symbol} SL/TP calculation error: {str(e)}")
            return None, None

    def _calculate_rr_ratio(self, entry: float, sl: float, tp: float) -> Optional[float]:
        """Calcula Risk:Reward ratio."""
        if not all([entry, sl, tp]) or entry == sl:
            return None

        risk = abs(entry - sl)
        reward = abs(tp - entry)

        return reward / risk if risk > 0 else None

    def _log_signal(self, signal: HeuristicSignal) -> None:
        """Registra sinal em audit trail."""
        logger.info(
            f"[{signal.symbol}] Signal={signal.signal_type} | "
            f"Confidence={signal.confidence:.1f}% | Confluence={signal.confluence_score}/4 | "
            f"Risk={signal.risk_assessment} | Regime={signal.market_regime} | "
            f"R:R={signal.risk_reward_ratio:.2f}x" if signal.risk_reward_ratio else "N/A"
        )
