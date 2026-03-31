#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Controlador automático do ciclo contínuo de autoaprendizado.

Verifica se é hora de executar continuous_learning_cycle.py com base em:
1. Número de novos episódios persistidos desde última execução
2. Tempo decorrido mínimo entre execuções

Essa etapa é TOTALMENTE AUTOMÁTICA e TRANSPARENTE ao usuário.
Zero intervenção necessária.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Importar constante centralizada de threshold
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model2.cycle_report import (
    RETRAIN_EPISODE_THRESHOLD,
    RETRAIN_WARMUP_EPISODE_THRESHOLD,
    TRAINING_EPISODE_ELIGIBLE_STATUSES,
    collect_training_info_for_symbol,
    resolve_retrain_threshold,
)

try:
    from config.settings import M2_SYMBOLS
except Exception:
    M2_SYMBOLS = ("BTCUSDT",)

WARMUP_RETRAIN_INTERVAL_HOURS = 0.25  # 15 minutos
DEFAULT_RETRAIN_INTERVAL_HOURS = 2.0
DEFAULT_TRAINING_TIMEFRAME = "M5"

# Diretórios
REPO_ROOT = Path(__file__).parent.parent.parent
STATE_FILE = REPO_ROOT / "results" / "model2" / "learning_state.json"
DB_PATH = REPO_ROOT / "db" / "modelo2.db"


