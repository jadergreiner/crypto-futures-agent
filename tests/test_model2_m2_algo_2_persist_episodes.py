"""Suite RED — M2-ALGO.2: Persistir episodios para retreino incremental de ALGOUSDT.

Testa fallback de candle OHLCV em model2_db quando source_db nao tem dados
para simbolos bootstrapados (ex: ALGOUSDT). Todos os testes devem falhar
antes da implementacao da correcao em persist_training_episodes.py.

Cobertura de requisitos:
- RF-ALGO.2.1: flush_deferred_rewards usa model2_db como fallback de candle
- RF-ALGO.2.2: _latest_candle aceita fallback_conn opcional
- RF-ALGO.2.3: episodios transitam de label='pending' para hold_correct/missed
- RF-ALGO.2.4: collect_training_info_for_symbol conta episodios apos flush
- RF-ALGO.2.5: BTCUSDT e demais simbolos nao sao afetados pelo fallback
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pytest

from scripts.model2.persist_training_episodes import (
    _latest_candle,
    flush_deferred_rewards,
    _ensure_training_episodes_table,
)
from core.model2.cycle_report import collect_training_info_for_symbol


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

_NOW_MS = 1_775_100_000_000  # timestamp fixo para testes
_EVENT_TS = _NOW_MS - 600_000  # 10 min antes
_LOOKUP_TS = _NOW_MS - 300_000  # 5 min antes (dentro da janela)
_CANDLE_TS = _LOOKUP_TS - 1  # candle dentro da janela de lookup


def _make_source_db(
    *,
    symbol: str | None = None,
    close: float = 0.8,
    ts: int = _CANDLE_TS,
) -> sqlite3.Connection:
    """Cria source_db em memoria, com ou sem candle ohlcv_m5."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE ohlcv_m5 (
            timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL
        )
        """
    )
    if symbol is not None:
        conn.execute(
            "INSERT INTO ohlcv_m5 (timestamp, symbol, open, high, low, close, volume)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, symbol, close, close, close, close, 1000.0),
        )
    conn.commit()
    return conn


def _make_model2_db(
    *,
    symbol: str | None = None,
    close: float = 0.82,
    ts: int = _CANDLE_TS,
    with_episode: bool = False,
    episode_symbol: str = "ALGOUSDT",
    close_t: float = 0.80,
) -> sqlite3.Connection:
    """Cria model2_db em memoria com tabela ohlcv_m5 e training_episodes."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE ohlcv_m5 (
            timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL
        )
        """
    )
    if symbol is not None:
        conn.execute(
            "INSERT INTO ohlcv_m5 (timestamp, symbol, open, high, low, close, volume)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, symbol, close, close, close, close, 1000.0),
        )
    _ensure_training_episodes_table(conn)
    if with_episode:
        features = json.dumps(
            {"close_t": close_t, "signal_side": "NEUTRAL"}, ensure_ascii=True
        )
        conn.execute(
            """
            INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, reward_source,
                reward_lookup_at_ms, features_json, target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"hold_decision:1:{_EVENT_TS}",
                "test-run",
                0,
                episode_symbol,
                "M5",
                "HOLD_DECISION",
                _EVENT_TS,
                "pending",
                None,
                "none",
                _LOOKUP_TS,
                features,
                "{}",
                _EVENT_TS,
            ),
        )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# RF-ALGO.2.1 — flush usa model2_db como fallback quando source_db e vazio
# ---------------------------------------------------------------------------

