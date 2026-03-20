"""Treinamento de agentes PPO individuais por simbolo — US-06 do PRD.

Uso:
    python scripts/model2/train_entry_agents.py --symbol BTCUSDT
    python scripts/model2/train_entry_agents.py --symbol ETHUSDT --timeframe H1
    python scripts/model2/train_entry_agents.py --symbol ALL

Treina (ou re-treina) um modelo PPO especifico para o simbolo fornecido e
salva o checkpoint em checkpoints/ppo_training/<SYMBOL>/.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import MODEL2_DB_PATH  # noqa: E402
from config.symbols import ALL_SYMBOLS  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_DEFAULT_CHECKPOINT_ROOT = REPO_ROOT / "checkpoints" / "ppo_training"
_MIN_EPISODES = 30


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _load_episodes(
    db_path: Path,
    symbol: str,
    timeframe: str,
) -> list[dict[str, Any]]:
    """Carrega episodios de treinamento do banco para um simbolo/timeframe."""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, symbol, timeframe, label, reward_proxy,
                   features_json, target_json, created_at
            FROM training_episodes
            WHERE symbol = ? AND timeframe = ?
            ORDER BY created_at ASC
            """,
            (symbol, timeframe),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("[%s] Erro ao carregar episodios: %s", symbol, exc)
        return []


def _build_obs_array(episodes: list[dict[str, Any]]) -> np.ndarray:
    """Constroi array de observacoes a partir dos episodios."""
    obs_list: list[np.ndarray] = []
    for ep in episodes:
        try:
            features = json.loads(ep.get("features_json") or "[]")
            if features:
                obs_list.append(np.array(features, dtype=np.float32))
        except (json.JSONDecodeError, ValueError):
            continue
    if not obs_list:
        return np.empty((0,), dtype=np.float32)
    return np.vstack(obs_list)


