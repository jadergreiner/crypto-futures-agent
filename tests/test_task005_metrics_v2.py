from agent.rl.data_loader import TradeHistoryLoader
from agent.rl.metrics_utils import compute_performance_metrics
from agent.rl.training_env import CryptoTradingEnv
from data.trades_history_generator import (
    generate_sprint1_trades,
    validate_trade_baseline,
)


def test_trade_generator_baseline_is_plausible(tmp_path):
    filepath = tmp_path / "trades_history.json"
    trades = generate_sprint1_trades(num_trades=500, filepath=str(filepath))

    assert filepath.exists()
    assert len(trades) >= 500

    baseline = validate_trade_baseline(trades)
    assert baseline['baseline_valid'] is True
    assert 0.35 <= baseline['win_rate'] <= 0.65
    assert 0 < baseline['profit_factor'] <= 20


def test_environment_exposes_raw_pnl_and_shaped_reward():
    trades = [
        {
            'entry_price': 100.0,
            'exit_price': 110.0,
            'qty': 1.0,
            'direction': 'LONG',
        },
        {
            'entry_price': 100.0,
            'exit_price': 90.0,
            'qty': 1.0,
            'direction': 'LONG',
        },
    ]

    env = CryptoTradingEnv(trade_data=trades, initial_capital=1000.0)
    env.reset()

    _, open_reward, _, _, open_info = env.step(1)
    assert open_info['trade_closed'] is False
    assert open_info['raw_pnl'] == 0.0
    assert open_info['shaped_reward'] == open_reward

    _, close_reward, _, _, close_info = env.step(0)
    assert close_info['trade_closed'] is True
    assert close_info['closed_trade'] is not None
    assert close_info['closed_trade']['raw_pnl'] == -10.0
    assert close_info['closed_trade']['shaped_reward'] == close_reward
    assert close_info['raw_pnl'] == -10.0
    assert close_reward != close_info['raw_pnl']


def test_metrics_use_raw_pnl_with_volatility_floor():
    trade_results = [
        {'raw_pnl': 10.0, 'equity': 1010.0, 'shaped_reward': 0.21},
        {'raw_pnl': -5.0, 'equity': 1005.0, 'shaped_reward': -0.04},
        {'raw_pnl': 8.0, 'equity': 1013.0, 'shaped_reward': 0.19},
    ]

    metrics = compute_performance_metrics(trade_results, initial_capital=1000.0)

    assert metrics['num_trades_evaluated'] == 3
    assert metrics['total_pnl'] == 13.0
    assert metrics['vol_floor'] >= 0.01
    assert 0 <= metrics['win_rate'] <= 1
    assert metrics['profit_factor'] > 0
    assert metrics['metric_sanity_passed'] is True


def test_loader_validates_dataset_baseline():
    loader = TradeHistoryLoader("data/trades_history.json")
    loader.load()
    baseline = loader.validate_baseline()

    assert baseline['total_trades'] >= 500
    assert baseline['baseline_valid'] is True
