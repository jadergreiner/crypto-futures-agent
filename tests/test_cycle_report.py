"""Testes para modulo cycle_report.py."""

import sqlite3
import sys
from pathlib import Path

import pytest
from core.model2.cycle_report import (
    SymbolReport,
    collect_training_info,
    format_symbol_report,
    format_cycle_summary,
    _decision_icon,
    _progress_bar,
)


class TestSymbolReport:
    """Testes para dataclass SymbolReport."""

    def test_creation_minimal(self):
        """SymbolReport criado com campos minimos."""
        r = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03"
        )
        assert r.symbol == "BTCUSDT"
        assert r.timeframe == "H4"
        assert r.decision == "INDEFINIDA"
        assert r.pending_episodes == 0

    def test_creation_full(self):
        """SymbolReport com todos os campos."""
        r = SymbolReport(
            symbol="ETHUSDT",
            timeframe="H1",
            timestamp="2026-03-22 08:54:03",
            candles_count=500,
            last_candle_time="2026-03-22 08:00 UTC",
            decision="OPEN_LONG",
            confidence=0.89,
            decision_fresh=True,
            episode_id=1850,
            episode_persisted=True,
            reward=0.0120,
            last_train_time="2026-03-15 17:22:40",
            pending_episodes=37,
            has_position=True,
            position_side="LONG",
            position_qty=0.05,
            position_entry_price=1823.40,
            position_mark_price=1847.10,
            position_pnl_pct=1.23,
            position_pnl_usd=11.20,
            execution_mode="shadow"
        )
        assert r.symbol == "ETHUSDT"
        assert r.confidence == 0.89
        assert r.position_pnl_pct == 1.23


class TestDecisionIcon:
    """Testes para funcao _decision_icon."""

    def test_open_long(self):
        """Icone para OPEN_LONG."""
        assert _decision_icon("OPEN_LONG") == "🟢"

    def test_open_short(self):
        """Icone para OPEN_SHORT."""
        assert _decision_icon("OPEN_SHORT") == "🔴"

    def test_hold(self):
        """Icone para HOLD."""
        assert _decision_icon("HOLD") == "⏸"

    def test_unknown(self):
        """Icone para decisao desconhecida."""
        assert _decision_icon("UNKNOWN") == "❓"


class TestProgressBar:
    """Testes para funcao _progress_bar."""

    def test_empty(self):
        """Barra vazia (0%)."""
        bar = _progress_bar(0.0, width=10)
        assert bar == "[░░░░░░░░░░]"

    def test_full(self):
        """Barra cheia (100%)."""
        bar = _progress_bar(1.0, width=10)
        assert bar == "[██████████]"

    def test_half(self):
        """Barra meia (50%)."""
        bar = _progress_bar(0.5, width=10)
        assert bar == "[█████░░░░░]"


