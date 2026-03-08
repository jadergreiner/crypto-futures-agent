"""
Utilitários de métricas para TASK-005.

Centraliza o cálculo de métricas de performance para que treino e validação
usem a mesma fonte de verdade baseada em PnL/equity, nunca em shaped reward.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np


def _to_float(value, default: float = 0.0) -> float:
    """Converte para float com fallback seguro."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_performance_metrics(
    trade_results: Iterable[Dict],
    initial_capital: float,
    min_volatility_floor: float = 0.01,
    max_reasonable_sharpe: float = 10.0,
    max_reasonable_profit_factor: float = 100.0,
) -> Dict:
    """
    Calcula métricas de performance a partir de resultados por trade.

    Cada item de `trade_results` deve conter ao menos:
    - `raw_pnl`
    - `equity`
    - opcionalmente `shaped_reward`

    Returns:
        dict: métricas calculadas + diagnóstico de sanidade.
    """
    trades: List[Dict] = list(trade_results)
    sanity_issues: List[str] = []

    if not trades:
        return {
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'max_drawdown': 0.0,
            'profit_factor': 0.0,
            'consecutive_losses': 0,
            'total_trades': 0,
            'total_pnl': 0.0,
            'total_return_pct': 0.0,
            'mean_trade_return': 0.0,
            'std_trade_return': 0.0,
            'vol_floor': float(min_volatility_floor),
            'num_trades_evaluated': 0,
            'metric_sanity_passed': False,
            'sanity_issues': ['no_trades'],
        }

    pnls = np.array([_to_float(t.get('raw_pnl', 0.0)) for t in trades], dtype=float)
    equities = np.array([_to_float(t.get('equity', initial_capital)) for t in trades], dtype=float)
    shaped_rewards = np.array(
        [_to_float(t.get('shaped_reward', 0.0)) for t in trades],
        dtype=float,
    )

    previous_equity = initial_capital
    trade_returns = []
    for pnl, equity in zip(pnls, equities):
        base_equity = max(abs(previous_equity), 1e-8)
        trade_returns.append(pnl / base_equity)
        previous_equity = equity if equity > 0 else previous_equity + pnl

    returns = np.array(trade_returns, dtype=float)
    mean_return = float(np.mean(returns))
    std_return = float(np.std(returns))
    vol_floor = float(max(min_volatility_floor, abs(mean_return) * 0.1))
    adjusted_vol = max(std_return, vol_floor)
    sharpe_ratio = mean_return / adjusted_vol

    if abs(sharpe_ratio) > max_reasonable_sharpe:
        sanity_issues.append('sharpe_capped')
        sharpe_ratio = float(np.clip(sharpe_ratio, -max_reasonable_sharpe, max_reasonable_sharpe))

    gains = float(np.sum(pnls[pnls > 0]))
    losses = float(-np.sum(pnls[pnls < 0]))
    if losses > 0:
        profit_factor = gains / losses
    elif gains > 0:
        profit_factor = max_reasonable_profit_factor
        sanity_issues.append('profit_factor_open_ended_capped')
    else:
        profit_factor = 0.0

    if profit_factor > max_reasonable_profit_factor:
        sanity_issues.append('profit_factor_capped')
        profit_factor = max_reasonable_profit_factor

    cumulative_equity = np.concatenate(([initial_capital], equities))
    running_max = np.maximum.accumulate(cumulative_equity)
    drawdowns = (running_max - cumulative_equity) / np.maximum(running_max, 1e-8)
    max_drawdown = float(np.clip(np.max(drawdowns), 0.0, 1.0))

    winning_trades = int(np.sum(pnls > 0))
    win_rate = winning_trades / len(pnls)

    max_consecutive_losses = 0
    current_consecutive_losses = 0
    for pnl in pnls:
        if pnl < 0:
            current_consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
        else:
            current_consecutive_losses = 0

    if not np.isfinite(sharpe_ratio):
        sanity_issues.append('sharpe_not_finite')
    if not np.isfinite(profit_factor):
        sanity_issues.append('profit_factor_not_finite')
    if np.allclose(pnls, 0.0):
        sanity_issues.append('all_pnl_zero')

    metric_sanity_passed = len(
        [issue for issue in sanity_issues if issue not in {'profit_factor_open_ended_capped', 'profit_factor_capped', 'sharpe_capped'}]
    ) == 0

    return {
        'sharpe_ratio': float(sharpe_ratio),
        'win_rate': float(win_rate),
        'max_drawdown': float(max_drawdown),
        'profit_factor': float(profit_factor),
        'consecutive_losses': int(max_consecutive_losses),
        'total_trades': int(len(pnls)),
        'total_pnl': float(np.sum(pnls)),
        'total_return_pct': float((equities[-1] - initial_capital) / max(initial_capital, 1e-8)),
        'mean_trade_return': mean_return,
        'std_trade_return': std_return,
        'vol_floor': vol_floor,
        'num_trades_evaluated': int(len(pnls)),
        'metric_sanity_passed': metric_sanity_passed,
        'sanity_issues': sanity_issues,
        'avg_shaped_reward': float(np.mean(shaped_rewards)) if len(shaped_rewards) else 0.0,
    }
