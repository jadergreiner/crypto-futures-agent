"""
Carregador de episódios de treinamento com normalização automática.

Componente da iniciativa M2-019: RL por Símbolo como Decisor de Entrada.
Responsável por carregar episódios do banco modelo2.db, filtrar por symbol
e timeframe, descartar pendentes, normalizar features e retornar lista
pronta para EntryDecisionEnv.

Contrato:
  load_episodes(db_path, symbol, timeframe, min_episodes=20)
  -> List[Dict] com episódios normalizados ou [] quando insuficiente.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional


class EpisodeNormalizer:
    """Normaliza features de episódios para [-1, 1]."""

    # Limites empíricos de features típicas em dados de criptomoedas
    # (ajustáveis com calibração futura)
    FEATURE_BOUNDS = {
        # OHLCV candle (5 features)
        "open_norm": (-0.5, 0.5),
        "high_norm": (-0.5, 0.5),
        "low_norm": (-0.5, 0.5),
        "close_norm": (-0.5, 0.5),
        "volume_norm": (0, 1),
        # Volatility indicators (6 features)
        "rsi": (0, 100),
        "macd_line": (-1, 1),
        "macd_signal": (-1, 1),
        "bb_upper": (-0.5, 0.5),
        "bb_lower": (-0.5, 0.5),
        "atr_norm": (0, 1),
        # Multi-timeframe context (9 features: 3 candles × 3 timeframes)
        "h1_open_norm": (-0.5, 0.5),
        "h1_close_norm": (-0.5, 0.5),
        "h1_volume_norm": (0, 1),
        "h4_open_norm": (-0.5, 0.5),
        "h4_close_norm": (-0.5, 0.5),
        "h4_volume_norm": (0, 1),
        "d1_open_norm": (-0.5, 0.5),
        "d1_close_norm": (-0.5, 0.5),
        "d1_volume_norm": (0, 1),
        # Funding & sentiment (3 features)
        "fr_sentiment": (-1, 1),
        "oi_sentiment": (-1, 1),
        "ls_ratio": (0, 1),
        # SMC context (3 features)
        "smc_zone_proximity": (0, 1),
        "smc_rejection_strength": (0, 1),
        "smc_direction_bias": (-1, 1),
    }

    FEATURE_KEYS = [
        "open_norm",
        "high_norm",
        "low_norm",
        "close_norm",
        "volume_norm",
        "rsi",
        "macd_line",
        "macd_signal",
        "bb_upper",
        "bb_lower",
        "atr_norm",
        "h1_open_norm",
        "h1_close_norm",
        "h1_volume_norm",
        "h4_open_norm",
        "h4_close_norm",
        "h4_volume_norm",
        "d1_open_norm",
        "d1_close_norm",
        "d1_volume_norm",
        "fr_sentiment",
        "oi_sentiment",
        "ls_ratio",
        "smc_zone_proximity",
        "smc_rejection_strength",
        "smc_direction_bias",
    ]

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_ratio(value: Any, *, default: float = 0.5) -> float:
        parsed = EpisodeNormalizer._to_float(value)
        if parsed is None:
            return float(default)
        return float(max(0.0, min(1.0, parsed)))

    @staticmethod
    def _sentiment_to_numeric(value: Any) -> float:
        normalized = str(value or "").strip().lower()
        if normalized in {"bullish", "positive", "accumulating", "up", "increasing"}:
            return 1.0
        if normalized in {"bearish", "negative", "distribution", "down", "decreasing"}:
            return -1.0
        return 0.0

    @staticmethod
    def _direction_to_bias(value: Any) -> float:
        normalized = str(value or "").strip().upper()
        if normalized in {"LONG", "BUY"}:
            return 1.0
        if normalized in {"SHORT", "SELL"}:
            return -1.0
        return 0.0

    @staticmethod
    def _relative_delta(base: float, candidate: float) -> float:
        if base <= 0:
            return 0.0
        return float((candidate - base) / base)

    @classmethod
    def _flatten_feature_schema(cls, features_dict: dict[str, Any]) -> dict[str, Any]:
        if any(key in features_dict for key in cls.FEATURE_KEYS):
            return dict(features_dict)

        latest_candle = features_dict.get("latest_candle")
        volatility = features_dict.get("volatility")
        multi_tf = features_dict.get("multi_timeframe_context")
        funding_rates = features_dict.get("funding_rates")
        open_interest = features_dict.get("open_interest")
        opportunities = features_dict.get("opportunities_by_status")

        latest_candle = latest_candle if isinstance(latest_candle, dict) else {}
        volatility = volatility if isinstance(volatility, dict) else {}
        multi_tf = multi_tf if isinstance(multi_tf, dict) else {}
        funding_rates = funding_rates if isinstance(funding_rates, dict) else {}
        open_interest = open_interest if isinstance(open_interest, dict) else {}
        opportunities = opportunities if isinstance(opportunities, dict) else {}

        close_price = cls._to_float(
            latest_candle.get("close")
            if latest_candle.get("close") is not None
            else features_dict.get("close_t")
        )
        if close_price is None or close_price <= 0:
            close_price = 1.0

        open_price = cls._to_float(latest_candle.get("open")) or close_price
        high_price = cls._to_float(latest_candle.get("high")) or close_price
        low_price = cls._to_float(latest_candle.get("low")) or close_price
        volume_raw = cls._to_float(latest_candle.get("volume"))
        volume_norm = min(1.0, max(0.0, (volume_raw or 0.0) / 1_000_000.0))

        atr_raw = cls._to_float(
            volatility.get("atr_normalized")
            if volatility.get("atr_normalized") is not None
            else features_dict.get("atr_norm")
        )
        atr_norm = 0.0 if atr_raw is None else (atr_raw / 100.0 if atr_raw > 1.0 else atr_raw)

        def _tf_values(tf_key: str) -> tuple[float, float, float]:
            tf_payload = multi_tf.get(tf_key)
            if not isinstance(tf_payload, dict):
                return 0.0, 0.0, 0.0
            tf_close = cls._to_float(tf_payload.get("current_close")) or close_price
            tf_ma = cls._to_float(tf_payload.get("ma_20")) or tf_close
            tf_count = cls._to_float(tf_payload.get("count")) or 0.0
            return (
                cls._relative_delta(tf_close, tf_ma),
                cls._relative_delta(close_price, tf_close),
                max(0.0, min(1.0, tf_count / 240.0)),
            )

        h1_open_norm, h1_close_norm, h1_volume_norm = _tf_values("H1")
        h4_open_norm, h4_close_norm, h4_volume_norm = _tf_values("H4")
        d1_open_norm, d1_close_norm, d1_volume_norm = _tf_values("D1")

        validada = cls._to_float(opportunities.get("VALIDADA")) or 0.0
        invalidada = cls._to_float(opportunities.get("INVALIDADA")) or 0.0
        monitorando = cls._to_float(opportunities.get("MONITORANDO")) or 0.0
        total_opportunities = max(1.0, validada + invalidada + monitorando)

        return {
            "open_norm": cls._relative_delta(close_price, open_price),
            "high_norm": cls._relative_delta(close_price, high_price),
            "low_norm": cls._relative_delta(close_price, low_price),
            "close_norm": 0.0,
            "volume_norm": volume_norm,
            "rsi": cls._to_float(volatility.get("rsi_14")) or 50.0,
            "macd_line": cls._to_float(volatility.get("macd_line")) or 0.0,
            "macd_signal": cls._to_float(volatility.get("macd_signal")) or 0.0,
            "bb_upper": cls._relative_delta(close_price, cls._to_float(volatility.get("bb_upper")) or close_price),
            "bb_lower": cls._relative_delta(close_price, cls._to_float(volatility.get("bb_lower")) or close_price),
            "atr_norm": atr_norm,
            "h1_open_norm": h1_open_norm,
            "h1_close_norm": h1_close_norm,
            "h1_volume_norm": h1_volume_norm,
            "h4_open_norm": h4_open_norm,
            "h4_close_norm": h4_close_norm,
            "h4_volume_norm": h4_volume_norm,
            "d1_open_norm": d1_open_norm,
            "d1_close_norm": d1_close_norm,
            "d1_volume_norm": d1_volume_norm,
            "fr_sentiment": cls._sentiment_to_numeric(
                funding_rates.get("sentiment_24h")
                if funding_rates.get("sentiment_24h") is not None
                else funding_rates.get("trend")
            ),
            "oi_sentiment": cls._sentiment_to_numeric(
                open_interest.get("oi_sentiment")
                if open_interest.get("oi_sentiment") is not None
                else open_interest.get("oi_change_direction")
            ),
            "ls_ratio": cls._to_ratio(
                funding_rates.get("estimated_leverage")
                if funding_rates.get("estimated_leverage") is not None
                else features_dict.get("ls_ratio")
            ),
            "smc_zone_proximity": max(0.0, min(1.0, validada / total_opportunities)),
            "smc_rejection_strength": max(0.0, min(1.0, invalidada / total_opportunities)),
            "smc_direction_bias": cls._direction_to_bias(features_dict.get("signal_side")),
        }

    @staticmethod
    def normalize_value(
        value: float | None, min_bound: float, max_bound: float
    ) -> float:
        """Normaliza um valor para [-1, 1]."""
        if value is None or (isinstance(value, float) and (
            value != value or value == float('inf') or value == float('-inf')
        )):
            # NaN ou infinito -> retorna 0
            return 0.0

        # Clamp ao intervalo [min_bound, max_bound]
        clamped = max(min_bound, min(max_bound, float(value)))

        # Normaliza para [-1, 1]
        range_size = max_bound - min_bound
        if range_size == 0:
            return 0.0

        normalized = (clamped - min_bound) / range_size * 2.0 - 1.0
        return float(max(-1.0, min(1.0, normalized)))

    @staticmethod
    def normalize_features(features_dict: dict[str, Any]) -> list[float]:
        """
        Normaliza features_json em lista ordenada de 36 floats em [-1, 1].

        Ordem:
        - Indices 0-4: OHLCV candle
        - Indices 5-10: Volatility
        - Indices 11-19: Multi-TF
        - Indices 20-22: Funding & Sentiment
        - Indices 23-25: SMC context
        - Indices 26-35: Reserved (zeros por enquanto)
        """
        if not isinstance(features_dict, dict):
            return [0.0] * 36
        if not features_dict:
            return [0.0] * 36

        flattened = EpisodeNormalizer._flatten_feature_schema(features_dict)

        result = []
        for key in EpisodeNormalizer.FEATURE_KEYS:
            bounds = EpisodeNormalizer.FEATURE_BOUNDS.get(key, (-1, 1))
            value = flattened.get(key)
            normalized = EpisodeNormalizer.normalize_value(
                value, bounds[0], bounds[1]
            )
            result.append(normalized)

        # Preencher com zeros até 36
        while len(result) < 36:
            result.append(0.0)

        return result[:36]


def load_episodes(
    db_path: str | Path,
    symbol: str,
    timeframe: str,
    min_episodes: int = 20,
) -> list[dict[str, Any]]:
    """
    Carregar episódios de treinamento normalizado.

    Args:
        db_path: Caminho para modelo2.db
        symbol: Símbolo a filtrar (ex: BTCUSDT)
        timeframe: Timeframe a filtrar (ex: H4)
        min_episodes: Mínimo de episódios válidos para retornar

    Returns:
        Lista de dicts com episódios normalizados ou [] se insuficiente.
        Cada dict contém:
        - id: ID do episódio no BD
        - symbol: Símbolo
        - timeframe: Timeframe
        - label: Label final (win|loss|breakeven|pending)
        - reward_proxy: Reward estimado
        - features: Array 36-float normalizado
        - metadata: Dict com info adicional
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Verificar existência da tabela
        table_check = cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='training_episodes'
            """
        ).fetchone()

        if not table_check:
            conn.close()
            return []

        # Carregar episódios filtrando:
        # - symbol e timeframe
        # - label != 'pending' (descartar sem outcome real)
        query = """
            SELECT
                id,
                symbol,
                timeframe,
                status,
                label,
                reward_proxy,
                features_json,
                target_json,
                created_at
            FROM training_episodes
            WHERE symbol = ? AND timeframe = ? AND label != 'pending'
            ORDER BY created_at DESC
            LIMIT 1000
        """
        rows = cursor.execute(query, (symbol, timeframe)).fetchall()

        episodes = []
        for row in rows:
            try:
                features_dict = json.loads(row["features_json"] or "{}")
                if not isinstance(features_dict, dict):
                    # Garante que features_json é dict válido
                    features_dict = {}
            except (json.JSONDecodeError, TypeError):
                features_dict = {}

            # Normalizar features
            normalized_features = EpisodeNormalizer.normalize_features(
                features_dict
            )

            episode = {
                "id": int(row["id"]),
                "symbol": str(row["symbol"]),
                "timeframe": str(row["timeframe"]),
                "label": str(row["label"]),
                "reward_proxy": float(row["reward_proxy"] or 0.0),
                "features": normalized_features,
                "metadata": {
                    "status": str(row["status"]),
                    "created_at": int(row["created_at"]),
                    "raw_features": features_dict,
                },
            }
            episodes.append(episode)

        conn.close()

        # Retornar [] se insuficiente; caso contrário, retornar episodes
        if len(episodes) < min_episodes:
            return []

        return episodes

    except Exception as e:
        # Fallback seguro em erro de banco
        print(f"[DEBUG] EpisodeLoader: erro ao carregar episódios: {e}")
        return []


def validate_episodes(episodes: list[dict[str, Any]]) -> bool:
    """
    Valida lista de episódios carregados.

    Retorna True se:
    - Lista não vazia
    - Todos os episódios têm features de 36 floats
    - Todos os floats estão em [-1, 1]
    """
    if not episodes:
        return False

    for episode in episodes:
        if not isinstance(episode, dict):
            return False

        features = episode.get("features")
        if not isinstance(features, list) or len(features) != 36:
            return False

        for f in features:
            if not isinstance(f, (int, float)):
                return False
            if f != f or f == float('inf') or f == float('-inf'):  # NaN check
                return False
            if not (-1.0 <= f <= 1.0):
                return False

    return True
