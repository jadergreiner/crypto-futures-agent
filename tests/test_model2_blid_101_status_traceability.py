#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Suite RED BLID-101: contrato verificavel do status operacional por simbolo."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.operator_cycle_status import _build_symbol_report


def _create_traceability_db(*, include_decision: bool, include_execution: bool, include_episode: bool) -> str:
    """Cria DB temporario com tabelas minimas para cenarios de correlacao."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    conn = sqlite3.connect(tmp.name)
    conn.execute(
        "CREATE TABLE model_decisions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "symbol TEXT NOT NULL,"
        "action TEXT NOT NULL,"
        "confidence REAL,"
        "model_version TEXT,"
        "reason_code TEXT,"
        "decision_timestamp INTEGER,"
        "input_json TEXT"
        ")"
    )
    conn.execute(
        "CREATE TABLE signal_executions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "symbol TEXT NOT NULL,"
        "decision_id INTEGER"
        ")"
    )
    conn.execute(
        "CREATE TABLE training_episodes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "symbol TEXT NOT NULL,"
        "execution_id INTEGER NOT NULL,"
        "status TEXT NOT NULL,"
        "reward_proxy REAL"
        ")"
    )
    conn.execute("CREATE TABLE ohlcv_d1 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_h4 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_h1 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_m5 (symbol TEXT, timestamp INTEGER)")

    symbol = "FLUXUSDT"
    conn.execute("INSERT INTO ohlcv_d1 (symbol, timestamp) VALUES (?, ?)", (symbol, 1774742400000))
    conn.execute("INSERT INTO ohlcv_h4 (symbol, timestamp) VALUES (?, ?)", (symbol, 1774814400000))
    conn.execute("INSERT INTO ohlcv_h1 (symbol, timestamp) VALUES (?, ?)", (symbol, 1774818000000))
    conn.execute("INSERT INTO ohlcv_m5 (symbol, timestamp) VALUES (?, ?)", (symbol, 1774820100000))

    decision_id: int | None = None
    execution_id: int | None = None

    if include_decision:
        conn.execute(
            "INSERT INTO model_decisions (symbol, action, confidence, model_version, reason_code, decision_timestamp, input_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                symbol,
                "OPEN_LONG",
                0.30,
                "m2-inference-v1",
                "inference_from_symbol_model_divergence",
                1774820372854,
                (
                    '{"market_state":{"signal_timestamp":1774804817563},'
                    '"risk_state":{"signal_age_ms":15555291,"max_signal_age_ms":14400000}}'
                ),
            ),
        )
        decision_id = int(conn.execute("SELECT MAX(id) FROM model_decisions").fetchone()[0])

    if include_execution:
        conn.execute(
            "INSERT INTO signal_executions (symbol, decision_id) VALUES (?, ?)",
            (symbol, decision_id),
        )
        execution_id = int(conn.execute("SELECT MAX(id) FROM signal_executions").fetchone()[0])

    if include_episode:
        conn.execute(
            "INSERT INTO training_episodes (symbol, execution_id, status, reward_proxy) VALUES (?, ?, ?, ?)",
            (symbol, execution_id or 0, "EXITED", -0.0005),
        )

    conn.commit()
    conn.close()
    return tmp.name


def _build_report(db_path: str) -> str:
    with patch("scripts.model2.operator_cycle_status._query_risk_state_from_db", return_value=None):
        return _build_symbol_report(
            symbol="FLUXUSDT",
            scan_d1=None,
            scan_h4=None,
            scan_h1=None,
            scan_m5=None,
            live_execute_summary=None,
            exchange=None,
            last_train_time="N/A",
            pending_episodes=0,
            db_path=db_path,
        )


# ---------------------------------------------------------------------------
# Unitarios (8)
# ---------------------------------------------------------------------------

def test_status_decisao_quando_correlacionado_entao_exibe_decision_id_model_version_reason_source() -> None:
    """R1: linha Decisao deve incluir trilha auditavel da decisao."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    decision_line = next(line for line in report.splitlines() if "Decisao  :" in line)
    assert "decision_id=" in decision_line
    assert "model_version=" in decision_line
    assert "reason=" in decision_line
    assert "source=" in decision_line


def test_status_frescor_quando_decisao_existe_entao_exibe_signal_timestamp_idade_e_limite() -> None:
    """R2: contrato deve incluir linha de Frescor objetiva."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    frescor_line = next(line for line in report.splitlines() if "Frescor  :" in line)
    assert "signal_ts=" in frescor_line
    assert "signal_age_ms=" in frescor_line
    assert "max_signal_age_ms=" in frescor_line


def test_status_features_quando_decisao_existe_entao_lista_features_chave_e_snapshot() -> None:
    """R3: linha Features deve explicitar vetor usado e snapshot_at."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    features_line = next(line for line in report.splitlines() if "Features :" in line)
    assert "close" in features_line
    assert "rr_ratio" in features_line
    assert "snapshot_at=" in features_line


