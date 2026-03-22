#!/usr/bin/env python3
"""Verificar tabelas do banco M2."""

import sqlite3

conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [t[0] for t in cursor.fetchall()]
for table in sorted(tables):
    print(table)
conn.close()
