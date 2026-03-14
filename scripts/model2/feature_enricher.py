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

            enriched["volatility"] = {
                "atr_20": atr,
                "rsi_14": rsi,
                "bb_lower": bb_lower,
                "bb_upper": bb_upper,
                "bb_position": bb_position,
            }

        # Buscar candles de outros timeframes para contexto
        multi_tf = {}
        for other_tf in ["H1", "H4", "D1"]:
            if other_tf == timeframe:
                continue  # Já coletado acima
            other_candles = cls.fetch_candles_by_timeframe(conn, symbol, other_tf, limit=50)
            if other_candles.get("available"):
                closes = other_candles["closes"]
                multi_tf[other_tf] = {
                    "count": other_candles["count"],
                    "last_5_closes": closes[-5:] if len(closes) >= 5 else closes,
                    "current_close": closes[-1],
                    "ma_20": float(np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)),
                }

        if multi_tf:
            enriched["multi_timeframe_context"] = multi_tf

        return enriched
