#!/usr/bin/env python
"""Inspeção de payload_json dos technical_signals para validar persistência do bloco ensemble."""

import sqlite3
import json
from pathlib import Path

db_path = Path('db/modelo2.db')
if not db_path.exists():
    print(f'[ERRO] Banco nao encontrado: {db_path}')
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Consulta technical_signals com payload_json não nulo
cursor.execute('''
    SELECT id, symbol, timeframe, signal_side, status, payload_json, created_at
    FROM technical_signals
    WHERE payload_json IS NOT NULL
    ORDER BY updated_at DESC
    LIMIT 5
''')

rows = cursor.fetchall()
if not rows:
    print('[INFO] Nenhum technical_signal com payload_json encontrado')
    conn.close()
    exit(0)

print(f'[INFO] Inspecionando {len(rows)} technical_signals:\n')

for idx, row in enumerate(rows, 1):
    signal_id = row['id']
    symbol = row['symbol']
    timeframe = row['timeframe']
    signal_side = row['signal_side']
    status = row['status']

    try:
        payload = json.loads(row['payload_json'])
        ensemble = payload.get('ensemble')

        print(f'[{idx}] Signal ID: {signal_id} | {symbol} | {timeframe} | {signal_side} | Status: {status}')
        print(f'    Payload keys: {list(payload.keys())}')

        if ensemble:
            print(f'    [SUCESSO] Bloco ENSEMBLE persistido:')
            print(f'      - action: {ensemble.get("action")}')
            conf = ensemble.get('confidence')
            if isinstance(conf, (int, float)):
                print(f'      - confidence: {conf:.4f}')
            else:
                print(f'      - confidence: {conf}')
            print(f'      - method: {ensemble.get("method")}')
            print(f'      - timestamp: {ensemble.get("timestamp")}')
            voting = ensemble.get('voting_summary', {})
            if voting:
                print(f'      - voting_summary: MLP={voting.get("mlp_action")}, LSTM={voting.get("lstm_action")}, agreement={voting.get("agreement")}')
        else:
            print(f'    [FALHA] Bloco ENSEMBLE NAO encontrado no payload')
        print()
    except json.JSONDecodeError as e:
        print(f'[{idx}] Signal ID: {signal_id} | ERRO ao parsear JSON: {e}\n')

conn.close()
print('[OK] Inspecao concluida')
