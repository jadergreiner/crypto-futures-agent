import sqlite3
from datetime import datetime
import pytz
import json

tz_brt = pytz.timezone('America/Sao_Paulo')
conn = sqlite3.connect('db/modelo2.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Buscar informações da execução FAILED às 11:19 do BTCUSDT (decision_id=43343)
cursor.execute('''
SELECT
    se.id,
    se.symbol,
    se.decision_id,
    se.status,
    se.created_at,
    se.failure_reason,
    se.payload_json
FROM signal_executions se
WHERE se.decision_id = 43343 AND se.symbol = 'BTCUSDT'
''')

row = cursor.fetchone()
if row:
    ms = row['created_at']
    dt_utc = datetime.utcfromtimestamp(ms / 1000)
    dt_brt = pytz.utc.localize(dt_utc).astimezone(tz_brt)

    print(f"[EXECUÇÃO FAILED #43343 BTCUSDT]")
    print(f"  Horário: {str(dt_brt)[:19]} BRT")
    print(f"  Status: {row['status']}")
    print(f"  Motivo: {row['failure_reason']}")

    if row['payload_json']:
        try:
            details = json.loads(row['payload_json'])
            print(f"\n  [DETALHES DA FALHA]")
            for k, v in details.items():
                if isinstance(v, dict):
                    print(f"    {k}:")
                    for k2, v2 in v.items():
                        print(f"      {k2}: {v2}")
                else:
                    print(f"    {k}: {v}")
        except json.JSONDecodeError:
            print(f"  Payload (raw): {row['payload_json'][:200]}")

# Também verificar eventos relacionados
print(f"\n[EVENTOS RELACIONADOS A EXECUÇÃO #43343]")
cursor.execute('''
SELECT
    event_type,
    payload_json,
    event_timestamp
FROM signal_execution_events
WHERE signal_execution_id = (SELECT id FROM signal_executions WHERE decision_id = 43343)
ORDER BY event_timestamp
print(f"  ETHUSDT #43341 (11:12 BRT - DEPOIS ajuste): sucesso com $15.00")
print(f"  BTCUSDT #43343 (11:19 BRT - POST ajuste): fallback ou reload do .env?")

# Verificar criação de model/checkpoint por timestamp
print(f"\n[INVESTIGAÇÃO PARA DESVENDAR O TERCEIRO BTCUSDT FAILED]")
print(f"  Se #43343 falhou mesmo com $15, pode ser:")
print(f"  1. BBAPT factor muito baixo naquele momento (loss_streak + failure_ratio alto)")
print(f"  2. .env não foi recarregado entre ciclos")
print(f"  3. Há outro fator limitando a margem (por símbolo em config/risk_params.py)")

conn.close()
