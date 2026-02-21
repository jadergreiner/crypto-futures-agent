#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduler Contínuo - Rodar monitor_positions a cada minuto
Execute: python scripts/schedule_monitor.py
Ou para background: python scripts/schedule_monitor.py &
"""

import logging
import sys
import os
import time
from datetime import datetime
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_scheduler(interval_seconds=60):
    """
    Rodar monitor_positions continuamente.

    Args:
        interval_seconds: Intervalo entre execuções (padrão: 60s / 1 minuto)
    """

    logger.info("=" * 80)
    logger.info("🔄 SCHEDULER - MONITORAMENTO CONTÍNUO DE POSIÇÕES")
    logger.info("=" * 80)
    logger.info(f"   Intervalo: {interval_seconds} segundos")
    logger.info(f"   Inicie com: Ctrl+C para parar")
    logger.info("")

    cycle = 0

    try:
        while True:
            cycle += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            logger.info("")
            logger.info(f"🔄 CICLO {cycle} - {timestamp}")
            logger.info("-" * 80)

            try:
                # Executar monitor_positions
                result = subprocess.run(
                    [sys.executable, "scripts/monitor_positions.py"],
                    capture_output=False,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.warning(f"   ⚠️  monitor_positions retornou código: {result.returncode}")

            except subprocess.TimeoutExpired:
                logger.warning(f"   ⚠️  monitor_positions excedeu timeout de 30s")
            except Exception as e:
                logger.error(f"   ❌ Erro ao executar monitor_positions: {e}")

            # Aguardar próximo ciclo
            logger.info(f"   ⏳ Aguardando próximo ciclo em {interval_seconds}s...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        logger.info("")
        logger.info("🛑 SCHEDULER PARADO PELO USUÁRIO")
        logger.info("=" * 80)
        return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scheduler para monitorar posições continuamente")
    parser.add_argument("--interval", type=int, default=60, help="Intervalo em segundos (padrão: 60)")
    parser.add_argument("--once", action="store_true", help="Executar apenas uma vez")

    args = parser.parse_args()

    if args.once:
        # Executar apenas uma vez
        logger.info("Executando monitor_positions uma vez...")
        subprocess.run([sys.executable, "scripts/monitor_positions.py"])
    else:
        # Rodar scheduler
        success = run_scheduler(interval_seconds=args.interval)
        exit(0 if success else 1)
