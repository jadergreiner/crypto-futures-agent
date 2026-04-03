from __future__ import annotations

import json
import sqlite3
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from scripts.model2.continuous_learning_controller import should_run_continuous_cycle, mark_run_executed
from scripts.model2.continuous_learning_cycle import run_continuous_learning_cycle_once

# Matriz de Rastreabilidade
# T001 -> RF-01 -> ADR-006 -> continuous_learning_controller -> unit
# T002 -> RF-02 -> ADR-007 -> promotion_gate -> unit
# T003 -> RF-03 -> ADR-007 -> promotion_gate -> unit
# T004 -> RF-04 -> ADR-006 -> continuous_learning_controller -> idempotency
# T005 -> RF-05 -> ADR-009 -> training_runs -> observability

def _prepare_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS training_episodes (id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT, label TEXT, status TEXT, reward_proxy REAL, created_at INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS training_runs (id INTEGER PRIMARY KEY, model_version_candidate TEXT, dataset_window TEXT, metrics_json TEXT, go_no_go TEXT, created_at INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS rl_training_audit (id INTEGER PRIMARY KEY, triggered_at_ms INTEGER, trigger_reason TEXT, status TEXT)")
        conn.commit()

@pytest.fixture
def mock_db(tmp_path):
    db_path = tmp_path / "db" / "modelo2.db"
    _prepare_db(db_path)
    # Mocking the constants in the scripts to use our temp DB
    with patch("scripts.model2.continuous_learning_controller.DB_PATH", db_path), \
         patch("scripts.model2.continuous_learning_cycle.MODEL2_DB_PATH", db_path):
        yield db_path

def test_controller_triggers_retrain_when_episodes_above_threshold(mock_db, tmp_path):
    """T001: Validar se o controller dispara quando episódios >= threshold."""
    # Arrange: Inserir episódios suficientes
    with sqlite3.connect(str(mock_db)) as conn:
        conn.executemany(
            "INSERT INTO training_episodes (symbol, timeframe, label, status, reward_proxy, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [("BTCUSDT", "M5", "trade", "WIN", 1.0, 1000 + i) for i in range(101)]
        )
        conn.commit()

    # Act
    with patch("scripts.model2.continuous_learning_controller.STATE_FILE", tmp_path / "state.json"):
        should_run, reason = should_run_continuous_cycle(min_new_episodes=100, symbols=["BTCUSDT"])

    # Assert
    assert should_run is True
    assert "pendentes" in reason.lower()

def test_cycle_implements_promotion_gate_with_sharpe_comparison(mock_db, tmp_path):
    """T002: Validar que o ciclo rejeita um modelo se o Sharpe Ratio for menor que o baseline."""
    # Este teste deve FALHAR (RED) porque a lógica de gate ainda não existe no scripts/model2/continuous_learning_cycle.py
    
    # Mock dos scripts de treino para retornar métricas simuladas
    with patch("scripts.model2.continuous_learning_cycle.run_train_entry_agents") as mock_train:
        # Simular que o treino gerou um modelo com Sharpe baixo (0.5 vs baseline 1.0)
        mock_train.return_value = {"status": "ok", "metrics": {"sharpe": 0.5, "win_rate": 0.4}}
        
        # Simular que temos um modelo ativo com Sharpe 1.0
        # (Isso exige que o script leia o baseline de algum lugar)
        
        summary = run_continuous_learning_cycle_once(
            source_db_path=tmp_path / "source.db",
            model2_db_path=mock_db,
            symbols=["BTCUSDT"],
            timeframe="M5",
            output_dir=tmp_path / "output",
            enable_retrain=True,
            enable_collection=False,
            enable_persist=False
        )
        
        # Esperamos que o sumário indique que a promoção foi REJEITADA
        # Atualmente o ciclo não possui essa chave "promotion_status"
        assert "promotion_status" in summary
        assert summary["promotion_status"] == "NO_GO"

def test_controller_prevents_simultaneous_runs(mock_db, tmp_path):
    """T004: Validar idempotência do trigger de retreino."""
    state_file = tmp_path / "state.json"
    with patch("scripts.model2.continuous_learning_controller.STATE_FILE", state_file):
        # Arrange: Marcar como executado há 1 minuto
        last_run = (datetime.now() - timedelta(minutes=1)).isoformat()
        with open(state_file, "w") as f:
            json.dump({"last_continuous_run": last_run, "symbol_states": {"BTCUSDT": {"last_continuous_run": last_run}}}, f)
            
        # Act: Tentar rodar com intervalo mínimo de 2 horas
        should_run, reason = should_run_continuous_cycle(min_hours_between_runs=2.0, symbols=["BTCUSDT"])
        
    # Assert
    assert should_run is False
    assert "proxima execução" in reason.lower()

def test_promotion_gate_persists_decision_in_training_runs(mock_db, tmp_path):
    """T005: Verificar se a decisão do gate (GO/NO-GO) é persistida em training_runs."""
    # RED: training_runs atualmente não é populada pelo continuous_learning_cycle.py
    
    with patch("scripts.model2.continuous_learning_cycle.run_train_entry_agents") as mock_train:
        mock_train.return_value = {"status": "ok", "metrics": {"sharpe": 2.0, "win_rate": 0.6}, "episodes_used": 120}
        
        run_continuous_learning_cycle_once(
            source_db_path=tmp_path / "source.db",
            model2_db_path=mock_db,
            symbols=["BTCUSDT"],
            timeframe="M5",
            output_dir=tmp_path / "output",
            enable_retrain=True,
            enable_collection=False,
            enable_persist=False
        )
        
        with sqlite3.connect(str(mock_db)) as conn:
            row = conn.execute("SELECT go_no_go, metrics_json FROM training_runs ORDER BY id DESC LIMIT 1").fetchone()
            
        assert row is not None
        assert row[0] == "GO"
        metrics = json.loads(row[1])
        assert metrics["sharpe"] == 2.0

def test_cycle_failsafe_on_training_error(mock_db, tmp_path):
    """T007: Garantir que se o treino falhar, o sistema mantém o modelo anterior (Fail-safe)."""
    with patch("scripts.model2.continuous_learning_cycle.run_train_entry_agents", side_effect=Exception("GPU Error")):
        summary = run_continuous_learning_cycle_once(
            source_db_path=tmp_path / "source.db",
            model2_db_path=mock_db,
            symbols=["BTCUSDT"],
            timeframe="M5",
            output_dir=tmp_path / "output",
            enable_retrain=True
        )
        
        # O ciclo deve reportar o erro mas não quebrar o sistema
        assert summary["status"] == "partial"
        assert any(e["stage"] == "retreino_entry_agents" for e in summary["stage_errors"])
