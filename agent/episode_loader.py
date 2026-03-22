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

        feature_keys = [
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

        result = []
        for key in feature_keys:
            bounds = EpisodeNormalizer.FEATURE_BOUNDS.get(key, (-1, 1))
            value = features_dict.get(key)
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
