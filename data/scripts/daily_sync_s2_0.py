#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📅 Daily Sync Script - S2-0 Data Strategy
Execute daily para sincronizar novos candles (últimas 4h)

Scheduling:
  Cron:  '5 0 * * *' (00:05 UTC daily)
  Systemd: ExecStart=/usr/bin/python3 /path/to/daily_sync_s2_0.py
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from data.scripts.klines_cache_manager import KlinesOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[
        logging.FileHandler("data/daily_sync_s2_0.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def daily_sync():
    """Executa sincronização diária de dados."""
    logger.info("=" * 80)
    logger.info("📅 DAILY SYNC S2-0 START")
    logger.info("=" * 80)
    
    try:
        # Initialize
        orch = KlinesOrchestrator(
            db_path="data/klines_cache.db",
            symbols_file="config/symbols.json"
        )
        
        logger.info(f"\n📊 Iniciando sync para {len(orch.symbols)} símbolos...")
        
        # Fetch apenas últimos 4h (+ 30min de margem para segurança)
        sync_stats = orch.fetch_full_year(
            symbols=orch.symbols,
            interval="4h",
            from_days_ago=1  # Apenas últimas 24h
        )
        
        # Analyze results
        success_count = sum(1 for c in sync_stats.values() if isinstance(c, int) and c > 0)
        total_new = sum(c for c in sync_stats.values() if isinstance(c, int))
        
        logger.info(f"\n✅ SYNC COMPLETADO")
        logger.info(f"   Símbolos processados: {success_count}")
        logger.info(f"   Candles inseridos: {total_new}")
        logger.info(f"   Timestamp: {datetime.utcnow().isoformat()}")
        
        # Save report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbols_processed": success_count,
            "candles_inserted": total_new,
            "status": "SUCCESS"
        }
        
        report_path = Path("data/daily_sync_reports.jsonl")
        with open(report_path, 'a') as f:
            f.write(json.dumps(report) + "\n")
        
        logger.info(f"   Report: {report_path}")
        
        return 0
    
    except Exception as e:
        logger.error(f"\n❌ SYNC FAILED: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = daily_sync()
    sys.exit(exit_code)