def _criar_db_treino(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS training_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_key TEXT,
                cycle_run_id TEXT,
                execution_id INTEGER,
                symbol TEXT,
                timeframe TEXT,
                status TEXT,
                event_timestamp INTEGER,
                label TEXT,
                reward_proxy REAL,
                features_json TEXT,
                target_json TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS rl_training_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                completed_at TEXT,
                episodes_used INTEGER,
                status TEXT
            );
            """
        )


def _inserir_episodio_treino(
    db_path: Path,
    *,
    status: str,
    created_at: str,
    label: str = "win",
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO training_episodes (
                episode_key,
                cycle_run_id,
                execution_id,
                symbol,
                timeframe,
                status,
                event_timestamp,
                label,
                reward_proxy,
                features_json,
                target_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"ep_{status}_{created_at}",
                "cycle-red",
                1,
                "BTCUSDT",
                "H4",
                status,
                1_700_000_000_000,
                label,
                0.5,
                "{}",
                "{}",
                created_at,
            ),
        )


class TestCollectTrainingInfo:
    """Testes para coleta de backlog/treino incremental."""

    def test_collect_training_info_le_training_episodes_nao_rl_episodes(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = tmp_path / "modelo2.db"
        _criar_db_treino(db_path)

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO rl_training_log (completed_at, episodes_used, status)
                VALUES (?, ?, ?)
                """,
                ("2026-03-22 10:00:00", 12, "ok"),
            )

        _inserir_episodio_treino(
            db_path,
            status="win",
            created_at="2026-03-22 10:30:00",
        )
        _inserir_episodio_treino(
            db_path,
            status="loss",
            created_at="2026-03-22 11:00:00",
        )
        _inserir_episodio_treino(
            db_path,
            status="pending",
            created_at="2026-03-22 11:30:00",
            label="pending",
        )

        last_train, pending = collect_training_info(str(db_path))

        assert last_train == "2026-03-22 10:00:00"
        assert pending == 2

    def test_collect_training_info_pendentes_zero_quando_tabela_vazia(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = tmp_path / "modelo2.db"
        _criar_db_treino(db_path)

        last_train, pending = collect_training_info(str(db_path))

        assert last_train == "nunca"
        assert pending == 0

    def test_pendentes_decaem_apos_treino_registrado(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = tmp_path / "modelo2.db"
        _criar_db_treino(db_path)

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO rl_training_log (completed_at, episodes_used, status)
                VALUES (?, ?, ?)
                """,
                ("2026-03-22 10:00:00", 8, "ok"),
            )

        _inserir_episodio_treino(
            db_path,
            status="win",
            created_at="2026-03-22 10:30:00",
        )
        _inserir_episodio_treino(
            db_path,
            status="loss",
            created_at="2026-03-22 11:15:00",
        )

        _, pending_antes = collect_training_info(str(db_path))

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO rl_training_log (completed_at, episodes_used, status)
                VALUES (?, ?, ?)
                """,
                ("2026-03-22 11:00:00", 1, "ok"),
            )

        _, pending_depois = collect_training_info(str(db_path))

        assert pending_antes == 2
        assert pending_depois == 1

    def test_collect_training_info_fallback_seguro_tabela_ausente(
        self,
        tmp_path: Path,
    ) -> None:
        db_path = tmp_path / "modelo2.db"
        db_path.touch()

        last_train, pending = collect_training_info(str(db_path))

        assert last_train == "nunca"
        assert pending == 0


class TestFormatSymbolReport:
    """Testes para funcao format_symbol_report."""

    def test_format_symbol_report_confianca_zero(self) -> None:
        """BLID-079: confidence=0.0 deve exibir 0% e nao N/A."""
        report = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            decision="OPEN_SHORT",
            confidence=0.0,
            execution_mode="shadow",
        )

        output = format_symbol_report(report)

        assert "confianca: 0%" in output

    def test_format_symbol_report_confianca_positiva(self) -> None:
        """Confidence positiva continua sendo formatada como porcentagem."""
        report = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            decision="OPEN_SHORT",
            confidence=0.25,
            execution_mode="live",
        )

        output = format_symbol_report(report)

        assert "confianca: 25%" in output

    def test_format_symbol_report_confianca_nao_inicializada_exibe_na(self) -> None:
        """Quando confidence e None, o formato continua exibindo N/A."""
        report = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            decision="OPEN_SHORT",
            confidence=None,
            execution_mode="live",
        )

        output = format_symbol_report(report)

        assert "confianca: N/A" in output

    def test_cycle_report_integrado_confianca_shadow_equals_live(self) -> None:
        """BLID-079: shadow e live exibem a mesma confianca para 0.0."""
        shadow = format_symbol_report(
            SymbolReport(
                symbol="BTCUSDT",
                timeframe="H4",
                timestamp="2026-03-22 08:54:03",
                decision="OPEN_SHORT",
                confidence=0.0,
                execution_mode="shadow",
            )
        )
        live = format_symbol_report(
            SymbolReport(
                symbol="BTCUSDT",
                timeframe="H4",
                timestamp="2026-03-22 08:54:03",
                decision="OPEN_SHORT",
                confidence=0.0,
                execution_mode="live",
            )
        )

        assert "confianca: 0%" in shadow
        assert "confianca: 0%" in live

    def test_barra_progresso_proporcional_a_pendentes(self) -> None:
        """BLID-081: barra reflete backlog proporcional ao threshold."""
        report = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            pending_episodes=25,
            retrain_threshold=100,
        )

        output = format_symbol_report(report)

        assert "25/100" in output
        assert "[██░░░░░░░░]" in output

    def test_format_hold_no_position(self):
        """Formata relatorio de HOLD sem posicao."""
        r = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            candles_count=500,
            last_candle_time="2026-03-22 08:00 UTC",
            decision="HOLD",
            confidence=0.72,
            episode_id=1847,
            reward=-0.0030,
            last_train_time="2026-03-15 17:22:40",
            pending_episodes=37,
            execution_mode="shadow"
        )
        output = format_symbol_report(r)
        assert "BTCUSDT" in output
        assert "⏸" in output
        assert "HOLD" in output
        assert "SEM POSICAO" in output
        assert "37/100" in output

    def test_format_open_long_with_position(self):
        """Formata relatorio de OPEN_LONG com posicao aberta."""
        r = SymbolReport(
            symbol="ETHUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            candles_count=500,
            decision="OPEN_LONG",
            confidence=0.89,
            episode_id=1850,
            reward=0.0120,
            has_position=True,
            position_side="LONG",
            position_qty=0.05,
            position_entry_price=1823.40,
            position_mark_price=1847.10,
            position_pnl_pct=1.23,
            position_pnl_usd=11.20,
            execution_mode="shadow"
        )
        output = format_symbol_report(r)
        assert "ETHUSDT" in output
        assert "🟢" in output
        assert "OPEN_LONG" in output
        assert "LONG" in output
        assert "0.05" in output
        assert "1.23" in output

    def test_output_structure(self):
        """Valida estrutura do output (separadores, linhas)."""
        r = SymbolReport(
            symbol="TEST",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03"
        )
        output = format_symbol_report(r)
        lines = output.split("\n")
        # Deve ter separador superior, dados, separador inferior
        assert lines[0].startswith("─")
        assert lines[-1].startswith("─")
        assert len(lines) >= 8  # pelo menos header + 6 campos + 2 separadores


