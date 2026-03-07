#!/usr/bin/env python
"""
Teste do Background Data Collector.

Verifica se:
1. Collector inicia sem erros
2. Coleta dados de alguns símbolos
3. Insere corretamente no banco
"""

import os
import sys
import time
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

from data.database import DatabaseManager
from data.background_data_collector import BackgroundDataCollector
from config.symbols import ALL_SYMBOLS

# Use test database
TEST_DB = "test_background_collector.db"

def test_background_collector():
    """Test background data collector."""
    logger.info("=" * 70)
    logger.info("TEST: Background Data Collector")
    logger.info("=" * 70)
    
    # Clean up test DB if it exists
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        logger.info(f"Removed existing test DB: {TEST_DB}")
    
    # Create fresh test DB
    db = DatabaseManager(TEST_DB)
    logger.info(f"✅ Created test database: {TEST_DB}")
    
    # Create collector
    collector = BackgroundDataCollector(db, interval_seconds=10)
    logger.info(f"✅ Created BackgroundDataCollector")
    logger.info(f"   - Symbols to collect: {len(ALL_SYMBOLS)}")
    logger.info(f"   - Interval: 10 seconds (shortened for test)")
    logger.info(f"   - Timeframes: H4, H1")
    
    # Start collector
    collector.start()
    logger.info(f"✅ Started collector (runs in background)")
    
    # Wait for one cycle to complete
    logger.info("\n🕐 Waiting for first collection cycle to complete...")
    time.sleep(35)  # First cycle takes ~18s + interval 10s + buffer
    
    # Get stats
    stats = collector.get_stats()
    logger.info(f"\n📊 Collector Statistics:")
    logger.info(f"   - Cycles completed: {stats['cycles']}")
    logger.info(f"   - Symbols processed: {stats['symbols_processed']}")
    logger.info(f"   - Symbols succeeded: {stats['symbols_succeeded']}")
    logger.info(f"   - Symbols failed: {stats['symbols_failed']}")
    logger.info(f"   - Last cycle: {stats['last_cycle_timestamp']}")
    
    if stats['last_error']:
        logger.warning(f"   - Last error: {stats['last_error']}")
    
    # Check database
    logger.info(f"\n🗄️  Checking database...")
    sample_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    for symbol in sample_symbols:
        h4_data = db.get_ohlcv('H4', symbol, limit=5)
        h1_data = db.get_ohlcv('H1', symbol, limit=5)
        logger.info(f"   {symbol}: H4={len(h4_data)} candles, H1={len(h1_data)} candles")
    
    # Stop collector
    collector.stop()
    logger.info(f"\n✅ Stopped collector")
    
    # Final results
    success = (
        stats['symbols_succeeded'] > 0 and
        stats['symbols_failed'] == 0
    )
    
    logger.info("\n" + "=" * 70)
    if success:
        logger.info("✅ TEST PASSED: Background collector working correctly")
    else:
        logger.error("❌ TEST FAILED: Issues detected")
        logger.error(f"   Succeeded: {stats['symbols_succeeded']}")
        logger.error(f"   Failed: {stats['symbols_failed']}")
    logger.info("=" * 70)
    
    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        logger.info(f"Cleaned up test DB: {TEST_DB}")
    
    return success

if __name__ == "__main__":
    success = test_background_collector()
    sys.exit(0 if success else 1)
