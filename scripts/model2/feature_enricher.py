"""Feature enrichment utilities for training episodes."""

from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np


class FeatureEnricher:
    """Enriquece features dos episódios com volatilidade e multi-timeframe."""

    @staticmethod
    def calculate_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 20) -> float:
        """Calcula ATR (Average True Range) - volatilidade."""
        if len(highs) < period:
            return 0.0

        trs = []
        for i in range(len(highs)):
            if i == 0:
                tr = highs[i] - lows[i]
            else:
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1]),
                )
            trs.append(tr)

        atr = np.mean(trs[-period:])
        return float(atr)

    @staticmethod
    def calculate_rsi(closes: list[float], period: int = 14) -> float:
        """Calcula RSI (Relative Strength Index) - momentum."""
        if len(closes) < period + 1:
            return 50.0

        changes = np.diff(closes[-period - 1 :])
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, -changes, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            rsi = 100.0 if avg_gain > 0 else 50.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        return float(rsi)

    @staticmethod
    def calculate_bollinger_bands(closes: list[float], period: int = 20, std_dev: int = 2) -> tuple[float, float, float]:
        """Calcula Bandas de Bollinger e posição."""
        if len(closes) < period:
            return 0.0, 0.0, 50.0

        recent = closes[-period:]
        ma = np.mean(recent)
        std = np.std(recent)

        upper_band = ma + (std_dev * std)
        lower_band = ma - (std_dev * std)

        current = closes[-1]
        if upper_band == lower_band:
            bb_position = 50.0
        else:
            bb_position = ((current - lower_band) / (upper_band - lower_band)) * 100.0
            bb_position = np.clip(bb_position, 0.0, 100.0)

        return float(lower_band), float(upper_band), float(bb_position)

    @staticmethod
    def calculate_macd(
        closes: list[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ) -> tuple[float, float, float]:
        """Calcula MACD (Moving Average Convergence Divergence)."""
        if len(closes) < slow_period:
            return 0.0, 0.0, 0.0

        slow_ema = np.mean(closes[-slow_period:])
        fast_ema = np.mean(closes[-fast_period:])

        macd_line = fast_ema - slow_ema

        # Para o signal, precisaríamos de um histórico de MACD, simplificando para a simulação
        # Usando uma média simples da macd_line como proxy
        if len(closes) < slow_period + signal_period:
             signal_line = np.mean([fast_ema - np.mean(closes[-(slow_period+i):-(i if i > 0 else None)]) for i in range(signal_period)])
        else:
             signal_line = np.mean([fast_ema - np.mean(closes[-(slow_period+i):-(i if i > 0 else None)]) for i in range(signal_period)])

        histogram = macd_line - signal_line

        return float(macd_line), float(signal_line), float(histogram)

    @staticmethod
    def calculate_stochastic(highs: list[float], lows: list[float], closes: list[float], period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> tuple[float, float]:
        """Calcula Estocastico (K e D) - indicador de momentum em zonas extremas."""
        if len(closes) < period:
            return 50.0, 50.0

        recent_highs = highs[-period:]
        recent_lows = lows[-period:]
        recent_closes = closes[-period:]

        highest = max(recent_highs)
        lowest = min(recent_lows)

        if highest == lowest:
            k_line = 50.0
        else:
            k_line = ((closes[-1] - lowest) / (highest - lowest)) * 100.0

        # Suavizar K com EMA simples
        if len(closes) >= period + smooth_k - 1:
            k_values = []
            for i in range(len(closes) - period - smooth_k + 2):
                h = max(closes[i:i+period])
                l = min(closes[i:i+period])
                if h == l:
                    k = 50.0
                else:
                    k = ((closes[i+period-1] - l) / (h - l)) * 100.0
                k_values.append(k)
            k_line = float(np.mean(k_values[-smooth_k:])) if k_values else 50.0

        # D linha e uma media suavizada de K
        d_line = k_line  # Simplificacao: usar K como proxy

        return float(np.clip(k_line, 0.0, 100.0)), float(np.clip(d_line, 0.0, 100.0))

    @staticmethod
    def calculate_williams_r(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
        """Calcula Williams %R - oscilador relacionado ao Estocastico."""
        if len(closes) < period:
            return -50.0

        recent_highs = highs[-period:]
        recent_lows = lows[-period:]

        highest = max(recent_highs)
        lowest = min(recent_lows)

        if highest == lowest:
            williams_r = -50.0
        else:
            williams_r = -100.0 * (highest - closes[-1]) / (highest - lowest)

        return float(np.clip(williams_r, -100.0, 0.0))

    @staticmethod
    def calculate_atr_normalized(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
        """Calcula ATR normalizado (em percentual do preco)."""
        if len(closes) < period:
            return 0.0

        atr = FeatureEnricher.calculate_atr(highs, lows, closes, period)
        current_close = closes[-1]

        if current_close == 0:
            return 0.0

        atr_normalized = (atr / current_close) * 100.0
        return float(atr_normalized)

    @staticmethod
    def fetch_candles_by_timeframe(
        conn: sqlite3.Connection,
        symbol: str,
        timeframe: str,
        limit: int = 240,
    ) -> dict[str, Any]:
        """Busca candles de um timeframe específico."""
        table_name = {
            "D1": "ohlcv_d1",
            "H4": "ohlcv_h4",
            "H1": "ohlcv_h1",
            "M5": "ohlcv_m5",
        }.get(timeframe, "ohlcv_h4")

        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT open, high, low, close, volume
                FROM {table_name}
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (symbol, limit),
            )
            rows = cursor.fetchall()

            if not rows:
                return {"available": False, "count": 0}

            # Reverter para ordem crescente de timestamp
            rows = list(reversed(rows))

            opens = [float(r[0]) for r in rows]
            highs = [float(r[1]) for r in rows]
            lows = [float(r[2]) for r in rows]
            closes = [float(r[3]) for r in rows]
            volumes = [float(r[4]) for r in rows]

            return {
                "available": True,
                "count": len(rows),
                "opens": opens,
                "highs": highs,
                "lows": lows,
                "closes": closes,
                "volumes": volumes,
                "current_close": closes[-1] if closes else None,
            }
        except Exception as e:
            return {"available": False, "count": 0, "error": str(e)}

    @classmethod
    def enrich_features(
        cls,
        conn: sqlite3.Connection,
        symbol: str,
        timeframe: str,
        base_features: dict[str, Any],
    ) -> dict[str, Any]:
        """Enriquece features base com volatilidade e multi-timeframe."""
        enriched = dict(base_features)  # Cópia

        # Buscar candles do timeframe atual
        current_tf_candles = cls.fetch_candles_by_timeframe(conn, symbol, timeframe, limit=240)

        if current_tf_candles.get("available"):
            closes = current_tf_candles["closes"]
            highs = current_tf_candles["highs"]
            lows = current_tf_candles["lows"]

            # Calcular volatilidade
            atr = cls.calculate_atr(highs, lows, closes, period=20)
            rsi = cls.calculate_rsi(closes, period=14)
            bb_lower, bb_upper, bb_position = cls.calculate_bollinger_bands(closes, period=20)
            macd_line, macd_signal, macd_hist = cls.calculate_macd(closes)
            stoch_k, stoch_d = cls.calculate_stochastic(highs, lows, closes, period=14)
            williams_r = cls.calculate_williams_r(highs, lows, closes, period=14)
            atr_normalized = cls.calculate_atr_normalized(highs, lows, closes, period=14)

            enriched["volatility"] = {
                "atr_20": atr,
                "rsi_14": rsi,
                "bb_lower": bb_lower,
                "bb_upper": bb_upper,
                "bb_position": bb_position,
                "macd_line": macd_line,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "stoch_k": stoch_k,
                "stoch_d": stoch_d,
                "williams_r": williams_r,
                "atr_normalized": atr_normalized,
            }

        # Buscar candles de outros timeframes para contexto
        multi_tf = {}
        for other_tf in ["H1", "H4", "D1"]:
            if other_tf == timeframe:
                continue  # Já coletado acima
            other_candles = cls.fetch_candles_by_timeframe(conn, symbol, other_tf, limit=50)
            if other_candles.get("available"):
                closes = other_candles["closes"]
                highs = other_candles["highs"]
                lows = other_candles["lows"]
                atr_norm_tf = cls.calculate_atr_normalized(highs, lows, closes, period=14)

                multi_tf[other_tf] = {
                    "count": other_candles["count"],
                    "last_5_closes": closes[-5:] if len(closes) >= 5 else closes,
                    "current_close": closes[-1],
                    "ma_20": float(np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)),
                    "atr_normalized": atr_norm_tf,
                }

        if multi_tf:
            enriched["multi_timeframe_context"] = multi_tf

        return enriched

    @staticmethod
    def enrich_with_funding_data(
        enriched_features: dict[str, Any],
        symbol: str,
        funding_collector: Any = None,  # BinanceFundingCollector instance
    ) -> dict[str, Any]:
        """
        Enriquece features com dados de funding rates e open interest.

        Args:
            enriched_features: Features já enriquecidas
            symbol: Ex. 'BTCUSDT'
            funding_collector: Instância de BinanceFundingCollector (lazy import)

        Returns:
            Dict enriquecido com chaves 'funding_rates' e 'open_interest'
        """
        if not funding_collector:
            return enriched_features

        enriched = dict(enriched_features)

        try:
            # Funding rates data
            fr = funding_collector.get_latest_funding_rate(symbol)
            if fr:
                sentiment = funding_collector.estimate_funding_sentiment(symbol, hours=24)
                enriched["funding_rates"] = {
                    "latest_rate": fr.get("funding_rate"),
                    "estimated_leverage": fr.get("estimated_leverage"),
                    "timestamp_utc": fr.get("timestamp_utc"),
                    "sentiment_24h": sentiment.get("sentiment"),
                    "avg_rate_24h": sentiment.get("avg_funding_rate"),
                    "trend": sentiment.get("trend"),
                }

            # Open interest data
            oi = funding_collector.get_latest_open_interest(symbol)
            if oi:
                oi_sentiment = funding_collector.estimate_oi_sentiment(symbol)
                enriched["open_interest"] = {
                    "current_oi": oi.get("open_interest"),
                    "oi_usd": oi.get("open_interest_usd"),
                    "timestamp_utc": oi.get("timestamp_utc"),
                    "oi_sentiment": oi_sentiment.get("sentiment"),
                    "oi_change_direction": oi_sentiment.get("change_direction"),
                }
        except Exception as e:
            # Graceful fallback se API/DB falhar
            enriched["funding_data_error"] = str(e)

        return enriched
