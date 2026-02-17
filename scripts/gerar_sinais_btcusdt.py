# Script para gerar sinais sintéticos iniciais para BTCUSDT
import logging
from config.settings import DB_PATH
from data.database import DatabaseManager
from tests.test_e2e_pipeline import create_synthetic_ohlcv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def gerar_sinais_btcusdt(db_path: str = DB_PATH, n=1000):
    db = DatabaseManager(db_path)
    logger.info('Gerando %d sinais sintéticos para BTCUSDT...', n)
    ohlcv = create_synthetic_ohlcv(length=n, seed=42)
    ohlcv_records = ohlcv.to_dict('records')

    for i, row in enumerate(ohlcv_records):
        direction = 'LONG' if i % 2 == 0 else 'SHORT'
        entry_price = row['open']
        stop_loss = entry_price * 0.98
        take_profit_1 = entry_price * 1.02
        take_profit_2 = entry_price * 1.04
        take_profit_3 = entry_price * 1.06
        exit_price = row['close']
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        if direction == 'SHORT':
            pnl_pct = -pnl_pct
        r_multiple = 0.0
        if entry_price != stop_loss:
            r_multiple = (exit_price - entry_price) / (entry_price - stop_loss)

        signal_payload = {
            'timestamp': row['timestamp'],
            'symbol': 'BTCUSDT',
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'take_profit_3': take_profit_3,
            'position_size_suggested': 1000.0,
            'risk_pct': 1.0,
            'risk_reward_ratio': 2.0,
            'leverage_suggested': 3,
            'confluence_score': 75.0,
            'confluence_details': 'synthetic_seed',
            'rsi_14': 50.0,
            'ema_17': entry_price,
            'ema_34': entry_price,
            'ema_72': entry_price,
            'ema_144': entry_price,
            'macd_line': 0.0,
            'macd_signal': 0.0,
            'macd_histogram': 0.0,
            'bb_upper': row['high'],
            'bb_lower': row['low'],
            'bb_percent_b': 0.5,
            'atr_14': 100.0,
            'adx_14': 20.0,
            'di_plus': 25.0,
            'di_minus': 15.0,
            'market_structure': 'NEUTRO',
            'bos_recent': 0,
            'choch_recent': 0,
            'nearest_ob_distance_pct': 1.5,
            'nearest_fvg_distance_pct': 2.0,
            'premium_discount_zone': 'NEUTRO',
            'liquidity_above_pct': 10.0,
            'liquidity_below_pct': 8.0,
            'funding_rate': 0.0001,
            'long_short_ratio': 1.1,
            'open_interest_change_pct': 0.5,
            'fear_greed_value': 60,
            'd1_bias': 1.0,
            'h4_trend': 'UP',
            'h1_trend': 'UP',
            'market_regime': 'RISK_ON',
            'execution_mode': 'paper',
            'executed_at': row['timestamp'] + 3_600_000,
            'executed_price': exit_price,
            'execution_slippage_pct': 0.1,
            'status': 'CLOSED'
        }
        signal_payload['pnl_pct'] = pnl_pct
        signal_payload['pnl_usdt'] = (exit_price - entry_price) * signal_payload['position_size_suggested']
        signal_payload['r_multiple'] = r_multiple
        signal_payload['outcome_label'] = 'win' if pnl_pct >= 0 else 'loss'
        signal_payload['exit_price'] = exit_price
        signal_payload['exit_timestamp'] = row['timestamp'] + 3_600_000
        signal_payload['exit_reason'] = 'synthetic'
        signal_payload['duration_minutes'] = 60
        signal_payload['max_favorable_excursion_pct'] = max(0.0, pnl_pct)
        signal_payload['max_adverse_excursion_pct'] = min(0.0, pnl_pct)
        signal_payload['reward_calculated'] = pnl_pct / 100.0
        db.insert_trade_signal(signal_payload)

    logger.info('Sinais sintéticos inseridos com sucesso.')


if __name__ == '__main__':
    gerar_sinais_btcusdt()
