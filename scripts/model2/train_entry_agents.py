"""Runner de treinamento diário para EntryDecisionAgents.

Este arquivo treina (ou re-treina) agentes PPO por símbolo usando episódios
armazenados em `training_episodes` do DB `modelo2.db`.

Principais comportamentos:
- Suporta `--symbol <SYMBOL>` ou `ALL` para treinar todos os símbolos.
- Fallback seguro quando `stable_baselines3` não estiver disponível.
- Salva checkpoints em `checkpoints/ppo_training/<SYMBOL>/ppo_model.pkl`.
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


def _load_episodes(db_path: Path, symbol: str, timeframe: str) -> list[dict[str, Any]]:
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

    episodes = _load_episodes(db_path, symbol, timeframe)
    result["episodes"] = len(episodes)

    if len(episodes) < _MIN_EPISODES:
        result["status"] = "skipped"
        result["reason"] = f"episodios insuficientes: {len(episodes)} < {_MIN_EPISODES}"
        logger.warning("[%s] %s", symbol, result["reason"])
        return result

    try:
        from stable_baselines3 import PPO  # type: ignore
    except Exception:
        result["status"] = "fallback"
        result["reason"] = (
            "stable_baselines3 nao instalado; checkpoint nao gerado (modo fallback)"
        )
        logger.warning("[%s] %s", symbol, result["reason"])
        return result

    if dry_run:
        result["status"] = "dry_run"
        result["reason"] = "dry_run ativo; nenhum arquivo salvo"
        logger.info("[%s] dry_run: pulando treinamento", symbol)
        return result

    checkpoint_dir = checkpoint_root / symbol
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "ppo_model.pkl"

    try:
        from gymnasium import spaces

        obs_array = _build_obs_array(episodes)
        if obs_array.shape[0] == 0:
            result["status"] = "skipped"
            result["reason"] = "features vazias nos episodios"
            return result

        n_features = obs_array.shape[1] if obs_array.ndim > 1 else 1

        try:
            from agent.lstm_environment import LSTMSignalEnvironment  # type: ignore

            env = LSTMSignalEnvironment(episodes=episodes, seq_len=10, n_features=n_features)
        except Exception as env_exc:
            logger.warning(
                "[%s] LSTMSignalEnvironment indisponivel (%s); usando ambiente minimalista",
                symbol,
                env_exc,
            )
            from gymnasium import Env

            class _MinimalEnv(Env):
                def __init__(self) -> None:
                    super().__init__()
                    self.observation_space = spaces.Box(
                        low=-np.inf, high=np.inf, shape=(n_features,), dtype=np.float32
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
                    reward = float(episodes[self._idx].get("reward_proxy") or 0.0)
                    done = self._idx == len(obs_array) - 1
                    return obs, reward, done, False, {}

            env = _MinimalEnv()

        if checkpoint_path.exists():
            model = PPO.load(str(checkpoint_path), env=env)  # type: ignore
            logger.info("[%s] Checkpoint existente carregado; re-treinando", symbol)
        else:
            model = PPO("MlpPolicy", env, verbose=0)
            logger.info("[%s] Novo modelo PPO criado", symbol)

        model.learn(total_timesteps=total_timesteps)
        model.save(str(checkpoint_path))

        result["status"] = "ok"
        result["checkpoint"] = str(checkpoint_path)
        result["timesteps"] = total_timesteps
        logger.info("[%s] Treinamento concluido. Checkpoint: %s", symbol, checkpoint_path)
    except Exception as exc:
        result["status"] = "error"
        result["reason"] = str(exc)
        logger.error("[%s] Erro durante treinamento: %s", symbol, exc)

    result["duration_ms"] = _utc_now_ms() - start_ms
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Treina agentes PPO individuais por simbolo")
    parser.add_argument("--symbol", required=True, help="Simbolo (ex.: BTCUSDT) ou ALL")
    parser.add_argument(
        "--timeframe", default="H4", choices=["D1", "H4", "H1", "M5"], help="Timeframe"
    )
    parser.add_argument("--db-path", type=Path, default=MODEL2_DB_PATH, help="Caminho do banco modelo2.db")
    parser.add_argument(
        "--checkpoint-root", type=Path, default=_DEFAULT_CHECKPOINT_ROOT, help="Diretorio raiz para checkpoints"
    )
    parser.add_argument("--total-timesteps", type=int, default=50_000, help="Total de timesteps")
    parser.add_argument("--dry-run", action="store_true", help="Nao grava checkpoints quando ativo")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists() and str(args.db_path) != ":memory":
        logger.error("Banco de dados nao encontrado: %s", db_path)
        return 2

    symbols: list[str]
    if args.symbol.upper() == "ALL":
        symbols = list(ALL_SYMBOLS)
    else:
        symbols = [args.symbol]

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "timeframe": args.timeframe,
        "total_timesteps": args.total_timesteps,
        "dry_run": args.dry_run,
        "results": {},
    }

    for sym in symbols:
        res = train_symbol(
            sym,
            timeframe=args.timeframe,
            db_path=db_path,
            checkpoint_root=Path(args.checkpoint_root),
            total_timesteps=args.total_timesteps,
            dry_run=args.dry_run,
        )
        summary["results"][sym] = res

    out_dir = REPO_ROOT / "results" / "model2" / "runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"train_entry_agents_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    logger.info("Resumo salvo em %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

    for sym in symbols:
        sym = sym.strip().upper()

        # 1. Carregar episodios do DB
        episodes = load_episodes(
            db_path=db_path,
            symbol=sym,
            timeframe=args.timeframe,
            min_episodes=args.min_episodes,
        )

        n_ep = len(episodes)

        # 2. Verificar condicao de minimo de episodios
        if n_ep < args.min_episodes:
            logger.info(f"[{sym}] SKIPPED: Apenas {n_ep} episodios "
                        f"(min={args.min_episodes}) ignorando treino.")
            skipped_count += 1
            summary["results"][sym] = {
                "status": "skipped",
                "reason": f"insufficient_episodes: {n_ep} < {args.min_episodes}",
                "episodes_found": n_ep,
            }
            continue

        # 3. Treinar EntryAgent via manager
        logger.info(f"[{sym}] TREINANDO Entry Agent (Episodios: {n_ep})...")
        train_result = manager.train_entry_agent(
            symbol=sym,
            episodes=episodes,
            total_timesteps=args.steps,
        )

        if train_result.get("success"):
            trained_count += 1
            summary["results"][sym] = {
                "status": "trained",
                "episodes_used": n_ep,
                "steps_run": args.steps,
            }
            logger.info(f"[{sym}] SUCCESS: Treino finalizado.")
        else:
            errors_count += 1
            error_reason = train_result.get("error", train_result.get("reason", "unknown"))
            summary["results"][sym] = {
                "status": "error",
                "error": error_reason,
                "episodes_found": n_ep,
            }
            logger.error(f"[{sym}] ERROR: {error_reason}")

    # 4. Salvar modelos se nao for dry-run e houver mudancas
    if not args.dry_run and trained_count > 0:
        logger.info("Salvando modelos e status em sub-agentes...")
        manager.save_all()
    elif args.dry_run:
        logger.info("[DRY-RUN] Pulando a gravacao dos modelos no disco.")

    summary["summary_stats"] = {
        "trained": trained_count,
        "skipped": skipped_count,
        "errors": errors_count,
    }

    # 5. Output Summary (JSON)
    results_dir = REPO_ROOT / "results" / "model2" / "runtime"
    results_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    summary_path = results_dir / f"entry_training_summary_{date_str}.json"

    with summary_path.open("w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Pipeline finalizada. Sumario salvo em: {summary_path}")
    logger.info(
        f"Resultado -> Trained: {trained_count} | "
        f"Skipped: {skipped_count} | Errors: {errors_count}"
    )


if __name__ == "__main__":
    run_training_pipeline()
=======
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
>>>>>>> 2bf2e7607858435dc5e8a384098b052404b53a35