def train_symbol(
    symbol: str,
    *,
    timeframe: str,
    db_path: Path,
    checkpoint_root: Path,
    total_timesteps: int,
    dry_run: bool,
) -> dict[str, Any]:
    """Treina (ou re-treina) o agente PPO para um simbolo especifico.

    Se o stable_baselines3 nao estiver disponivel, registra aviso e
    retorna status de fallback sem erro.
    """
    start_ms = _utc_now_ms()
    result: dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "status": "pending",
        "checkpoint": None,
        "episodes": 0,
        "timesteps": 0,
        "duration_ms": 0,
    }

    # ---- Carregar episodios ------------------------------------------
    episodes = _load_episodes(db_path, symbol, timeframe)
    result["episodes"] = len(episodes)

    if len(episodes) < _MIN_EPISODES:
        result["status"] = "skipped"
        result["reason"] = (
            f"episodios insuficientes: {len(episodes)} < {_MIN_EPISODES}"
        )
        logger.warning(
            "[%s] %s", symbol, result["reason"]
        )
        return result

    # ---- Verificar disponibilidade do SB3 ---------------------------
    try:
        from stable_baselines3 import PPO  # noqa: F401
        from stable_baselines3.common.env_util import make_vec_env  # noqa: F401
        sb3_available = True
    except ImportError:
        sb3_available = False

    if not sb3_available:
        result["status"] = "fallback"
        result["reason"] = (
            "stable_baselines3 nao instalado; "
            "checkpoint nao gerado (modo fallback determinístico ativo)"
        )
        logger.warning("[%s] %s", symbol, result["reason"])
        return result

    if dry_run:
        result["status"] = "dry_run"
        result["reason"] = "dry_run ativo; nenhum arquivo salvo"
        logger.info("[%s] dry_run: pulando treinamento", symbol)
        return result

    # ---- Treinar -------------------------------------------------------
    checkpoint_dir = checkpoint_root / symbol
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "ppo_model.pkl"

    try:
        from stable_baselines3 import PPO
        from gymnasium import spaces

        obs_array = _build_obs_array(episodes)
        if obs_array.shape[0] == 0:
            result["status"] = "skipped"
            result["reason"] = "features vazias nos episodios"
            return result

        n_features = obs_array.shape[1] if obs_array.ndim > 1 else 1

        # Importar ambiente LSTM se disponivel; usar DummyEnv como fallback
        try:
            from agent.lstm_environment import LSTMSignalEnvironment

            env = LSTMSignalEnvironment(
                episodes=episodes,
                seq_len=10,
                n_features=n_features,
            )
        except (ImportError, Exception) as env_exc:
            logger.warning(
                "[%s] LSTMSignalEnvironment indisponivel (%s); "
                "usando ambiente minimalista",
                symbol,
                env_exc,
            )
            from gymnasium import Env

            class _MinimalEnv(Env):
                def __init__(self) -> None:
                    super().__init__()
                    self.observation_space = spaces.Box(
                        low=-np.inf,
                        high=np.inf,
                        shape=(n_features,),
                        dtype=np.float32,
                    )
                    self.action_space = spaces.Discrete(3)
                    self._idx = 0

                def reset(self, *, seed=None, options=None):
                    super().reset(seed=seed)
                    self._idx = 0
                    return obs_array[0], {}

                def step(self, action):
                    self._idx = (self._idx + 1) % len(obs_array)
                    obs = obs_array[self._idx]
                    reward = float(
                        episodes[self._idx].get("reward_proxy") or 0.0
                    )
                    done = self._idx == len(obs_array) - 1
                    return obs, reward, done, False, {}

            env = _MinimalEnv()

        # Carregar ou criar modelo
        if checkpoint_path.exists():
            model = PPO.load(str(checkpoint_path), env=env)
            logger.info("[%s] Checkpoint existente carregado; re-treinando", symbol)
        else:
            model = PPO("MlpPolicy", env, verbose=0)
            logger.info("[%s] Novo modelo PPO criado", symbol)

        model.learn(total_timesteps=total_timesteps)
        model.save(str(checkpoint_path))

        result["status"] = "ok"
        result["checkpoint"] = str(checkpoint_path)
        result["timesteps"] = total_timesteps
        logger.info(
            "[%s] Treinamento concluido. Checkpoint: %s", symbol, checkpoint_path
        )
    except Exception as exc:
        result["status"] = "error"
        result["reason"] = str(exc)
        logger.error("[%s] Erro durante treinamento: %s", symbol, exc)

    result["duration_ms"] = _utc_now_ms() - start_ms
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Treina agentes PPO individuais por simbolo (US-06 do PRD)"
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Simbolo para treinar (ex.: BTCUSDT) ou ALL para todos",
    )
    parser.add_argument(
        "--timeframe",
        default="H4",
        choices=["D1", "H4", "H1", "M5"],
        help="Timeframe de treinamento (padrao: H4)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=MODEL2_DB_PATH,
        help="Caminho do banco modelo2.db",
    )
    parser.add_argument(
        "--checkpoint-root",
        type=Path,
        default=_DEFAULT_CHECKPOINT_ROOT,
        help="Diretorio raiz para checkpoints por simbolo",
    )
    parser.add_argument(
        "--total-timesteps",
        type=int,
        default=50_000,
        help="Total de timesteps de treinamento (padrao: 50000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula treinamento sem salvar checkpoints",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Caminho do arquivo JSON de saida (opcional)",
    )
    args = parser.parse_args()

    # Resolver lista de simbolos
    if args.symbol.upper() == "ALL":
        symbols = list(ALL_SYMBOLS)
    else:
        symbols = [args.symbol.upper()]

    logger.info("=" * 60)
    logger.info("MODEL 2.0 — TRAIN ENTRY AGENTS")
    logger.info("Simbolos: %s | Timeframe: %s | Timesteps: %d",
                symbols, args.timeframe, args.total_timesteps)
    logger.info("=" * 60)

    results: list[dict[str, Any]] = []
    for symbol in symbols:
        res = train_symbol(
            symbol,
            timeframe=args.timeframe,
            db_path=args.db_path,
            checkpoint_root=args.checkpoint_root,
            total_timesteps=args.total_timesteps,
            dry_run=args.dry_run,
        )
        results.append(res)

    summary = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "timestamp_utc_ms": _utc_now_ms(),
        "symbols_requested": len(symbols),
        "trained_ok": sum(1 for r in results if r["status"] == "ok"),
        "skipped": sum(1 for r in results if r["status"] in {"skipped", "dry_run"}),
        "fallback": sum(1 for r in results if r["status"] == "fallback"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }

    print(json.dumps(summary, indent=2, ensure_ascii=True))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        logger.info("Resultado salvo: %s", args.output)

    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
