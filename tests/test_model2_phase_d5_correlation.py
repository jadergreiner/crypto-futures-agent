from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.model2.migrate import run_up
from scripts.model2.phase_d5_real_data_correlation import main as run_d5_analysis

# Helper para popular o banco de dados
def _prepare_and_populate_db(tmp_path: Path) -> Path:
    """Prepara o DB e insere dados mock para os testes."""
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    
    # 1. Cria o schema (isso já cria todas as tabelas necessárias)
    run_up(db_path=db_path, output_dir=output_dir)

    # 2. Popula com dados mock
    with sqlite3.connect(db_path) as conn:
        # A tabela `training_episodes` não faz parte da migração principal
        conn.execute(
        """
        CREATE TABLE IF NOT EXISTS training_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_key TEXT NOT NULL UNIQUE,
            cycle_run_id TEXT NOT NULL,
            execution_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            status TEXT NOT NULL,
            event_timestamp INTEGER NOT NULL,
            label TEXT NOT NULL,
            reward_proxy REAL,
            features_json TEXT NOT NULL,
            target_json TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_training_episodes_execution_id ON training_episodes(execution_id)"
        )

        # Insere `opportunities` para satisfazer as foreign keys
        conn.execute("INSERT INTO opportunities (id, symbol, timeframe, side, thesis_type, status, zone_low, zone_high, trigger_price, invalidation_price, created_at, updated_at, expires_at) VALUES (1, 'BTCUSDT', 'H4', 'SHORT', 'test', 'VALIDADA', 1, 2, 1, 2, 1, 1, 9999999999999)")
        conn.execute("INSERT INTO opportunities (id, symbol, timeframe, side, thesis_type, status, zone_low, zone_high, trigger_price, invalidation_price, created_at, updated_at, expires_at) VALUES (2, 'BTCUSDT', 'H4', 'SHORT', 'test', 'VALIDADA', 1, 2, 1, 2, 1, 1, 9999999999999)")
        conn.execute("INSERT INTO opportunities (id, symbol, timeframe, side, thesis_type, status, zone_low, zone_high, trigger_price, invalidation_price, created_at, updated_at, expires_at) VALUES (3, 'ETHUSDT', 'H4', 'SHORT', 'test', 'VALIDADA', 1, 2, 1, 2, 1, 1, 9999999999999)")
        conn.execute("INSERT INTO opportunities (id, symbol, timeframe, side, thesis_type, status, zone_low, zone_high, trigger_price, invalidation_price, created_at, updated_at, expires_at) VALUES (4, 'BTCUSDT', 'H4', 'SHORT', 'test', 'VALIDADA', 1, 2, 1, 2, 1, 1, 9999999999999)")

        # Insere `technical_signals`
        conn.execute("INSERT INTO technical_signals (id, opportunity_id, symbol, timeframe, signal_side, status, entry_type, entry_price, stop_loss, take_profit, signal_timestamp, rule_id, created_at, updated_at) VALUES (101, 1, 'BTCUSDT', 'H4', 'SHORT', 'CONSUMED', 'MARKET', 1, 1, 1, 1, 'test', 1, 1)")
        conn.execute("INSERT INTO technical_signals (id, opportunity_id, symbol, timeframe, signal_side, status, entry_type, entry_price, stop_loss, take_profit, signal_timestamp, rule_id, created_at, updated_at) VALUES (102, 2, 'BTCUSDT', 'H4', 'SHORT', 'CONSUMED', 'MARKET', 1, 1, 1, 1, 'test', 1, 1)")
        conn.execute("INSERT INTO technical_signals (id, opportunity_id, symbol, timeframe, signal_side, status, entry_type, entry_price, stop_loss, take_profit, signal_timestamp, rule_id, created_at, updated_at) VALUES (103, 3, 'ETHUSDT', 'H4', 'SHORT', 'CONSUMED', 'MARKET', 1, 1, 1, 1, 'test', 1, 1)")
        conn.execute("INSERT INTO technical_signals (id, opportunity_id, symbol, timeframe, signal_side, status, entry_type, entry_price, stop_loss, take_profit, signal_timestamp, rule_id, created_at, updated_at) VALUES (201, 4, 'BTCUSDT', 'H4', 'SHORT', 'CONSUMED', 'MARKET', 1, 1, 1, 1, 'test', 1, 1)")
        
        # Insere `signal_executions`
        conn.execute("INSERT INTO signal_executions (id, technical_signal_id, opportunity_id, symbol, timeframe, signal_side, execution_mode, status, entry_order_type, created_at, updated_at) VALUES (1, 101, 1, 'BTCUSDT', 'H4', 'SHORT', 'shadow', 'EXITED', 'MARKET', 1, 1)")
        conn.execute("INSERT INTO signal_executions (id, technical_signal_id, opportunity_id, symbol, timeframe, signal_side, execution_mode, status, entry_order_type, created_at, updated_at) VALUES (2, 102, 2, 'BTCUSDT', 'H4', 'SHORT', 'shadow', 'EXITED', 'MARKET', 1, 1)")
        conn.execute("INSERT INTO signal_executions (id, technical_signal_id, opportunity_id, symbol, timeframe, signal_side, execution_mode, status, entry_order_type, created_at, updated_at) VALUES (3, 103, 3, 'ETHUSDT', 'H4', 'SHORT', 'shadow', 'EXITED', 'MARKET', 1, 1)")
        conn.execute("INSERT INTO signal_executions (id, technical_signal_id, opportunity_id, symbol, timeframe, signal_side, execution_mode, status, entry_order_type, created_at, updated_at) VALUES (4, 201, 4, 'BTCUSDT', 'H4', 'SHORT', 'live', 'EXITED', 'MARKET', 1, 1)")

        # Insere episódios de treino
        episodes = [
            # Shadow mode episodes
            (1, 'win', 0.5, json.dumps({'funding_rates': {'sentiment': 'bullish'}, 'open_interest': {'oi_sentiment': 'accumulating'}})),
            (2, 'loss', -0.5, json.dumps({'funding_rates': {'sentiment': 'bearish'}, 'open_interest': {'oi_sentiment': 'distributing'}})),
            (3, 'breakeven', 0.0, json.dumps({'funding_rates': {'sentiment': 'neutral'}, 'open_interest': {'oi_sentiment': 'neutral'}})),
            # Live mode episode
            (4, 'win', 1.0, json.dumps({'funding_rates': {'sentiment': 'bullish'}, 'open_interest': {'oi_sentiment': 'accumulating'}})),
        ]
        
        for exec_id, label, reward, features in episodes:
            conn.execute(
                "INSERT INTO training_episodes (episode_key, cycle_run_id, execution_id, symbol, timeframe, status, event_timestamp, label, reward_proxy, features_json, target_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f'exec:{exec_id}:1', 'test_run', exec_id, 'BTCUSDT', 'H4', 'EXITED', 1, label, reward, features, '{}', 1)
            )
            
    return db_path

def test_d5_analyzer_insufficient_data(tmp_path: Path, capsys):
    """Testa se o script aborta quando min_episodes não é atingido."""
    db_path = _prepare_and_populate_db(tmp_path)
    output_dir = tmp_path / "analysis"

    test_args = [
        "prog_name", # Nome do programa, ignorado pelo argparse mas necessário na lista
        "--db", str(db_path),
        "--output-dir", str(output_dir),
        "--execution-mode", "shadow",
        "--min-episodes", "10", # Apenas 3 episódios shadow existem
    ]

    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as excinfo:
            run_d5_analysis()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Dados insuficientes" in captured.out
    assert "Encontrado(s) 3 episodio(s) para o modo 'shadow', mas o minimo requerido e 10" in captured.out

def test_d5_analyzer_happy_path_shadow_mode(tmp_path: Path, capsys):
    """Testa o caminho feliz da análise para o modo shadow."""
    db_path = _prepare_and_populate_db(tmp_path)
    output_dir = tmp_path / "analysis"

    test_args = [
        "prog_name",
        "--db", str(db_path),
        "--output-dir", str(output_dir),
        "--execution-mode", "shadow",
        "--min-episodes", "3",
    ]

    with patch.object(sys, 'argv', test_args):
         with pytest.raises(SystemExit) as excinfo:
            run_d5_analysis()

    assert excinfo.value.code == 0
    
    # Verifica se o arquivo de relatório foi criado
    report_files = list(output_dir.glob("phase_d5_correlation_shadow_*.json"))
    assert len(report_files) == 1
    report_path = report_files[0]
    
    # Carrega e valida o conteúdo do relatório
    report = json.loads(report_path.read_text())
    
    assert report["analysis_type"] == "Phase D.5 Real Data Correlation Analysis"
    assert report["execution_mode"] == "shadow"
    assert report["total_episodes"] == 3
    
    # Valida análise FR Sentiment vs Label
    fr_analysis = report["fr_sentiment_vs_label"]
    assert fr_analysis["status"] == "OK"
    assert fr_analysis["n_samples"] == 3
    assert "pearson_correlation" in fr_analysis
    assert fr_analysis["win_rates_by_sentiment"]["bullish"]["win_rate"] == 1.0
    assert fr_analysis["win_rates_by_sentiment"]["bearish"]["win_rate"] == 0.0
    assert fr_analysis["win_rates_by_sentiment"]["neutral"]["win_rate"] == 0.0

    # Valida análise OI Sentiment vs Label
    oi_analysis = report["oi_sentiment_vs_label"]
    assert oi_analysis["status"] == "OK"
    assert oi_analysis["n_samples"] == 3
    assert oi_analysis["win_rates_by_sentiment"]["accumulating"]["win_rate"] == 1.0
    assert oi_analysis["win_rates_by_sentiment"]["distributing"]["win_rate"] == 0.0
    assert oi_analysis["win_rates_by_sentiment"]["neutral"]["win_rate"] == 0.0

    # Valida recomendações
    assert len(report["recommendations"]) > 0
    assert any("[WARNING] Win rate baixo" in rec for rec in report["recommendations"])


def test_d5_analyzer_filters_live_mode(tmp_path: Path, capsys):
    """Testa se o filtro de modo de execução 'live' funciona."""
    db_path = _prepare_and_populate_db(tmp_path)
    output_dir = tmp_path / "analysis"

    test_args = [
        "prog_name",
        "--db", str(db_path),
        "--output-dir", str(output_dir),
        "--execution-mode", "live",
        "--min-episodes", "1",
    ]

    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as excinfo:
            run_d5_analysis()

    assert excinfo.value.code == 0
    
    report_files = list(output_dir.glob("phase_d5_correlation_live_*.json"))
    assert len(report_files) == 1
    report = json.loads(report_files[0].read_text())
    
    assert report["execution_mode"] == "live"
    assert report["total_episodes"] == 1
    
    # Com apenas 1 episódio, a análise deve retornar dados insuficientes
    assert report["fr_sentiment_vs_label"]["status"] == "INSUFFICIENT_DATA"
    assert report["oi_sentiment_vs_label"]["status"] == "INSUFFICIENT_DATA"
