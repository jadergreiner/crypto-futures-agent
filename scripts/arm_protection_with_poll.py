import os
import time
import shutil
from pathlib import Path
from dotenv import load_dotenv

from binance_common.configuration import ConfigurationRestAPI
from binance_sdk_derivatives_trading_usds_futures.rest_api.rest_api import DerivativesTradingUsdsFuturesRestAPI

from core.model2.repository import Model2ThesisRepository
from core.model2.live_exchange import Model2LiveExchange

# Config
RETRIES = 6
DELAY_S = 5

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

# Backup DB if exists
db_path = Path('db/modelo2.db')
if db_path.exists():
    bk = db_path.with_suffix('.db.backup_poll_' + time.strftime('%Y%m%dT%H%M%S'))
    shutil.copy2(db_path, bk)
    print('DB backup created at', bk)

# Instantiate REST client
config = ConfigurationRestAPI(api_key=API_KEY, api_secret=API_SECRET, base_path=BASE_PATH)
rest_api = DerivativesTradingUsdsFuturesRestAPI(config)
client = type('C', (), {'rest_api': rest_api})()
# Increase recv_window tolerance for signed requests
exchange = Model2LiveExchange(client, recv_window=60_000)

# Load execution
repo = Model2ThesisRepository(db_path='db/modelo2.db')
execution_id = 15
execution = repo.get_signal_execution(execution_id)
if not execution:
    print(f'Execution id {execution_id} not found in DB')
    raise SystemExit(1)

symbol = execution['symbol']
signal_side = execution['signal_side']
print('Polling for open position for', symbol)
position = None
for i in range(RETRIES):
    try:
        position = exchange.get_open_position(symbol)
    except Exception as e:
        print('error fetching position:', e)
        position = None
    if position:
        print('Position detected:', position)
        break
    print(f'No position yet (attempt {i+1}/{RETRIES}), waiting {DELAY_S}s')
    time.sleep(DELAY_S)

if not position:
    print('Position did not appear after retries; aborting to avoid reduce-only rejects')
    raise SystemExit(0)

# Try to arm protections
results = {"sl": None, "tp": None}
for order_type, trigger_key, label in (
    ('STOP_MARKET', 'stop_loss', 'sl'),
    ('TAKE_PROFIT_MARKET', 'take_profit', 'tp'),
):
    trigger_val = execution.get(trigger_key)
    try:
        resp = exchange.place_protective_order(symbol=symbol, signal_side=signal_side, trigger_price=float(trigger_val), order_type=order_type)
        results[label] = {'response': resp}
        print(f'{order_type} placed, id:', exchange.extract_order_identifier(resp))
    except Exception as e:
        results[label] = {'exception': str(e)}
        print(f'{order_type} exception:', str(e))

print('Protection attempt results:', results)
