"""Suite RED para M2-027.3: OrphanDetector em orphan_guard.py.

Testa:
- Deteccao de posicoes abertas na Binance sem signal_execution correspondente
- Comparacao entre posicoes reais e registros no DB
- Retorno estruturado com lista de orfaos
"""

from __future__ import annotations

import sqlite3
import pytest
from typing import Any
from unittest.mock import MagicMock

# Importacoes RED - modulo ainda nao existe
from core.model2.orphan_guard import OrphanDetector, OrphanDetectionResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_memory() -> sqlite3.Connection:
    """DB em memoria com schema minimo de signal_executions."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE signal_executions (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            status TEXT NOT NULL,
            signal_side TEXT NOT NULL
        );
    """)
    conn.commit()
    return conn


@pytest.fixture
def detector(db_memory: sqlite3.Connection) -> OrphanDetector:
    """OrphanDetector com DB em memoria."""
    return OrphanDetector(db_conn=db_memory)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_orphan_detector_sem_orfaos_quando_posicoes_registradas(
    detector: OrphanDetector,
    db_memory: sqlite3.Connection,
) -> None:
    """Nao deve detectar orfaos quando todas as posicoes tem registro no DB."""
    # Arrange: posicao na Binance com registro correspondente
    db_memory.execute(
        "INSERT INTO signal_executions (id, symbol, status, signal_side) VALUES (1, 'BTCUSDT', 'ENTRY_FILLED', 'SHORT')"
    )
    db_memory.commit()

    posicoes_binance: list[dict[str, Any]] = [
        {"symbol": "BTCUSDT", "direction": "SHORT", "position_size_qty": 0.01}
    ]

    # Act
    resultado: OrphanDetectionResult = detector.detect(binance_positions=posicoes_binance)

    # Assert
    assert resultado.orphan_count == 0
    assert resultado.orphans == []


def test_orphan_detector_detecta_posicao_sem_registro(
    detector: OrphanDetector,
) -> None:
    """Deve detectar posicao aberta na Binance sem signal_execution correspondente."""
    # Arrange: posicao sem registro no DB
    posicoes_binance: list[dict[str, Any]] = [
        {"symbol": "ETHUSDT", "direction": "SHORT", "position_size_qty": 0.5}
    ]

    # Act
    resultado: OrphanDetectionResult = detector.detect(binance_positions=posicoes_binance)

    # Assert
    assert resultado.orphan_count == 1
    assert resultado.orphans[0]["symbol"] == "ETHUSDT"


def test_orphan_detector_multiplas_posicoes_parte_orfas(
    detector: OrphanDetector,
    db_memory: sqlite3.Connection,
) -> None:
    """Deve identificar corretamente apenas as posicoes sem registro."""
    # Arrange
    db_memory.execute(
        "INSERT INTO signal_executions (id, symbol, status, signal_side) VALUES (1, 'BTCUSDT', 'ENTRY_FILLED', 'SHORT')"
    )
    db_memory.commit()

    posicoes_binance: list[dict[str, Any]] = [
        {"symbol": "BTCUSDT", "direction": "SHORT", "position_size_qty": 0.01},
        {"symbol": "SOLUSDT", "direction": "LONG", "position_size_qty": 10.0},
    ]

    # Act
    resultado: OrphanDetectionResult = detector.detect(binance_positions=posicoes_binance)

    # Assert
    assert resultado.orphan_count == 1
    simbolos_orfaos = [o["symbol"] for o in resultado.orphans]
    assert "SOLUSDT" in simbolos_orfaos
    assert "BTCUSDT" not in simbolos_orfaos


def test_orphan_detector_ignora_posicoes_zeradas(
    detector: OrphanDetector,
) -> None:
    """Posicoes com quantidade zero nao devem ser consideradas orfas."""
    posicoes_binance: list[dict[str, Any]] = [
        {"symbol": "ADAUSDT", "direction": "SHORT", "position_size_qty": 0.0}
    ]

    resultado: OrphanDetectionResult = detector.detect(binance_positions=posicoes_binance)

    assert resultado.orphan_count == 0


def test_orphan_detector_resultado_contem_timestamp(
    detector: OrphanDetector,
) -> None:
    """OrphanDetectionResult deve incluir timestamp da deteccao."""
    posicoes_binance: list[dict[str, Any]] = []
    resultado: OrphanDetectionResult = detector.detect(binance_positions=posicoes_binance)
    assert hasattr(resultado, "detected_at_ms")
    assert isinstance(resultado.detected_at_ms, int)
    assert resultado.detected_at_ms > 0


def test_orphan_detector_considera_apenas_status_ativos(
    detector: OrphanDetector,
    db_memory: sqlite3.Connection,
) -> None:
    """Execucoes em status terminal (EXITED, CANCELLED) nao contam como registro ativo."""
    # Arrange: execucao encerrada
    db_memory.execute(
        "INSERT INTO signal_executions (id, symbol, status, signal_side) VALUES (1, 'BNBUSDT', 'EXITED', 'SHORT')"
    )
    db_memory.commit()

    posicoes_binance: list[dict[str, Any]] = [
        {"symbol": "BNBUSDT", "direction": "SHORT", "position_size_qty": 1.0}
    ]

    # Act
    resultado: OrphanDetectionResult = detector.detect(binance_positions=posicoes_binance)

    # Assert: EXITED = sem cobertura ativa, posicao e considerada orfa
    assert resultado.orphan_count == 1
