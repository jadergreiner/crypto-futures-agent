#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('db/crypto_futures.db')
cursor = conn.cursor()

cursor.execute('SELECT trade_id, symbol, direcao, entry_price, stop_loss, take_profit, binance_order_id, binance_sl_order_id, binance_tp_order_id FROM trade_log ORDER BY trade_id DESC LIMIT 1')
row = cursor.fetchone()

if row:
    print('\n╔════════════════════════════════════════════════════════════════════════════╗')
    print('║           ÚLTIMA POSIÇÃO ABERTA - ORDENS REAIS APREGOADAS NA BINANCE        ║')
    print('╚════════════════════════════════════════════════════════════════════════════╝\n')
    print(f'Trade ID: {row[0]}')
    print(f'Symbol: {row[1]} {row[2]}')
    print(f'Entry Price: ${row[3]:.8f}')
    print(f'Stop Loss: ${row[4]:.8f}')
    print(f'Take Profit: ${row[5]:.8f}')
    print(f'Binance Order ID (MARKET): {row[6]}')
    print(f'Binance SL Order ID: {row[7]}')
    print(f'Binance TP Order ID: {row[8]}')
    print('\nSTATUS: 🟢 POSIÇÃO ABERTA COM ORDENS CONDICIONAIS REAIS NA BINANCE')
    print('\n════════════════════════════════════════════════════════════════════════════\n')
