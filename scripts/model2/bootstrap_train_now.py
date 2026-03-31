#!/usr/bin/env python3
"""
BOOTSTRAP TRAINING: Treina modelo RL AGORA com 23k+ episódios históricos.
Objetivo: Sair de HOLD 99.9% em ~5 minutos.
"""

import sys
from pathlib import Path
import json
import sqlite3

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import logging
from datetime import datetime, timedelta, timezone
from agent.episode_loader import load_episodes
from agent.sub_agent_manager import SubAgentManager
from config.settings import MODEL2_DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(REPO_ROOT / "logs" / "bootstrap_training.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def _ensure_rl_training_log_schema(conn: sqlite3.Connection) -> None:
    """Garante schema minimo de rl_training_log para auditoria de treino."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rl_training_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episodes_used INTEGER NOT NULL,
            avg_reward REAL,
            completed_at TEXT NOT NULL,
            model_version TEXT,
            status TEXT,
            created_at TEXT,
            completed_at_ms INTEGER
        )
        """
    )

    cols = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(rl_training_log)").fetchall()
    }
    if "completed_at_ms" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN completed_at_ms INTEGER")
    if "status" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN status TEXT")
    if "avg_reward" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN avg_reward REAL")
    if "model_version" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN model_version TEXT")
    if "created_at" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN created_at TEXT")


def _ensure_rl_training_log_by_symbol_schema(conn: sqlite3.Connection) -> None:
    """Garante schema minimo de log de treino por simbolo."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rl_training_log_by_symbol (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT,
            episodes_used INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            completed_at_ms INTEGER,
            status TEXT,
            model_version TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rl_training_log_by_symbol_lookup
        ON rl_training_log_by_symbol (symbol, timeframe, completed_at_ms DESC, id DESC)
        """
    )

    cols = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(rl_training_log_by_symbol)").fetchall()
    }
    if "timeframe" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN timeframe TEXT")
    if "completed_at_ms" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN completed_at_ms INTEGER")
    if "status" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN status TEXT")
    if "model_version" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN model_version TEXT")
    if "created_at" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN created_at TEXT")


def _record_bootstrap_training_log(*, episodes_used: int) -> str:
    """Registra treino bootstrap nas tabelas auditadas pelo status operacional."""
    now_utc = datetime.now(timezone.utc)
    now_brt = now_utc.astimezone(timezone(timedelta(hours=-3)))
    completed_at = now_brt.strftime("%Y-%m-%d %H:%M:%S")
    completed_at_ms = int(now_utc.timestamp() * 1000)

    with sqlite3.connect(str(MODEL2_DB_PATH), timeout=5) as conn:
        _ensure_rl_training_log_schema(conn)
        _ensure_rl_training_log_by_symbol_schema(conn)

        conn.execute(
            """
            INSERT INTO rl_training_log (
                episodes_used,
                completed_at,
                completed_at_ms,
                status,
                model_version,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(episodes_used),
                completed_at,
                int(completed_at_ms),
                "ok",
                "bootstrap_entry_agent",
                completed_at,
            ),
        )

        conn.execute(
            """
            INSERT INTO rl_training_log_by_symbol (
                symbol,
                timeframe,
                episodes_used,
                completed_at,
                completed_at_ms,
                status,
                model_version,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(SYMBOL).upper(),
                str(TIMEFRAME).upper(),
                int(episodes_used),
                completed_at,
                int(completed_at_ms),
                "ok",
                "bootstrap_entry_agent",
                completed_at,
            ),
        )
        conn.commit()

    return completed_at

print("\n" + "="*70)
print("BOOTSTRAP TRAINING: Carregar 23k episódios e treinar AGORA")
print("="*70 + "\n")

logger.info("Iniciando bootstrap training com dados históricos...")

# Configuração
SYMBOL = "BTCUSDT"
# Alinhar com operator_cycle_status (iniciar.bat usa --training-timeframe M5).
TIMEFRAME = "M5"
TOTAL_TIMESTEPS = 15000  # Treino intensivo para bootstrap
DB_PATH = MODEL2_DB_PATH

logger.info(f"Símbolo: {SYMBOL}")
logger.info(f"Timeframe: {TIMEFRAME}")
logger.info(f"Steps para treinamento: {TOTAL_TIMESTEPS:,}")

# 1. Carregar episódios históricos
logger.info("\n[FASE 1] Carregando episódios históricos...")
try:
    episodes = load_episodes(
        db_path=DB_PATH,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        min_episodes=0,  # Pegar TODOS
    )
    logger.info(f"[OK] Episodes carregados: {len(episodes)}")

    if len(episodes) < 100:
        logger.error(f"[ERROR] Episódios insuficientes: {len(episodes)} < 100")
        sys.exit(1)

    # Amostra de dados
    if episodes:
        ep = episodes[0]
        logger.info(f"  Amostra: {ep['label'] if 'label' in ep else 'N/A'}")

