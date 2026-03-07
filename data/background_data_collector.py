"""
Background data collector - Coleta contínua de dados OHLCV em paralelo.

Propósito:
- Coletar dados de TODOS os símbolos periodicamente
- Persistir em banco de dados para manter histórico atualizado
- Rodar em thread separada (não bloqueia o agente)
- Tratamento robusto de erros e rate limiting
"""

import threading
import time
import logging
from typing import Optional, List
from datetime import datetime

from data.binance_client import create_data_client
from data.collector import BinanceCollector
from data.database import DatabaseManager
from config.symbols import ALL_SYMBOLS

logger = logging.getLogger(__name__)


class BackgroundDataCollector:
    """
    Coleta dados OHLCV continuamente em background.
    
    Roda em thread separada para não bloquear operações principais.
    Atualiza banco de dados com dados frescos de todos os símbolos.
    """

    def __init__(self, db: DatabaseManager, interval_seconds: int = 300):
        """
        Initialize background data collector.

        Args:
            db: DatabaseManager instance
            interval_seconds: Intervalo entre ciclos de coleta (default: 300s = 5min)
        """
        self.db = db
        self.interval_seconds = interval_seconds
        self._data_client = create_data_client()  # Always production
        self._collector = BinanceCollector(self._data_client)  # Wrapper for klines fetching
        self._running = False
        self._thread = None
        self._stats = {
            'cycles': 0,
            'symbols_processed': 0,
            'symbols_succeeded': 0,
            'symbols_failed': 0,
            'last_cycle_timestamp': None,
            'last_error': None
        }
        logger.info(
            f"BackgroundDataCollector initialized (interval={interval_seconds}s, "
            f"symbols={len(ALL_SYMBOLS)})"
        )

    def start(self) -> None:
        """Inicia coleta em background."""
        if self._running:
            logger.warning("BackgroundDataCollector já está rodando")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_collection_loop, daemon=True)
        self._thread.start()
        logger.info("[INICIADO] BackgroundDataCollector iniciado")

    def stop(self) -> None:
        """Para coleta em background."""
        if not self._running:
            logger.warning("BackgroundDataCollector não está rodando")
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[PARADO] BackgroundDataCollector parado")

    def _run_collection_loop(self) -> None:
        """
        Main collection loop - roda em thread separada.
        
        Ciclo:
        1. Coleta H4 e H1 para todos os símbolos
        2. Persiste no banco
        3. Aguarda interval_seconds
        4. Repete
        """
        logger.info(
            f"Iniciando loop de coleta (interval={self.interval_seconds}s, "
            f"ciclo inicial em {self.interval_seconds}s)"
        )

        # Inicial delay - permite que o agente comece primeiro
        time.sleep(2)

        while self._running:
            try:
                self._run_collection_cycle()
                time.sleep(self.interval_seconds)
            except Exception as e:
                logger.error(f"Erro no loop de coleta: {e}", exc_info=True)
                self._stats['last_error'] = str(e)
                time.sleep(self.interval_seconds)

    def _run_collection_cycle(self) -> None:
        """
        Execute uma coleta completa de todos os símbolos.
        
        Processa H4 e H1 para cada símbolo, inserindo no banco.
        """
        cycle_start = time.time()
        self._stats['symbols_processed'] = 0
        self._stats['symbols_succeeded'] = 0
        self._stats['symbols_failed'] = 0

        logger.info(
            f"\n{'='*70}\n"
            f"CICLO DE COLETA #{self._stats['cycles'] + 1} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'='*70}"
        )

        # Coletar para cada símbolo
        for symbol in ALL_SYMBOLS:
            self._stats['symbols_processed'] += 1

            try:
                # Coletar H4
                self._collect_symbol_timeframe(symbol, '4h', 'H4', limit=300)

                # Coletar H1
                self._collect_symbol_timeframe(symbol, '1h', 'H1', limit=250)

                self._stats['symbols_succeeded'] += 1

            except Exception as e:
                logger.warning(f"Erro coletando {symbol}: {e}")
                self._stats['symbols_failed'] += 1

        # Estatísticas do ciclo
        cycle_duration = time.time() - cycle_start
        self._stats['cycles'] += 1
        self._stats['last_cycle_timestamp'] = datetime.now().isoformat()

        logger.info(
            f"\n[CICLO] #{self._stats['cycles']} completo\n"
            f"   - Simbolos processados: {self._stats['symbols_succeeded']}/{self._stats['symbols_processed']}\n"
            f"   - Falhas: {self._stats['symbols_failed']}\n"
            f"   - Duracao: {cycle_duration:.1f}s\n"
            f"{'='*70}\n"
        )

    def _collect_symbol_timeframe(
        self, symbol: str, timeframe: str, timeframe_db: str, limit: int
    ) -> None:
        """
        Coleta dados para um símbolo em um timeframe específico.

        Args:
            symbol: Símbolo (ex: BTCUSDT)
            timeframe: Timeframe API (ex: '4h', '1h')
            timeframe_db: Timeframe banco (ex: 'H4', 'H1')
            limit: Quantidade de candles a buscar
        """
        try:
            # Buscar candles usando BinanceCollector
            df = self._collector.fetch_klines(
                symbol=symbol,
                interval=timeframe,
                limit=limit
            )

            if df is None or df.empty:
                logger.debug(f"Sem dados para {symbol} {timeframe}")
                return

            # Inserir no banco (INSERT OR REPLACE evita duplicatas)
            self.db.insert_ohlcv(timeframe_db, df)
            logger.debug(f"[OK] {symbol} {timeframe}: {len(df)} candles inseridos")

        except Exception as e:
            logger.warning(f"Erro coletando {symbol} {timeframe}: {e}")
            raise

    def get_stats(self) -> dict:
        """Retorna estatísticas de coleta."""
        return self._stats.copy()

    def is_running(self) -> bool:
        """Retorna se collector está rodando."""
        return self._running


def start_background_collector(
    db: DatabaseManager, interval_seconds: int = 300
) -> BackgroundDataCollector:
    """
    Cria e inicia o background data collector.

    Args:
        db: DatabaseManager
        interval_seconds: Intervalo de coleta em segundos

    Returns:
        BackgroundDataCollector instance já iniciado
    """
    collector = BackgroundDataCollector(db, interval_seconds)
    collector.start()
    return collector