def test_status_persistencia_quando_correlacionado_entao_exibe_decisao_execucao_episodio() -> None:
    """R4: linha Persist deve correlacionar model_decisions, signal_executions e episodes."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    persist_line = next(line for line in report.splitlines() if "Persist. :" in line)
    assert "model_decisions=" in persist_line
    assert "signal_execution=" in persist_line
    assert "episode=" in persist_line
    assert "symbol=FLUXUSDT" in persist_line


def test_status_persistencia_quando_episodio_legado_sem_decision_link_entao_exibe_legacy_flag() -> None:
    """R5: legado sem decision_id deve ser explicito no status."""
    report = _build_report(_create_traceability_db(include_decision=False, include_execution=True, include_episode=True))
    persist_line = next(line for line in report.splitlines() if "Persist. :" in line)
    assert "LEGACY_NO_DECISION_LINK" in persist_line


def test_status_candles_quando_renderiza_entao_exibe_janela_explicita_de_frescor() -> None:
    """R6: linha Candles deve informar janela usada para classificar fresh/stale."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    candles_line = next(line for line in report.splitlines() if "Candles  :" in line)
    assert "window_ms=" in candles_line


def test_status_contrato_quando_renderiza_entao_exibe_tag_de_versao_do_contrato() -> None:
    """R7: contrato de saida deve ser versionado para auditoria."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    assert "contract=BLID-101-v1" in report


def test_status_determinismo_quando_mesmas_entradas_entao_bloco_de_auditoria_igual() -> None:
    """R8: output deve manter bloco de auditoria deterministico."""
    db_path = _create_traceability_db(include_decision=True, include_execution=True, include_episode=True)
    first = _build_report(db_path)
    second = _build_report(db_path)
    first_audit = [l for l in first.splitlines() if "Frescor  :" in l or "Persist. :" in l or "Features :" in l]
    second_audit = [l for l in second.splitlines() if "Frescor  :" in l or "Persist. :" in l or "Features :" in l]
    assert first_audit == second_audit


# ---------------------------------------------------------------------------
# Integracao (3)
# ---------------------------------------------------------------------------

def test_integracao_correlacao_quando_decisao_execucao_episodio_validos_entao_status_mostra_join_ponta_a_ponta() -> None:
    """I1: join real sqlite deve alimentar linha Persist com ids correlacionados."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    persist_line = next(line for line in report.splitlines() if "Persist. :" in line)
    assert "model_decisions=" in persist_line and "signal_execution=" in persist_line and "episode=" in persist_line


def test_integracao_legado_quando_execucao_sem_decision_id_entao_status_mostra_lacuna_sem_mascarar() -> None:
    """I2: join real sqlite deve cair em LEGACY_NO_DECISION_LINK quando faltar decision_id."""
    report = _build_report(_create_traceability_db(include_decision=False, include_execution=True, include_episode=True))
    persist_line = next(line for line in report.splitlines() if "Persist. :" in line)
    assert "LEGACY_NO_DECISION_LINK" in persist_line


def test_integracao_candles_quando_tabelas_ohlcv_presentes_entao_frescor_exibe_m5_h1_h4_d1() -> None:
    """I3: com OHLCV persistido, linha Frescor deve carregar timestamps por timeframe."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    frescor_line = next(line for line in report.splitlines() if "Frescor  :" in line)
    assert "M5_last=" in frescor_line
    assert "H1_last=" in frescor_line
    assert "H4_last=" in frescor_line
    assert "D1_last=" in frescor_line


# ---------------------------------------------------------------------------
# Regressao/Risco (3)
# ---------------------------------------------------------------------------

def test_regressao_risk_quando_novo_contrato_ativo_entao_linha_risk_permanece_presente() -> None:
    """RR1: novo contrato nao pode remover visibilidade de risco existente."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    assert "Risk     :" in report


def test_regressao_fail_safe_quando_db_inacessivel_entao_report_nao_quebra_e_exibe_legacy_flag() -> None:
    """RR2: fail-safe deve manter status renderizavel com lacuna explicita."""
    report = _build_report("C:/nao/existe/modelo2.db")
    assert "LEGACY_NO_DECISION_LINK" in report


def test_regressao_guardrail_quando_novo_contrato_ativo_entao_linha_candles_permanece_presente() -> None:
    """RR3: contrato novo nao pode remover linha de candles do operador."""
    report = _build_report(_create_traceability_db(include_decision=True, include_execution=True, include_episode=True))
    assert "Candles  :" in report
