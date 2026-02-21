"""
ParquetCache — Cache de dados históricos para backtesting (3-tier pipeline).

Camadas:
1. SQLite (db/crypto_agent.db) → Fonte de verdade
2. Parquet (cache/) → Cached persistente (6-10x mais rápido)
3. NumPy arrays → Memory residente durante backtest

Implementado em 22 FEV por SWE Senior.
"""

import logging
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np
from pathlib import Path
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)


class ParquetCache:
    """
    Cache Parquet para aceleração de backtesting.

    Carrega dados SQLite → converts para Parquet → loads como NumPy.

    Pipeline:
    1. load_ohlcv_for_symbol(symbol) → check Parquet cache
    2. Se cache existe: retorna DataFrame rápido
    3. Se não: carrega SQLite, converte Parquet, salva cache
    """

    def __init__(self, db_path: str, cache_dir: str = "backtest/cache"):
        """
        Inicializa ParquetCache.

        Args:
            db_path: Path para SQLite database
            cache_dir: Diretório para armazenar arquivos Parquet
        """
        self.db_path = db_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Memory cache (opcional, 3-tier adicional)
        self._memory_cache: Dict[str, pd.DataFrame] = {}

        logger.info(f"ParquetCache initialized: cache_dir={self.cache_dir}")

    def _get_parquet_path(self, symbol: str, timeframe: str) -> Path:
        """
        Retorna path para arquivo Parquet de um símbolo/timeframe.

        Args:
            symbol: Ex. 'BTCUSDT'
            timeframe: 'h1', 'h4', 'd1'

        Returns:
            Path absoluto do arquivo Parquet
        """
        return self.cache_dir / f"{symbol}_{timeframe}.parquet"

    def load_ohlcv_for_symbol(self, symbol: str,
                              timeframe: str = 'h4',
                              start_date: Optional[int] = None,
                              end_date: Optional[int] = None) -> pd.DataFrame:
        """
        Carrega OHLCV para símbolo, usando cache Parquet se disponível.

        Pipeline:
        1. Tentar carregar do Parquet cache (rápido)
        2. Se falhar, carregar do SQLite (lento mas authoritative)
        3. Converter para Parquet se não existia
        4. Aplicar filtros de data
        5. Retornar DataFrame

        Args:
            symbol: Símbolo (ex: 'BTCUSDT')
            timeframe: 'h1', 'h4', ou 'd1' (default: h4)
            start_date: Timestamp início (opcional)
            end_date: Timestamp fim (opcional)

        Returns:
            DataFrame com OHLCV histórico normalizados

        Raises:
            ValueError: Se símbolo/timeframe inválido
            IOError: Se banco SQLite inacessível
        """
        try:
            cache_key = f"{symbol}_{timeframe}"

            # 1. Tentar memory cache (mais rápido)
            if cache_key in self._memory_cache:
                logger.debug(f"Cache hit (memory): {cache_key}")
                df = self._memory_cache[cache_key]
            else:
                # 2. Tentar Parquet cache
                parquet_path = self._get_parquet_path(symbol, timeframe)

                if parquet_path.exists():
                    logger.debug(f"Cache hit (Parquet): {parquet_path}")
                    df = pd.read_parquet(parquet_path)
                else:
                    # 3. Carregar do SQLite (fonte de verdade)
                    logger.debug(f"Cache miss, loading from SQLite: {symbol} {timeframe}")
                    df = self._load_from_sqlite(symbol, timeframe)

                    if df.empty:
                        logger.warning(f"No data found for {symbol} {timeframe}")
                        return pd.DataFrame()

                    # Salvar para Parquet cache
                    try:
                        df.to_parquet(parquet_path, index=False)
                        logger.debug(f"Parquet cache created: {parquet_path}")
                    except Exception as e:
                        logger.warning(f"Failed to save Parquet cache: {e}")

                # Armazenar em memory cache
                self._memory_cache[cache_key] = df

            # 4. Aplicar filtros de data
            if start_date or end_date:
                df = df.copy()
                if 'timestamp' in df.columns:
                    if start_date:
                        df = df[df['timestamp'] >= start_date]
                    if end_date:
                        df = df[df['timestamp'] <= end_date]

            return df.reset_index(drop=True)

        except Exception as e:
            logger.error(f"Error loading OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    def _load_from_sqlite(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Carrega dados OHLCV do SQLite.

        Args:
            symbol: Ex. 'BTCUSDT'
            timeframe: 'h1', 'h4', 'd1'

        Returns:
            DataFrame com dados históricos
        """
        try:
            # Map timeframe para table no SQLite
            table_map = {
                'h1': 'ohlcv_h1',
                'h4': 'ohlcv_h4',
                'd1': 'ohlcv_d1'
            }

            table_name = table_map.get(timeframe)
            if not table_name:
                logger.error(f"Unknown timeframe: {timeframe}")
                return pd.DataFrame()

            # Query com ORDER BY para garantir continuidade
            query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM {table_name}
            WHERE symbol = ?
            ORDER BY timestamp ASC
            """

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=(symbol,))

            logger.info(f"Loaded {len(df)} candles from SQLite: {symbol} {timeframe}")
            return df

        except Exception as e:
            logger.error(f"Error loading from SQLite ({symbol} {timeframe}): {e}")
            return pd.DataFrame()

    def get_cached_data_as_arrays(self, symbol: str) -> Dict[str, np.ndarray]:
        """
        Retorna dados em formato NumPy arrays para performance máxima.

        Carrega H1, H4, D1 e retorna como arrays prontos para cálculos vetorizados.

        Returns:
            {
                'h1': np.array (N, 5) — [open, high, low, close, volume],
                'h4': np.array (M, 5),
                'd1': np.array (K, 5)
            }

        Raises:
            ValueError: Se símbolo inválido ou sem dados
        """
        try:
            result = {}

            for timeframe in ['h1', 'h4', 'd1']:
                df = self.load_ohlcv_for_symbol(symbol, timeframe)

                if df.empty:
                    logger.warning(f"No data for {symbol} {timeframe}, using zeros")
                    result[timeframe] = np.zeros((0, 5), dtype=np.float32)
                else:
                    # Extrair colunas e converter para array
                    cols = ['open', 'high', 'low', 'close', 'volume']
                    arr = df[cols].values.astype(np.float32)
                    result[timeframe] = arr
                    logger.debug(f"Loaded {len(arr)} rows for {symbol} {timeframe}")

            return result

        except Exception as e:
            logger.error(f"Error getting cached arrays for {symbol}: {e}")
            return {
                'h1': np.zeros((0, 5), dtype=np.float32),
                'h4': np.zeros((0, 5), dtype=np.float32),
                'd1': np.zeros((0, 5), dtype=np.float32)
            }

    def validate_candle_continuity(self, symbol: str, timeframe: str) -> Tuple[bool, Optional[str]]:
        """
        Validar que não há gaps nos dados OHLCV (continuidade de candles).

        Verifica que:
        - Cada timestamp segue o anterior pelo intervalo correto
        - Sem volume zero
        - OHLC sanity (high >= max(open,close), low <= min(open,close))

        Args:
            symbol: Símbolo
            timeframe: 'h1', 'h4', ou 'd1'

        Returns:
            (is_valid: bool, error_message: Optional[str])
            Se inválido, retorna False + mensagem descritiva
        """
        try:
            df = self.load_ohlcv_for_symbol(symbol, timeframe)

            if df.empty:
                return False, f"No data found for {symbol} {timeframe}"

            # Validações
            # 1. Check gaps de timestamp
            timeframe_seconds = {
                'h1': 3600,
                'h4': 3600 * 4,
                'd1': 3600 * 24
            }.get(timeframe, 3600)

            if len(df) > 1 and 'timestamp' in df.columns:
                diffs = df['timestamp'].diff()[1:]
                invalid_gaps = diffs[diffs != timeframe_seconds]

                if len(invalid_gaps) > 0:
                    return False, f"Found {len(invalid_gaps)} gaps (expected {timeframe_seconds}s intervals)"

            # 2. Check volume zero
            zero_volume = (df['volume'] == 0).sum()
            if zero_volume > 0:
                return False, f"Found {zero_volume} candles with zero volume"

            # 3. Check OHLC sanity
            max_open_close = df[['open', 'close']].max(axis=1)
            min_open_close = df[['open', 'close']].min(axis=1)

            invalid_high = (df['high'] < max_open_close).sum()
            invalid_low = (df['low'] > min_open_close).sum()

            if invalid_high > 0 or invalid_low > 0:
                return False, f"OHLC sanity violations: {invalid_high} high, {invalid_low} low"

            logger.info(f"✅ Continuity OK: {symbol} {timeframe} ({len(df)} candles)")
            return True, None

        except Exception as e:
            logger.error(f"Error validating continuity for {symbol}: {e}")
            return False, str(e)

    def clear_memory_cache(self):
        """
        Limpar cache em memória (útil durante testes).
        Parquet cache persistente não é alterado.
        """
        self._memory_cache.clear()
        logger.info("Memory cache cleared")

