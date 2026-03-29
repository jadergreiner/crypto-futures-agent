#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Suite RED BLID-102: clareza operacional do status por simbolo."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.operator_cycle_status import _build_symbol_report


def _create_status_db_with_real_and_context_episode() -> str:
    """Cria DB com episodio de trade e contexto para provocar ids diferentes."""
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
        "reward_proxy REAL,"
        "event_timestamp INTEGER,"
        "created_at INTEGER,"
        "timeframe TEXT,"
        "label TEXT"
        ")"
    )
    conn.execute(
        "CREATE TABLE rl_training_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "completed_at TEXT,"
        "completed_at_ms INTEGER,"
        "episodes_used INTEGER,"
        "status TEXT"
        ")"
    )
    conn.execute("CREATE TABLE ohlcv_d1 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_h4 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_h1 (symbol TEXT, timestamp INTEGER)")
    conn.execute("CREATE TABLE ohlcv_m5 (symbol TEXT, timestamp INTEGER)")

    symbol = "FLUXUSDT"
    conn.execute("INSERT INTO ohlcv_d1 (symbol, timestamp) VALUES (?, ?)", (symbol, 1774742400000))
    conn.execute("INSERT INTO ohlcv_h4 (symbol, timestamp) VALUES (?, ?)", (symbol, 1774814400000))
    conn.execute("INSERT INTO ohlcv_h1 (symbol, timestamp) VALUES (?, ?)", (symbol, 1774821600000))
    conn.execute("INSERT INTO ohlcv_m5 (symbol, timestamp) VALUES (?, ?)", (symbol, 1774823100000))

    conn.execute(
        "INSERT INTO model_decisions (symbol, action, confidence, model_version, reason_code, decision_timestamp, input_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            symbol,
            "OPEN_SHORT",
            0.30,
            "m2-inference-v1",
            "inference_from_symbol_model_divergence",
            1774823203270,
            (
                '{"market_state":{"signal_timestamp":1774687353836},'
                '"risk_state":{"signal_age_ms":135849434,"max_signal_age_ms":14400000}}'
            ),
        ),
    )
    decision_id = int(conn.execute("SELECT MAX(id) FROM model_decisions").fetchone()[0])

    # Execucao sem vinculo de decision_id para simular legado.
    conn.execute("INSERT INTO signal_executions (symbol, decision_id) VALUES (?, ?)", (symbol, None))

    # Episodio real de trade com reward (deve aparecer na linha Episodio).
    conn.execute(
        "INSERT INTO training_episodes (symbol, execution_id, status, reward_proxy, event_timestamp, created_at, timeframe, label) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (symbol, 10, "EXITED", -0.0005, 1774057941720, 1774058038298, "H4", "loss"),
    )
    # Episodio mais recente de contexto (deve aparecer na linha Persist.).
    conn.execute(
        "INSERT INTO training_episodes (symbol, execution_id, status, reward_proxy, event_timestamp, created_at, timeframe, label) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (symbol, 0, "CYCLE_CONTEXT", None, 1774822453731, 1774822453731, "H4", "context"),
    )

    conn.execute(
        "INSERT INTO rl_training_log (completed_at, completed_at_ms, episodes_used, status) VALUES (?, ?, ?, ?)",
        ("2026-03-27 02:50:37", 1774579837160, 8, "ok"),
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
            last_train_time="2026-03-27 02:50:37",
            pending_episodes=0,
            db_path=db_path,
        )


def test_status_episodio_quando_ids_divergem_entao_exibe_tipo_e_elegibilidade_de_treino() -> None:
    """R1/R2: Episodio deve explicar tipo e se conta para treino."""
    report = _build_report(_create_status_db_with_real_and_context_episode())
    episode_line = next(line for line in report.splitlines() if "Episodio :" in line)
    assert "episode_type=" in episode_line
    assert "eligibility_for_training=" in episode_line


def test_status_persist_quando_legado_entao_exibe_trilha_tecnica_e_mensagem_humana() -> None:
    """R3: Persist deve ter diagnostico tecnico+humano no legado."""
    report = _build_report(_create_status_db_with_real_and_context_episode())
    persist_line = next(line for line in report.splitlines() if "Persist. :" in line)
    assert "LEGACY_NO_DECISION_LINK" in persist_line
    assert "human_reason=" in persist_line
    assert "model_decisions=" in persist_line
    assert "signal_execution=" in persist_line
    assert "episode=" in persist_line


def test_status_legacy_quando_sem_link_entao_traduz_para_linguagem_de_operador() -> None:
    """R4: LEGACY deve ser traduzido para linguagem acessivel."""
    report = _build_report(_create_status_db_with_real_and_context_episode())
    persist_line = next(line for line in report.splitlines() if "Persist. :" in line)
    assert "registro existe mas sem vinculo completo" in persist_line


def test_status_treino_quando_zero_de_cem_entao_exibe_regra_de_elegibilidade_e_cutoff() -> None:
    """R5: Treino 0/100 precisa explicar regra e ponto de corte."""
    report = _build_report(_create_status_db_with_real_and_context_episode())
    train_line = next(line for line in report.splitlines() if "Treino   :" in line)
    assert "eligibility_rule=" in train_line
    assert "cutoff_ms=" in train_line
    assert "timeframe=H4" in train_line


def test_status_aud24h_quando_sem_inicio_entao_mantem_campos_tecnicos_e_texto_humano() -> None:
    """R6: aud24h deve manter tecnico + traducao operacional."""
    report = _build_report(_create_status_db_with_real_and_context_episode())
    train_line = next(line for line in report.splitlines() if "Treino   :" in line)
    assert "aud24h: started=" in train_line
    assert "running_block=" in train_line
    assert "conclusivo=" in train_line
    assert "aud24h_human=" in train_line


def test_status_fail_safe_quando_db_inacessivel_entao_renderiza_bloco_com_explicacao_humana() -> None:
    """R7: fail-safe nao quebra e explica lacuna em linguagem de operador."""
    report = _build_report("C:/nao/existe/modelo2.db")
    assert "Persist. :" in report
    persist_line = next(line for line in report.splitlines() if "Persist. :" in line)
    assert "LEGACY_NO_DECISION_LINK" in persist_line
    assert "human_reason=" in persist_line


def test_status_determinismo_quando_mesmas_entradas_entao_secao_clareza_permanece_igual() -> None:
    """R8: secao de clareza precisa ser deterministica."""
    db_path = _create_status_db_with_real_and_context_episode()
    first = _build_report(db_path)
    second = _build_report(db_path)
    first_lines = [l for l in first.splitlines() if "Episodio :" in l or "Persist. :" in l or "Treino   :" in l]
    second_lines = [l for l in second.splitlines() if "Episodio :" in l or "Persist. :" in l or "Treino   :" in l]
    assert first_lines == second_lines


def test_regressao_risk_quando_clareza_ativa_entao_linha_risk_permanece_presente() -> None:
    """RR1: nova clareza nao remove Risk."""
    report = _build_report(_create_status_db_with_real_and_context_episode())
    assert "Risk     :" in report


def test_regressao_candles_quando_clareza_ativa_entao_linha_candles_permanece_presente() -> None:
    """RR2: nova clareza nao remove Candles."""
    report = _build_report(_create_status_db_with_real_and_context_episode())
    assert "Candles  :" in report

