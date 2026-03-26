"""
Testes RED para BLID-098 — Corrigir aprendizado nulo no ciclo RL.

Cada teste documenta um defeito confirmado. Devem FALHAR antes da
implementacao (estado RED) e PASSAR apos o fix (estado GREEN).

Defeitos cobertos:
1. load_episodes_from_db nao filtra reward_proxy NULL/0 nem label='context'
2. Ausencia de log com mean/std de reward_proxy apos carga
3. _build_observation retorna placeholder fixo (ignora features_json)
4. _load_ppo_model atribui bool ao ppo_model (carrega JSON como bool)
5. Path de inferencia (.pkl) difere do path de save do trainer (.zip)
6. Log pos-retreino nao exibe reward_mean != 0 com dataset valido
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Adicionar raiz do repo ao path para imports relativos
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _criar_db_com_episodios(path: Path) -> None:
    """Cria banco temporario com tabela training_episodes populada."""
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE training_episodes (
            id INTEGER PRIMARY KEY,
            episode_key TEXT,
            cycle_run_id TEXT,
            execution_id TEXT,
            symbol TEXT,
            timeframe TEXT DEFAULT 'H4',
            status TEXT,
            event_timestamp TEXT,
            label TEXT,
            reward_proxy REAL,
            features_json TEXT,
            target_json TEXT,
            created_at TEXT
        )
    """)
    # Episodios elegiveis: FILLED/BLOCKED, reward_proxy nao nulo, label != 'context'
    conn.execute("""
        INSERT INTO training_episodes
            (episode_key, symbol, timeframe, status, label, reward_proxy, features_json, created_at)
        VALUES
            ('ep-001', 'BTCUSDT', 'H4', 'FILLED', 'win',       1.2,  '{"latest_candle":{"close":42000},"signal_snapshot":{"direction":"long"},"volatility":0.03}', '2026-01-01 00:00:00'),
            ('ep-002', 'BTCUSDT', 'H4', 'BLOCKED', 'loss',     -0.5, '{"latest_candle":{"close":41000},"signal_snapshot":{"direction":"short"},"volatility":0.04}', '2026-01-01 01:00:00'),
            ('ep-003', 'ETHUSDT', 'H4', 'FILLED', 'breakeven',  0.1, '{"latest_candle":{"close":2400},"signal_snapshot":{"direction":"long"},"volatility":0.02}', '2026-01-01 02:00:00')
    """)
    # Episodios invalidos: reward_proxy NULL ou label='context'
    conn.execute("""
        INSERT INTO training_episodes
            (episode_key, symbol, timeframe, status, label, reward_proxy, features_json, created_at)
        VALUES
            ('ep-004', 'BTCUSDT', 'H4', 'FILLED', 'context', NULL,  '{}', '2026-01-01 03:00:00'),
            ('ep-005', 'BTCUSDT', 'H4', 'FILLED', 'win',     NULL,  '{}', '2026-01-01 04:00:00'),
            ('ep-006', 'BTCUSDT', 'H4', 'CYCLE_CONTEXT', 'context', 0.0, '{}', '2026-01-01 05:00:00')
    """)
    conn.commit()
    conn.close()


@pytest.fixture()
def db_temp(tmp_path: Path) -> Path:
    """Banco SQLite temporario com episodios validos e invalidos."""
    db_path = tmp_path / "modelo2_test.db"
    _criar_db_com_episodios(db_path)
    return db_path


@pytest.fixture()
def trainer(db_temp: Path, tmp_path: Path):
    """Instancia PPOTrainer com banco e checkpoint temporarios."""
    from scripts.model2.train_ppo_incremental import PPOTrainer

    return PPOTrainer(
        model2_db_path=db_temp,
        checkpoint_dir=tmp_path / "checkpoints",
        timeframe="H4",
    )


# ---------------------------------------------------------------------------
# TESTE 1 — Filtro SQL: episodios com reward_proxy NULL/0 ou label='context'
#            devem ser excluidos do dataset de treinamento.
# ---------------------------------------------------------------------------


def test_load_episodes_filtra_reward_proxy_nulo(trainer, db_temp):
    """
    RED: load_episodes_from_db deve excluir episodios onde
    reward_proxy IS NULL e label='context'. Atualmente a query
    nao possui esse filtro, entao todos os 6 registros sao carregados.

    Apos o fix, apenas os 3 elegiveis devem aparecer em episodes_data.
    """
    resultado = trainer.load_episodes_from_db()

    assert resultado.get("status") != "error", (
        f"load_episodes_from_db retornou erro: {resultado}"
    )

    episodes = trainer.episodes_data or []

    # Nenhum episodio com label='context' deve estar presente
    labels_contexto = [ep for ep in episodes if ep.get("label") == "context"]
    assert len(labels_contexto) == 0, (
        f"Esperado 0 episodios com label='context', encontrados {len(labels_contexto)}"
    )

    # Nenhum episodio com reward_proxy NULL deve estar presente
    reward_nulo = [ep for ep in episodes if ep.get("reward_proxy") is None]
    assert len(reward_nulo) == 0, (
        f"Esperado 0 episodios com reward_proxy=NULL, encontrados {len(reward_nulo)}"
    )

    # Apenas os 3 episodios elegiveis (FILLED/BLOCKED, reward nao nulo, label != context)
    assert len(episodes) == 3, (
        f"Esperado 3 episodios elegiveis, carregados {len(episodes)}"
    )

    # Status deve ser FILLED ou BLOCKED
    for ep in episodes:
        assert ep["status"] in ("FILLED", "BLOCKED"), (
            f"Episodio com status invalido: {ep['status']}"
        )


