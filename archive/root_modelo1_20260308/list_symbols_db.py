#!/usr/bin/env python
"""
Script para listar símbolos disponíveis no banco de dados.
"""
import sqlite3
from pathlib import Path

db_path = Path('crypto_agent.db')
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Listar símbolos em cada tabela
for table in ['ohlcv_h1', 'ohlcv_h4', 'ohlcv_d1']:
    print(f"\n{table}:")
    cursor.execute(f"SELECT DISTINCT symbol FROM {table} ORDER BY symbol")
    symbols = [row[0] for row in cursor.fetchall()]
    print(f"  Símbolos: {symbols}")
    if symbols:
        # Contar candles por símbolo
        for symbol in symbols:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE symbol='{symbol}'")
            count = cursor.fetchone()[0]
            print(f"    {symbol}: {count} candles")

conn.close()
