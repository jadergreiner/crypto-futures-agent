"""Imprime resumo de um ciclo M2 a partir do arquivo JSON temporario."""
import json
import re
import sys

label = sys.argv[1] if len(sys.argv) > 1 else 'output'
path = sys.argv[2] if len(sys.argv) > 2 else 'logs/m2_tmp.json'

try:
    raw = open(path, encoding='utf-8').read()
except Exception as e:
    print(f'[{label}] ERRO ao ler {path}: {e}')
    sys.exit(0)

m = re.search(r'\{.*\}', raw, re.DOTALL)
if not m:
    print(f'[{label}] ERRO: JSON nao encontrado em {path}')
    sys.exit(0)

try:
    d = json.loads(m.group())
except Exception as e:
    print(f'[{label}] ERRO ao parsear JSON: {e}')
    sys.exit(0)

if label == 'sync':
    tf = d.get('timeframe', '?')
    print(f'[sync {tf:<3}] status={d.get("status","?")} | persisted={d.get("candles_persisted",0)} | skipped={d.get("candles_duplicated_skipped",0)}')

elif label == 'pipeline':
    stages = d.get('stages', {})
    erros = d.get('stage_errors', [])
    ok = sum(1 for s in stages.values() if s.get('status') == 'ok')
    extra = f' | ERROS={erros}' if erros else ''
    print(f'[pipeline] status={d.get("status","?")} | stages_ok={ok}/{len(stages)}{extra}')

elif label == 'live':
    dash = d.get('dashboard', {})
    exe = d.get('execute', {})
    staged = exe.get('staged', [])
    ready = exe.get('processed_ready', [])
    live_symbols = exe.get('live_symbols', [])
    blocked = dash.get('blocked_count', 0)
    protected = dash.get('protected_count', 0)
    exited = dash.get('exited_count', 0)
    failed = dash.get('failed_count', 0)
    print(f'[live    ] status={d.get("status","?")} | staged={len(staged)} | ready={len(ready)} | blocked={blocked} | protected={protected} | exited={exited} | failed={failed}')
    # Mapear status por simbolo
    staged_map = {s.get('symbol'): s for s in staged}
    ready_map = {r.get('symbol'): r for r in ready}
    for sym in live_symbols:
        if sym in ready_map:
            r = ready_map[sym]
            print(f'  {sym:<10} READY -> {r.get("status","?")}')
        elif sym in staged_map:
            s = staged_map[sym]
            reason = s.get('reason', '')
            detail = f' ({reason})' if reason else ''
            print(f'  {sym:<10} {s.get("status","?")}{detail}')
        else:
            print(f'  {sym:<10} aguardando oportunidade')

elif label == 'episodio':
    inseridos = d.get('episodes_inserted', d.get('inserted', 0))
    print(f'[episodio] status={d.get("status","?")} | inseridos={inseridos}')

elif label == 'health':
    v = d.get('violations', [])
    extra = f' | VIOLACOES: {v}' if v else ''
    print(f'[health  ] status={d.get("status","?")}{extra}')

else:
    print(f'[{label}] status={d.get("status","?")}')
