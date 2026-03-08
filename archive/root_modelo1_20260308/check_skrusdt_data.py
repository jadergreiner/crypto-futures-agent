#!/usr/bin/env python3
"""Quick check for SKRUSDT data in cache."""

import sqlite3

def check_skrusdt():
    conn = sqlite3.connect('data/klines_cache.db')
    cur = conn.cursor()

    # Check SKRUSDT count
    cur.execute('SELECT symbol, COUNT(*) FROM klines WHERE symbol="SKRUSDT" GROUP BY symbol')
    result = cur.fetchall()

    if result:
        symbol, count = result[0]
        print(f"✅ SKRUSDT: {count} candles in cache")
    else:
        print("❌ SKRUSDT: Not found in database")

    # See all symbols
    cur.execute('SELECT DISTINCT symbol FROM klines ORDER BY symbol')
    all_symbols = cur.fetchall()
    print(f"\n📊 Total symbols in cache: {len(all_symbols)}")

    conn.close()

if __name__ == "__main__":
    check_skrusdt()
