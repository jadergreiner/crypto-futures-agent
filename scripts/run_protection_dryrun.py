import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv

from binance_common.configuration import ConfigurationRestAPI
from binance_sdk_derivatives_trading_usds_futures.rest_api.rest_api import DerivativesTradingUsdsFuturesRestAPI

from core.model2.repository import Model2ThesisRepository
from core.model2.live_exchange import Model2LiveExchange

# Load .env
env_path = Path('.env')
if not env_path.exists():
    raise SystemExit('.env not found')
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
BASE_PATH = os.getenv('BINANCE_BASE_PATH') or 'https://fapi.binance.com'

if not API_KEY or not API_SECRET:
    raise SystemExit('API credentials not found in .env')

# Instantiate REST client and adapter
config = ConfigurationRestAPI(api_key=API_KEY, api_secret=API_SECRET, base_path=BASE_PATH)
rest_api = DerivativesTradingUsdsFuturesRestAPI(config)
client = type('C', (), {'rest_api': rest_api})()
exchange = Model2LiveExchange(client)

# Load execution
repo = Model2ThesisRepository(db_path='db/modelo2.db')
execution_id = int(os.getenv('EXECUTION_ID', '15'))
execution = repo.get_signal_execution(execution_id)
if not execution:
    print('Execution not found in DB:', execution_id)
    raise SystemExit(1)

symbol = execution['symbol']
signal_side = execution['signal_side']

def build_protection_payloads(symbol: str, signal_side: str, trigger: float, order_type: str):
    close_side = 'SELL' if str(signal_side).upper() == 'LONG' else 'BUY'
    normalized_trigger = exchange._normalize_trigger_price(symbol, trigger, close_side)

    # qty_needed: prefer open position size; fallback to execution filled_qty if present
    pos = exchange.get_open_position(symbol)
    qty_needed = None
    if pos:
        qty_needed = float(pos.get('position_size_qty') or 0.0)
    else:
        qty_needed = float(execution.get('filled_qty') or execution.get('filled_quantity') or 0.0)

    candidates = [
        {
            "type": order_type,
            "symbol": symbol,
            "side": close_side,
            "stop_price": normalized_trigger,
            "close_position": "true",
        },
        {
            "type": order_type,
            "symbol": symbol,
            "side": close_side,
            "stopPrice": normalized_trigger,
            "closePosition": "true",
        },
        {
            "type": order_type,
            "symbol": symbol,
            "side": close_side,
            "stop_price": normalized_trigger,
            "reduce_only": "true",
        },
        {
            "type": "STOP_MARKET",
            "symbol": symbol,
            "side": close_side,
            "stopPrice": normalized_trigger,
            "reduceOnly": True,
        },
    ]

    # If quantity is known, add to payloads that may require it
    results = []
    for p in candidates:
        p_copy = dict(p)
        if qty_needed and qty_needed > 0:
            p_copy.setdefault('quantity', qty_needed)
        results.append(p_copy)
    return results


os.makedirs('logs', exist_ok=True)
out = {'execution_id': execution_id, 'symbol': symbol, 'constructed': {}, 'meta': {}}

for order_type, trigger_key in (('STOP_MARKET', 'stop_loss'), ('TAKE_PROFIT_MARKET', 'take_profit')):
    try:
        trigger_raw = execution.get(trigger_key)
        trigger = float(trigger_raw) if trigger_raw is not None else None
    except Exception:
        trigger = None

    if trigger is None:
        out['constructed'][order_type] = {'error': f'missing trigger {trigger_key}'}
        continue

    payloads = build_protection_payloads(symbol, signal_side, trigger, order_type)
    out['constructed'][order_type] = payloads

out['meta']['timestamp'] = time.strftime('%Y%m%dT%H%M%SZ')
out_path = Path('logs') / f'protective_dryrun_{execution_id}_{int(time.time())}.json'
out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
print('Dry-run payloads written to', out_path)
print(json.dumps(out, indent=2, ensure_ascii=False))