# ============================================================================
# Helper Functions
# ============================================================================

def timestamp_to_parquet_path(symbol: str, date: int, cache_dir: str = "backtest/cache") -> str:
    """
    Convert timestamp + symbol to Parquet file path com partição por data.

    Útil para organizar cache por data (ex. para rebalancing semanal).

    Args:
        symbol: Ex. 'BTCUSDT'
        date: Unix timestamp em ms
        cache_dir: Diretório base

    Returns:
        Path string (ex. 'backtest/cache/BTCUSDT/2026/02/21.parquet')
    """
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(date / 1000, tz=timezone.utc)
    year = dt.strftime('%Y')
    month = dt.strftime('%m')
    day = dt.strftime('%d')

    dir_path = Path(cache_dir) / symbol / year / month
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"{day}.parquet"
    return str(file_path)


def merge_timeframes(h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    """
    Merge múltiplos timeframes em DataFrame único com prefixo.

    Útil para análise multi-timeframe em contexto único.

    Args:
        h1: DataFrame H1 com colunas [timestamp, open, high, low, close, volume]
        h4: DataFrame H4 (idem)
        d1: DataFrame D1 (idem)

    Returns:
        DataFrame merged com colunas:
        - timestamp (de H1, mais granular)
        - h1_open, h1_high, ... (H1 data)
        - h4_open, h4_high, ... (H4 data interpolada)
        - d1_open, d1_high, ... (D1 data interpolada)
    """
    try:
        if h1.empty:
            logger.warning("H1 data empty, returning empty DataFrame")
            return pd.DataFrame()

        # Use H1 como base (mais granular)
        merged = h1.copy()

        # Renomear colunas H1
        h1_cols = ['open', 'high', 'low', 'close', 'volume']
        h1_rename = {col: f'h1_{col}' for col in h1_cols if col in merged.columns}
        merged = merged.rename(columns=h1_rename)

        # Merge H4 (interpolar para H1 timestamps)
        if not h4.empty:
            h4_renamed = h4.rename(columns={
                'open': 'h4_open',
                'high': 'h4_high',
                'low': 'h4_low',
                'close': 'h4_close',
                'volume': 'h4_volume'
            })
            merged = pd.merge_asof(
                merged, h4_renamed,
                on='timestamp',
                direction='backward'
            )

        # Merge D1 (interpolar para H1 timestamps)
        if not d1.empty:
            d1_renamed = d1.rename(columns={
                'open': 'd1_open',
                'high': 'd1_high',
                'low': 'd1_low',
                'close': 'd1_close',
                'volume': 'd1_volume'
            })
            merged = pd.merge_asof(
                merged, d1_renamed,
                on='timestamp',
                direction='backward'
            )

        logger.info(f"Merged {len(h1)} H1 rows with H4 and D1 data")
        return merged

    except Exception as e:
        logger.error(f"Error merging timeframes: {e}")
        return pd.DataFrame()
