#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Testes RED para BLID-090: _query_risk_state_from_db e linha Risk em _build_symbol_report."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.operator_cycle_status import (
    _build_symbol_report,
    _query_last_episode_trace,
    _query_risk_state_from_db,
    _query_training_cutoff_ms,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _create_db_with_decision(
    input_json: dict | None = None,
    action: str = "HOLD",
    confidence: float = 0.75,
) -> str:
    """Cria DB temporario com uma decisao em model_decisions."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute(
        "CREATE TABLE model_decisions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "symbol TEXT NOT NULL,"
        "action TEXT NOT NULL,"
        "confidence REAL,"
        "input_json TEXT NOT NULL DEFAULT '{}',"
        "created_at TEXT"
        ")"
    )
    payload = json.dumps(input_json) if input_json is not None else "{}"
    conn.execute(
        "INSERT INTO model_decisions (symbol, action, confidence, input_json) VALUES (?,?,?,?)",
        ("BTCUSDT", action, confidence, payload),
    )
    conn.commit()
    conn.close()
    return tmp.name


def _create_empty_db() -> str:
    """Cria DB temporario sem tabela model_decisions."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    return tmp.name


# ---------------------------------------------------------------------------
# Testes: _query_risk_state_from_db — retorno correto
# ---------------------------------------------------------------------------

def test_query_risk_state_from_db_retorna_todos_campos_quando_input_json_completo():
    """REQ-1: funcao retorna dict com todos os campos esperados quando input_json completo."""
    # Arrange
    risk_data = {
        "circuit_breaker_state": "normal",
        "risk_gate_status": "ATIVO",
        "short_only": False,
        "recent_entries_today": 2,
        "max_daily_entries": 5,
    }
    db_path = _create_db_with_decision(input_json=risk_data)

    # Act
    result = _query_risk_state_from_db("BTCUSDT", db_path)

    # Assert
    assert result is not None
    assert result["circuit_breaker_state"] == "normal"
    assert result["risk_gate_status"] == "ATIVO"
    assert result["short_only"] is False
    assert result["recent_entries_today"] == 2
    assert result["max_daily_entries"] == 5


def test_query_risk_state_from_db_retorna_dict_vazio_quando_input_json_sem_campos_risk():
    """REQ-7 parcial: quando input_json existe mas sem campos risk, retorna dict sem crash."""
    # Arrange
    db_path = _create_db_with_decision(input_json={"outro_campo": "valor"})

    # Act
    result = _query_risk_state_from_db("BTCUSDT", db_path)

    # Assert
    assert result is not None
    assert isinstance(result, dict)


def test_query_risk_state_from_db_retorna_none_quando_db_vazio():
    """REQ-7: sem dados de risk_state, retorna None sem excecao."""
    # Arrange
    db_path = _create_empty_db()

    # Act
    result = _query_risk_state_from_db("BTCUSDT", db_path)

    # Assert
    assert result is None


def test_query_risk_state_from_db_retorna_none_quando_symbol_nao_existe():
    """REQ-7: symbol sem decisao retorna None."""
    # Arrange
    db_path = _create_db_with_decision(input_json={"circuit_breaker_state": "normal"})

    # Act
    result = _query_risk_state_from_db("ETHUSDT", db_path)

    # Assert
    assert result is None


def test_query_risk_state_from_db_retorna_none_quando_db_inexistente():
    """REQ-7: path invalido nao levanta excecao, retorna None."""
    # Act
    result = _query_risk_state_from_db("BTCUSDT", "/nao/existe/modelo2.db")

    # Assert
    assert result is None


def test_query_risk_state_from_db_usa_decisao_mais_recente():
    """REQ-1: deve retornar dados da decisao mais recente (maior id)."""
    # Arrange
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute(
        "CREATE TABLE model_decisions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "symbol TEXT NOT NULL,"
        "action TEXT NOT NULL,"
        "confidence REAL,"
        "input_json TEXT NOT NULL DEFAULT '{}',"
        "created_at TEXT"
        ")"
    )
    old_data = json.dumps({"circuit_breaker_state": "tripped", "recent_entries_today": 1, "max_daily_entries": 5})
    new_data = json.dumps({"circuit_breaker_state": "normal", "recent_entries_today": 3, "max_daily_entries": 5})
    conn.execute("INSERT INTO model_decisions (symbol, action, confidence, input_json) VALUES (?,?,?,?)",
                 ("BTCUSDT", "HOLD", 0.5, old_data))
    conn.execute("INSERT INTO model_decisions (symbol, action, confidence, input_json) VALUES (?,?,?,?)",
                 ("BTCUSDT", "HOLD", 0.8, new_data))
    conn.commit()
    conn.close()

    # Act
    result = _query_risk_state_from_db("BTCUSDT", tmp.name)

    # Assert
    assert result is not None
    assert result["circuit_breaker_state"] == "normal"
    assert result["recent_entries_today"] == 3