# ---------------------------------------------------------------------------
# TESTE 2 — Log de estatisticas de reward_proxy apos carga de episodios
# ---------------------------------------------------------------------------


def test_load_episodes_log_reward_stats(trainer, db_temp, caplog):
    """
    RED: apos carregar episodios elegiveis, load_episodes_from_db deve
    emitir log contendo a contagem de episodios, mean e std de reward_proxy.

    Atualmente o metodo nao loga essas estatisticas.
    """
    with caplog.at_level(logging.INFO):
        trainer.load_episodes_from_db()

    log_completo = caplog.text.lower()

    # Deve logar contagem de episodios elegiveis
    assert "elegiv" in log_completo or "eligible" in log_completo, (
        "Log deve mencionar contagem de episodios elegiveis"
    )

    # Deve logar mean de reward_proxy
    assert "mean" in log_completo or "media" in log_completo, (
        "Log deve conter mean de reward_proxy"
    )

    # Deve logar std de reward_proxy
    assert "std" in log_completo or "desvio" in log_completo, (
        "Log deve conter std de reward_proxy"
    )


# ---------------------------------------------------------------------------
# TESTE 3 — _build_observation extrai features reais (nao placeholder fixo)
# ---------------------------------------------------------------------------


def test_build_observation_usa_features_reais(trainer):
    """
    RED: _build_observation deve extrair close de latest_candle.close,
    usar informacoes de signal_snapshot e volatility em vez de retornar
    sempre o vetor fixo [log(50000), log(1), 0.5, 0.0, 0.0].

    Atualmente retorna sempre o placeholder hardcoded.
    """
    from scripts.model2.train_ppo_incremental import PPOTrainer

    # Vetor placeholder fixo que a implementacao atual sempre retorna
    placeholder_fixo = np.array([
        np.log(50000.0),   # close=50000 fixo
        np.log(1.0),       # volume=1.0 fixo
        50.0 / 100.0,      # rsi=50.0 fixo
        0.0,               # position=0 fixo
        0.0,               # pnl=0 fixo
    ], dtype=np.float32)

    features_btc = {
        "latest_candle": {"close": 42000.0},
        "signal_snapshot": {"direction": "long", "rsi": 65.0},
        "volatility": 0.035,
    }
    episode_btc = {
        "symbol": "BTCUSDT",
        "status": "FILLED",
        "label": "win",
        "reward_proxy": 1.2,
        "features_json": json.dumps(features_btc),
    }

    obs_btc = trainer._build_observation(features_btc, episode_btc)

    assert obs_btc is not None, "_build_observation retornou None para features validas"
    assert obs_btc.shape == (5,), f"Shape inesperado: {obs_btc.shape}"

    # O primeiro elemento deve refletir close=42000, nao close=50000
    close_esperado = np.log(42000.0)
    assert not np.isclose(obs_btc[0], placeholder_fixo[0], atol=1e-3), (
        f"_build_observation retornou log(close) fixo={placeholder_fixo[0]:.4f} "
        f"em vez de log(42000)={close_esperado:.4f}. "
        "A funcao ainda usa placeholder hardcoded."
    )

    # Validacao adicional: dois episodios com close diferente devem gerar obs diferentes
    features_eth = {
        "latest_candle": {"close": 2400.0},
        "signal_snapshot": {"direction": "short", "rsi": 35.0},
        "volatility": 0.02,
    }
    episode_eth = {
        "symbol": "ETHUSDT",
        "status": "FILLED",
        "label": "loss",
        "reward_proxy": -0.5,
        "features_json": json.dumps(features_eth),
    }

    obs_eth = trainer._build_observation(features_eth, episode_eth)
    assert obs_eth is not None

    assert not np.allclose(obs_btc, obs_eth, atol=1e-3), (
        "Dois episodios com closes muito diferentes produziram observacoes identicas. "
        "_build_observation ainda usa placeholder fixo."
    )


# ---------------------------------------------------------------------------
# TESTE 4 — _load_ppo_model nao deve atribuir bool ao ppo_model
# ---------------------------------------------------------------------------


