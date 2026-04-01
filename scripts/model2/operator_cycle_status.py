#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
"""Resumo operacional por simbolo para cada ciclo M2."""

import argparse
import io
import json
import os
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, cast

# Forçar UTF-8 no stdout para suportar emojis e caracteres Unicode no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adicionar root do repositório ao sys.path para importações
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.model2.time_utils import now_brt_str, posix_to_brt_str, ts_ms_to_brt_str
from core.model2.io_retry import read_json_with_retry
from core.model2.cycle_report import (
    DEFAULT_REPORT_FRESHNESS_WINDOW_MS,
    SymbolReport,
    collect_training_info,
    collect_training_info_for_symbol,
    format_symbol_report,
    resolve_training_cutoff_ms,
    resolve_retrain_threshold,
    resolve_candle_freshness_contract,
)
from core.model2.training_audit import summarize_training_audit_window
from config.settings import M2_EXECUTION_MODE

try:
    from data.binance_client import create_binance_client
    from core.model2.live_exchange import Model2LiveExchange
    _EXCHANGE_AVAILABLE = True
except Exception:
    _EXCHANGE_AVAILABLE = False

try:
    from config.settings import M2_SYMBOLS, _normalize_symbol_scope
except Exception:
    M2_SYMBOLS = ("BTCUSDT",)

    def _normalize_symbol_scope(
        raw_value: str | None,
        *,
        fallback_symbols: Iterable[str],
    ) -> tuple[str, ...]:
        fallback_list = [str(s).strip().upper() for s in fallback_symbols if str(s).strip()]
        if raw_value is None:
            return ()
        placeholder_tokens = {
            "M2_SYMBOLS", "M2_SYMBOLS:", "M2_LIVE_SYMBOLS", "M2_LIVE_SYMBOLS:",
            "ALL_SYMBOLS", "ALL_SYMBOLS:",
        }
        normalized: list[str] = []
        for token in str(raw_value).split(","):
            symbol = str(token).strip().upper()
            if not symbol:
                continue
            if symbol in placeholder_tokens:
                normalized.extend(fallback_list)
                continue
            normalized.append(symbol)
        return tuple(dict.fromkeys(normalized))


# ---------------------------------------------------------------------------
# Helpers de artefatos JSON
# ---------------------------------------------------------------------------

def _load_latest_json(runtime_dir: Path, prefix: str, max_age_seconds: int) -> dict[str, Any] | None:
    files = sorted(runtime_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    newest = files[0]
    age = (datetime.now(timezone.utc).timestamp() - newest.stat().st_mtime)
    if age > max_age_seconds:
        return None
    result = read_json_with_retry(str(newest), fail_safe=True)
    if not result or not isinstance(result, dict):
        return None
    return result


def _load_latest_json_by_timeframe(
    runtime_dir: Path, prefix: str, timeframe: str, max_age_seconds: int
) -> dict[str, Any] | None:
    """Carrega o JSON mais recente de um prefix filtrado pelo timeframe."""
    files = sorted(runtime_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        age = (datetime.now(timezone.utc).timestamp() - f.stat().st_mtime)
        if age > max_age_seconds:
            break  # Ordenados por mtime, os mais velhos não precisam ser checados
        result = read_json_with_retry(str(f), fail_safe=True)
        if not result or not isinstance(result, dict):
            continue
        if str(result.get("timeframe", "")).upper() == timeframe.upper():
            return result
    return None


# ---------------------------------------------------------------------------
# Helpers de checkpoint / último treino
# ---------------------------------------------------------------------------

def _checkpoint_aliases(path: Path) -> list[Path]:
    candidates = [path]
    if path.suffix:
        return candidates
    candidates.append(path.with_suffix(".zip"))
    candidates.append(path.with_suffix(".pkl"))
    return candidates


def _get_last_train_time_from_checkpoint() -> str:
    """Fallback: mtime do checkpoint mais recente."""
    candidates = [
        REPO_ROOT / "checkpoints" / "ppo_training" / "ppo_model.zip",
        REPO_ROOT / "checkpoints" / "ppo_training" / "ppo_model.pkl",
        REPO_ROOT / "checkpoints" / "ppo_training" / "best_model.zip",
        REPO_ROOT / "checkpoints" / "ppo_training" / "best_model.pkl",
        REPO_ROOT / "checkpoints" / "ppo_training" / "mlp" / "optuna" / "ppo_mlp_e8_optuna.zip",
        REPO_ROOT / "checkpoints" / "ppo_training" / "mlp" / "ppo_model_mlp.zip",
        REPO_ROOT / "models" / "ppo_model.zip",
        REPO_ROOT / "models" / "ppo_model.pkl",
    ]
    latest_time = 0.0
    for path in candidates:
        for alias in _checkpoint_aliases(path):
            if alias.exists():
                t = alias.stat().st_mtime
                if t > latest_time:
                    latest_time = t
    return posix_to_brt_str(latest_time) if latest_time > 0.0 else "N/A"


def _get_last_train_time_from_symbol_checkpoint(symbol: str) -> str:
    """Fallback para mtime do checkpoint dedicado do símbolo."""
    normalized_symbol = str(symbol).strip().upper()
    if not normalized_symbol:
        return "N/A"

    latest_time = 0.0
    candidates = [
        REPO_ROOT / "models" / "sub_agents" / f"{normalized_symbol}_entry_ppo.zip",
        REPO_ROOT / "models" / "sub_agents" / f"{normalized_symbol}_ppo.zip",
    ]
    for path in candidates:
        for alias in _checkpoint_aliases(path):
            if alias.exists():
                latest_time = max(latest_time, alias.stat().st_mtime)

    if latest_time <= 0.0:
        return "N/A"
    return posix_to_brt_str(latest_time)


# ---------------------------------------------------------------------------
# Helpers de DB
# ---------------------------------------------------------------------------

def _get_model2_db_path() -> str:
    return str(REPO_ROOT / "db" / "modelo2.db")


def _get_legacy_market_db_path() -> str:
    return str(REPO_ROOT / "db" / "crypto_agent.db")


@dataclass(frozen=True)
class TimeframeCandleStatus:
    timeframe: str
    display_time: str
    scan_count: int
    persisted_count: int
    state: str


BLID_101_STATUS_CONTRACT = "BLID-101-v1"


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """Retorna colunas de uma tabela em lowercase; fail-safe retorna set vazio."""
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row[1]).lower() for row in rows}
    except Exception:
        return set()


