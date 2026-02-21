#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Posições Abertas - Resumo Simples
Mostra rapidamente o que há aberto e o PnL
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.binance_client import create_binance_client
from monitoring.position_monitor import PositionMonitor
from data.database import DatabaseManager
from config.settings import DB_PATH


def show_positions_summary():
    """Mostra posições abertas de forma simples"""

    try:
        client = create_binance_client()
        db = DatabaseManager(DB_PATH)
        monitor = PositionMonitor(client, db, mode="live")
    except Exception as e:
        print(f"[ERRO] Falha ao conectar: {e}")
        return

    # Buscar posições abertas
    try:
        positions = monitor.fetch_open_positions(symbol=None, log_each_position=False)
    except Exception as e:
        print(f"[ERRO] Falha ao buscar posições: {e}")
        return

    print()
    print("=" * 100)
    print("POSIÇÕES ABERTAS - RESUMO EXECUTIVO")
    print("=" * 100)
    print()

    if not positions:
        print("❌ NENHUMA POSIÇÃO ABERTA")
        print()
        return

    # Mostrar cada posição
    print(f"✅ {len(positions)} POSIÇÃO(ÕES) ABERTA(S):\n")

    total_pnl_usdt = 0
    total_pnl_pct = 0

    for idx, pos in enumerate(positions, 1):
        symbol = pos.get('symbol', 'N/A')
        direction = pos.get('direction', 'N/A')
        qty = pos.get('quantity', 0)
        entry = pos.get('entry_price', 0)
        current = pos.get('mark_price', 0)
        pnl_usdt = pos.get('unrealized_pnl', 0)
        pnl_pct = pos.get('unrealized_pnl_pct', 0)
        margin = pos.get('margin_invested', 0)

        # Acumular
        total_pnl_usdt += pnl_usdt
        total_pnl_pct += pnl_pct

        # Cor baseada em PnL
        if pnl_pct >= 10:
            indicator = "🟢🟢"  # Muito bom
        elif pnl_pct >= 5:
            indicator = "🟢 "   # Bom
        elif pnl_pct >= 0:
            indicator = "🟡 "   # Neutro positivo
        elif pnl_pct >= -5:
            indicator = "🟠 "   # Pouco negativo
        else:
            indicator = "🔴"    # Muito negativo

        print(f"{idx:2}. {indicator} {symbol:15} {direction:6} | "
              f"Qty: {qty:12.6f} | "
              f"Entry: {entry:12.8f} | "
              f"Atual: {current:12.8f} | "
              f"PnL: {pnl_usdt:10.2f} USDT ({pnl_pct:7.2f}%)")

    print()
    print("-" * 100)

    # Resumo final
    avg_pnl_pct = total_pnl_pct / len(positions) if positions else 0

    if total_pnl_usdt >= 0:
        final_color = "🟢 POSITIVO"
    else:
        final_color = "🔴 NEGATIVO"

    print(f"\n📊 RESUMO TOTAL:")
    print(f"  Posições: {len(positions)}")
    print(f"  PnL Total: {total_pnl_usdt:.2f} USDT ({avg_pnl_pct:.2f}% média)")
    print(f"  Status: {final_color}")
    print()
    print("=" * 100)
    print()


if __name__ == "__main__":
    show_positions_summary()
