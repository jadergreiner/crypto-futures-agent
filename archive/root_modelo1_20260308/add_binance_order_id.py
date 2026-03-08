#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adicionar coluna binance_order_id ao trade_log
"""

import sqlite3

try:
    conn = sqlite3.connect("db/crypto_futures.db")
    cursor = conn.cursor()

    # Verificar se a coluna já existe
    cursor.execute("PRAGMA table_info(trade_log)")
    existing_cols = [col[1] for col in cursor.fetchall()]

    if "binance_order_id" not in existing_cols:
        print("📋 Adicionando coluna binance_order_id...")
        cursor.execute("""
            ALTER TABLE trade_log
            ADD COLUMN binance_order_id TEXT
        """)
        conn.commit()
        print("✅ Coluna adicionada com sucesso!")
    else:
        print("ℹ️  Coluna binance_order_id já existe")

    conn.close()

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
