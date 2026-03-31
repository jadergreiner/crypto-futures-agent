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
from core.model2.cycle_report import RETRAIN_EPISODE_THRESHOLD

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
        "runs": []
    }


def _save_state(state: Dict[str, Any]) -> None:
    """Persiste estado de controle."""
    os.makedirs(STATE_FILE.parent, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


def _get_episode_count() -> int:
    """Retorna total de episodes na tabela training_episodes."""
    if not DB_PATH.exists():
        return 0
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM training_episodes")
        result = cur.fetchone()
        count = result[0] if result else 0
        conn.close()
        return int(count)
    except Exception:
        return 0


def should_run_continuous_cycle(
    min_new_episodes: int = RETRAIN_EPISODE_THRESHOLD,
    min_hours_between_runs: float = 2.0
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
    current_episode_count = _get_episode_count()

    # Verificação 1: Primeira execução?
    if state["last_continuous_run"] is None:
        # Se há episódios suficientes acumulados, rodar agora
        if current_episode_count >= min_new_episodes:
            return (
                True,
                f"Primeira execução. Episodes acumulados: {current_episode_count}"
            )
        return (
            False,
            f"Aguardando {min_new_episodes - current_episode_count} episódios. "
            f"Atual: {current_episode_count}"
        )

    # Verificação 2: Tempo mínimo entre execuções?
    last_run_str = state["last_continuous_run"]
    try:
        last_run_dt = datetime.fromisoformat(str(last_run_str))
        now = datetime.now()
        hours_since_last = (now - last_run_dt).total_seconds() / 3600.0
        if hours_since_last < min_hours_between_runs:
            time_remaining = min_hours_between_runs - hours_since_last
            return (
                False,
                f"Próxima execução em {time_remaining:.1f}h ("
                f"{(time_remaining * 60):.0f}m). "
                f"Episódios: {current_episode_count}"
            )
    except Exception:
        pass

    # Verificação 3: Episódios novos desde última execução?
    new_episodes = current_episode_count - state["last_episode_count"]
    if new_episodes >= min_new_episodes:
        return (
            True,
            f"Novos episódios: {new_episodes}. "
            f"Total: {current_episode_count}"
        )

    return (
        False,
        f"Insuficientes novos episódios. "
        f"Atual: {new_episodes}, Necessário: {min_new_episodes}. "
        f"Total: {current_episode_count}"
    )


def mark_run_executed(symbols: Optional[List[str]] = None) -> None:
    """Marca ciclo como executado agora."""
    state = _load_state()
    now_str = datetime.now().isoformat()
    state["last_continuous_run"] = now_str
    state["last_episode_count"] = _get_episode_count()

    state["runs"].append({
        "timestamp": now_str,
        "episode_count": state["last_episode_count"],
        "symbols": symbols or []
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
        current_count = _get_episode_count()
        should_run, reason = should_run_continuous_cycle()

        print("\n" + "=" * 80)
        print("CONTINUOUS LEARNING CONTROLLER - STATUS")
        print("=" * 80)
        print(f"\nÚltima execução: {state['last_continuous_run'] or 'Nunca'}")
        print(f"Episodes na última execução: {state['last_episode_count']}")
        print(f"Episodes atuais no DB: {current_count}")
        print(f"Episodes novos desde última execução: "
              f"{current_count - state['last_episode_count']}")
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