def test_flush_deferred_rewards_algousdt_usa_model2_fallback_quando_source_vazio(
    tmp_path: Path,
) -> None:
    """flush_deferred_rewards deve preencher reward_proxy para ALGOUSDT M5
    usando candle de model2_db quando source_db nao tem o candle.

    Cobre: RF-ALGO.2.1
    """
    # Arrange: source_db SEM candle de ALGOUSDT; model2_db COM candle
    source_db = tmp_path / "source.db"
    model2_db = tmp_path / "model2.db"

    src_conn = _make_source_db(symbol=None)  # vazio
    m2_conn = _make_model2_db(
        symbol="ALGOUSDT",
        close=0.82,
        ts=_CANDLE_TS,
        with_episode=True,
        episode_symbol="ALGOUSDT",
        close_t=0.80,
    )
    # Persiste DBs em arquivo para flush_deferred_rewards (usa paths)
    with sqlite3.connect(source_db) as sc:
        for line in src_conn.iterdump():
            sc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        sc.commit()
    with sqlite3.connect(model2_db) as mc:
        for line in m2_conn.iterdump():
            mc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        mc.commit()

    # Act
    result = flush_deferred_rewards(
        model2_db_path=model2_db,
        source_db_path=source_db,
        now_ms=_NOW_MS,
    )

    # Assert: deve ter feito flush, nao ficado como pendente
    assert result["flushed"] == 1, (
        f"Esperado flushed=1, obtido: {result}. "
        "flush_deferred_rewards nao usa model2_db como fallback."
    )
    assert result["pending"] == 0, (
        f"Esperado pending=0, obtido: {result}"
    )
    # reward_proxy deve ter sido preenchido no DB
    with sqlite3.connect(model2_db) as mc:
        row = mc.execute(
            "SELECT reward_proxy, label FROM training_episodes WHERE symbol='ALGOUSDT'"
        ).fetchone()
    assert row is not None
    assert row[0] is not None, "reward_proxy permanece NULL apos flush com fallback"
    assert row[1] not in ("pending", "context"), f"label invalido: {row[1]}"


# ---------------------------------------------------------------------------
# RF-ALGO.2.5 — BTCUSDT com candle em source_db nao ativa fallback
# ---------------------------------------------------------------------------

def test_flush_deferred_rewards_btcusdt_nao_usa_fallback_quando_source_tem_candle(
    tmp_path: Path,
) -> None:
    """flush_deferred_rewards nao deve alterar comportamento para BTCUSDT
    quando source_db ja tem o candle M5 necessario.

    Cobre: RF-ALGO.2.5
    """
    # Arrange: source_db COM candle de BTCUSDT; model2_db SEM candle M5
    source_db = tmp_path / "source.db"
    model2_db = tmp_path / "model2.db"

    src_conn = _make_source_db(symbol="BTCUSDT", close=65000.0, ts=_CANDLE_TS)
    m2_conn = _make_model2_db(
        symbol=None,  # sem candle M5 de BTCUSDT no model2
        with_episode=True,
        episode_symbol="BTCUSDT",
        close_t=64500.0,
    )

    with sqlite3.connect(source_db) as sc:
        for line in src_conn.iterdump():
            sc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        sc.commit()
    with sqlite3.connect(model2_db) as mc:
        for line in m2_conn.iterdump():
            mc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        mc.commit()

    # Act
    result = flush_deferred_rewards(
        model2_db_path=model2_db,
        source_db_path=source_db,
        now_ms=_NOW_MS,
    )

    # Assert: deve flush normalmente usando source_db
    assert result["flushed"] == 1, (
        f"Esperado flushed=1 para BTCUSDT com candle em source_db, obtido: {result}"
    )
    assert result["pending"] == 0


# ---------------------------------------------------------------------------
# RF-ALGO.2.1 (negativo) — nenhum DB tem candle -> deve ficar pendente
# ---------------------------------------------------------------------------

