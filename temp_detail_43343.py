import sqlite3
from datetime import datetime
import pytz
import json

tz_brt = pytz.timezone('America/Sao_Paulo')
conn = sqlite3.connect('db/modelo2.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Buscar execução FAILED #43343
cursor.execute(
    "SELECT id, symbol, decision_id, status, created_at, failure_reason, payload_json FROM signal_executions WHERE decision_id = 43343"
)

row = cursor.fetchone()
if row:
    ms = row['created_at']
    dt_utc = datetime.utcfromtimestamp(ms / 1000)
    dt_brt = pytz.utc.localize(dt_utc).astimezone(tz_brt)

    print("[EXECUÇÃO FAILED #43343 BTCUSDT]")
    print(f"  Horário: {str(dt_brt)[:19]} BRT")
    print(f"  Status: {row['status']}")
    print(f"  Motivo: {row['failure_reason']}")

    if row['payload_json']:
        try:
            details = json.loads(row['payload_json'])
            print("\n  [DETALHES DO PAYLOAD]")
            for k, v in sorted(details.items()):
                if isinstance(v, dict):
                    print(f"    {k}:")
                    for k2, v2 in sorted(v.items()):
                        if isinstance(v2, float):
                            print(f"      {k2}: {v2:.4f}")
                        else:
                            print(f"      {k2}: {v2}")
                elif isinstance(v, float):
                    print(f"    {k}: {v:.4f}")
                else:
                    print(f"    {k}: {v}")
        except Exception as e:
            print(f"  Erro ao parsear JSON: {e}")

print("\n[RESUMO]")
print("  Execução #43343 (11:19 BRT BTCUSDT):")
print("  - Falhou com 'invalid_requested_quantity'")
print("  - Mesmo com M2_MAX_MARGIN_PER_POSITION_USD = $15.00 já ativo")
print("  - Sugere BBAPT factor muito baixo naquele momento")

conn.close()
