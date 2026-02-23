"""
Daily incremental candle sync from Binance.
Runs once per day via cron, refreshes last 4 candles for all symbols.

Role: Infrastructure lead ensures data freshness 24/7
Execute: cron @ 01:00 UTC daily (via /opt/jobs/daily_sync.sh)
SLA: 30 minutes max (hard timeout)
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Any

# Configure logging (stdout for cron to capture)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entrypoint for daily sync."""
    
    parser = argparse.ArgumentParser(
        description="Daily incremental candle sync from Binance Futures"
    )
    parser.add_argument("--workspace", type=str, required=True, help="Workspace root")
    parser.add_argument("--symbols", type=str, default="all", help="Symbols to sync")
    parser.add_argument("--lookback", type=int, default=4, help="Recent candles to fetch")
    parser.add_argument("--mode", type=str, default="incremental", help="Sync mode")
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("🚀 DAILY CANDLE SYNC INITIATED")
    logger.info(f"   Workspace: {args.workspace}")
    logger.info(f"   Symbols: {args.symbols}")
    logger.info(f"   Lookback: {args.lookback} candles")
    logger.info("=" * 70)
    
    try:
        # === IMPORTS (lazy to avoid early failures) ===
        sys.path.insert(0, args.workspace)
        
        from data.collector import BinanceCollector
        from data.database import DatabaseManager
        from data.binance_client import get_binance_client
        from config.symbols import ALL_SYMBOLS
        from config.settings import get_db_path
        
        # === SETUP ===
        db_path = get_db_path(args.workspace)
        db = DatabaseManager(db_path)
        client = get_binance_client()
        collector = BinanceCollector(client)
        
        symbols = ALL_SYMBOLS if args.symbols == "all" else args.symbols.split(",")
        
        logger.info(f"📡 {len(symbols)} symbols to sync")
        logger.info(f"📁 Database: {db_path}")
        
        # === SYNC LOOP ===
        stats: Dict[str, Any] = {
            "total_symbols": len(symbols),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "start_time": datetime.utcnow().isoformat(),
        }
        
        for idx, symbol in enumerate(symbols, 1):
            try:
                # Progress indicator
                logger.info(f"[{idx}/{len(symbols)}] Fetching {symbol} (last {args.lookback} candles)...")
                
                # Fetch last 4h candles (incremental)
                candles = collector.get_klines(
                    symbol=symbol,
                    interval="4h",
                    limit=args.lookback
                )
                
                if not candles:
                    logger.warning(f"    ⚠️  No data returned for {symbol}")
                    stats["skipped"] += 1
                    continue
                
                # Upsert to database
                db.upsert_ohlcv_h4(candles)
                
                logger.info(f"    ✅ {len(candles)} candles inserted")
                stats["successful"] += 1
                
            except Exception as e:
                logger.error(f"    ❌ Error: {str(e)}")
                stats["failed"] += 1
                stats["errors"].append({
                    "symbol": symbol,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # === RESULTS ===
        stats["end_time"] = datetime.utcnow().isoformat()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 SYNC RESULTS")
        logger.info(f"   ✅ Successful: {stats['successful']}/{stats['total_symbols']}")
        logger.info(f"   ❌ Failed: {stats['failed']}/{stats['total_symbols']}")
        logger.info(f"   ⏭️  Skipped: {stats['skipped']}/{stats['total_symbols']}")
        
        if stats["errors"]:
            logger.error(f"   🔴 Errors ({len(stats['errors'])}):")
            for err in stats["errors"]:
                logger.error(f"      - {err['symbol']}: {err['error']}")
        
        logger.info("=" * 70)
        
        # === EXIT CODE LOGIC ===
        # Success: >= 59/60 symbols OK (allow 1 failure)
        # Partial failure: >= 50/60 (warn but exit 0)
        # Major failure: < 50/60 (fail)
        
        success_rate = stats["successful"] / stats["total_symbols"]
        
        if success_rate >= 0.98:  # 59+/60
            logger.info("✅ SYNC COMPLETE (full success)")
            return 0
        elif success_rate >= 0.80:  # 48+/60
            logger.warning(f"⚠️  SYNC COMPLETE but {stats['failed']} symbols failed")
            logger.warning("    Data is still usable, monitor next sync run")
            return 0  # Non-blocking (still useful)
        else:
            logger.critical(f"❌ SYNC FAILED (only {stats['successful']} symbols succeeded)")
            return 1
        
    except KeyboardInterrupt:
        logger.warning("⏱️  Sync interrupted by timeout or signal")
        return 124
    except Exception as e:
        logger.critical(f"💥 CRITICAL ERROR (unhandled): {str(e)}")
        import traceback
        logger.critical(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