def test_flush_deferred_rewards_pendente_quando_nenhum_db_tem_candle(
    tmp_path: Path,
) -> None:
    """Quando source_db e model2_db nao tem candle, episodio deve ficar
    com reward_proxy=NULL e pending=1.

    Cobre: RF-ALGO.2.1 (falha segura)
    """
    # Arrange: ambos sem candle M5
    source_db = tmp_path / "source.db"
    model2_db = tmp_path / "model2.db"

    src_conn = _make_source_db(symbol=None)
    m2_conn = _make_model2_db(symbol=None, with_episode=True, episode_symbol="ALGOUSDT")

    with sqlite3.connect(source_db) as sc:
        for line in src_conn.iterdump():
            sc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        sc.commit()
    with sqlite3.connect(model2_db) as mc:
        for line in m2_conn.iterdump():
            mc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        mc.commit()

    # Act
    result = flush_deferred_rewards(
        model2_db_path=model2_db,
        source_db_path=source_db,
        now_ms=_NOW_MS,
    )

    # Assert: deve permanecer pendente, sem erro
    assert result["flushed"] == 0
    assert result["pending"] == 1, (
        f"Esperado pending=1 quando nenhum DB tem candle, obtido: {result}"
    )
    with sqlite3.connect(model2_db) as mc:
        row = mc.execute(
            "SELECT reward_proxy FROM training_episodes WHERE symbol='ALGOUSDT'"
        ).fetchone()
    assert row is not None
    assert row[0] is None, "reward_proxy nao deveria ser preenchido sem candle disponivel"


# ---------------------------------------------------------------------------
# RF-ALGO.2.2 — _latest_candle aceita fallback_conn
# ---------------------------------------------------------------------------

def test_latest_candle_fallback_retorna_model2_quando_source_vazio() -> None:
    """_latest_candle deve retornar candle de fallback_conn quando conn
    principal nao tem dados para o simbolo.

    Cobre: RF-ALGO.2.2
    """
    # Arrange
    src_conn = _make_source_db(symbol=None)  # sem ALGOUSDT
    m2_conn = _make_model2_db(symbol="ALGOUSDT", close=0.82, ts=_CANDLE_TS)

    # Act — fallback_conn e parametro novo a ser implementado
    result = _latest_candle(src_conn, "ALGOUSDT", "M5", fallback_conn=m2_conn)

    # Assert
    assert result is not None, (
        "_latest_candle retornou None mesmo com fallback_conn populado. "
        "Parametro fallback_conn ainda nao implementado."
    )
    assert abs(result["close"] - 0.82) < 1e-6, (
        f"Valor close incorreto: {result['close']} != 0.82"
    )


# ---------------------------------------------------------------------------
# RF-ALGO.2.2 (retrocompatibilidade) — sem fallback, comportamento atual
# ---------------------------------------------------------------------------

def test_latest_candle_sem_fallback_retorna_none_quando_source_vazio() -> None:
    """_latest_candle sem fallback_conn deve retornar None quando source_conn
    nao tem dados (comportamento atual preservado).

    Cobre: RF-ALGO.2.2 (retrocompatibilidade)
    """
    # Arrange
    src_conn = _make_source_db(symbol=None)

    # Act — chamada sem fallback_conn (assinatura atual)
    result = _latest_candle(src_conn, "ALGOUSDT", "M5")

    # Assert
    assert result is None, (
        f"Esperado None sem fallback_conn, obtido: {result}"
    )


# ---------------------------------------------------------------------------
# RF-ALGO.2.2 — _latest_candle nao usa fallback quando source tem dados
# ---------------------------------------------------------------------------

def test_latest_candle_usa_source_quando_disponivel_ignora_fallback() -> None:
    """_latest_candle deve retornar candle de conn principal (source) mesmo
    quando fallback_conn esta populado. Source tem prioridade.

    Cobre: RF-ALGO.2.2 (prioridade de source_db)
    """
    # Arrange: source COM ALGOUSDT close=0.80; model2 COM ALGOUSDT close=0.99
    src_conn = _make_source_db(symbol="ALGOUSDT", close=0.80, ts=_CANDLE_TS)
    m2_conn = _make_model2_db(symbol="ALGOUSDT", close=0.99, ts=_CANDLE_TS + 1)

    # Act
    result = _latest_candle(src_conn, "ALGOUSDT", "M5", fallback_conn=m2_conn)

    # Assert: deve retornar valor de source (0.80), nao do fallback (0.99)
    assert result is not None
    assert abs(result["close"] - 0.80) < 1e-6, (
        f"Esperado close=0.80 de source_db, obtido: {result['close']}"
    )


