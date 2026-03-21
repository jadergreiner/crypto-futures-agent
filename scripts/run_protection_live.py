import os
import time
import shutil
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

# Backup DB
db_path = Path('db/modelo2.db')
if db_path.exists():
    bk = db_path.with_suffix('.db.backup_' + time.strftime('%Y%m%dT%H%M%S'))
    shutil.copy2(db_path, bk)
    print('DB backup created at', bk)
else:
    print('Warning: db/modelo2.db not found; proceeding')

# Instantiate REST client
config = ConfigurationRestAPI(api_key=API_KEY, api_secret=API_SECRET, base_path=BASE_PATH)
rest_api = DerivativesTradingUsdsFuturesRestAPI(config)
client = type('C', (), {'rest_api': rest_api})()
exchange = Model2LiveExchange(client)

# Load execution
repo = Model2ThesisRepository(db_path='db/modelo2.db')
execution_id = 15
execution = repo.get_signal_execution(execution_id)
if not execution:
    print('Execution not found in DB:', execution_id)
    raise SystemExit(1)

symbol = execution['symbol']
signal_side = execution['signal_side']

print('Checking open position for', symbol)
pos = None
# Polling configuration (seconds) - can be overridden via env
POLL_TIMEOUT_SEC = int(os.getenv('POLL_TIMEOUT_SEC', '60'))
POLL_INTERVAL_SEC = int(os.getenv('POLL_INTERVAL_SEC', '5'))
start = time.time()
while True:
    try:
        pos = exchange.get_open_position(symbol)
        print('Open position:', pos)
    except Exception as e:
        print('Error fetching open position:', e)
        pos = None

    if pos:
        break

    elapsed = time.time() - start
    if elapsed >= POLL_TIMEOUT_SEC:
        print(f'No open position detected within {POLL_TIMEOUT_SEC}s; aborting to avoid reduce-only rejects')
        raise SystemExit(0)

    time.sleep(POLL_INTERVAL_SEC)

# Attempt to place SL and TP via place_protective_order
results = {}
for order_type, trigger in (('STOP_MARKET', float(execution.get('stop_loss'))), ('TAKE_PROFIT_MARKET', float(execution.get('take_profit')))):
    try:
        resp = exchange.place_protective_order(symbol=symbol, signal_side=signal_side, trigger_price=trigger, order_type=order_type)
        results[order_type] = {'response': resp}
        print(order_type, 'response id:', exchange.extract_order_identifier(resp))
    except Exception as e:
        results[order_type] = {'exception': str(e)}
        print(order_type, 'exception:', str(e))

print('Summary:', results)
