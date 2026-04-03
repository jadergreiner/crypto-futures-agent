"""Suite RED/GREEN para M2-023.6 - Trilha de auditoria de bloqueios do risk gate.

Cobre:
    RF-023.6.1 - Bloqueio por risk_gate gera evento com reason_code e metadados
    RF-023.6.2 - Consulta por decision_id retorna trilha ponta a ponta do DB
    RF-023.6.3 - Trilha vazia quando decision_id nao tem bloqueios
    RF-023.6.4 - Fail-safe: sem excecao em DB ausente ou corrompido
    RF-023.6.5 - Campos obrigatorios presentes em cada entrada da trilha
    RF-023.6.6 - Multiplos bloqueios para mesmo decision_id sao todos retornados
    RF-023.6.7 - Regressao de risco: risk_gate e circuit_breaker preservados
"""
from __future__ import annotations

import sqlite3
import tempfile
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _create_test_db(tmp_path: str) -> str:
    """Cria banco in-memory em arquivo temporario com schema minimo."""
    db_path = os.path.join(tmp_path, "test_m2_023_6.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE signal_executions (
            id INTEGER PRIMARY KEY,
            decision_id INTEGER,
            symbol TEXT,
            timeframe TEXT,
            failure_reason TEXT,
            gate_reason TEXT,
            status TEXT,
            created_at INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE signal_execution_events (
            id INTEGER PRIMARY KEY,
            signal_execution_id INTEGER,
            event_type TEXT,
            from_status TEXT,
            to_status TEXT,
            event_timestamp INTEGER,
            rule_id TEXT,
            payload_json TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db_path


def _seed_risk_gate_block(
    db_path: str,
    decision_id: int,
    symbol: str = "BTCUSDT",
    reason: str = "risk_gate_blocked",
    payload: str = '{"guardrails": {"risk_gate_status": "BLOCKED"}}',
) -> None:
    """Insere um bloqueio de risk_gate no DB de teste."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO signal_executions
        (decision_id, symbol, timeframe, failure_reason, gate_reason, status, created_at)
        VALUES (?, ?, 'H4', ?, ?, 'FAILED', 1700000000000)
    """, (decision_id, symbol, reason, reason))
    exec_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("""
        INSERT INTO signal_execution_events
        (signal_execution_id, event_type, from_status, to_status,
         event_timestamp, rule_id, payload_json)
        VALUES (?, 'FAILED', 'PENDING', 'FAILED', 1700000000000, 'M2-009-3', ?)
    """, (exec_id, payload))
    conn.commit()
    conn.close()


# RF-023.6.2: Consulta por decision_id retorna trilha ponta a ponta
def test_build_audit_trail_retorna_trilha_por_decision_id() -> None:
    """RF-023.6.2: funcao retorna lista com entradas para decision_id."""
    from core.model2.resilience_controls import build_risk_gate_audit_trail

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _create_test_db(tmp)
        _seed_risk_gate_block(db_path, decision_id=42)

        trail = build_risk_gate_audit_trail(db_path=db_path, decision_id=42)

        assert isinstance(trail, list)
        assert len(trail) == 1
        assert trail[0]["decision_id"] == 42


# RF-023.6.1: Entradas contêm reason_code e symbol
def test_build_audit_trail_contem_reason_code_e_symbol() -> None:
    """RF-023.6.1: cada entrada tem reason_code e symbol."""
    from core.model2.resilience_controls import build_risk_gate_audit_trail

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _create_test_db(tmp)
        _seed_risk_gate_block(db_path, decision_id=55, symbol="ALGOUSDT")

        trail = build_risk_gate_audit_trail(db_path=db_path, decision_id=55)

        assert len(trail) == 1
        entry = trail[0]
        assert entry["reason_code"] == "risk_gate_blocked"
        assert entry["symbol"] == "ALGOUSDT"


# RF-023.6.3: Trilha vazia para decision_id sem bloqueios
def test_build_audit_trail_vazia_para_decision_id_sem_bloqueios() -> None:
    """RF-023.6.3: lista vazia quando nao ha bloqueios para o decision_id."""
    from core.model2.resilience_controls import build_risk_gate_audit_trail

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _create_test_db(tmp)
        _seed_risk_gate_block(db_path, decision_id=100)  # outro decision_id

        trail = build_risk_gate_audit_trail(db_path=db_path, decision_id=999)

        assert trail == []


# RF-023.6.4: Fail-safe com DB inexistente
def test_build_audit_trail_failsafe_db_ausente() -> None:
    """RF-023.6.4: retorna lista vazia sem excecao quando DB nao existe."""
    from core.model2.resilience_controls import build_risk_gate_audit_trail

    trail = build_risk_gate_audit_trail(
        db_path="/tmp/inexistente_m2_023_6_test.db",
        decision_id=1,
    )

    assert trail == []


# RF-023.6.5: Campos obrigatórios presentes
def test_build_audit_trail_campos_obrigatorios() -> None:
    """RF-023.6.5: entradas contem todos os campos obrigatorios."""
    from core.model2.resilience_controls import build_risk_gate_audit_trail

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _create_test_db(tmp)
        _seed_risk_gate_block(db_path, decision_id=77)

        trail = build_risk_gate_audit_trail(db_path=db_path, decision_id=77)

        assert len(trail) == 1
        entry = trail[0]
        obrigatorios = {"execution_id", "decision_id", "reason_code", "symbol", "timestamp_ms"}
        for campo in obrigatorios:
            assert campo in entry, f"Campo obrigatorio ausente: {campo}"


# RF-023.6.6: Múltiplos bloqueios para mesmo decision_id
def test_build_audit_trail_multiplos_bloqueios() -> None:
    """RF-023.6.6: todos os bloqueios para o decision_id sao retornados."""
    from core.model2.resilience_controls import build_risk_gate_audit_trail

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _create_test_db(tmp)
        _seed_risk_gate_block(db_path, decision_id=88, symbol="BTCUSDT")
        _seed_risk_gate_block(db_path, decision_id=88, symbol="BTCUSDT")

        trail = build_risk_gate_audit_trail(db_path=db_path, decision_id=88)

        assert len(trail) == 2


# RF-023.6.7: Regressão de guardrails
def test_build_audit_trail_guardrails_preservados() -> None:
    """RF-023.6.7: importar e chamar funcao nao altera risk_gate nem CB."""
    from risk import risk_gate, circuit_breaker
    from core.model2.resilience_controls import build_risk_gate_audit_trail

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _create_test_db(tmp)
        build_risk_gate_audit_trail(db_path=db_path, decision_id=1)

    assert hasattr(risk_gate, "RiskGate") or hasattr(risk_gate, "evaluate")
    assert hasattr(circuit_breaker, "CircuitBreaker")
