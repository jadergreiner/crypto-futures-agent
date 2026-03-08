import sqlite3
from pathlib import Path

db_path = Path('db/crypto_agent.db')
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print(f'✅ Database found: {db_path}')
    print(f'   Tables: {len(tables)}')
    for t in tables:
        print(f'     - {t[0]}')
        # Count records in each table
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t[0]}")
            count = cursor.fetchone()[0]
            print(f'       ({count} records)')
        except:
            pass
    conn.close()
else:
    print(f'❌ Database not found at {db_path}')
