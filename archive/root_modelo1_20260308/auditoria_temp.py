#!/usr/bin/env python3
"""Temporary audit script for VALIDA-000"""

import sqlite3
from datetime import datetime

# ==============================================================================
# FASE 1.2: ESTADO DATABASE LOCAL
# ==============================================================================

conn = sqlite3.connect('db/crypto_futures.db')
c = conn.cursor()

print("\n" + "=" * 80)
print("FASE 1.2: ESTADO DATABASE LOCAL")
print("=" * 80)

# Contar posições abertas
c.execute('SELECT COUNT(*) FROM trade_log WHERE timestamp_saida IS NULL')
open_count = c.fetchone()[0]

print(f"\nTotal de posições abertas: {open_count}")

if open_count > 0:
    # Ver detalhes
    c.execute('''
    SELECT trade_id, symbol, direcao, entry_price, position_size_usdt,
           unrealized_pnl_at_snapshot, binance_order_id
    FROM trade_log
    WHERE timestamp_saida IS NULL
    ORDER BY trade_id DESC
    ''')

    positions = c.fetchall()

    print("\nDETALHES DAS POSIÇÕES ABERTAS:")
    print("-" * 80)

    total_margin = 0.0
    total_unrealized = 0.0

    for row in positions:
        trade_id, symbol, dir_pos, entry_price, margin, unrealized, bid = row
        print(f"\nTrade ID {trade_id}: {symbol} {dir_pos}")
        if entry_price:
            print(f"  Entry Price: ${entry_price:.8f}")
        if margin:
            print(f"  Position Size (USDT): ${margin:.2f}")
            total_margin += margin
        if unrealized:
            print(f"  Unrealized PnL: ${unrealized:.2f}")
            total_unrealized += unrealized
        if bid:
            print(f"  Binance Order ID: {bid}")

    print("\n" + "-" * 80)
    print(f"TOTAL Margem Utilizada: ${total_margin:.2f}")
    print(f"TOTAL Unrealized PnL: ${total_unrealized:.2f}")
else:
    print("\nNenhuma posição aberta no banco de dados.")

# ==============================================================================
# RECONCILIAÇÃO PRELIMINAR
# ==============================================================================

print("\n" + "=" * 80)
print("RECONCILIAÇÃO PRELIMINAR")
print("=" * 80)

print(f"\nInvestidor reportou (20/02 23:35 UTC):")
print(f"  Capital: ~$424 USDT")
print(f"  Posições abertas: 20")
print(f"  Perdas não realizadas: -$182 USDT")

print(f"\nDatabase Local reporta:")
print(f"  Capital utilizado: ${total_margin:.2f} USDT")
print(f"  Posições abertas: {open_count}")
print(f"  Perdas/Ganhos não realizados: ${total_unrealized:.2f} USDT")

print(f"\n❌ INCONSISTÊNCIA CRÍTICA DETECTADA:")
print(f"   Posições: Investidor=20  vs  Database={open_count}")
print(f"   PnL: Investidor=-$182  vs  Database=${total_unrealized:.2f}")

conn.close()
