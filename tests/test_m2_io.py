"""Testes unitarios para src/live_utils.py e src/m2_writer.py."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from src import live_utils
from src import m2_writer


def test_load_m2_tmp_missing(tmp_path, monkeypatch):
    """Retorna placeholder quando logs/m2_tmp.json nao existe."""
    monkeypatch.setattr(live_utils, "get_project_root", lambda: str(tmp_path))
    logs_dir = tmp_path / "logs"
    assert not logs_dir.exists()

    data = live_utils.load_m2_tmp()

    assert isinstance(data, dict)
    assert "generated_at" in data
    assert data.get("symbols") == {}


def test_load_m2_tmp_corrupt(tmp_path, monkeypatch):
    """Renomeia arquivo corrompido e retorna placeholder quando JSON e invalido."""
    monkeypatch.setattr(live_utils, "get_project_root", lambda: str(tmp_path))
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)
    file_path = logs_dir / "m2_tmp.json"
    file_path.write_text("{ invalid json", encoding="utf-8")

    data = live_utils.load_m2_tmp()

    assert isinstance(data, dict)
    assert data.get("symbols") == {}
    corrupts = list(logs_dir.glob("m2_tmp.json.corrupt.*"))
    assert len(corrupts) == 1


def test_atomic_write_json(tmp_path):
    """atomic_write_json cria arquivo valido e nao deixa temporario."""
    logs_dir = tmp_path / "logs"
    target = str(logs_dir / "m2_tmp.json")
    sample = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": {"BTCUSDT": {}},
    }

    m2_writer.atomic_write_json(target, sample)

    assert os.path.exists(target)
    with open(target, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["symbols"].get("BTCUSDT") == {}
    # nenhum arquivo temporario deve restar
    tmps = list(logs_dir.glob(".m2_tmp_*"))
    assert tmps == []
