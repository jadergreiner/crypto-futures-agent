"""Suite RED/GREEN para BLID-104 - Linha Promocao no status operacional M2.

Cobre:
    RF-104.1 - Linha Promocao presente no bloco por simbolo
    RF-104.2 - GO quando risco, estabilidade e consistencia ok
    RF-104.3 - NO_GO quando circuit_breaker nao esta normal
    RF-104.4 - NO_GO quando candles nao estao frescos
    RF-104.5 - Fail-safe: nenhuma excecao propagada mesmo com dados ausentes
    RF-104.6 - Regressao de risco: risk_gate e circuit_breaker preservados
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Any

# Adicionar root ao sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.operator_cycle_status import (
    _build_promotion_readiness_line,
    TimeframeCandleStatus,
)


def _make_tf_status(state: str, timeframe: str = "H4") -> TimeframeCandleStatus:
    """Cria TimeframeCandleStatus para testes."""
    return TimeframeCandleStatus(
        timeframe=timeframe,
        display_time="2026-04-03 12:00:00",
        scan_count=10,
        persisted_count=10,
        state=state,
    )


def _make_risk_state(cb_state: str = "normal", rg_status: str = "ok") -> dict[str, Any]:
    return {
        "circuit_breaker_state": cb_state,
        "risk_gate_status": rg_status,
        "short_only": False,
        "recent_entries_today": 0,
        "max_daily_entries": 3,
    }


# RF-104.1: Linha Promocao presente no resultado
def test_promotion_line_presente() -> None:
    """RF-104.1: funcao retorna string nao vazia."""
    tf_statuses = [
        _make_tf_status("fresh", "D1"),
        _make_tf_status("fresh", "H4"),
        _make_tf_status("fresh", "H1"),
        _make_tf_status("fresh", "M5"),
    ]
    risk_state = _make_risk_state()
    result = _build_promotion_readiness_line(
        symbol="BTCUSDT",
        risk_state=risk_state,
        tf_statuses=tf_statuses,
    )
    assert isinstance(result, str)
    assert len(result) > 0


# RF-104.2: GO quando todos os pilares ok
def test_promotion_go_quando_tudo_ok() -> None:
    """RF-104.2: GO exibe [PRONTO PARA PROMOCAO]."""
    tf_statuses = [
        _make_tf_status("fresh", "D1"),
        _make_tf_status("fresh", "H4"),
        _make_tf_status("fresh", "H1"),
        _make_tf_status("fresh", "M5"),
    ]
    risk_state = _make_risk_state(cb_state="normal", rg_status="ok")
    result = _build_promotion_readiness_line(
        symbol="BTCUSDT",
        risk_state=risk_state,
        tf_statuses=tf_statuses,
    )
    assert "GO" in result
    assert "PRONTO" in result or "PROMOCAO" in result


# RF-104.3: NO_GO quando circuit_breaker nao esta normal
def test_promotion_no_go_circuit_breaker_trancado() -> None:
    """RF-104.3: NO_GO quando CB nao esta normal."""
    tf_statuses = [
        _make_tf_status("fresh", "H4"),
        _make_tf_status("fresh", "H1"),
    ]
    risk_state = _make_risk_state(cb_state="trancado")
    result = _build_promotion_readiness_line(
        symbol="BTCUSDT",
        risk_state=risk_state,
        tf_statuses=tf_statuses,
    )
    assert "NO_GO" in result


# RF-104.4: NO_GO quando candles nao estao frescos
def test_promotion_no_go_candles_stale() -> None:
    """RF-104.4: NO_GO quando todos os candles estao stale."""
    tf_statuses = [
        _make_tf_status("stale", "H4"),
        _make_tf_status("stale", "H1"),
        _make_tf_status("absent", "M5"),
    ]
    risk_state = _make_risk_state()
    result = _build_promotion_readiness_line(
        symbol="ALGOUSDT",
        risk_state=risk_state,
        tf_statuses=tf_statuses,
    )
    assert "NO_GO" in result


# RF-104.5: Fail-safe com risk_state None
def test_promotion_failsafe_risk_state_none() -> None:
    """RF-104.5: nenhuma excecao quando risk_state e None."""
    tf_statuses = [_make_tf_status("fresh", "H4")]
    try:
        result = _build_promotion_readiness_line(
            symbol="XRPUSDT",
            risk_state=None,
            tf_statuses=tf_statuses,
        )
        assert isinstance(result, str)
    except Exception as exc:
        raise AssertionError(f"Excecao nao esperada: {exc}") from exc


# RF-104.5b: Fail-safe com tf_statuses vazio
def test_promotion_failsafe_tf_statuses_vazio() -> None:
    """RF-104.5b: nenhuma excecao quando tf_statuses e lista vazia."""
    risk_state = _make_risk_state()
    try:
        result = _build_promotion_readiness_line(
            symbol="SOLUSDT",
            risk_state=risk_state,
            tf_statuses=[],
        )
        assert isinstance(result, str)
    except Exception as exc:
        raise AssertionError(f"Excecao nao esperada: {exc}") from exc


# RF-104.6: Regressao de risco - risk_gate e circuit_breaker preservados
def test_promotion_nao_altera_guardrails() -> None:
    """RF-104.6: importar e chamar a funcao nao altera risk_gate nem CB."""
    from risk import risk_gate, circuit_breaker

    tf_statuses = [_make_tf_status("fresh", "H4")]
    risk_state = _make_risk_state()

    _build_promotion_readiness_line(
        symbol="BTCUSDT",
        risk_state=risk_state,
        tf_statuses=tf_statuses,
    )

    # Guardrails devem permanecer importaveis e funcionais
    assert hasattr(risk_gate, "RiskGate") or hasattr(risk_gate, "evaluate")
    assert hasattr(circuit_breaker, "CircuitBreaker")
