"""Testes para M2-028.5 — Gate de Correlacao de Portfolio."""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from core.model2.correlation_gate import CorrelationGate, CorrelationGateDecision
from core.model2.live_execution import REASON_CODE_CATALOG
from core.model2.order_layer import (
    OrderLayerInput,
    evaluate_signal_for_order_layer,
)

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

_SYMBOLS_CONFIG: dict[str, dict[str, Any]] = {
    "BTCUSDT": {"classificacao": "alta_cap", "correlacao_btc": 1.0},
    "ETHUSDT": {"classificacao": "alta_cap", "correlacao_btc": [0.85, 0.95]},
    "SOLUSDT": {"classificacao": "alta_cap", "correlacao_btc": [0.75, 0.90]},
    "ARBUSDT": {"classificacao": "mid_cap_l2", "correlacao_btc": [0.60, 0.78]},
    "C98USDT": {"classificacao": "low_cap_defi", "correlacao_btc": [0.50, 0.75]},
    "NILSUSDT": {"classificacao": "low_cap_privacy_compute", "correlacao_btc": [0.35, 0.65]},
}


def _criar_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE signal_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            execution_mode TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _inserir_posicao(
    conn: sqlite3.Connection,
    symbol: str,
    mode: str = "live",
    status: str = "ENTRY_FILLED",
) -> None:
    conn.execute(
        "INSERT INTO signal_executions (symbol, execution_mode, status) VALUES (?, ?, ?)",
        (symbol, mode, status),
    )
    conn.commit()


def _criar_gate(conn: sqlite3.Connection, max_per_group: int = 2) -> CorrelationGate:
    return CorrelationGate(
        max_positions_per_corr_group=max_per_group,
        btc_correlation_high_threshold=0.75,
        symbols_config=_SYMBOLS_CONFIG,
        db_conn_factory=lambda: conn,
    )


# ---------------------------------------------------------------------------
# Grupo 1 — Testes unitarios do CorrelationGate
# ---------------------------------------------------------------------------


def test_gate_permite_quando_grupo_vazio() -> None:
    conn = _criar_db()
    gate = _criar_gate(conn)
    assert gate.evaluate(symbol="BTCUSDT", execution_mode="live") is None


def test_gate_permite_quando_grupo_abaixo_do_limite() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT")
    gate = _criar_gate(conn, max_per_group=2)
    # 1 posicao alta_cap aberta; max=2; segundo alta_cap deve passar
    assert gate.evaluate(symbol="ETHUSDT", execution_mode="live") is None


def test_gate_bloqueia_quando_grupo_atinge_limite() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT")
    _inserir_posicao(conn, "ETHUSDT")
    gate = _criar_gate(conn, max_per_group=2)
    decisao = gate.evaluate(symbol="SOLUSDT", execution_mode="live")
    assert decisao is not None
    assert not decisao.allowed


def test_gate_decision_contem_blocked_group_classificacao() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT")
    _inserir_posicao(conn, "ETHUSDT")
    gate = _criar_gate(conn)
    decisao = gate.evaluate(symbol="SOLUSDT", execution_mode="live")
    assert decisao is not None
    assert decisao.blocked_group == "classificacao:alta_cap"


def test_gate_decision_contem_contagem_e_maximo_corretos() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT")
    _inserir_posicao(conn, "ETHUSDT")
    gate = _criar_gate(conn, max_per_group=2)
    decisao = gate.evaluate(symbol="SOLUSDT", execution_mode="live")
    assert decisao is not None
    assert decisao.open_count == 2
    assert decisao.max_per_group == 2


def test_gate_permite_simbolo_de_outra_classificacao() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT")
    _inserir_posicao(conn, "ETHUSDT")
    gate = _criar_gate(conn)
    # NILSUSDT e low_cap_privacy_compute e correlacao_btc max=0.65 < 0.75;
    # deve passar mesmo com 2 alta_cap abertas (grupo diferente e sem alta corr BTC)
    assert gate.evaluate(symbol="NILSUSDT", execution_mode="live") is None


def test_gate_bloqueia_por_correlacao_btc_alta() -> None:
    conn = _criar_db()
    # ARBUSDT tem correlacao_btc max=0.78 >= 0.75 (high BTC)
    _inserir_posicao(conn, "BTCUSDT")
    _inserir_posicao(conn, "ETHUSDT")
    gate = _criar_gate(conn, max_per_group=2)
    decisao = gate.evaluate(symbol="ARBUSDT", execution_mode="live")
    assert decisao is not None
    assert decisao.blocked_group == "btc_correlation_high"


def test_gate_permite_por_correlacao_btc_baixa() -> None:
    conn = _criar_db()
    # NILSUSDT tem correlacao_btc max=0.65 < 0.75 (nao entra no grupo high-BTC)
    _inserir_posicao(conn, "BTCUSDT")
    _inserir_posicao(conn, "ETHUSDT")
    gate = _criar_gate(conn, max_per_group=2)
    # NILSUSDT e low_cap_privacy_compute (nenhuma outra do grupo aberta) e correlacao baixa
    assert gate.evaluate(symbol="NILSUSDT", execution_mode="live") is None


