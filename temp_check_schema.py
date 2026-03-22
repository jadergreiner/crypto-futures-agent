#!/usr/bin/env python3
"""Verificar schema de training_episodes."""

import sqlite3

conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(training_episodes)')
columns = cursor.fetchall()
print("Colunas em training_episodes:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")
conn.close()
