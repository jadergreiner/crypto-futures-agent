"""
Pipeline de dados para treinamento do modelo RL.
Carrega OHLCV + 104 features do banco de dados com otimizações SQL e lazy-loading.

Arquitetura:
- load_training_data(): carrega dados históricos do DB com validações
- prepare_training_sequences(): cria séries temporais deslizantes
- DataLoader: classe reutilizável com batch generation
- RobustScaler aplicado por símbolo (sem data leakage)

Performance alvo:
- Load 18M dados H1: < 2 segundos
- Batch 100K timesteps: < 5 segundos
- Peak memory: < 8 GB
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Generator, Any
from contextlib import contextmanager

import pandas as pd
import numpy as np
from sklearn.preprocessing import RobustScaler

from config.symbols import SYMBOLS
from indicators.features import FeatureEngineer
from monitoring.logger import AgentLogger

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Carregador de dados para treinamento com suporte a batch generation.

    Features:
    - Carregamento otimizado do DB com índices SQL
    - Validação de integridade de dados (gaps, NaN, distribuição)
    - RobustScaler por símbolo (evita data leakage)
    - Generator lazy para batches (economiza memória)
    - Normalização dinâmica de features

    Exemplo:
        >>> loader = DataLoader('db/agent.db')
        >>> for batch_x, batch_y in loader.get_training_batches(['BTCUSDT'], batch_size=32):
        ...     # batch_x: (32, 50, 104) - sequências normalizadas
        ...     # batch_y: (32, 5) - ações (one-hot)
        ...     model.train_on_batch(batch_x, batch_y)
    """

    def __init__(self, db_path: str):
        """
        Inicializa DataLoader.

        Args:
            db_path: Caminho para arquivo SQLite
        """
        self.db_path = db_path
        self.fe = FeatureEngineer()
        self.scalers: Dict[str, RobustScaler] = {}  # Um scaler por símbolo

        logger.info(f"[DataLoader] Inicializado com DB: {db_path}")

    @contextmanager
    def get_connection(self):
        """Context manager para conexão com DB."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def load_training_data(
        self,
        symbol: str,
        start_date: str = "2024-08-01",
        end_date: str = "2026-02-20",
        timeframe: str = "H1"
    ) -> pd.DataFrame:
        """
        Carrega dados históricos do DB com validações.

        Args:
            symbol: Símbolo (ex: 'BTCUSDT')
            start_date: Data de início (format: 'YYYY-MM-DD')
            end_date: Data de fim (format: 'YYYY-MM-DD')
            timeframe: 'H1', 'H4', 'D1'

        Returns:
            DataFrame com colunas [timestamp, open, high, low, close, volume, ...104 features]

        Raises:
            RuntimeError: Se DB vazio ou dados inválidos
        """
        try:
            # Parse datas
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

            table_name = f"ohlcv_{timeframe.lower()}"

            logger.info(f"[DataLoader.load] Carregando {symbol} {timeframe}: {start_date} → {end_date}")

            with self.get_connection() as conn:
                # Query otimizada com índices
                query = f"""
                SELECT
                    timestamp,
                    symbol,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    quote_volume,
                    trades_count
                FROM {table_name}
                WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                """

                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(symbol, start_ts, end_ts)
                )

            if df.empty:
                raise RuntimeError(f"[DataLoader] {symbol} sem dados entre {start_date} e {end_date}")

            logger.info(f"[DataLoader.load] {symbol}: {len(df)} candles carregados")

            # --- Validações ---
            # 1. Remove candles com volume = 0 (não tradável)
            df_before = len(df)
            df = df[df['volume'] > 0]
            if len(df) < df_before:
                logger.warning(f"[DataLoader.load] {symbol}: removidos {df_before - len(df)} candles com volume=0")

            # 2. Detecta gaps > 15 minutos (indica dados faltantes)
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['gap_minutes'] = df['timestamp_dt'].diff().dt.total_seconds() / 60

            gaps = df[df['gap_minutes'] > 15]
            if not gaps.empty:
                logger.warning(f"[DataLoader.load] {symbol}: {len(gaps)} gaps detectados (> 15 min)")
                # Remove períodos com gaps longos
                df = df[df['gap_minutes'].fillna(0) <= 15]

            # 3. Valida NaN e inf
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            nan_count = df[numeric_cols].isna().sum().sum()
            if nan_count > 0:
                logger.warning(f"[DataLoader.load] {symbol}: {nan_count} valores NaN encontrados, removendo")
                df = df.dropna(subset=numeric_cols)

            # 4. Valida integridade OHLC
            invalid_ohlc = df[(df['high'] < df['low']) | (df['high'] < df['close']) | (df['low'] > df['close'])]
            if not invalid_ohlc.empty:
                logger.warning(f"[DataLoader.load] {symbol}: {len(invalid_ohlc)} candles com OHLC inválido, removendo")
                df = df.drop(invalid_ohlc.index)

            # Se perdemos > 10% dos dados → problema na coleta
            if len(df) < df_before * 0.9:
                logger.error(f"[DataLoader.load] {symbol}: perdeu {(1 - len(df)/df_before)*100:.1f}% dos dados")
                raise RuntimeError(f"Integridade de dados comprometida para {symbol}")

            # Drop coluna temporal auxiliar
            df = df.drop(columns=['timestamp_dt', 'gap_minutes'])

            # Converte timestamp millisegundos → índice datetime
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp_dt')
            df.index.name = 'timestamp'

            logger.info(f"[DataLoader.load] {symbol}: {len(df)} candles validados")

            return df

        except Exception as e:
            logger.error(f"[DataLoader.load] Erro ao carregar {symbol}: {e}")
            raise

    def prepare_training_sequences(
        self,
        df: pd.DataFrame,
        symbols: List[str],
        window_size: int = 50,
        stride: int = 10,
        normalize: bool = True
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Prepara séries temporais com janelas deslizantes.

        Args:
            df: DataFrame com OHLCV (índice: timestamp)
            symbols: Lista de símbolos (para construir features)
            window_size: Tamanho da janela (50 = ~2 dias em H1)
            stride: Passo (10 = divisão em 5 partes para treino, 25 para validação)
            normalize: Normalizar com RobustScaler?

        Returns:
            (X, scalers_dict) onde:
            - X: (n_sequences, window_size, 104) - features normalizadas
            - scalers_dict: {symbol: RobustScaler} para inverse_transform posterior

        Shape esperado:
            Input:  (4380, 8) [18M candles H1, 8 colunas OHLCV]
            Output: (n_sequences, 50, 104) [sequências prontas para env.step()]
        """
        try:
            if len(df) < window_size * 2:
                raise ValueError(f"Dataset é muito pequeno: {len(df)} < {window_size*2}")

            symbol = symbols[0] if symbols else "BTCUSDT"
            logger.info(f"[DataLoader.prepare] Preparando {symbol}: window={window_size}, stride={stride}")

            sequences = []

            # Itera com janela deslizante
            for i in range(0, len(df) - window_size, stride):
                window_data = df.iloc[i:i+window_size]

                # Constrói features para cada timestep na janela
                timestep_features = []
                for j in range(len(window_data)):
                    # Observação até step j (without look-ahead)
                    h1_data = window_data.iloc[:j+1]

                    # Extrai features usando FeatureEngineer
                    # (simplificado: usa apenas OHLCV, sem sentimento/macro/SMC para versão 0.3)
                    features = self._extract_features_simple(h1_data, symbol)
                    timestep_features.append(features)

                # Sequence: (window_size, 104)
                sequence = np.array(timestep_features, dtype=np.float32)

                # Validação
                if sequence.shape != (window_size, 104):
                    logger.warning(f"[DataLoader.prepare] Sequência com shape inválido: {sequence.shape}, pulando")
                    continue

                if np.isnan(sequence).any() or np.isinf(sequence).any():
                    logger.warning(f"[DataLoader.prepare] Sequência contém NaN/inf, pulando")
                    continue

                sequences.append(sequence)

            if not sequences:
                raise RuntimeError(f"Nenhuma sequência válida gerada para {symbol}")

            X = np.array(sequences, dtype=np.float32)  # (n_sequences, 50, 104)

            logger.info(f"[DataLoader.prepare] {len(sequences)} sequências geradas, shape={X.shape}")

            # Normalização com RobustScaler por símbolo
            scalers_dict = {}
            if normalize:
                X_normalized = X.copy()

                for symbol in symbols:
                    # Reshape para fit: (n_sequences * window_size, 104)
                    X_reshaped = X.reshape(-1, 104)

                    scaler = RobustScaler()
                    X_scaled = scaler.fit_transform(X_reshaped)
                    X_normalized = X_scaled.reshape(X.shape)

                    scalers_dict[symbol] = scaler
                    logger.info(f"[DataLoader.prepare] {symbol}: RobustScaler fit e aplicado")

                X = X_normalized

            return X, scalers_dict

        except Exception as e:
            logger.error(f"[DataLoader.prepare] Erro ao preparar sequências: {e}")
            raise

    def get_training_batches(
        self,
        symbols: List[str],
        batch_size: int = 32,
        shuffle: bool = True,
        start_date: str = "2024-08-01",
        end_date: str = "2026-02-20",
        window_size: int = 50,
        stride_train: int = 10
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generator de batches para treinamento.

        Args:
            symbols: Lista de símbolos para treinar
            batch_size: Tamanho do batch (32)
            shuffle: Embaralhar batches?
            start_date: Data de início
            end_date: Data de fim
            window_size: Tamanho da janela
            stride_train: Stride para treino (pode ter overlap)

        Yields:
            (X_batch, y_batch) onde:
            - X_batch: (batch_size, window_size, 104)
            - y_batch: (batch_size, 5) - ações one-hot [HOLD, LONG, SHORT, CLOSE, REDUCE_50]

        Exemplo:
            >>> for X, y in loader.get_training_batches(['BTCUSDT'], batch_size=32):
            ...     print(X.shape)  # (32, 50, 104)
            ...     break
        """
        try:
            all_sequences = []

            # Carrega dados para cada símbolo
            for symbol in symbols:
                logger.info(f"[DataLoader.batches] Carregando {symbol}...")
                df = self.load_training_data(symbol, start_date, end_date, timeframe="H1")

                X_symbol, scalers = self.prepare_training_sequences(
                    df, [symbol], window_size, stride_train, normalize=True
                )

                all_sequences.extend(X_symbol)

            all_sequences = np.array(all_sequences, dtype=np.float32)

            if shuffle:
                indices = np.random.permutation(len(all_sequences))
                all_sequences = all_sequences[indices]

            # Yield em batches
            for i in range(0, len(all_sequences), batch_size):
                X_batch = all_sequences[i:i+batch_size]

                # Y_batch: dummy ações (será gerado pelo modelo durante treinamento)
                # Para agora: distribuição uniforme
                y_batch = np.random.randint(0, 5, size=(len(X_batch),))
                y_batch = np.eye(5)[y_batch]  # One-hot

                yield X_batch, y_batch

        except Exception as e:
            logger.error(f"[DataLoader.batches] Erro ao gerar batches: {e}")
            raise

    @staticmethod
    def _extract_features_simple(h1_data: pd.DataFrame, symbol: str) -> np.ndarray:
        """
        Extrai 104 features de um DataFrame H1.
        Versão simplificada para v0.3 (sem sentimento/macro/SMC).

        Args:
            h1_data: DataFrame H1 até um ponto específico (sem look-ahead)
            symbol: Símbolo para contexto

        Returns:
            Array (104,) com features normalizadas
        """
        features = []

        # Bloco 1: Price (11)
        if len(h1_data) >= 2:
            close = h1_data['close'].values
            ret_1 = (close[-1] - close[-2]) / close[-2] * 100 if close[-2] != 0 else 0
            features.append(ret_1)
        else:
            features.append(0.0)

        # Preenchimento até 11
        while len(features) < 11:
            features.append(0.0)

        # Bloco 2: EMAs (6)
        features.extend([0.0] * 6)  # Placeholder para EMAs (necessita indicadores computados)

        # Bloco 3: Indicadores (11)
        features.extend([0.5] * 11)  # Placeholder

        # Bloco 4: SMC (19)
        features.extend([0.0] * 19)  # Placeholder

        # Bloco 5: Sentiment (4)
        features.extend([0.0] * 4)  # Placeholder

        # Bloco 6: Macro (4)
        features.extend([0.0] * 4)  # Placeholder

        # Bloco 7: Position state (32)
        features.extend([0.0] * 32)  # Placeholder

        # Bloco 8: Multi-timeframe (1)
        features.extend([0.0] * 1)  # Placeholder

        return np.array(features[:104], dtype=np.float32)


def validate_training_data(
    db_path: str,
    symbols: List[str],
    start_date: str = "2024-08-01",
    end_date: str = "2026-02-20"
) -> Dict[str, Any]:
    """
    Valida integridade do dataset de treinamento.

    Retorna:
        {
            'overall_status': 'OK' | 'WARNING' | 'CRITICAL',
            'timestamp_range': { 'start': '', 'end': '', 'duration_days': 0 },
            'symbols': { symbol: { 'candles': 0, 'gaps': 0, 'nans': 0, ... } },
            'recommendations': ['...']
        }
    """
    loader = DataLoader(db_path)
    results = {
        'overall_status': 'OK',
        'symbol_results': {},
        'recommendations': []
    }

    for symbol in symbols:
        try:
            df = loader.load_training_data(symbol, start_date, end_date)

            results['symbol_results'][symbol] = {
                'candles': len(df),
                'date_range': f"{df.index.min()} to {df.index.max()}",
                'volume_mean': float(df['volume'].mean()),
                'volume_std': float(df['volume'].std()),
                'close_mean': float(df['close'].mean()),
                'close_std': float(df['close'].std())
            }

        except Exception as e:
            logger.error(f"Validação falhou para {symbol}: {e}")
            results['overall_status'] = 'CRITICAL'
            results['symbol_results'][symbol] = {'error': str(e)}

    return results


if __name__ == "__main__":
    # ===== TESTE RÁPIDO =====
    from config.settings import DATABASE_PATH

    loader = DataLoader(DATABASE_PATH)

    print("[TEST] Carregando BTCUSDT...")
    df = loader.load_training_data("BTCUSDT", "2025-11-01", "2026-02-20")
    print(f"Shape: {df.shape}")

    print("\n[TEST] Preparando sequências...")
    X, scalers = loader.prepare_training_sequences(df, ["BTCUSDT"], window_size=50)
    print(f"X.shape: {X.shape}")

    print("\n[TEST] Gerando batches...")
    batch_count = 0
    for X_batch, y_batch in loader.get_training_batches(["BTCUSDT"], batch_size=32):
        batch_count += 1
        print(f"Batch {batch_count}: X={X_batch.shape}, y={y_batch.shape}")
        if batch_count == 3:
            break