def test_gate_btc_correlation_como_float_simples() -> None:
    """BTCUSDT tem correlacao_btc=1.0 (float, nao lista); deve ser detectado como high-BTC."""
    conn = _criar_db()
    gate = _criar_gate(conn)
    # Verifica que o gate nao lanca excecao ao processar float simples
    resultado = gate.evaluate(symbol="BTCUSDT", execution_mode="live")
    assert resultado is None  # grupo vazio, passa


def test_gate_simbolo_desconhecido_no_config_passa() -> None:
    conn = _criar_db()
    gate = _criar_gate(conn)
    assert gate.evaluate(symbol="XYZUSDT", execution_mode="live") is None


# ---------------------------------------------------------------------------
# Grupo 2 — DB in-memory: contagem e isolamento
# ---------------------------------------------------------------------------


def test_contagem_por_classificacao_com_sqlite_em_memoria() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT", status="ENTRY_FILLED")
    _inserir_posicao(conn, "ETHUSDT", status="PROTECTED")
    gate = _criar_gate(conn, max_per_group=2)
    decisao = gate.evaluate(symbol="SOLUSDT", execution_mode="live")
    assert decisao is not None
    assert not decisao.allowed
    assert decisao.open_count == 2


def test_contagem_ignora_status_inativo() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT", status="EXITED")
    _inserir_posicao(conn, "ETHUSDT", status="CANCELLED")
    gate = _criar_gate(conn, max_per_group=2)
    assert gate.evaluate(symbol="SOLUSDT", execution_mode="live") is None


def test_contagem_respeita_execution_mode() -> None:
    conn = _criar_db()
    # 2 posicoes shadow abertas; avaliacao em mode=live nao deve ver
    _inserir_posicao(conn, "BTCUSDT", mode="shadow")
    _inserir_posicao(conn, "ETHUSDT", mode="shadow")
    gate = _criar_gate(conn, max_per_group=2)
    assert gate.evaluate(symbol="SOLUSDT", execution_mode="live") is None


def test_contagem_nao_duplica_mesmo_simbolo() -> None:
    """Duas linhas para o mesmo simbolo devem ser contadas como 1 (COUNT DISTINCT)."""
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT", status="READY")
    _inserir_posicao(conn, "BTCUSDT", status="ENTRY_FILLED")
    gate = _criar_gate(conn, max_per_group=2)
    # Apenas 1 simbolo distinto aberto; nao deve bloquear ETHUSDT
    assert gate.evaluate(symbol="ETHUSDT", execution_mode="live") is None


# ---------------------------------------------------------------------------
# Grupo 3 — Integracao com order_layer
# ---------------------------------------------------------------------------

def _input_valido(symbol: str = "BTCUSDT", payload: dict[str, Any] | None = None) -> OrderLayerInput:
    return OrderLayerInput(
        signal_id=1,
        opportunity_id=1,
        symbol=symbol,
        timeframe="M5",
        signal_side="LONG",
        entry_type="MARKET",
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        status="CREATED",
        signal_timestamp=1_700_000_000_000,
        payload=payload or {"execution_mode": "live"},
        decision_timestamp=1_700_000_001_000,
        decision_id=None,
    )


def test_correlation_gate_none_nao_ativa_bloqueio() -> None:
    resultado = evaluate_signal_for_order_layer(
        _input_valido(),
        authorized_symbols={"BTCUSDT"},
        correlation_gate=None,
    )
    assert resultado.target_status == "CONSUMED"


def test_correlation_gate_bloqueado_cancela_sinal() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT")
    _inserir_posicao(conn, "ETHUSDT")
    gate = _criar_gate(conn, max_per_group=2)
    resultado = evaluate_signal_for_order_layer(
        _input_valido(symbol="SOLUSDT"),
        authorized_symbols={"SOLUSDT"},
        correlation_gate=gate,
    )
    assert not resultado.should_transition
    assert resultado.target_status == "CANCELLED"


def test_correlation_gate_bloqueado_contem_detalhes() -> None:
    conn = _criar_db()
    _inserir_posicao(conn, "BTCUSDT")
    _inserir_posicao(conn, "ETHUSDT")
    gate = _criar_gate(conn, max_per_group=2)
    resultado = evaluate_signal_for_order_layer(
        _input_valido(symbol="SOLUSDT"),
        authorized_symbols={"SOLUSDT"},
        correlation_gate=gate,
    )
    assert resultado.details["reason_code"] == "portfolio_correlation_limit"
    assert "blocked_group" in resultado.details
    assert resultado.details["open_count"] == 2


def test_correlation_gate_passa_sinal_para_consumed() -> None:
    conn = _criar_db()
    gate = _criar_gate(conn)
    resultado = evaluate_signal_for_order_layer(
        _input_valido(),
        authorized_symbols={"BTCUSDT"},
        correlation_gate=gate,
    )
    assert resultado.target_status == "CONSUMED"


def test_reason_code_no_catalogo() -> None:
    assert "portfolio_correlation_limit" in REASON_CODE_CATALOG