def _has_table(conn: sqlite3.Connection, table_name: str) -> bool:
    """Indica se tabela existe no schema atual."""
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table_name,),
        ).fetchone()
        return row is not None
    except Exception:
        return False


def _normalize_ts_ms(raw_value: Any) -> int | None:
    """Normaliza timestamp para ms quando possivel."""
    try:
        if raw_value is None:
            return None
        ts = int(raw_value)
        if ts <= 0:
            return None
        if ts < 1_000_000_000_000:
            ts *= 1000
        return ts
    except Exception:
        return None


def _to_int_or_none(raw_value: Any) -> int | None:
    """Converte valor para int quando possivel."""
    try:
        if raw_value is None:
            return None
        return int(raw_value)
    except Exception:
        return None


def _to_float_or_none(raw_value: Any) -> float | None:
    """Converte valor para float quando possivel."""
    try:
        if raw_value is None:
            return None
        return float(raw_value)
    except Exception:
        return None


def _safe_json_loads(raw_value: Any) -> dict[str, Any]:
    """Parse defensivo de JSON para dict."""
    try:
        parsed = json.loads(raw_value or "{}")
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_nested_value(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    """Resolve valor aninhado quando o caminho existir por completo."""
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _normalize_status_source(raw_value: Any) -> str | None:
    """Normaliza origem textual de decisao para o contrato do status."""
    normalized = str(raw_value or "").strip().upper()
    if not normalized:
        return None
    aliases = {
        "RL_MODEL": "RL_MODEL",
        "FALLBACK": "FALLBACK_MODELO_RL",
        "FALLBACK_MODELO_RL": "FALLBACK_MODELO_RL",
        "FALLBACK_MODEL": "FALLBACK_MODELO_RL",
        "FALLBACK_RL": "FALLBACK_MODELO_RL",
    }
    return aliases.get(normalized, normalized)


def _resolve_decision_status_source(
    *,
    reason_code: Any,
    input_json: dict[str, Any],
    output_json: dict[str, Any],
) -> str:
    """Deriva a origem observavel da decisao sem confundir fallbacks."""
    source_paths = (
        ("source",),
        ("origin",),
        ("metadata", "source"),
        ("metadata", "origin"),
        ("decision", "source"),
        ("decision", "origin"),
        ("decision", "metadata", "source"),
        ("decision", "metadata", "origin"),
    )
    for container in (output_json, input_json):
        for path in source_paths:
            normalized = _normalize_status_source(_extract_nested_value(container, path))
            if normalized is not None:
                return normalized

    fallback_paths = (
        ("rl_fallback",),
        ("metadata", "rl_fallback"),
        ("decision", "rl_fallback"),
        ("decision", "metadata", "rl_fallback"),
    )
    for container in (output_json, input_json):
        for path in fallback_paths:
            if _extract_nested_value(container, path) is True:
                return "FALLBACK_MODELO_RL"

    fallback_reasons = {
        "INFERENCE_UNAVAILABLE",
        "INVALID_MODEL_INFERENCE_STATE",
    }
    normalized_reason = str(reason_code or "").strip().upper()
    if normalized_reason in fallback_reasons:
        return "FALLBACK_MODELO_INFERENCIA"

    return "RL_MODEL"


def _format_confidence_for_status(confidence: float | None) -> str:
    """Formata confianca preservando 0.0 como valor valido."""
    if confidence is None:
        return "N/A"
    return f"{confidence:.0%}"


def _query_last_decision_trace(symbol: str, db_path: str) -> dict[str, Any] | None:
    """Busca trilha detalhada da decisao mais recente por simbolo."""
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            if not _has_table(conn, "model_decisions"):
                return None
            cols = _table_columns(conn, "model_decisions")
            select_cols: list[str] = ["id", "action"]
            if "confidence" in cols:
                select_cols.append("confidence")
            if "sl_target" in cols:
                select_cols.append("sl_target")
            if "tp_target" in cols:
                select_cols.append("tp_target")
            if "model_version" in cols:
                select_cols.append("model_version")
            if "reason_code" in cols:
                select_cols.append("reason_code")
            if "decision_timestamp" in cols:
                select_cols.append("decision_timestamp")
            if "input_json" in cols:
                select_cols.append("input_json")
            if "output_json" in cols:
                select_cols.append("output_json")
            row = conn.execute(
                f"SELECT {', '.join(select_cols)} FROM model_decisions "
                "WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
            if row is None:
                return None
            payload = dict(zip(select_cols, row))
            input_json = _safe_json_loads(payload.get("input_json"))
            output_json = _safe_json_loads(payload.get("output_json"))
            raw_market_state = input_json.get("market_state")
            raw_risk_state = input_json.get("risk_state")
            market_state: dict[str, Any] = raw_market_state if isinstance(raw_market_state, dict) else {}
            risk_state: dict[str, Any] = raw_risk_state if isinstance(raw_risk_state, dict) else {}
            signal_ts_ms = _normalize_ts_ms(market_state.get("signal_timestamp"))
            decision_ts_ms = _normalize_ts_ms(payload.get("decision_timestamp"))
            confidence = _to_float_or_none(payload.get("confidence"))
            return {
                "decision_id": _to_int_or_none(payload.get("id")),
                "action": str(payload.get("action") or "HOLD"),
                "confidence": confidence,
                "sl_target": _to_float_or_none(payload.get("sl_target")),
                "tp_target": _to_float_or_none(payload.get("tp_target")),
                "entry_price": _to_float_or_none(market_state.get("entry_price")),
                "targets_origin": str(market_state.get("source_rule_id") or "N/A"),
                "model_version": str(payload.get("model_version") or "N/A"),
                "reason_code": str(payload.get("reason_code") or "N/A"),
                "decision_timestamp_ms": decision_ts_ms,
                "signal_timestamp_ms": signal_ts_ms,
                "signal_age_ms": _to_int_or_none(risk_state.get("signal_age_ms")),
                "max_signal_age_ms": _to_int_or_none(risk_state.get("max_signal_age_ms")),
                "source": _resolve_decision_status_source(
                    reason_code=payload.get("reason_code"),
                    input_json=input_json,
                    output_json=output_json,
                ),
            }
    except Exception:
        return None


def _query_last_execution_trace(
    *,
    symbol: str,
    db_path: str,
    decision_id: int | None,
) -> dict[str, Any] | None:
    """Busca execucao mais recente correlacionada (ou fallback por simbolo)."""
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            if not _has_table(conn, "signal_executions"):
                return None
            cols = _table_columns(conn, "signal_executions")
            select_cols = ["id"]
            if "decision_id" in cols:
                select_cols.append("decision_id")
            if "created_at" in cols:
                select_cols.append("created_at")
            if "updated_at" in cols:
                select_cols.append("updated_at")

            sql = (
                f"SELECT {', '.join(select_cols)} FROM signal_executions "
                "WHERE symbol = ?"
            )
            params: list[Any] = [symbol]
            if "decision_id" in cols and decision_id is not None:
                sql += " AND decision_id = ?"
                params.append(int(decision_id))
            sql += " ORDER BY id DESC LIMIT 1"
            row = conn.execute(sql, tuple(params)).fetchone()
            if row is None:
                return None
            payload = dict(zip(select_cols, row))
            return {
                "execution_id": _to_int_or_none(payload.get("id")),
                "decision_id": _to_int_or_none(payload.get("decision_id")),
                "created_at_ms": _normalize_ts_ms(payload.get("created_at")),
                "updated_at_ms": _normalize_ts_ms(payload.get("updated_at")),
            }
    except Exception:
        return None


def _query_last_episode_trace(*, symbol: str, db_path: str) -> dict[str, Any] | None:
    """Busca episodio mais recente por simbolo com contexto minimo de correlacao."""
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            if not _has_table(conn, "training_episodes"):
                return None
            cols = _table_columns(conn, "training_episodes")
            select_cols = ["id", "execution_id"]
            if "status" in cols:
                select_cols.append("status")
            if "event_timestamp" in cols:
                select_cols.append("event_timestamp")
            if "created_at" in cols:
                select_cols.append("created_at")
            query_parts = [
                f"SELECT {', '.join(select_cols)} FROM training_episodes",
                "WHERE symbol = ?",
            ]
            params: list[Any] = [symbol]

            # Evita falso LEGACY: ignora episodios de contexto quando houver dados reais.
            if "status" in cols:
                query_parts.append("AND UPPER(COALESCE(status, '')) != 'CYCLE_CONTEXT'")
            if "execution_id" in cols:
                if "status" in cols:
                    query_parts.append(
                        "AND (COALESCE(execution_id, 0) > 0 OR UPPER(COALESCE(status, '')) = 'HOLD_DECISION')"
                    )
                else:
                    query_parts.append("AND COALESCE(execution_id, 0) > 0")

            query_parts.append("ORDER BY id DESC LIMIT 1")
            row = conn.execute(" ".join(query_parts), tuple(params)).fetchone()
            if row is None:
                return None
            payload = dict(zip(select_cols, row))
            return {
                "episode_id": _to_int_or_none(payload.get("id")),
                "execution_id": _to_int_or_none(payload.get("execution_id")),
                "status": str(payload.get("status") or ""),
                "event_timestamp_ms": _normalize_ts_ms(payload.get("event_timestamp")),
                "created_at_ms": _normalize_ts_ms(payload.get("created_at")),
            }
    except Exception:
        return None


def _query_persisted_ohlcv_stats(
    *,
    symbol: str,
    timeframe: str,
    db_path: str,
) -> tuple[int, str, bool]:
    """Retorna (count, last_brt, degraded) para o timeframe informado.

    degraded=True quando a fonte de persistencia nao pode ser consultada.
    """
    table_by_timeframe = {
        "D1": "ohlcv_d1",
        "H4": "ohlcv_h4",
        "H1": "ohlcv_h1",
        "M5": "ohlcv_m5",
    }
    table_name = table_by_timeframe.get(str(timeframe).upper())
    if not table_name:
        return 0, "N/A", False

    candidates: list[Path] = [Path(db_path)]
    # Fallback apenas no caminho canonico do status em runtime
    # (modelo2 -> crypto_agent legado com ohlcv_*).
    try:
        if Path(db_path).resolve() == Path(_get_model2_db_path()).resolve():
            candidates.append(Path(_get_legacy_market_db_path()))
    except Exception:
        pass

    checked_any = False
    had_io_error = False
    for candidate in candidates:
        if str(candidate) in ("", "."):
            continue
        checked_any = True
        try:
            with sqlite3.connect(str(candidate), timeout=5) as conn:
                row = conn.execute(
                    f"SELECT COUNT(*), MAX(timestamp) FROM {table_name} WHERE symbol = ?",
                    (symbol,),
                ).fetchone()
            count = int(row[0]) if row and row[0] is not None else 0
            last_ts = int(row[1]) if row and row[1] is not None else 0
            if last_ts > 0:
                # Compatibilidade defensiva: segundos POSIX legados.
                if last_ts < 1_000_000_000_000:
                    last_ts *= 1000
                return count, ts_ms_to_brt_str(last_ts), False
            return count, "N/A", False
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            if "no such table" in msg:
                continue
            had_io_error = True
        except Exception:
            had_io_error = True

    if had_io_error or checked_any:
        # checked_any=True e sem retorno indica tabela ausente em todas as fontes
        # ou erro de leitura. A distinção é feita no nível de estado final.
        return 0, "N/A", had_io_error
    return 0, "N/A", False


def _resolve_timeframe_candle_status(
    *,
    symbol: str,
    timeframe: str,
    scan_summary: dict[str, Any] | None,
    db_path: str,
) -> TimeframeCandleStatus:
    scan_count, scan_last = _get_candle_info_for_timeframe(scan_summary, symbol)
    has_scan_entry = _has_scan_entry_for_symbol(scan_summary, symbol)
    persisted_count, persisted_last, degraded = _query_persisted_ohlcv_stats(
        symbol=symbol,
        timeframe=timeframe,
        db_path=db_path,
    )

    display_time = scan_last if has_scan_entry else (persisted_last if persisted_count > 0 else "N/A")

    if degraded:
        state = "degradado"
    elif not has_scan_entry:
        # Sem artefato de runtime: distinguir entre nao executado e sem persistencia.
        state = "nao_executado" if persisted_count > 0 else "sem_persistencia"
    elif not display_time or display_time == "N/A":
        # Compatibilidade legada BLID-082/025.1: sem timestamp deve sinalizar stale+absent.
        state = "stale/absent"
    else:
        freshness = resolve_candle_freshness_contract(
            last_candle_time=display_time,
            signal_age_ms=None,
            max_signal_age_ms=DEFAULT_REPORT_FRESHNESS_WINDOW_MS,
        )
        state = str(freshness["candle_state"])

    return TimeframeCandleStatus(
        timeframe=str(timeframe).upper(),
        display_time=display_time or "N/A",
        scan_count=max(0, int(scan_count)),
        persisted_count=max(0, int(persisted_count)),
        state=state,
    )


def _format_candle_status_contract(status: TimeframeCandleStatus) -> str:
    state = status.state
    if state == "fresh":
        state = "fresh [Candle Atualizado]"
    return (
        f"{status.timeframe}: {status.display_time} | "
        f"scan={status.scan_count} | db={status.persisted_count} | {state}"
    )


def _query_confidence_from_db(symbol: str, db_path: str) -> float | None:
    """Busca a confiança da decisão mais recente do modelo para o símbolo."""
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT confidence FROM model_decisions "
                "WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row and row[0] is not None:
            return float(row[0])
    except Exception:
        pass
    return None


def _query_last_decision_from_db(symbol: str, db_path: str) -> tuple[str, float | None]:
    """Retorna (action, confidence) da decisão mais recente no DB."""
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT action, confidence FROM model_decisions "
                "WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row:
            action = str(row[0] or "HOLD")
            confidence = float(row[1]) if row[1] is not None else None
            return action, confidence
    except Exception:
        pass
    return "HOLD", None


def _query_risk_state_from_db(symbol: str, db_path: str) -> dict[str, Any] | None:
    """Extrai campos de risk_state do input_json da decisao mais recente.

    Retorna dict com os campos presentes em input_json["risk_state"], ou None
    se nao houver dados (DB inexistente, tabela ausente, symbol sem decisao).
    Nunca levanta excecao.
    """
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT input_json FROM model_decisions "
                "WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row is None:
            return None
        raw = row[0]
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        # Extrair risk_state aninhado em input_json.
        # Compatibilidade legada: quando os campos vierem na raiz do payload,
        # retornamos o próprio dict para evitar regressao na leitura do status.
        risk_state_payload = data.get("risk_state")
        if isinstance(risk_state_payload, dict):
            return risk_state_payload
        return data
    except Exception:
        return None


def _query_episode_info(symbol: str, db_path: str) -> tuple[int | None, bool, float]:
    """Retorna (episode_id, persisted, reward) do ultimo episodio real do simbolo.

    Filtra episodios de contexto (CYCLE_CONTEXT) e pendentes sem reward.
    Exibe apenas episodios de execucao real com reward_proxy preenchido.
    """
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT id, status, reward_proxy FROM training_episodes "
                "WHERE symbol = ? AND reward_proxy IS NOT NULL "
                "AND status NOT IN ('CYCLE_CONTEXT') "
                "AND (execution_id > 0 OR status = 'HOLD_DECISION') "
                "ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
            if row:
                ep_id = int(row[0])
                persisted = str(row[1] or "").upper() not in ("", "PENDING", "CONTEXT", "CYCLE_CONTEXT")
                reward = float(row[2])

                # M2-020.7: evita vies operacional para reward neutro cronico.
                # Se o episodio mais recente tiver reward neutro, busca o mais recente
                # com reward informativo nao-neutro para exibicao no status.
                if abs(reward) <= 1e-12:
                    non_zero_row = conn.execute(
                        "SELECT id, status, reward_proxy FROM training_episodes "
                        "WHERE symbol = ? AND reward_proxy IS NOT NULL "
                        "AND ABS(reward_proxy) > 1e-12 "
                        "AND status NOT IN ('CYCLE_CONTEXT') "
                        "AND (execution_id > 0 OR status = 'HOLD_DECISION') "
                        "ORDER BY id DESC LIMIT 1",
                        (symbol,),
                    ).fetchone()
                    if non_zero_row:
                        ep_id = int(non_zero_row[0])
                        persisted = str(non_zero_row[1] or "").upper() not in ("", "PENDING", "CONTEXT", "CYCLE_CONTEXT")
                        reward = float(non_zero_row[2])

                return ep_id, persisted, reward
    except Exception:
        pass
    return None, False, 0.0


def _query_episode_metadata(
    *,
    symbol: str,
    episode_id: int | None,
    db_path: str,
) -> dict[str, Any]:
    """Busca metadados do episodio exibido na linha Episodio."""
    if episode_id is None:
        return {}
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT status, execution_id, label, timeframe FROM training_episodes "
                "WHERE symbol = ? AND id = ? LIMIT 1",
                (symbol, int(episode_id)),
            ).fetchone()
            if row is None:
                return {}
            return {
                "status": str(row[0] or ""),
                "execution_id": _to_int_or_none(row[1]),
                "label": str(row[2] or ""),
                "timeframe": str(row[3] or ""),
            }
    except Exception:
        return {}


def _derive_episode_type(status: str, label: str, execution_id: int | None) -> str:
    """Classifica tipo do episodio para leitura operacional."""
    normalized_status = str(status or "").upper()
    normalized_label = str(label or "").lower()
    if normalized_status == "CYCLE_CONTEXT" or normalized_label == "context" or int(execution_id or 0) <= 0:
        return "CYCLE_CONTEXT"
    return "TRADE_EPISODE"


def _derive_training_eligibility(
    *,
    episode_type: str,
    persisted: bool,
    reward: float,
) -> str:
    """Determina se o episodio exibido e elegivel para treino incremental."""
    if episode_type != "TRADE_EPISODE":
        return "NOT_ELIGIBLE"
    if not persisted:
        return "NOT_ELIGIBLE"
    # Episodio de trade exibido no status sempre possui reward_proxy.
    _ = reward
    return "ELIGIBLE"


def _query_training_cutoff_ms(
    db_path: str,
    *,
    symbol: str | None = None,
    timeframe: str | None = None,
) -> int:
    """Retorna cutoff de treino em ms, isolado por símbolo quando possível."""
    return resolve_training_cutoff_ms(
        db_path,
        symbol=symbol,
        timeframe=timeframe,
    )


def _build_aud24h_human(*, started: int, running_block: int, conclusive: bool) -> str:
    """Gera resumo humano de auditoria das ultimas 24h."""
    if started > 0:
        return "treino iniciou na janela"
    if running_block > 0:
        return "houve bloqueio por treino em execucao"
    if not conclusive:
        return "nenhum treino iniciado nas ultimas 24h"
    return "janela sem anomalias"


# ---------------------------------------------------------------------------
# Construção do relatório por símbolo
# ---------------------------------------------------------------------------

def _get_candle_info_for_timeframe(
    scan_summary: dict[str, Any] | None, symbol: str
) -> tuple[int, str]:
    """Extrai (candles_count, last_candle_time) do sumário de scan para um símbolo."""
    if not scan_summary:
        return 0, ""
    symbols_dict = scan_summary.get("symbols") or {}
    if isinstance(symbols_dict, dict):
        sym_data = symbols_dict.get(symbol) or {}
        if isinstance(sym_data, dict):
            return (
                int(sym_data.get("candles_count", 0)),
                str(sym_data.get("last_candle_time", "")),
            )
    # fallback: items lista
    items = scan_summary.get("items") or []
    for item in items:
        if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol:
            return (
                int(item.get("candles_count", 0)),
                str(item.get("last_candle_time", "")),
            )
    return 0, ""


def _has_scan_entry_for_symbol(
    scan_summary: dict[str, Any] | None,
    symbol: str,
) -> bool:
    """Indica se o artefato de scan contem entrada explicita para o simbolo."""
    if not scan_summary:
        return False
    symbols_dict = scan_summary.get("symbols") or {}
    if isinstance(symbols_dict, dict):
        if symbol in symbols_dict:
            return True
    items = scan_summary.get("items") or []
    for item in items:
        if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol:
            return True
    return False


def _build_symbol_report(
    *,
    symbol: str,
    scan_d1: dict[str, Any] | None = None,
    scan_h4: dict[str, Any] | None = None,
    scan_h1: dict[str, Any] | None = None,
    scan_m5: dict[str, Any] | None = None,
    live_execute_summary: dict[str, Any] | None = None,
    exchange: Any | None = None,
    last_train_time: str = "N/A",
    pending_episodes: int = 0,
    training_timeframe: str = "H4",
    db_path: str = "",
) -> str:
    """Constroi bloco de status rico para um simbolo com contrato multi-timeframe."""
    from core.model2.time_utils import now_brt_str as _now_brt

    sep = "─" * 56
    mode_tag = f"[{M2_EXECUTION_MODE.upper()}]"

    # --- Candles D1/H4/H1/M5 ---
    tf_statuses = [
        _resolve_timeframe_candle_status(
            symbol=symbol,
            timeframe="D1",
            scan_summary=scan_d1,
            db_path=db_path,
        ),
        _resolve_timeframe_candle_status(
            symbol=symbol,
            timeframe="H4",
            scan_summary=scan_h4,
            db_path=db_path,
        ),
        _resolve_timeframe_candle_status(
            symbol=symbol,
            timeframe="H1",
            scan_summary=scan_h1,
            db_path=db_path,
        ),
        _resolve_timeframe_candle_status(
            symbol=symbol,
            timeframe="M5",
            scan_summary=scan_m5,
            db_path=db_path,
        ),
    ]
    candles_line = "  ".join(_format_candle_status_contract(item) for item in tf_statuses)
    candles_line = f"{candles_line} | window_ms={DEFAULT_REPORT_FRESHNESS_WINDOW_MS}"

    # --- Decisão e confiança ---
    # Prioridade: model_decisions DB > live_execute JSON
    action_db, confidence_db = _query_last_decision_from_db(symbol, db_path)
    decision = action_db
    confidence: float | None = confidence_db
    decision_trace = _query_last_decision_trace(symbol, db_path)
    execution_trace = _query_last_execution_trace(
        symbol=symbol,
        db_path=db_path,
        decision_id=(int(decision_trace["decision_id"]) if decision_trace is not None else None),
    )
    episode_trace = _query_last_episode_trace(symbol=symbol, db_path=db_path)

    # Verificar se live_execute traz decisão mais recente
    if live_execute_summary:
        for item in live_execute_summary.get("staged", []):
            if str(item.get("symbol", "")).upper() == symbol:
                raw_action = str(item.get("action", "HOLD"))
                if "LONG" in raw_action:
                    decision = "OPEN_LONG"
                elif "SHORT" in raw_action:
                    decision = "OPEN_SHORT"
                else:
                    decision = raw_action
                confidence = _to_float_or_none(item.get("confidence", confidence))
                break

    icons = {"OPEN_LONG": "🟢", "OPEN_SHORT": "🔴", "HOLD": "⏸", "REDUCE": "🟡", "CLOSE": "⛔"}
    icon = icons.get(decision, "❓")
    if decision_trace is not None:
        confidence = _to_float_or_none(decision_trace.get("confidence"))
    conf_str = _format_confidence_for_status(confidence)
    decision_parts = [f"{icon} {decision} (confianca: {conf_str})"]
    if decision_trace is not None:
        decision_parts.extend(
            [
                f"decision_id={decision_trace['decision_id']}",
                f"model_version={decision_trace['model_version']}",
                f"reason={decision_trace['reason_code']}",
                f"source={decision_trace['source']}",
            ]
        )
    else:
        decision_parts.append("source=FALLBACK_STATUS_SEM_DECISION_TRACE")
    decision_line = " | ".join(decision_parts)

    # --- Frescor verificavel ---
    tf_map = {item.timeframe: item.display_time for item in tf_statuses}
    signal_ts_ms = decision_trace.get("signal_timestamp_ms") if decision_trace is not None else None
    signal_ts = ts_ms_to_brt_str(signal_ts_ms) if signal_ts_ms else "N/A"
    signal_age_ms = decision_trace.get("signal_age_ms") if decision_trace is not None else None
    max_signal_age_ms = decision_trace.get("max_signal_age_ms") if decision_trace is not None else None
    frescor_line = (
        f"signal_ts={signal_ts} | "
        f"signal_age_ms={signal_age_ms if signal_age_ms is not None else 'N/A'} | "
        f"max_signal_age_ms={max_signal_age_ms if max_signal_age_ms is not None else 'N/A'} | "
        f"M5_last={tf_map.get('M5', 'N/A')} | H1_last={tf_map.get('H1', 'N/A')} | "
        f"H4_last={tf_map.get('H4', 'N/A')} | D1_last={tf_map.get('D1', 'N/A')}"
    )

    # --- Features usadas na inferencia ---
    snapshot_ts_ms = decision_trace.get("decision_timestamp_ms") if decision_trace is not None else None
    snapshot_at = ts_ms_to_brt_str(snapshot_ts_ms) if snapshot_ts_ms else "N/A"
    features_line = (
        "[close, sl, tp, rr_ratio, funding_rate, basis, signal_age_h, open_position_qty] "
        f"| snapshot_at={snapshot_at}"
    )

    # --- Protecao (SL/TP) ---
    protection_line = "N/A"
    if decision_trace is not None and decision in {"OPEN_LONG", "OPEN_SHORT"}:
        entry_price = decision_trace.get("entry_price")
        sl_target = decision_trace.get("sl_target")
        tp_target = decision_trace.get("tp_target")
        targets_origin = str(decision_trace.get("targets_origin") or "N/A")

        if entry_price is not None and sl_target is not None and tp_target is not None:
            risk_distance = abs(float(entry_price) - float(sl_target))
            reward_distance = abs(float(entry_price) - float(tp_target))
            rr_ratio = (reward_distance / risk_distance) if risk_distance > 0 else None

            if decision == "OPEN_LONG":
                geometry_ok = float(sl_target) < float(entry_price) < float(tp_target)
            else:
                geometry_ok = float(tp_target) < float(entry_price) < float(sl_target)

            rr_text = f"{rr_ratio:.2f}" if rr_ratio is not None else "N/A"
            geometry_text = "ok" if geometry_ok else "invalida"
            protection_line = (
                f"entry={float(entry_price):.4f} | "
                f"sl={float(sl_target):.4f} | "
                f"tp={float(tp_target):.4f} | "
                f"rr={rr_text} | geometria={geometry_text} | origem={targets_origin}"
            )
        else:
            protection_line = f"alvos indisponiveis na decisao | origem={targets_origin}"

    # --- Persistencia correlacionada ---
    persist_line = ""
    if (
        decision_trace is not None
        and execution_trace is not None
        and episode_trace is not None
        and execution_trace.get("decision_id") == decision_trace.get("decision_id")
        and episode_trace.get("execution_id") == execution_trace.get("execution_id")
    ):
        technical_decision_id = decision_trace.get("decision_id")
        technical_execution_id = execution_trace.get("execution_id")
        technical_episode_id = episode_trace.get("episode_id")
        persist_line = (
            f"model_decisions={technical_decision_id} | "
            f"signal_execution={technical_execution_id} | "
            f"episode=#{technical_episode_id} | "
            "human_reason=correlacao completa decisao->execucao->episodio | "
            f"symbol={symbol}"
        )
    else:
        technical_decision_id = (
            decision_trace.get("decision_id")
            if decision_trace is not None
            else "N/A"
        )
        technical_execution_id = (
            execution_trace.get("execution_id")
            if execution_trace is not None
            else "N/A"
        )
        technical_episode_id = (
            episode_trace.get("episode_id")
            if episode_trace is not None and episode_trace.get("episode_id") is not None
            else "N/A"
        )
        persist_line = (
            f"model_decisions={technical_decision_id} | "
            f"signal_execution={technical_execution_id} | "
            f"episode={technical_episode_id} | "
            "LEGACY_NO_DECISION_LINK | "
            "human_reason=registro existe mas sem vinculo completo decisao->execucao->episodio | "
            f"symbol={symbol}"
        )

    # --- Episódio / Reward ---
    ep_id, ep_persisted, reward = _query_episode_info(symbol, db_path)
    episode_metadata = _query_episode_metadata(
        symbol=symbol,
        episode_id=ep_id,
        db_path=db_path,
    )
    episode_type = _derive_episode_type(
        str(episode_metadata.get("status") or ""),
        str(episode_metadata.get("label") or ""),
        _to_int_or_none(episode_metadata.get("execution_id")),
    )
    eligibility_for_training = _derive_training_eligibility(
        episode_type=episode_type,
        persisted=ep_persisted,
        reward=reward,
    )
    ep_label = f"#{ep_id}" if ep_id else "N/A"
    ep_status = "persistido" if ep_persisted else "nao persistido"
    reward_sign = "+" if reward >= 0 else ""
    episode_line = (
        f"{ep_label} {ep_status} | reward: {reward_sign}{reward:.4f} | "
        f"episode_type={episode_type} | "
        f"eligibility_for_training={eligibility_for_training}"
    )

    # --- Treino ---
    from core.model2.cycle_report import _progress_bar
    thresh, train_confidence = resolve_retrain_threshold(
        db_path,
        symbol=symbol,
        timeframe=training_timeframe,
    )
    pct = pending_episodes / thresh if thresh > 0 else 0.0
    bar = _progress_bar(pct, width=10)
    episodes_restantes = max(0, thresh - pending_episodes)
    confidence_tag = "N/A" if train_confidence is None else f"{train_confidence:.0%}"
    train_line = (
        f"ultimo: {last_train_time} | "
        f"pendentes: {pending_episodes}/{thresh} {bar} "
        f"(faltam {episodes_restantes} para retreino) | "
        f"confidence_gate={confidence_tag} | "
        "eligibility_rule=reward_proxy!=NULL,status_eligivel,label!=context,created_at>cutoff | "
        f"cutoff_ms={_query_training_cutoff_ms(db_path, symbol=symbol, timeframe=training_timeframe)} | "
        f"timeframe={str(training_timeframe).upper()}"
    )
    audit_started = 0
    audit_running_block = 0
    audit_conclusive = False
    audit_train_line = (
        "aud24h: started=0 | running_block=0 | conclusivo=nao | "
        "aud24h_human=nenhum treino iniciado nas ultimas 24h"
    )
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            summary = summarize_training_audit_window(
                conn,
                since_ms=now_ms - (24 * 60 * 60 * 1000),
            )
            audit_started = int(summary["started_events"])
            audit_running_block = int(summary["blocked_running_events"])
            audit_conclusive = bool(summary["conclusive"])
            audit_train_line = (
                f"aud24h: started={audit_started} | "
                f"running_block={audit_running_block} | "
                f"conclusivo={'sim' if audit_conclusive else 'nao'} | "
                f"aud24h_human={_build_aud24h_human(started=audit_started, running_block=audit_running_block, conclusive=audit_conclusive)}"
            )
    except Exception:
        pass

    # --- Risk State ---
    risk_state = _query_risk_state_from_db(symbol, db_path)

    def _build_risk_line(rs: dict[str, Any] | None, current_action: str) -> str:
        if rs is None:
            return "N/A"
        cb_state = str(rs.get("circuit_breaker_state", "N/A"))
        rg_status = str(rs.get("risk_gate_status", "N/A"))
        short_only = rs.get("short_only", False)
        recent = rs.get("recent_entries_today")
        max_daily = rs.get("max_daily_entries")

        parts: list[str] = [f"CB:{cb_state}", f"RG:{rg_status}"]

        if cb_state not in ("normal", "N/A"):
            parts.append("[CB TRANCADO]")

        if short_only:
            parts.append(f"short_only:{short_only}")
            if current_action == "OPEN_LONG":
                parts.append("[LONG BLOQUEADO - short_only]")

        if recent is not None and max_daily is not None:
            entry_str = f"entradas hoje: {recent}/{max_daily}"
            if int(recent) >= int(max_daily):
                entry_str += " [LIMITE ATINGIDO]"
            parts.append(entry_str)

        return " | ".join(parts)

    risk_line = _build_risk_line(risk_state, decision)

    # --- Posição Binance ---
    has_position = False
    position_line = "SEM POSICAO"
    if exchange:
        try:
            position = exchange.get_open_position(symbol)
            if position and float(position.get("position_size_qty", 0)) != 0:
                has_position = True
                direction = str(position.get("direction", "")).upper()
                qty = float(position.get("position_size_qty", 0))
                size_usdt = float(position.get("position_size_usdt", 0) or 0)
                entry = float(position.get("entry_price", 0))
                mark = float(position.get("mark_price", 0))
                margin = float(
                    position.get(
                        "margin_invested",
                        position.get("initial_margin", position.get("margin", 0)),
                    )
                    or 0
                )
                leverage = position.get("leverage", "N/A")
                pnl_usd = float(position.get("unrealized_pnl", 0) or 0)
                pnl_pct = float(position.get("unrealized_pnl_pct", 0) or 0)

                if pnl_usd == 0.0 and entry > 0 and qty > 0:
                    if direction == "LONG":
                        pnl_usd = (mark - entry) * qty
                    else:
                        pnl_usd = (entry - mark) * qty
                if pnl_pct == 0.0 and margin > 0:
                    pnl_pct = (pnl_usd / margin) * 100

                display_size = size_usdt if size_usdt > 0 else qty
                display_unit = "USDT" if size_usdt > 0 else "qty"

                pnl_sign = "+" if pnl_pct >= 0 else ""
                usd_sign = "+" if pnl_usd >= 0 else ""
                position_line = (
                    f"{direction} {display_size:.2f} {display_unit} @ {entry:.4f} | "
                    f"mark: {mark:.4f} | "
                    f"margem: ${margin:.2f} | alavancagem: {leverage}x | "
                    f"PnL: {pnl_sign}{pnl_pct:.2f}% ({usd_sign}${pnl_usd:.2f})"
                )
        except Exception:
            pass

    lines = [
        sep,
        f"  {symbol} | {_now_brt()} {mode_tag}",
        sep,
        f"  Contrato : contract={BLID_101_STATUS_CONTRACT}",
        f"  Candles  : {candles_line}",
        f"  Decisao  : {decision_line}",
        f"  Episodio : {episode_line}",
        f"  Frescor  : {frescor_line}",
        f"  Features : {features_line}",
        f"  Protecao : {protection_line}",
        f"  Persist. : {persist_line}",
        f"  Treino   : {train_line} | {audit_train_line}",
        f"  Posicao  : {position_line}",
        f"  Risk     : {risk_line}",
        sep,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Alias de compatibilidade com testes legados
# ---------------------------------------------------------------------------

def _build_symbol_line(
    *,
    symbol: str,
    scan_summary: dict[str, Any] | None,
    track_summary: dict[str, Any] | None,
    validate_summary: dict[str, Any] | None,
    resolve_summary: dict[str, Any] | None,
    live_execute_summary: dict[str, Any] | None,
    exchange: Any | None,
    last_train_time: str,
) -> str:
    """Compatibilidade: mapeia interface legada para _build_symbol_report."""
    candles_count, last_candle_time = _get_candle_info_for_timeframe(scan_summary, symbol)
    action = "HOLD"
    confidence = 0.0
    if live_execute_summary:
        for item in live_execute_summary.get("staged", []):
            if str(item.get("symbol", "")).upper() != symbol:
                continue
            raw_action = str(item.get("action", "HOLD"))
            if "LONG" in raw_action:
                action = "OPEN_LONG"
            elif "SHORT" in raw_action:
                action = "OPEN_SHORT"
            else:
                action = raw_action
            try:
                confidence = float(item.get("confidence", 0.0) or 0.0)
            except Exception:
                confidence = 0.0
            break

    # Compatibilidade legada: _build_symbol_line usa janela mais tolerante para
    # nao tornar snapshots validos do mesmo ciclo como stale por variacao de data
    # entre execucoes em CI/local.
    legacy_window_ms = 14 * 24 * 60 * 60 * 1000
    freshness = resolve_candle_freshness_contract(
        last_candle_time=last_candle_time,
        signal_age_ms=None,
        max_signal_age_ms=legacy_window_ms,
    )
    report = SymbolReport(
        symbol=symbol,
        timeframe="M5",
        timestamp=now_brt_str(),
        candles_count=candles_count,
        last_candle_time=last_candle_time,
        candle_state=freshness["candle_state"],
        freshness_reason=freshness["freshness_reason"],
        decision=action,
        confidence=confidence,
        decision_fresh=freshness["decision_fresh"],
        last_train_time=last_train_time,
        pending_episodes=0,
        execution_mode=M2_EXECUTION_MODE,
    )
    return format_symbol_report(report)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera resumo por simbolo a partir dos artefatos do ciclo M2"
    )
    parser.add_argument("--runtime-dir", default="results/model2/runtime")
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--symbols-csv", default="")
    parser.add_argument("--max-age-minutes", type=int, default=60)
    parser.add_argument(
        "--training-timeframe",
        default="H4",
        choices=["D1", "H4", "H1", "M5", "ALL"],
        help="Timeframe usado para contagem de pendencias de retreino (ALL = todos).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    runtime_dir = Path(args.runtime_dir).resolve()
    csv_symbols = _normalize_symbol_scope(args.symbols_csv, fallback_symbols=tuple(M2_SYMBOLS))
    cli_symbols = _normalize_symbol_scope(",".join(args.symbol or []), fallback_symbols=tuple(M2_SYMBOLS))
    symbols = list(dict.fromkeys([*csv_symbols, *cli_symbols]))

    if not symbols:
        print("Nenhum simbolo informado para resumo operacional.")
        return 0

    if not runtime_dir.exists():
        print(f"Diretorio de runtime nao encontrado: {runtime_dir}")
        for sym in symbols:
            print(f"[{now_brt_str()}] [M2][{sym}] | Status: sem_artefatos")
        return 0

    max_age_seconds = max(60, int(args.max_age_minutes) * 60)

    # Carregar artefatos por timeframe
    scan_d1 = _load_latest_json_by_timeframe(runtime_dir, "model2_scan", "D1", max_age_seconds)
    scan_h4 = _load_latest_json_by_timeframe(runtime_dir, "model2_scan", "H4", max_age_seconds)
    scan_h1 = _load_latest_json_by_timeframe(runtime_dir, "model2_scan", "H1", max_age_seconds)
    scan_m5 = _load_latest_json_by_timeframe(runtime_dir, "model2_scan", "M5", max_age_seconds)
    live_execute_summary = _load_latest_json(runtime_dir, "model2_live_execute", max_age_seconds)

    # DB path
    db_path = _get_model2_db_path()

    training_timeframe = None if str(args.training_timeframe).upper() == "ALL" else str(args.training_timeframe).upper()

    # Exchange (todos os modos — para posições reais na Binance)
    exchange = None
    if _EXCHANGE_AVAILABLE:
        try:
            client = create_binance_client(mode="live")
            exchange = Model2LiveExchange(client)
        except Exception as e:
            print(f"[WARN] Exchange nao disponivel: {e}", file=sys.stderr)

    for symbol in symbols:
        symbol_last_train, symbol_pending = collect_training_info_for_symbol(
            db_path,
            symbol=symbol,
            timeframe=training_timeframe,
        )
        if symbol_last_train == "nunca":
            symbol_last_train = _get_last_train_time_from_symbol_checkpoint(symbol)
            if symbol_last_train == "N/A":
                symbol_last_train = _get_last_train_time_from_checkpoint()

        line = _build_symbol_report(
            symbol=symbol,
            scan_d1=scan_d1,
            scan_h4=scan_h4,
            scan_h1=scan_h1,
            scan_m5=scan_m5,
            live_execute_summary=live_execute_summary,
            exchange=exchange,
            last_train_time=symbol_last_train,
            pending_episodes=symbol_pending,
            training_timeframe=(training_timeframe or "ALL"),
            db_path=db_path,
        )
        print(line, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
