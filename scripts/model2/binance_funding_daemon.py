"""
M2-016.3 Phase D.2: Daemon de Coleta Binance (Funding Rates + Open Interest).

Propósito:
- Background collector rodando continuamente
- Coleta funding rates a cada 8h (frequência oficial Binance)
- Coleta open interest a cada 1h
- Monitora e registra erros
"""

import sqlite3
import logging
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Adicionar root ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/binance_collector_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BinanceFundingDaemon:
    """Collector daemon para Binance Funding Rates e Open Interest."""

    def __init__(self, db_path: str = "db/modelo2.db", use_mock: bool = True):
        """
        Inicializa daemon.
        
        Args:
            db_path: Caminho SQLite
            use_mock: True = modo simulação, False = API real
        """
        self.db_path = db_path
        self.use_mock = use_mock
        
        # Importar client
        from scripts.model2.binance_funding_api_client import BinanceFundingAPIClient
        self.api_client = BinanceFundingAPIClient(
            db_path=db_path,
            use_mock=use_mock
        )
        
        # Schedule config
        self.fr_interval_sec = 8 * 3600  # 8 horas
        self.oi_interval_sec = 3600      # 1 hora
        self.last_fr_collect = {}
        self.last_oi_collect = {}
        
        # Símbolos monitorados (do config oficial)
        self.symbols = self._load_symbols()
        
        logger.info(f"Daemon inicializado: {len(self.symbols)} símbolos, mock={use_mock}")

    def _load_symbols(self) -> List[str]:
        """Carrega símbolos do config oficial."""
        try:
            # Tentar carregar de config/symbols.py
            from config.symbols import SYMBOLS_ENABLED
            return SYMBOLS_ENABLED
        except:
            # Fallback para símbolos padrão
            logger.warning("Falha ao carregar símbolos; usando padrão")
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    def should_collect_funding_rate(self, symbol: str) -> bool:
        """Verifica se é hora de coletar funding rate."""
        now = time.time()
        last = self.last_fr_collect.get(symbol, 0)
        return (now - last) >= self.fr_interval_sec

    def should_collect_oi(self, symbol: str) -> bool:
        """Verifica se é hora de coletar open interest."""
        now = time.time()
        last = self.last_oi_collect.get(symbol, 0)
        return (now - last) >= self.oi_interval_sec

    def collect_funding_rates(self) -> int:
        """
        Coleta funding rates para todos os símbolos.
        
        Returns:
            Número de registros coletados
        """
        count = 0
        for symbol in self.symbols:
            if not self.should_collect_funding_rate(symbol):
                continue
            
            try:
                history = self.api_client.fetch_funding_rate_history(symbol, limit=100)
                
                if history:
                    # Persistir últimos 10 registros
                    for rate_data in history[:10]:
                        if self.api_client.persist_funding_rate(symbol, rate_data):
                            count += 1
                    
                    self.last_fr_collect[symbol] = time.time()
                    logger.info(f"FR collected: {symbol} ({len(history)} history, {count} persisted)")
                
            except Exception as e:
                logger.error(f"Erro coletando FR para {symbol}: {e}")
        
        return count

    def collect_open_interest(self, price_map: dict = None) -> int:
        """
        Coleta open interest para todos os símbolos.
        
        Args:
            price_map: {symbol: current_price} para cálculo USD
            
        Returns:
            Número de registros coletados
        """
        if price_map is None:
            price_map = {s: 40000 for s in self.symbols}  # Mock prices
        
        count = 0
        for symbol in self.symbols:
            if not self.should_collect_oi(symbol):
                continue
            
            try:
                oi_data = self.api_client.fetch_open_interest(symbol)
                
                if oi_data:
                    price = price_map.get(symbol, 40000)
                    if self.api_client.persist_open_interest(symbol, oi_data, price):
                        count += 1
                        self.last_oi_collect[symbol] = time.time()
                        logger.info(f"OI collected: {symbol} (persisted)")
                
            except Exception as e:
                logger.error(f"Erro coletando OI para {symbol}: {e}")
        
        return count

    def run_once(self, price_map: dict = None) -> dict:
        """
        Executa uma iteração de coleta.
        
        Args:
            price_map: Preços para cálculo USD
            
        Returns:
            {fr_count, oi_count, timestamp}
        """
        fr_count = self.collect_funding_rates()
        oi_count = self.collect_open_interest(price_map)
        
        return {
            "fr_collected": fr_count,
            "oi_collected": oi_count,
            "timestamp": datetime.utcnow().isoformat(),
            "symbols_monitored": len(self.symbols)
        }

    def run_daemon(self, interval_sec: int = 300, max_iterations: int = None):
        """
        Executa daemon continuamente.
        
        Args:
            interval_sec: Sleep entre cheques (default 5 min)
            max_iterations: Máx iterações ou None (infinito)
        """
        logger.info(f"Daemon iniciando (interval={interval_sec}s)")
        
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            try:
                result = self.run_once()
                
                if result["fr_collected"] > 0 or result["oi_collected"] > 0:
                    logger.info(f"Cycle {iteration}: FR={result['fr_collected']}, OI={result['oi_collected']}")
                
                time.sleep(interval_sec)
                iteration += 1
                
            except KeyboardInterrupt:
                logger.info("Daemon parado by user")
                break
            except Exception as e:
                logger.error(f"Erro no daemon loop: {e}")
                time.sleep(interval_sec)

    def get_collection_stats(self) -> dict:
        """Retorna estatísticas de coleta."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM funding_rates_api")
                fr_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM open_interest_api")
                oi_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT symbol) FROM funding_rates_api")
                fr_symbols = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT symbol) FROM open_interest_api")
                oi_symbols = cursor.fetchone()[0]
            
            return {
                "funding_rates_total": fr_count,
                "funding_rate_symbols": fr_symbols,
                "open_interest_total": oi_count,
                "open_interest_symbols": oi_symbols,
            }
        except Exception as e:
            logger.error(f"Erro ao query stats: {e}")
            return {}


# ===== Test/Demo

if __name__ == "__main__":
    import json
    
    print("=== Binance Funding Daemon (Demo Mode) ===\n")
    
    daemon = BinanceFundingDaemon(use_mock=True)
    
    print("1. Executando 3 ciclos de coleta...\n")
    for i in range(3):
        result = daemon.run_once(price_map={"BTCUSDT": 40000, "ETHUSDT": 2500})
        print(f"Ciclo {i+1}: {json.dumps(result, indent=2)}")
        time.sleep(1)
    
    print("\n2. Estatísticas de coleta:")
    stats = daemon.get_collection_stats()
    print(f"   {json.dumps(stats, indent=2)}")
    
    print("\n[OK] Daemon funcionando corretamente")
