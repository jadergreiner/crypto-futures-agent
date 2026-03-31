from __future__ import annotations

import logging
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger("model_degradation_monitor")

_LABELS_WIN = {"win", "hold_correct"}
_LABELS_LOSS = {"loss", "hold_incorrect"}
_LABELS_IGNORADOS = {"pending", "context"}


@dataclass(frozen=True)
class ModelDegradationThresholds:
    min_avg_confidence: float
    min_hit_rate: float
    min_hit_rate_delta: float
    evaluation_window: int
    min_samples: int


@dataclass(frozen=True)
class ModelDegradationResult:
    symbol: str
    timeframe: str
    is_degraded: bool
    reason_code: str | None
    trigger_reason: str
    avg_confidence: float | None
    recent_hit_rate: float
    previous_hit_rate: float | None
    hit_rate_delta: float | None
    recent_samples: int
    previous_samples: int
    confidence_samples: int
    thresholds: ModelDegradationThresholds

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["thresholds"] = asdict(self.thresholds)
        return payload


class ModelDegradationMonitor:
    def __init__(self, db_conn: sqlite3.Connection, symbol: str, timeframe: str):
        self._db_conn = db_conn
        self._symbol = str(symbol)
        self._timeframe = str(timeframe)

    def _table_exists(self, table_name: str) -> bool:
        row = self._db_conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (str(table_name),),
        ).fetchone()
        return row is not None

    @staticmethod
    def _row_value(row: sqlite3.Row | tuple[Any, ...], key: str, index: int) -> Any:
        if isinstance(row, sqlite3.Row):
            return row[key]
        return row[index]

    def _fetch_recent_labels(self, *, limit: int, offset: int = 0) -> list[str]:
        if limit <= 0 or not self._table_exists("training_episodes"):
            return []
        rows = self._db_conn.execute(
            """
            SELECT label
            FROM training_episodes
            WHERE symbol = ?
              AND timeframe = ?
              AND LOWER(COALESCE(label, '')) NOT IN ('pending', 'context')
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (self._symbol, self._timeframe, int(limit), int(max(0, offset))),
        ).fetchall()
        return [str(self._row_value(row, "label", 0)).strip().lower() for row in rows]

    def _fetch_recent_confidences(self, *, limit: int) -> list[float]:
        if limit <= 0 or not self._table_exists("model_decisions"):
            return []
        rows = self._db_conn.execute(
            """
            SELECT confidence
            FROM model_decisions
            WHERE symbol = ?
            ORDER BY decision_timestamp DESC, id DESC
            LIMIT ?
            """,
            (self._symbol, int(limit)),
        ).fetchall()
        return [float(self._row_value(row, "confidence", 0)) for row in rows]

    @staticmethod
    def _calculate_hit_rate(labels: list[str]) -> tuple[float, int]:
        relevantes = [
            label for label in labels
            if label not in _LABELS_IGNORADOS and label in (_LABELS_WIN | _LABELS_LOSS)
        ]
        total = len(relevantes)
        if total == 0:
            return 0.0, 0
        wins = sum(1 for label in relevantes if label in _LABELS_WIN)
        return float(wins) / float(total), total

    def evaluate(self, thresholds: ModelDegradationThresholds) -> ModelDegradationResult:
        try:
            janela = max(1, int(thresholds.evaluation_window))
            min_samples = max(1, int(thresholds.min_samples))

            labels_recentes = self._fetch_recent_labels(limit=janela, offset=0)
            labels_anteriores = self._fetch_recent_labels(limit=janela, offset=janela)
            confidences = self._fetch_recent_confidences(limit=janela)

            recent_hit_rate, recent_samples = self._calculate_hit_rate(labels_recentes)
            previous_hit_rate, previous_samples = self._calculate_hit_rate(labels_anteriores)
            confidence_samples = len(confidences)
            avg_confidence = (
                float(sum(confidences) / len(confidences))
                if confidences
                else None
            )

            gatilhos: list[str] = []
            hit_rate_delta: float | None = None
            if (
                avg_confidence is not None
                and confidence_samples >= min_samples
                and avg_confidence < float(thresholds.min_avg_confidence)
            ):
                gatilhos.append("confidence_below_threshold")

            if (
                recent_samples >= min_samples
                and recent_hit_rate < float(thresholds.min_hit_rate)
            ):
                gatilhos.append("hit_rate_below_threshold")

            if previous_samples >= min_samples and recent_samples >= min_samples:
                hit_rate_delta = float(recent_hit_rate - previous_hit_rate)
                if hit_rate_delta < float(thresholds.min_hit_rate_delta):
                    gatilhos.append("hit_rate_regression")

            return ModelDegradationResult(
                symbol=self._symbol,
                timeframe=self._timeframe,
                is_degraded=bool(gatilhos),
                reason_code="MODEL_DEGRADATION" if gatilhos else None,
                trigger_reason=gatilhos[0] if gatilhos else "healthy",
                avg_confidence=avg_confidence,
                recent_hit_rate=recent_hit_rate,
                previous_hit_rate=(previous_hit_rate if previous_samples > 0 else None),
                hit_rate_delta=hit_rate_delta,
                recent_samples=recent_samples,
                previous_samples=previous_samples,
                confidence_samples=confidence_samples,
                thresholds=ModelDegradationThresholds(
                    min_avg_confidence=float(thresholds.min_avg_confidence),
                    min_hit_rate=float(thresholds.min_hit_rate),
                    min_hit_rate_delta=float(thresholds.min_hit_rate_delta),
                    evaluation_window=janela,
                    min_samples=min_samples,
                ),
            )
        except Exception as exc:
            logger.error("Erro ao calcular degradacao do modelo: %s", exc)
            return ModelDegradationResult(
                symbol=self._symbol,
                timeframe=self._timeframe,
                is_degraded=False,
                reason_code=None,
                trigger_reason="healthy",
                avg_confidence=None,
                recent_hit_rate=0.0,
                previous_hit_rate=None,
                hit_rate_delta=None,
                recent_samples=0,
                previous_samples=0,
                confidence_samples=0,
                thresholds=thresholds,
            )

    def check_degradation(
        self,
        threshold: float,
        window: int,
        min_samples: int = 3,
    ) -> tuple[bool, float]:
        """Wrapper legado baseado apenas em hit rate recente."""
        result = self.evaluate(
            ModelDegradationThresholds(
                min_avg_confidence=-1.0,
                min_hit_rate=float(threshold),
                min_hit_rate_delta=-1.0,
                evaluation_window=int(window),
                min_samples=int(min_samples),
            )
        )
        return result.is_degraded, result.recent_hit_rate
