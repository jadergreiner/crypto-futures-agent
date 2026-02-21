#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect("db/crypto_futures.db")
cursor = conn.cursor()

# Verificar schema
cursor.execute("pragma table_info(trade_log)")
cols = cursor.fetchall()

print("=== SCHEMA trade_log ===")
for col in cols:
    col_id, col_name, col_type, notnull, default_val, pk = col
    not_null_str = "NOT NULL" if notnull else "nullable"
    default_str = f" DEFAULT {default_val}" if default_val else ""
    print(f"{col_name:30} {col_type:10} {not_null_str:10}{default_str}")

conn.close()
