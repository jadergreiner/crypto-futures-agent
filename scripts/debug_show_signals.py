import sqlite3, json
from pathlib import Path
DB = Path("db/modelo2.db")
if not DB.exists():
    print("DB not found:", DB)
    raise SystemExit(1)
conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row
symbols = ["ETHUSDT","BNBUSDT","BTCUSDT","BTCUSDT"]
print("DB:", DB)
for table in ("technical_signals","signal_executions"):
    print("\n===", table, "===")
    try:
        cur = conn.execute(
            f"SELECT * FROM {table} WHERE symbol IN ({','.join(['?']*len(symbols))}) ORDER BY id DESC LIMIT 50",
            symbols,
        )
    except Exception as e:
        print("Error querying", table, e)
        continue
    rows = cur.fetchall()
    if not rows:
        print("No rows for table", table)
        continue
    for r in rows:
        d = dict(r)
        # Print compact JSON per row
        print(json.dumps(d, ensure_ascii=False, default=str))
conn.close()