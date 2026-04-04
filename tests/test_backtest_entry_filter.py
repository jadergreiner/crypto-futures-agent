"""Testes do filtro anti-churn por cooldown de entrada no backtest."""

import numpy as np
import pandas as pd

from agent.environment import CryptoFuturesEnv
from config.risk_params import RISK_PARAMS


def _build_data(n_h4: int = 120) -> dict:
    n_h1 = n_h4 * 4
    n_d1 = max(10, n_h4 // 6)

    h4 = pd.DataFrame(
        {
            "open": np.full(n_h4, 100.0),
            "high": np.full(n_h4, 101.0),
            "low": np.full(n_h4, 99.0),
            "close": np.full(n_h4, 100.0),
            "volume": np.full(n_h4, 1_000.0),
            "atr_14": np.full(n_h4, 1.0),
        }
    )
    h1 = pd.DataFrame(
        {
            "open": np.full(n_h1, 100.0),
            "high": np.full(n_h1, 101.0),
            "low": np.full(n_h1, 99.0),
            "close": np.full(n_h1, 100.0),
            "volume": np.full(n_h1, 1_000.0),
        }
    )
    d1 = pd.DataFrame(
        {
            "open": np.full(n_d1, 100.0),
            "high": np.full(n_d1, 101.0),
            "low": np.full(n_d1, 99.0),
            "close": np.full(n_d1, 100.0),
            "volume": np.full(n_d1, 1_000.0),
        }
    )

    return {
        "symbol": "BTCUSDT",
        "h1": h1,
        "h4": h4,
        "d1": d1,
        "sentiment": {},
        "macro": {},
        "smc": {},
    }


def test_entry_cooldown_blocks_reentry_immediate() -> None:
    data = _build_data()
    risk_params = dict(RISK_PARAMS)
    risk_params["entry_cooldown_steps"] = 3
    env = CryptoFuturesEnv(data=data, initial_capital=10_000, risk_params=risk_params, episode_length=60)
    env.reset(seed=42)

    # 1) Abre posição
    _obs, _reward, _terminated, _truncated, info_open = env.step(1)  # OPEN_LONG
    assert info_open["action_valid"] is True
    assert info_open["has_position"] is True

    # 2) Fecha manualmente na barra seguinte (pnl ~ 0, permitido)
    _obs, _reward, _terminated, _truncated, info_close = env.step(3)  # CLOSE
    assert info_close["has_position"] is False
    assert info_close["trades_count"] >= 1

    # 3) Tenta reabrir imediatamente: deve ser bloqueado pelo cooldown
    _obs, _reward, _terminated, _truncated, info_reopen = env.step(1)  # OPEN_LONG
    assert info_reopen["action_valid"] is False
    assert info_reopen["has_position"] is False
