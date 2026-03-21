import sqlite3
from pathlib import Path
DB=Path('db/modelo2.db')
conn=sqlite3.connect(str(DB))
cur=conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('technical_signals','opportunities','signal_executions')")
for row in cur.fetchall():
    print('---',row[0])
    print(row[1])
    print()
conn.close()
