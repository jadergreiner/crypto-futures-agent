"""Suite RED para runner M2-019.4 de treino diario por simbolo."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.model2 import train_entry_agents as train_entry_agents_module


def _criar_db_episodios(db_path: Path, *, symbol: str, total: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS training_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_key TEXT NOT NULL UNIQUE,
                cycle_run_id TEXT NOT NULL,
                execution_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                status TEXT NOT NULL,
                event_timestamp INTEGER NOT NULL,
                label TEXT NOT NULL,
                reward_proxy REAL,
                features_json TEXT NOT NULL,
                target_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )

        for idx in range(total):
            conn.execute(
                """
                INSERT INTO training_episodes (
                    episode_key,
                    cycle_run_id,
                    execution_id,
                    symbol,
                    timeframe,
                    status,
                    event_timestamp,
                    label,
                    reward_proxy,
                    features_json,
                    target_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{symbol}_H4_{idx}",
                    "cycle-red",
                    idx + 1,
                    symbol,
                    "H4",
                    "completed",
                    1_700_000_000_000 + idx,
                    "win",
                    0.25,
                    json.dumps({"open_norm": 0.0}),
                    "{}",
                    1_700_000_000_000 + idx,
                ),
            )


def test_runner_skipa_simbolos_com_menos_de_20_episodios(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_episodios(db_path, symbol="BTCUSDT", total=19)
    monkeypatch.setattr(train_entry_agents_module, "REPO_ROOT", tmp_path)

    summary = train_entry_agents_module.run_train_entry_agents(
        symbols=["BTCUSDT"],
        db_path=db_path,
        timeframe="H4",
        dry_run=False,
        total_timesteps=1000,
    )

    assert summary["results"]["BTCUSDT"]["status"] == "skipped"


def test_runner_treina_simbolo_com_30_episodios(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_episodios(db_path, symbol="BTCUSDT", total=30)
    monkeypatch.setattr(train_entry_agents_module, "REPO_ROOT", tmp_path)

    class _FakeManager:
        def __init__(self, base_dir: str = "") -> None:
            self.base_dir = base_dir

        def train_entry_agent(self, symbol, episodes, total_timesteps):
            return {
                "success": True,
                "symbol": symbol,
                "episodes_used": len(episodes),
                "total_timesteps": total_timesteps,
            }

        def save_all(self) -> None:
            return None

    monkeypatch.setattr(
        train_entry_agents_module,
        "SubAgentManager",
        _FakeManager,
        raising=False,
    )

    summary = train_entry_agents_module.run_train_entry_agents(
        symbols=["BTCUSDT"],
        db_path=db_path,
        timeframe="H4",
        dry_run=False,
        total_timesteps=1000,
    )

    assert summary["results"]["BTCUSDT"]["status"] == "trained"
    assert summary["results"]["BTCUSDT"]["episodes_used"] == 30


def test_dry_run_nao_salva_modelo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_episodios(db_path, symbol="BTCUSDT", total=30)
    monkeypatch.setattr(train_entry_agents_module, "REPO_ROOT", tmp_path)
    saved = {"called": False}

    class _FakeManager:
        def __init__(self, base_dir: str = "") -> None:
            self.base_dir = base_dir

        def train_entry_agent(self, symbol, episodes, total_timesteps):
            return {
                "success": True,
                "symbol": symbol,
                "episodes_used": len(episodes),
                "total_timesteps": total_timesteps,
            }

        def save_all(self) -> None:
            saved["called"] = True

    monkeypatch.setattr(
        train_entry_agents_module,
        "SubAgentManager",
        _FakeManager,
        raising=False,
    )

    summary = train_entry_agents_module.run_train_entry_agents(
        symbols=["BTCUSDT"],
        db_path=db_path,
        timeframe="H4",
        dry_run=True,
        total_timesteps=1000,
    )

    assert summary["dry_run"] is True
    assert saved["called"] is False


def test_output_json_contem_status_por_simbolo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_episodios(db_path, symbol="BTCUSDT", total=30)
    _criar_db_episodios(db_path, symbol="ETHUSDT", total=10)
    monkeypatch.setattr(train_entry_agents_module, "REPO_ROOT", tmp_path)

    class _FakeManager:
        def __init__(self, base_dir: str = "") -> None:
            self.base_dir = base_dir

        def train_entry_agent(self, symbol, episodes, total_timesteps):
            return {
                "success": True,
                "symbol": symbol,
                "episodes_used": len(episodes),
                "total_timesteps": total_timesteps,
            }

        def save_all(self) -> None:
            return None

    monkeypatch.setattr(
        train_entry_agents_module,
        "SubAgentManager",
        _FakeManager,
        raising=False,
    )

    summary = train_entry_agents_module.run_train_entry_agents(
        symbols=["BTCUSDT", "ETHUSDT"],
        db_path=db_path,
        timeframe="H4",
        dry_run=False,
        total_timesteps=1000,
    )

    output_file = Path(summary["output_file"])
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["results"]["BTCUSDT"]["status"] == "trained"
    assert payload["results"]["ETHUSDT"]["status"] == "skipped"


def test_continue_on_error_nao_aborta_restante_em_falha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_episodios(db_path, symbol="BTCUSDT", total=30)
    _criar_db_episodios(db_path, symbol="ETHUSDT", total=30)
    monkeypatch.setattr(train_entry_agents_module, "REPO_ROOT", tmp_path)

    class _FakeManager:
        def __init__(self, base_dir: str = "") -> None:
            self.base_dir = base_dir

        def train_entry_agent(self, symbol, episodes, total_timesteps):
            _ = episodes
            _ = total_timesteps
            if symbol == "BTCUSDT":
                raise RuntimeError("falha pontual")
            return {"success": True, "symbol": symbol, "episodes_used": 30}

        def save_all(self) -> None:
            return None

    monkeypatch.setattr(
        train_entry_agents_module,
        "SubAgentManager",
        _FakeManager,
        raising=False,
    )

    summary = train_entry_agents_module.run_train_entry_agents(
        symbols=["BTCUSDT", "ETHUSDT"],
        db_path=db_path,
        timeframe="H4",
        dry_run=False,
        total_timesteps=1000,
        continue_on_error=True,
    )

    assert summary["results"]["BTCUSDT"]["status"] == "error"
    assert summary["results"]["ETHUSDT"]["status"] == "trained"
