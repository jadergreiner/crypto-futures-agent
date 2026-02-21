#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Status Rápido - Uma linha de status
Mostra tudo o que importa em 1-2 linhas
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.binance_client import create_binance_client
from monitoring.position_monitor import PositionMonitor
from data.database import DatabaseManager
from config.settings import DB_PATH


def quick_status():
    """Status executivo em uma linha"""

    try:
        client = create_binance_client()
        db = DatabaseManager(DB_PATH)
        monitor = PositionMonitor(client, db, mode="live")
        positions = monitor.fetch_open_positions(symbol=None, log_each_position=False)
    except Exception as e:
        print(f"[ERRO] {e}")
        return

    if not positions:
        print("✅ Nenhuma posição aberta")
        return

    # Calcular totais
    total_pnl = sum(p.get('unrealized_pnl', 0) for p in positions)
    avg_pnl_pct = sum(p.get('unrealized_pnl_pct', 0) for p in positions) / len(positions)

    # Contar positivas e negativas
    winners = sum(1 for p in positions if p.get('unrealized_pnl_pct', 0) >= 0)
    losers = len(positions) - winners

    # Determinar cor
    if total_pnl >= 0:
        status = "📈 POSITIVO"
    else:
        status = "📉 NEGATIVO"

    print(f"\n{len(positions)} posição(ões) aberta(s) | "
          f"PnL: {total_pnl:+.2f} USDT ({avg_pnl_pct:+.1f}% média) | "
          f"{status} | "
          f"🟢 {winners} | 🔴 {losers}\n")


if __name__ == "__main__":
    quick_status()