def _load_state() -> Dict[str, Any]:
    """Carrega estado de controle (last run timestamp, count)."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    return loaded
        except Exception:
            pass
    return {
        "last_continuous_run": None,
        "last_episode_count": 0,
        "symbol_states": {},
        "runs": []
    }


def _save_state(state: Dict[str, Any]) -> None:
    """Persiste estado de controle."""
    os.makedirs(STATE_FILE.parent, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


def _normalize_symbols(symbols: Optional[List[str]] = None) -> List[str]:
    """Normaliza escopo de símbolos para o controller."""
    source = symbols if symbols else list(M2_SYMBOLS)
    normalized = [str(symbol).strip().upper() for symbol in source if str(symbol).strip()]
    return list(dict.fromkeys(normalized))


def _get_symbol_state(state: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """Retorna estado de execução do símbolo com fallback retrocompatível."""
    symbol_states = state.get("symbol_states")
    if isinstance(symbol_states, dict):
        raw_state = symbol_states.get(symbol)
        if isinstance(raw_state, dict):
            return {
                "last_continuous_run": raw_state.get("last_continuous_run"),
                "last_episode_count": int(raw_state.get("last_episode_count") or 0),
            }

    return {
        "last_continuous_run": state.get("last_continuous_run"),
        "last_episode_count": int(state.get("last_episode_count") or 0),
    }


def _get_episode_count(
    *,
    symbol: str | None = None,
    timeframe: str | None = DEFAULT_TRAINING_TIMEFRAME,
) -> int:
    """Retorna total de episódios elegíveis para treino, isolado por símbolo."""
    if not DB_PATH.exists():
        return 0
    try:
        with sqlite3.connect(str(DB_PATH), timeout=5) as conn:
            status_placeholders = ", ".join("?" for _ in TRAINING_EPISODE_ELIGIBLE_STATUSES)
            query_parts = [
                "SELECT COUNT(*) FROM training_episodes",
                "WHERE reward_proxy IS NOT NULL",
                f"  AND UPPER(COALESCE(status, '')) IN ({status_placeholders})",
                "  AND LOWER(COALESCE(label, '')) != 'context'",
            ]
            params: List[Any] = [*TRAINING_EPISODE_ELIGIBLE_STATUSES]

            normalized_symbol = str(symbol or "").strip().upper()
            if normalized_symbol:
                query_parts.append("  AND symbol = ?")
                params.append(normalized_symbol)

            normalized_timeframe = str(timeframe or "").strip().upper()
            if normalized_timeframe and normalized_timeframe != "ALL":
                query_parts.append("  AND timeframe = ?")
                params.append(normalized_timeframe)

            result = conn.execute(" ".join(query_parts), tuple(params)).fetchone()
            count = result[0] if result else 0
            return int(count)
    except Exception:
        return 0


def should_run_continuous_cycle(
    min_new_episodes: int | None = None,
    min_hours_between_runs: float | None = None,
    symbols: Optional[List[str]] = None,
    timeframe: str | None = DEFAULT_TRAINING_TIMEFRAME,
) -> Tuple[bool, str]:
    """
    Determina se continuous_learning_cycle.py deve ser executado agora.

    Args:
        min_new_episodes: Mínimo de novos episódios para triggerar execução
        min_hours_between_runs: Horas mínimas entre execuções consecutivas

    Returns:
        (should_run: bool, reason: str)
    """
    state = _load_state()
    symbol_scope = _normalize_symbols(symbols)
    waiting_reasons: List[str] = []

    for symbol in symbol_scope:
        _, pending_episodes = collect_training_info_for_symbol(
            str(DB_PATH),
            symbol=symbol,
            timeframe=timeframe,
        )
        resolved_threshold, resolved_confidence = resolve_retrain_threshold(
            str(DB_PATH),
            symbol=symbol,
            timeframe=timeframe,
        )
        effective_threshold = int(min_new_episodes or resolved_threshold)
        is_warmup_mode = effective_threshold <= RETRAIN_WARMUP_EPISODE_THRESHOLD
        effective_min_hours_between_runs = (
            float(min_hours_between_runs)
            if min_hours_between_runs is not None
            else (
                WARMUP_RETRAIN_INTERVAL_HOURS
                if is_warmup_mode
                else DEFAULT_RETRAIN_INTERVAL_HOURS
            )
        )
        symbol_state = _get_symbol_state(state, symbol)
        last_run_str = symbol_state.get("last_continuous_run")

        if last_run_str is None:
            if int(pending_episodes) >= effective_threshold:
                conf_tag = "N/A" if resolved_confidence is None else f"{resolved_confidence:.0%}"
                return (
                    True,
                    f"Símbolo {symbol}: primeira execução. Pendentes={int(pending_episodes)} "
                    f"(threshold={effective_threshold}, confianca={conf_tag})"
                )
            waiting_reasons.append(
                f"{symbol}: aguardando {max(0, effective_threshold - int(pending_episodes))} episódios "
                f"(pendentes={int(pending_episodes)}, threshold={effective_threshold})"
            )
            continue

        try:
            last_run_dt = datetime.fromisoformat(str(last_run_str))
            now = datetime.now()
            hours_since_last = (now - last_run_dt).total_seconds() / 3600.0
            if hours_since_last < effective_min_hours_between_runs:
                time_remaining = effective_min_hours_between_runs - hours_since_last
                waiting_reasons.append(
                    f"{symbol}: proxima execução em {time_remaining:.1f}h "
                    f"({(time_remaining * 60):.0f}m). pendentes={int(pending_episodes)}"
                )
                continue
        except Exception:
            pass

        if int(pending_episodes) >= effective_threshold:
            conf_tag = "N/A" if resolved_confidence is None else f"{resolved_confidence:.0%}"
            return (
                True,
                f"Símbolo {symbol}: pendentes pós-cutoff={int(pending_episodes)}. "
                f"Threshold={effective_threshold}. Confianca={conf_tag}"
            )

        waiting_reasons.append(
            f"{symbol}: insuficientes episódios pendentes (pendentes={int(pending_episodes)}, "
            f"necessário={effective_threshold})"
        )

    if waiting_reasons:
        return False, " | ".join(waiting_reasons)
    return False, "Nenhum símbolo elegível para retreino no momento"


def mark_run_executed(
    symbols: Optional[List[str]] = None,
    *,
    timeframe: str | None = DEFAULT_TRAINING_TIMEFRAME,
) -> None:
    """Marca ciclo como executado agora."""
    state = _load_state()
    now_str = datetime.now().isoformat()
    state["last_continuous_run"] = now_str
    state["last_episode_count"] = _get_episode_count(timeframe=timeframe)

    symbol_scope = _normalize_symbols(symbols)
    symbol_states = state.get("symbol_states")
    if not isinstance(symbol_states, dict):
        symbol_states = {}
    for symbol in symbol_scope:
        symbol_states[symbol] = {
            "last_continuous_run": now_str,
            "last_episode_count": _get_episode_count(symbol=symbol, timeframe=timeframe),
        }
    state["symbol_states"] = symbol_states

    state["runs"].append({
        "timestamp": now_str,
        "episode_count": state["last_episode_count"],
        "symbols": symbol_scope,
        "timeframe": str(timeframe or "ALL").upper(),
    })

    # Manter apenas últimas 100 execuções no histórico
    if len(state["runs"]) > 100:
        state["runs"] = state["runs"][-100:]

    _save_state(state)


def main() -> None:
    """
    CLI entry point para verificação e controle.
    Uso:
      python continuous_learning_controller.py check
      python continuous_learning_controller.py mark --symbols BTCUSDT,ETHUSDT
      python continuous_learning_controller.py status
    """
    if len(sys.argv) < 2:
        print("Uso: continuous_learning_controller.py {check|mark|status}")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "check":
        # Retorna true/false e reason (para uso em if de batch)
        should_run, reason = should_run_continuous_cycle()
        print(f"[LEARNING_CONTROLLER] {reason}")
        if should_run:
            print("[LEARNING_CONTROLLER] EXECUTANDO continuous_learning_cycle.py")
            sys.exit(0)
        else:
            print("[LEARNING_CONTROLLER] Aguardando próximo trigger...")
            sys.exit(1)

    elif command == "mark":
        # Marca execução realizada
        symbols: List[str] = []
        if "--symbols" in sys.argv:
            idx = sys.argv.index("--symbols")
            if idx + 1 < len(sys.argv):
                symbols = sys.argv[idx + 1].split(",")
        mark_run_executed(symbols)
        print("[LEARNING_CONTROLLER] Marcada execução com sucesso")
        sys.exit(0)

    elif command == "status":
        # Exibe status détalhado
        state = _load_state()
        symbol_scope = _normalize_symbols()
        current_count = _get_episode_count(timeframe=DEFAULT_TRAINING_TIMEFRAME)
        should_run, reason = should_run_continuous_cycle()

        print("\n" + "=" * 80)
        print("CONTINUOUS LEARNING CONTROLLER - STATUS")
        print("=" * 80)
        print(f"\nÚltima execução: {state['last_continuous_run'] or 'Nunca'}")
        print(f"Episodes na última execução: {state['last_episode_count']}")
        print(f"Episodes atuais no DB: {current_count}")
        print(f"Episodes novos desde última execução: "
              f"{current_count - state['last_episode_count']}")

        print("\nPor símbolo:")
        for symbol in symbol_scope:
            symbol_state = _get_symbol_state(state, symbol)
            symbol_count = _get_episode_count(symbol=symbol, timeframe=DEFAULT_TRAINING_TIMEFRAME)
            threshold_atual, confidence_atual = resolve_retrain_threshold(
                str(DB_PATH),
                symbol=symbol,
                timeframe=DEFAULT_TRAINING_TIMEFRAME,
            )
            confidence_tag = "N/A" if confidence_atual is None else f"{confidence_atual:.0%}"
            print(
                f"  {symbol}: last_run={symbol_state['last_continuous_run'] or 'Nunca'} | "
                f"episodes={symbol_count} | last_mark={symbol_state['last_episode_count']} | "
                f"threshold={threshold_atual} | confianca={confidence_tag}"
            )

        print(f"\nDecisão: {'SIM - Executar ciclo' if should_run else 'NÃO - Aguardar'}")
        print(f"Motivo: {reason}")

        if state["runs"]:
            print(f"\nÚltimas {min(5, len(state['runs']))} execuções:")
            for run in state["runs"][-5:]:
                print(f"  {run['timestamp']}: {run['episode_count']} episodes "
                      f"({', '.join(run['symbols']) or 'N/A'})")
        print()

    else:
        print(f"Comando desconhecido: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()