class TestFormatCycleSummary:
    """Testes para funcao format_cycle_summary."""

    def test_cycle_summary_single_symbol(self):
        """Formata resumo com um simbolo."""
        r1 = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            decision="HOLD"
        )
        output = format_cycle_summary([r1], cycle_number=47, next_cycle_time="2026-03-22 09:00")
        assert "CICLO #47" in output
        assert "Resumo: 1 simbolos" in output
        assert "1 HOLD" in output

    def test_cycle_summary_multiple_symbols(self):
        """Formata resumo com múltiplos símbolos."""
        reports = [
            SymbolReport(
                symbol="BTCUSDT",
                timeframe="H4",
                timestamp="2026-03-22 08:54:03",
                decision="HOLD"
            ),
            SymbolReport(
                symbol="ETHUSDT",
                timeframe="H4",
                timestamp="2026-03-22 08:54:03",
                decision="OPEN_LONG"
            ),
        ]
        output = format_cycle_summary(reports, cycle_number=47, next_cycle_time="2026-03-22 09:00")
        assert "CICLO #47" in output
        assert "Resumo: 2 simbolos" in output
        assert "1 sinais" in output
        assert "1 HOLD" in output

    def test_cycle_summary_with_pnl(self):
        """Formata resumo com PnL total."""
        reports = [
            SymbolReport(
                symbol="BTCUSDT",
                timeframe="H4",
                timestamp="2026-03-22 08:54:03",
                has_position=True,
                position_pnl_usd=50.0
            ),
        ]
        output = format_cycle_summary(reports, cycle_number=47, next_cycle_time="2026-03-22 09:00")
        assert "PnL total" in output
        assert "$50.00" in output or "50.0" in output


def test_train_ppo_incremental_escreve_rl_training_log_apos_treino(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BLID-081: treino incremental deve registrar rl_training_log."""
    import numpy as np

    from scripts.model2 import train_ppo_incremental as train_module

    db_path = tmp_path / "modelo2.db"
    _criar_db_treino(db_path)

    def _fake_load(self):
        self.episodes_data = [{"id": 1}]
        return {
            "status": "ok",
            "total_episodes": 1,
            "timeframe": "H4",
            "symbols": ["BTCUSDT"],
            "labels": {"win": 1},
        }

    def _fake_dataset(self):
        self.obs_data = np.array([[0, 0, 0, 0, 0]], dtype=np.float32)
        self.rewards_data = np.array([0.5], dtype=np.float32)
        return {
            "status": "ok",
            "observations_shape": (1, 5),
            "rewards_shape": (1,),
            "mean_reward": 0.5,
            "std_reward": 0.0,
            "reward_range": (0.5, 0.5),
        }

    monkeypatch.setattr(train_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(train_module.PPOTrainer, "load_episodes_from_db", _fake_load)
    monkeypatch.setattr(
        train_module.PPOTrainer,
        "episodes_to_training_dataset",
        _fake_dataset,
    )
    monkeypatch.setattr(
        train_module.PPOTrainer,
        "train_ppo_incremental",
        lambda self, timesteps: {
            "status": "ok",
            "timesteps_trained": timesteps,
            "episodes_used": 1,
        },
    )
    monkeypatch.setattr(
        train_module.PPOTrainer,
        "save_checkpoint_with_metadata",
        lambda self: {"status": "ok", "metadata_path": str(tmp_path / "meta.json")},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train_ppo_incremental.py",
            "--model2-db-path",
            str(db_path),
            "--checkpoint-dir",
            str(tmp_path / "checkpoints"),
            "--timesteps",
            "10",
        ],
    )

    exit_code = train_module.main()

    assert exit_code == 0
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT completed_at, episodes_used, status FROM rl_training_log"
        ).fetchone()

    assert row is not None
    assert row[0]
    assert int(row[1]) == 1
    assert row[2] == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
