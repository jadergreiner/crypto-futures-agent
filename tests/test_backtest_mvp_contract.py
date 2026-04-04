"""Testes do contrato MVP do backtesting (#59)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

from backtest.backtester import Backtester


class _ModelStub:
    """Modelo simples que sempre retorna HOLD."""

    def predict(self, _obs: np.ndarray, deterministic: bool = True):
        return 0, None


class _FakeDeterministicEnv:
    """Environment fake para validar contrato sem dependência externa."""

    def __init__(self, data: Dict[str, Any], initial_capital: float, episode_length: int, **_kwargs: Any):
        self.data = data
        self.initial_capital = initial_capital
        self.episode_length = episode_length
        self.capital = initial_capital
        self.current_step = 0
        self.trades_history = []
        self._rng = np.random.default_rng(0)

    def reset(self, seed: int | None = None, options: Dict[str, Any] | None = None):
        del options
        self.current_step = 0
        self.capital = self.initial_capital
        self.trades_history = []
        self._rng = np.random.default_rng(seed if seed is not None else 0)
        return np.zeros(4, dtype=np.float32), {}

    def step(self, action: int):
        del action
        self.current_step += 1
        delta = float(self._rng.normal(0.0, 1.0))
        self.capital += delta

        if self.current_step == 2:
            self.trades_history.append(
                {
                    "exit_reason": "stop_loss",
                    "pnl": -40.0,
                    "pnl_pct": -4.0,
                    "entry_fee": 0.10,
                    "exit_fee": 0.15,
                    "r_multiple": -1.2,
                }
            )

        terminated = self.current_step >= 5
        return np.zeros(4, dtype=np.float32), 0.0, terminated, False, {}


def _sample_data() -> Dict[str, Any]:
    return {
        "symbol": "BTCUSDT",
        "h4": pd.DataFrame({"close": [100.0, 99.0, 98.0, 101.0, 100.5, 102.0]}),
    }


def test_backtest_mvp_deterministico_com_mesma_seed() -> None:
    bt = Backtester(initial_capital=10_000)
    model = _ModelStub()
    data = _sample_data()

    run1 = bt.run(
        start_date="2026-01-01",
        end_date="2026-01-31",
        model=model,
        data=data,
        symbol="BTCUSDT",
        seed=42,
        deterministic=True,
        env_cls=_FakeDeterministicEnv,
    )
    run2 = bt.run(
        start_date="2026-01-01",
        end_date="2026-01-31",
        model=model,
        data=data,
        symbol="BTCUSDT",
        seed=42,
        deterministic=True,
        env_cls=_FakeDeterministicEnv,
    )

    assert run1["equity_curve"] == run2["equity_curve"]
    assert run1["final_capital"] == run2["final_capital"]
    assert run1["metrics"]["net_pnl_usd"] == run2["metrics"]["net_pnl_usd"]
    assert run1["risk_gate"]["status"] == "TRIGGERED"


def test_backtest_mvp_calcula_pnl_fees_e_risk_gate() -> None:
    bt = Backtester(initial_capital=10_000)
    model = _ModelStub()
    data = _sample_data()

    result = bt.run(
        start_date="2026-01-01",
        end_date="2026-01-31",
        model=model,
        data=data,
        symbol="BTCUSDT",
        seed=7,
        deterministic=True,
        env_cls=_FakeDeterministicEnv,
    )

    assert "net_pnl_usd" in result["metrics"]
    assert "total_fees_usd" in result["metrics"]
    assert result["metrics"]["total_fees_usd"] > 0
    assert result["risk_gate"]["triggered_by_stop_loss"] >= 1
    assert "PnL Liquido" in result["text_summary"]


def test_backtest_mvp_salva_artefatos_json_e_texto(tmp_path: Path) -> None:
    bt = Backtester(initial_capital=10_000)
    model = _ModelStub()
    data = _sample_data()
    result = bt.run(
        start_date="2026-01-01",
        end_date="2026-01-31",
        model=model,
        data=data,
        symbol="BTCUSDT",
        seed=99,
        deterministic=True,
        env_cls=_FakeDeterministicEnv,
    )

    json_path, txt_path = bt.save_results(result, output_dir=str(tmp_path))
    assert Path(json_path).exists()
    assert Path(txt_path).exists()
    assert "Risk Gate" in Path(txt_path).read_text(encoding="utf-8")