# ---------------------------------------------------------------------------
# RF-ALGO.2.1 (close_t fallback) — close_t zero usa model2_db
# ---------------------------------------------------------------------------

def test_flush_deferred_rewards_close_t_zero_usa_model2_fallback(
    tmp_path: Path,
) -> None:
    """flush_deferred_rewards deve buscar close_t base em model2_db quando
    features_json.close_t=0.0 e source_db nao tem o candle base.

    Cobre: RF-ALGO.2.1 (fallback close_t)
    """
    # Arrange: episode com close_t=0.0; source vazio; model2 com candle base
    source_db = tmp_path / "source.db"
    model2_db = tmp_path / "model2.db"

    src_conn = _make_source_db(symbol=None)
    m2_conn = _make_model2_db(
        symbol="ALGOUSDT",
        close=0.80,
        ts=_EVENT_TS - 1,   # candle base (antes do evento)
        with_episode=True,
        episode_symbol="ALGOUSDT",
        close_t=0.0,          # close_t invalido — deve buscar fallback
    )
    # Adiciona candle de lookup no model2_db
    m2_conn.execute(
        "INSERT INTO ohlcv_m5 (timestamp, symbol, open, high, low, close, volume)"
        " VALUES (?, 'ALGOUSDT', 0.82, 0.82, 0.82, 0.82, 1000.0)",
        (_CANDLE_TS,),
    )
    m2_conn.commit()

    with sqlite3.connect(source_db) as sc:
        for line in src_conn.iterdump():
            sc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        sc.commit()
    with sqlite3.connect(model2_db) as mc:
        for line in m2_conn.iterdump():
            mc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        mc.commit()

    # Act
    result = flush_deferred_rewards(
        model2_db_path=model2_db,
        source_db_path=source_db,
        now_ms=_NOW_MS,
    )

    # Assert: com close_t recuperado via fallback, reward deve ser calculado
    assert result["flushed"] == 1, (
        f"Esperado flushed=1 apos fallback close_t, obtido: {result}"
    )


# ---------------------------------------------------------------------------
# RF-ALGO.2.4 — collect_training_info_for_symbol conta apos flush
# ---------------------------------------------------------------------------

def test_collect_training_info_for_symbol_conta_pendentes_apos_flush(
    tmp_path: Path,
) -> None:
    """Apos flush com fallback, collect_training_info_for_symbol deve retornar
    pending >= 1 para ALGOUSDT (episodio elegivel com reward_proxy preenchido).

    Cobre: RF-ALGO.2.4
    """
    # Arrange
    model2_db = tmp_path / "model2.db"
    source_db = tmp_path / "source.db"

    src_conn = _make_source_db(symbol=None)
    m2_conn = _make_model2_db(
        symbol="ALGOUSDT",
        close=0.82,
        ts=_CANDLE_TS,
        with_episode=True,
        episode_symbol="ALGOUSDT",
        close_t=0.80,
    )
    with sqlite3.connect(source_db) as sc:
        for line in src_conn.iterdump():
            sc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        sc.commit()
    with sqlite3.connect(model2_db) as mc:
        for line in m2_conn.iterdump():
            mc.execute(line) if line not in ("BEGIN;", "COMMIT;") else None
        mc.commit()

    # Act: flush com fallback deve preencher reward_proxy
    flush_result = flush_deferred_rewards(
        model2_db_path=model2_db,
        source_db_path=source_db,
        now_ms=_NOW_MS,
    )
    assert flush_result["flushed"] == 1, (
        f"Pre-condicao falhou — flush nao ocorreu: {flush_result}"
    )

    # collect_training_info_for_symbol usa cutoff=0 (nenhum treino anterior)
    _last_train, pending = collect_training_info_for_symbol(
        str(model2_db),
        symbol="ALGOUSDT",
        timeframe="M5",
    )

    # Assert: episodio elegivel contado
    assert pending >= 1, (
        f"collect_training_info_for_symbol retornou pending={pending} "
        f"para ALGOUSDT apos flush. Episodio nao conta como elegivel."
    )
