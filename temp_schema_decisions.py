import sqlite3
conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(model_decisions)")
cols = cursor.fetchall()
print('[COLUNAS model_decisions]')
for col in cols:
    print(f"  {col[1]:30}")

cursor.execute("PRAGMA table_info(technical_signals)")
cols = cursor.fetchall()
print('\n[COLUNAS technical_signals]')
for col in cols:
    print(f"  {col[1]:30}")

conn.close()
