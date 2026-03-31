import sqlite3
import logging
from typing import Tuple

logger = logging.getLogger("model_degradation_monitor")

class ModelDegradationMonitor:
    def __init__(self, db_conn: sqlite3.Connection, symbol: str, timeframe: str):
        self._db_conn = db_conn
        self._symbol = symbol
        self._timeframe = timeframe

    def check_degradation(
        self, 
        threshold: float, 
        window: int, 
        min_samples: int = 3
    ) -> Tuple[bool, float]:
        """
        Calculates the win rate from the recent training_episodes.
        A 'win' is defined as label 'win' or 'hold_correct'. 
        A 'loss' is label 'loss'.
        'pending' states are normally not counted if they don't resolve.
        
        Returns:
            (is_degraded, win_rate)
        """
        try:
            # We fetch the last `window` non-pending episodes
            cursor = self._db_conn.cursor()
            cursor.execute(
                """
                SELECT label
                FROM training_episodes
                WHERE symbol = ? AND timeframe = ? AND label != 'pending'
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self._symbol, self._timeframe, window)
            )
            rows = cursor.fetchall()

            if len(rows) < min_samples:
                # Fail-safe: not enough data to claim degradation
                return False, 0.0

            total_valid: int = len(rows)
            wins: int = 0
            for row in rows:
                label = row["label"]
                if label in ("win", "hold_correct"):
                    wins += 1

            win_rate: float = float(wins) / float(total_valid)

            is_degraded = win_rate < threshold

            return is_degraded, win_rate

        except Exception as e:
            logger.error(f"Error calculating model degradation: {e}")
            # Fail-safe logic
            return False, 0.0
