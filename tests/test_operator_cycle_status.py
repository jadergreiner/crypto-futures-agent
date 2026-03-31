#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Testes RED para BLID-090: _query_risk_state_from_db e linha Risk em _build_symbol_report."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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
            last_train_time="2026-03-31 10:00:00",
            pending_episodes=5,
            db_path=db_path,
        )

    assert "pendentes: 5/3" in report
    assert "confidence_gate=34%" in report


def test_build_symbol_report_exibe_protecao_quando_decisao_abertura_tem_alvos() -> None:
    """Linha Protecao deve exibir entry/sl/tp/rr para OPEN_SHORT com geometria valida."""
    db_path = _create_empty_db()

    decision_trace = {
        "decision_id": 42728,
        "action": "OPEN_SHORT",
        "confidence": 0.34,
        "sl_target": 66386.1,
        "tp_target": 66304.1,
        "entry_price": 66358.7,
        "targets_origin": "M2-006.1-RULE-STANDARD-SIGNAL",
        "model_version": "m2-inference-v1",
        "reason_code": "inference_from_symbol_model_divergence",
        "decision_timestamp_ms": 1774925959000,
        "signal_timestamp_ms": 1774925935000,
        "signal_age_ms": 24000,
        "max_signal_age_ms": 14400000,
        "source": "RL_MODEL",
    }

    with (
        patch("scripts.model2.operator_cycle_status._query_last_decision_from_db", return_value=("OPEN_SHORT", 0.34)),
        patch("scripts.model2.operator_cycle_status._query_last_decision_trace", return_value=decision_trace),
        patch("scripts.model2.operator_cycle_status._query_last_execution_trace", return_value=None),
        patch("scripts.model2.operator_cycle_status._query_last_episode_trace", return_value=None),
        patch("scripts.model2.operator_cycle_status._query_episode_info", return_value=(None, False, 0.0)),
        patch("scripts.model2.operator_cycle_status._query_risk_state_from_db", return_value=None),
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

    protection_line = next(line for line in report.splitlines() if "Protecao :" in line)
    assert "entry=66358.7000" in protection_line
    assert "sl=66386.1000" in protection_line
    assert "tp=66304.1000" in protection_line
    assert "rr=" in protection_line
    assert "geometria=ok" in protection_line
    assert "origem=M2-006.1-RULE-STANDARD-SIGNAL" in protection_line


def test_query_last_episode_trace_ignora_cycle_context_quando_ha_trade_episode() -> None:
    """Deve priorizar episodio real e evitar falso LEGACY com CYCLE_CONTEXT mais novo."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    conn = sqlite3.connect(tmp.name)
    conn.execute(
        """
        CREATE TABLE training_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            status TEXT NOT NULL,
            event_timestamp INTEGER,
            created_at INTEGER
        )
        """
    )
    conn.execute(
        """
        INSERT INTO training_episodes (execution_id, symbol, timeframe, status, event_timestamp, created_at)
        VALUES (108, 'BTCUSDT', 'M5', 'FAILED', 1774933282140, 1774933290000)
        """
    )
    conn.execute(
        """
        INSERT INTO training_episodes (execution_id, symbol, timeframe, status, event_timestamp, created_at)
        VALUES (0, 'BTCUSDT', 'M5', 'CYCLE_CONTEXT', 1774933299043, 1774933299043)
        """
    )
    conn.commit()
    conn.close()

    trace = _query_last_episode_trace(symbol="BTCUSDT", db_path=tmp.name)

    assert trace is not None
    assert trace["execution_id"] == 108
    assert str(trace["status"]).upper() == "FAILED"


def test_query_training_cutoff_ms_isola_por_simbolo() -> None:
    """Status deve explicar cutoff usando auditoria dedicada do símbolo."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    conn = sqlite3.connect(tmp.name)
    conn.execute(
        """
        CREATE TABLE rl_training_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            completed_at TEXT,
            completed_at_ms INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE rl_training_log_by_symbol (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT,
            completed_at TEXT,
            completed_at_ms INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO rl_training_log (completed_at, completed_at_ms) VALUES (?, ?)",
        ("2026-03-31 02:33:40", 1000),
    )
    conn.execute(
        "INSERT INTO rl_training_log_by_symbol (symbol, timeframe, completed_at, completed_at_ms) VALUES (?, ?, ?, ?)",
        ("BTCUSDT", "M5", "2026-03-31 02:33:41", 2000),
    )
    conn.execute(
        "INSERT INTO rl_training_log_by_symbol (symbol, timeframe, completed_at, completed_at_ms) VALUES (?, ?, ?, ?)",
        ("ETHUSDT", "M5", "2026-03-31 02:33:42", 3000),
    )
    conn.commit()
    conn.close()

    assert _query_training_cutoff_ms(tmp.name, symbol="BTCUSDT", timeframe="M5") == 2000
    assert _query_training_cutoff_ms(tmp.name, symbol="ETHUSDT", timeframe="M5") == 3000
    assert _query_training_cutoff_ms(tmp.name, symbol="XRPUSDT", timeframe="M5") == 1000


# ---------------------------------------------------------------------------
# Testes: _build_symbol_report — conteudo da linha Risk
# ---------------------------------------------------------------------------

def _build_report_with_risk(risk_data: dict, action: str = "HOLD") -> str:
    """Helper: constroi relatorio com risk_state mockado."""
    db_path = _create_empty_db()

    with (
        patch("scripts.model2.operator_cycle_status._query_last_decision_from_db", return_value=(action, 0.75)),
        patch("scripts.model2.operator_cycle_status._query_episode_info", return_value=(None, False, 0.0)),
        patch("scripts.model2.operator_cycle_status._query_risk_state_from_db", return_value=risk_data),
    ):
        return _build_symbol_report(
            symbol="BTCUSDT",
            scan_h4=None,
            scan_h1=None,
            live_execute_summary=None,
            exchange=None,
            last_train_time="N/A",
            pending_episodes=0,
            db_path=db_path,
        )


def test_build_symbol_report_risk_exibe_estado_cb_normal():
    """REQ-3: linha Risk exibe estado CB quando normal."""
    # Arrange
    risk = {"circuit_breaker_state": "normal", "risk_gate_status": "ATIVO",
            "short_only": False, "recent_entries_today": 1, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk)
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert
    assert "normal" in risk_line
    assert "ATIVO" in risk_line


def test_build_symbol_report_risk_exibe_cb_trancado_quando_estado_tripped():
    """REQ-4: quando circuit_breaker_state != 'normal', exibe '[CB TRANCADO]'."""
    # Arrange
    risk = {"circuit_breaker_state": "tripped", "risk_gate_status": "ATIVO",
            "short_only": False, "recent_entries_today": 1, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk)
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert
    assert "[CB TRANCADO]" in risk_line


def test_build_symbol_report_risk_exibe_cb_trancado_quando_estado_halted():
    """REQ-4: circuit_breaker_state='halted' tambem exibe '[CB TRANCADO]'."""
    # Arrange
    risk = {"circuit_breaker_state": "halted", "risk_gate_status": "ATIVO",
            "short_only": False, "recent_entries_today": 1, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk)
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert
    assert "[CB TRANCADO]" in risk_line


def test_build_symbol_report_posicao_exibe_tamanho_nocional_e_roi_sobre_margem() -> None:
    """Posicao deve refletir nocional em USDT e ROI calculado sobre margem."""
    db_path = _create_empty_db()
    exchange = MagicMock()
    exchange.get_open_position.return_value = {
        "symbol": "BTCUSDT",
        "direction": "SHORT",
        "position_size_qty": 0.001,
        "position_size_usdt": 67.9830077,
        "entry_price": 70637.75,
        "mark_price": 67983.0077,
        "margin_invested": 6.79830077,
        "leverage": 10,
        "unrealized_pnl": 2.65,
        "unrealized_pnl_pct": 38.98,
    }

    with (
        patch("scripts.model2.operator_cycle_status._query_last_decision_from_db", return_value=("OPEN_SHORT", 0.30)),
        patch("scripts.model2.operator_cycle_status._query_episode_info", return_value=(None, False, 0.0)),
        patch("scripts.model2.operator_cycle_status._query_risk_state_from_db", return_value=None),
    ):
        report = _build_symbol_report(
            symbol="BTCUSDT",
            scan_h4=None,
            scan_h1=None,
            live_execute_summary=None,
            exchange=exchange,
            last_train_time="N/A",
            pending_episodes=0,
            db_path=db_path,
        )

    position_line = next(line for line in report.splitlines() if "Posicao  :" in line)
    assert "SHORT 67.98 USDT @ 70637.7500" in position_line
    assert "mark: 67983.0077" in position_line
    assert "margem: $6.80" in position_line
    assert "alavancagem: 10x" in position_line
    assert "PnL: +38.98% (+$2.65)" in position_line


def test_build_symbol_report_risk_exibe_long_bloqueado_quando_short_only_e_open_long():
    """REQ-5: short_only=True e decisao OPEN_LONG exibe '[LONG BLOQUEADO - short_only]'."""
    # Arrange
    risk = {"circuit_breaker_state": "normal", "risk_gate_status": "ATIVO",
            "short_only": True, "recent_entries_today": 1, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk, action="OPEN_LONG")
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert
    assert "[LONG BLOQUEADO - short_only]" in risk_line


def test_build_symbol_report_risk_nao_exibe_long_bloqueado_quando_short_only_e_open_short():
    """REQ-5: short_only=True mas decisao OPEN_SHORT nao exibe alerta de bloqueio LONG."""
    # Arrange
    risk = {"circuit_breaker_state": "normal", "risk_gate_status": "ATIVO",
            "short_only": True, "recent_entries_today": 1, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk, action="OPEN_SHORT")
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert
    assert "[LONG BLOQUEADO - short_only]" not in risk_line


def test_build_symbol_report_risk_exibe_limite_atingido_quando_entradas_esgotadas():
    """REQ-6: recent_entries_today >= max_daily_entries exibe 'entradas hoje: N/N [LIMITE ATINGIDO]'."""
    # Arrange
    risk = {"circuit_breaker_state": "normal", "risk_gate_status": "ATIVO",
            "short_only": False, "recent_entries_today": 5, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk)
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert
    assert "entradas hoje: 5/5" in risk_line
    assert "[LIMITE ATINGIDO]" in risk_line


def test_build_symbol_report_risk_exibe_limite_atingido_quando_entradas_excedem():
    """REQ-6: recent_entries_today > max_daily_entries tambem exibe [LIMITE ATINGIDO]."""
    # Arrange
    risk = {"circuit_breaker_state": "normal", "risk_gate_status": "ATIVO",
            "short_only": False, "recent_entries_today": 7, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk)
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert
    assert "[LIMITE ATINGIDO]" in risk_line


def test_build_symbol_report_risk_exibe_entradas_sem_limite_quando_abaixo_maximo():
    """REQ-6: abaixo do limite exibe contagem sem '[LIMITE ATINGIDO]'."""
    # Arrange
    risk = {"circuit_breaker_state": "normal", "risk_gate_status": "ATIVO",
            "short_only": False, "recent_entries_today": 2, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk)
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert
    assert "entradas hoje: 2/5" in risk_line
    assert "[LIMITE ATINGIDO]" not in risk_line


def test_build_symbol_report_risk_exibe_short_only_no_relatorio():
    """REQ-3: linha Risk exibe valor de short_only."""
    # Arrange
    risk = {"circuit_breaker_state": "normal", "risk_gate_status": "ATIVO",
            "short_only": True, "recent_entries_today": 1, "max_daily_entries": 5}

    # Act
    report = _build_report_with_risk(risk, action="HOLD")
    risk_line = next(l for l in report.splitlines() if "Risk     :" in l)

    # Assert — alguma representacao de short_only deve estar presente
    assert "short_only" in risk_line.lower() or "True" in risk_line


def test_build_symbol_report_nao_levanta_excecao_quando_db_inexistente():
    """REQ-7: DB inexistente nao deve propagar excecao."""
    # Act / Assert (nao deve lancar)
    try:
        result = _build_symbol_report(
            symbol="BTCUSDT",
            scan_h4=None,
            scan_h1=None,
            live_execute_summary=None,
            exchange=None,
            last_train_time="N/A",
            pending_episodes=0,
            db_path="/nao/existe/modelo2.db",
        )
        assert isinstance(result, str)
    except Exception as exc:
        pytest.fail(f"_build_symbol_report nao deve propagar excecao: {exc}")
