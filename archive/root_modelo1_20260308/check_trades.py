#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('db/crypto_futures.db')
cursor = conn.cursor()

print('\n╔════════════════════════════════════════════════════════════════════════════════╗')
print('║                     STATUS FINAL - AMBAS AS POSIÇÕES ABERTAS                   ║')
print('╚════════════════════════════════════════════════════════════════════════════════╝\n')

for trade_id in [1, 2]:
    cursor.execute('SELECT * FROM trade_log WHERE trade_id = ?', (trade_id,))
    row = cursor.fetchone()

    if row:
        cols = [d[0] for d in cursor.description]
        data = dict(zip(cols, row))

        status = 'ABERTA' if data['timestamp_saida'] is None else 'FECHADA'

        print(f'📊 TRADE ID {data["trade_id"]} | {data["symbol"]} {data["direcao"]}')
        print(f'   Binance Order ID: {data["binance_order_id"]}')
        print(f'   Entry Price: ${data["entry_price"]:.8f}')
        print(f'   Stop Loss:   ${data["stop_loss"]:.8f}')
        print(f'   Take Profit: ${data["take_profit"]:.8f}')
        print(f'   Status: {status} ✅')
        print()

print('════════════════════════════════════════════════════════════════════════════════\n')