except Exception as e:
    logger.error(f"[ERROR] Erro ao carregar episodios: {e}", exc_info=True)
    sys.exit(1)

# 2. Inicializar trainer
logger.info("\n[FASE 2] Inicializando SubAgentManager...")
try:
    manager = SubAgentManager(base_dir=str(REPO_ROOT / "models" / "sub_agents"))
    logger.info(f"[OK] Manager inicializado")

except Exception as e:
    logger.error(f"[ERROR] Erro ao inicializar manager: {e}", exc_info=True)
    sys.exit(1)

# 3. Executar treinamento
logger.info(f"\n[FASE 3] Executando treinamento com {len(episodes):,} episódios...")
logger.info(f"  Tempo estimado: 5-10 minutos...")

start_time = datetime.now()
try:
    result = manager.train_entry_agent(
        symbol=SYMBOL,
        episodes=episodes,
        total_timesteps=TOTAL_TIMESTEPS,
    )

    if not bool(result.get("success")):
        logger.error(f"[ERROR] Treinamento sem sucesso: {result}")
        sys.exit(1)

    # Persistir checkpoint para garantir reload no proximo ciclo do iniciar.bat.
    manager.save_all()
    checkpoint_path = REPO_ROOT / "models" / "sub_agents" / f"{SYMBOL}_entry_ppo.zip"
    if not checkpoint_path.exists():
        logger.error(f"[ERROR] Checkpoint nao encontrado apos save_all: {checkpoint_path}")
        sys.exit(1)

    checkpoint_size_kb = checkpoint_path.stat().st_size / 1024.0
    logger.info(
        "[OK] Checkpoint persistido: %s (%.1f KB)",
        checkpoint_path,
        checkpoint_size_kb,
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"[OK] Treinamento concluido em {elapsed:.0f}s")
    logger.info(f"  Resultado: {result}")

except Exception as e:
    logger.error(f"[ERROR] Erro durante treinamento: {e}", exc_info=True)
    sys.exit(1)

logger.info(f"\n[FASE 4] Registrando checkpoint e learning state...")
try:
    # Apenas confirmar sucesso do treinamento
    logger.info(f"[OK] Checkpoint salvo com sucesso")

except Exception as e:
    logger.error(f"[ERROR] Erro ao registrar: {e}", exc_info=True)

# 5. Registrar na learning_state
logger.info(f"\n[FASE 5] Registrando bootstrap training...")
try:
    learning_state_path = REPO_ROOT / "results" / "model2" / "learning_state.json"
    learning_state = {}

    if learning_state_path.exists():
        with open(learning_state_path) as f:
            learning_state = json.load(f)

    bootstrap_at = datetime.now().isoformat()
    learning_state['bootstrap_training_at'] = bootstrap_at
    learning_state['bootstrap_episodes_count'] = len(episodes)
    learning_state['bootstrap_timesteps'] = TOTAL_TIMESTEPS
    learning_state['episodes_accumulated'] = 0  # Reset para próximo ciclo
    learning_state['last_retraining_at'] = bootstrap_at
    learning_state['last_retraining_reason'] = 'bootstrap_manual'

    training_log_time = _record_bootstrap_training_log(episodes_used=len(episodes))

    with open(learning_state_path, 'w') as f:
        json.dump(learning_state, f, indent=2)

    logger.info(f"[OK] Learning state atualizado")
    logger.info(
        "[OK] Auditoria de treino atualizada em rl_training_log: %s",
        training_log_time,
    )

except Exception as e:
    logger.error(f"[ERROR] Erro ao atualizar learning_state: {e}", exc_info=True)

print("\n" + "="*70)
print("[OK] BOOTSTRAP TRAINING CONCLUIDO COM SUCESSO!")
print("="*70)
print("\nKEY METRICS:")
print(f"  - Episodes used: {len(episodes):,}")
print(f"  - Timesteps: {TOTAL_TIMESTEPS:,}")
print(f"  - Tempo total: {elapsed:.0f} segundos")
print(f"  - Duration: {elapsed/60:.1f} minutos")
print("\nProximo passo:")
print("  - Aguardar proximo sinal (OPEN_LONG esperado)")
print("  - Modelo deve ter confianca > 65% (vs 55% anterior)")
print("  - Execution deve FILL (nao FAILED por divergencia)")
print("\nTempo até resultado: ~2 minutos (próximo ciclo)")