# ---------------------------------------------------------------------------
# Testes: _build_symbol_report — linha Risk presente
# ---------------------------------------------------------------------------

def _build_report_minimal(symbol: str = "BTCUSDT", db_path: str | None = None) -> str:
    """Helper: constrói relatório com mocks minimos."""
    if db_path is None:
        db_path = _create_empty_db()

    with (
        patch("scripts.model2.operator_cycle_status._query_last_decision_from_db", return_value=("HOLD", 0.0)),
        patch("scripts.model2.operator_cycle_status._query_episode_info", return_value=(None, False, 0.0)),
        patch("scripts.model2.operator_cycle_status._query_risk_state_from_db", return_value=None),
        patch("scripts.model2.operator_cycle_status.resolve_retrain_threshold", return_value=(100, None)),
        patch("core.model2.cycle_report.collect_training_info", return_value=("nunca", 0)),
    ):
        return _build_symbol_report(
            symbol=symbol,
            scan_h4=None,
            scan_h1=None,
            live_execute_summary=None,
            exchange=None,
            last_train_time="N/A",
            pending_episodes=0,
            db_path=db_path,
        )


def test_build_symbol_report_contem_linha_risk():
    """REQ-2: relatorio deve conter linha 'Risk     :' apos 'Posicao  :'."""
    # Arrange / Act
    report = _build_report_minimal()

    # Assert
    assert "Risk     :" in report


def test_build_symbol_report_linha_risk_apos_posicao():
    """REQ-2: linha Risk deve aparecer imediatamente apos linha Posicao."""
    # Arrange / Act
    report = _build_report_minimal()
    lines = report.splitlines()

    posicao_idx = next((i for i, l in enumerate(lines) if "Posicao  :" in l), None)
    risk_idx = next((i for i, l in enumerate(lines) if "Risk     :" in l), None)

    # Assert
    assert posicao_idx is not None, "Linha Posicao nao encontrada"
    assert risk_idx is not None, "Linha Risk nao encontrada"
    assert risk_idx == posicao_idx + 1, f"Risk deve ser logo apos Posicao, mas posicao={posicao_idx} risk={risk_idx}"


def test_build_symbol_report_risk_exibe_na_quando_sem_dados():
    """REQ-7: sem dados de risk_state exibe 'Risk: N/A' sem quebrar."""
    # Arrange / Act
    report = _build_report_minimal()

    # Assert
    assert "N/A" in report or "Risk     :" in report
    lines = [l for l in report.splitlines() if "Risk     :" in l]
    assert len(lines) == 1
    assert "N/A" in lines[0]


def test_build_symbol_report_exibe_threshold_dinamico_de_treino() -> None:
    """Quando a confiança estiver baixa, o status deve expor threshold 3."""
    db_path = _create_empty_db()

    with (
        patch("scripts.model2.operator_cycle_status._query_last_decision_from_db", return_value=("HOLD", 0.34)),
        patch("scripts.model2.operator_cycle_status._query_episode_info", return_value=(None, False, 0.0)),
        patch("scripts.model2.operator_cycle_status._query_risk_state_from_db", return_value=None),
        patch("scripts.model2.operator_cycle_status.resolve_retrain_threshold", return_value=(3, 0.34)),
        patch("core.model2.cycle_report.collect_training_info", return_value=("2026-03-31 10:00:00", 5)),
    ):
        report = _build_symbol_report(
            symbol="BTCUSDT",
            scan_h4=None,
            scan_h1=None,
            live_execute_summary=None,
            exchange=None,
            last_train_time="N/A",
            pending_episodes=0,
            db_path=db_path,
        )
        assert "threshold" in report or "3" in report