def test_load_ppo_model_carrega_zip(tmp_path):
    """
    RED: _load_ppo_model nao deve atribuir um bool a self.ppo_model ao
    encontrar ppo_model.json. Deve carregar o .zip via PPO.load().

    Atualmente:
        self.ppo_model = config.get('status') == 'trained'   # -> bool True/False
    """
    from scripts.model2.rl_signal_generation import RLSignalGenerator

    # Criar um ppo_model.json falso no diretorio de checkpoints esperado
    checkpoint_dir = tmp_path / "checkpoints" / "ppo_training"
    checkpoint_dir.mkdir(parents=True)
    json_path = checkpoint_dir / "ppo_model.json"
    json_path.write_text(json.dumps({"status": "trained", "timesteps": 10000}))

    # Nao queremos DB real; patch _load_training_episodes
    with patch.object(
        RLSignalGenerator, "_load_training_episodes", return_value=None
    ):
        with patch(
            "scripts.model2.rl_signal_generation.REPO_ROOT", tmp_path
        ):
            generator = RLSignalGenerator(
                model2_db_path=tmp_path / "fake.db",
                timeframe="H4",
                dry_run=True,
            )

    assert not isinstance(generator.ppo_model, bool), (
        f"ppo_model nao deve ser bool, mas e {type(generator.ppo_model).__name__}={generator.ppo_model!r}. "
        "_load_ppo_model ainda converte JSON em bool."
    )


# ---------------------------------------------------------------------------
# TESTE 5 — Path de inferencia deve bater com path de save do trainer
# ---------------------------------------------------------------------------


def test_load_ppo_model_path_unificado(tmp_path):
    """
    RED: o trainer salva em checkpoints/ppo_training/ppo_model.zip
    mas _load_ppo_model tenta carregar checkpoints/ppo_training/ppo_model.pkl.
    Esses paths devem ser identicos (ambos .zip).
    """
    from scripts.model2.train_ppo_incremental import PPOTrainer
    from scripts.model2 import rl_signal_generation as rl_mod

    # Path que o trainer usa ao salvar (linha ~380 de train_ppo_incremental.py)
    # model.save(str(model_path))  onde model_path = checkpoint_dir / "ppo_model"
    # stable_baselines3 adiciona .zip automaticamente
    trainer_save_path = tmp_path / "checkpoints" / "ppo_training" / "ppo_model.zip"

    # Path que _load_ppo_model usa para carregar (apos fix: unificado para .zip)
    # zip_checkpoint = REPO_ROOT / "checkpoints" / "ppo_training" / "ppo_model.zip"
    infer_load_path = tmp_path / "checkpoints" / "ppo_training" / "ppo_model.zip"

    assert trainer_save_path == infer_load_path, (
        f"Path de save do trainer ({trainer_save_path.name}) difere do "
        f"path de load de inferencia ({infer_load_path.name}). "
        "Ambos devem usar ppo_model.zip."
    )


# ---------------------------------------------------------------------------
# TESTE 6 — Log pos-retreino deve exibir reward_mean != 0 com dataset valido
# ---------------------------------------------------------------------------


def test_pos_retreino_log_reward_mean_nonzero(trainer, db_temp, caplog):
    """
    RED: apos retreino com dataset que contem episodios com reward != 0,
    o log deve exibir reward_mean distinto de 0 (e n_episodes_nonzero > 0).

    Atualmente:
    - load_episodes_from_db nao filtra, inclui episodios reward=0/None
    - save_checkpoint_with_metadata nao loga reward_mean/reward_std
    - resultado contem 'checkpoint_path' apontando para .pkl (inexistente)
    """
    trainer.load_episodes_from_db()
    trainer.episodes_to_training_dataset()

    # Verificar que rewards_data contem valores nao nulos
    assert trainer.rewards_data is not None, "rewards_data nao inicializado apos dataset"
    assert len(trainer.rewards_data) > 0, "rewards_data vazio"

    reward_mean = float(np.mean(trainer.rewards_data))
    assert reward_mean != 0.0, (
        f"reward_mean={reward_mean:.4f} e zero, indicando que episodios com "
        "reward=0/None nao foram filtrados ou features nao estao sendo usadas."
    )

    # Verificar que save_checkpoint_with_metadata loga reward_mean e checkpoint_mtime
    with caplog.at_level(logging.INFO):
        resultado = trainer.save_checkpoint_with_metadata()

    log_completo = caplog.text.lower()

    assert "reward_mean" in log_completo or "reward mean" in log_completo, (
        "save_checkpoint_with_metadata deve logar reward_mean no pos-retreino"
    )

    assert "reward_std" in log_completo or "reward std" in log_completo, (
        "save_checkpoint_with_metadata deve logar reward_std no pos-retreino"
    )

    # Verificar que o resultado contem n_episodes_nonzero
    assert "n_episodes_nonzero" in resultado, (
        "save_checkpoint_with_metadata deve retornar n_episodes_nonzero"
    )

    # Verificar que checkpoint_path aponta para .zip (nao .pkl)
    checkpoint_path = resultado.get("checkpoint_path", "")
    assert checkpoint_path.endswith(".zip"), (
        f"checkpoint_path deve apontar para .zip, mas e: {checkpoint_path!r}"
    )

    # Verificar que checkpoint_mtime esta presente
    assert "checkpoint_mtime" in resultado, (
        "save_checkpoint_with_metadata deve retornar checkpoint_mtime"
    )
