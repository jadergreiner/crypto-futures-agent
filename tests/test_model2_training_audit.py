"""Suite RED M2-022.2: Auditoria de trigger de treino incremental.

Objetivo:
- R1: trilha de auditoria persistida em rl_training_audit
- R2: trigger nao duplica treino quando processo em andamento
- R3: trigger registra contexto de decisao (allow/block + motivo)
- R4: deteccao de treino stale (>6h) com fail-safe

Esta suite deve falhar na fase RED antes da implementacao GREEN.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _create_minimal_training_tables(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rl_training_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                completed_at TEXT,
                completed_at_ms INTEGER,
                episodes_used INTEGER,
                status TEXT
            )
            """
        )
        conn.commit()


class TestM20222TrainingAuditSchema:
    """R1: Schema de auditoria deve existir e conter colunas obrigatorias."""

    def test_ensure_rl_training_audit_schema_creates_table(self, tmp_path: Path) -> None:
        """R1: helper deve criar rl_training_audit quando ausente."""
        from core.model2.training_audit import ensure_rl_training_audit_schema

        db_path = tmp_path / "m20222_schema.db"
        _create_minimal_training_tables(db_path)

        with sqlite3.connect(db_path) as conn:
            ensure_rl_training_audit_schema(conn)
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rl_training_audit'"
            ).fetchone()

        assert row is not None

    def test_ensure_rl_training_audit_schema_has_required_columns(self, tmp_path: Path) -> None:
        """R1: tabela deve conter colunas minimas do contrato de auditoria."""
        from core.model2.training_audit import ensure_rl_training_audit_schema

        db_path = tmp_path / "m20222_columns.db"
        _create_minimal_training_tables(db_path)

        with sqlite3.connect(db_path) as conn:
            ensure_rl_training_audit_schema(conn)
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(rl_training_audit)").fetchall()
            }

        required = {
            "triggered_at_ms",
            "trigger_reason",
            "episodes_count",
            "model_id_before",
            "model_id_after",
            "avg_reward_delta",
            "status",
        }
        assert required.issubset(columns)


class TestM20222TrainingAuditEvents:
    """R2/R3: evento de trigger deve ser auditavel e anti-duplicidade."""

    def test_record_training_audit_event_persists_row(self, tmp_path: Path) -> None:
        """R3: evento de trigger permitido deve ser persistido com status."""
        from core.model2.training_audit import (
            ensure_rl_training_audit_schema,
            record_training_audit_event,
        )

        db_path = tmp_path / "m20222_event.db"
        _create_minimal_training_tables(db_path)

        with sqlite3.connect(db_path) as conn:
            ensure_rl_training_audit_schema(conn)
            record_training_audit_event(
                conn,
                triggered_at_ms=1_711_000_000_000,
                trigger_reason="threshold_reached",
                episodes_count=120,
                model_id_before="ppo_v1",
                model_id_after="ppo_v2",
                avg_reward_delta=0.14,
                status="started",
            )
            row = conn.execute(
                """
                SELECT trigger_reason, episodes_count, model_id_before, model_id_after, status
                FROM rl_training_audit
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        assert row is not None
        assert row[0] == "threshold_reached"
        assert row[1] == 120
        assert row[2] == "ppo_v1"
        assert row[3] == "ppo_v2"
        assert row[4] == "started"

    def test_evaluate_training_trigger_blocks_when_running(self) -> None:
        """R2: quando treino ja esta em andamento, novo trigger deve ser bloqueado."""
        from core.model2.training_audit import evaluate_training_trigger_audit

        result = evaluate_training_trigger_audit(
            pending_episodes=150,
            retrain_threshold=100,
            is_running=True,
            now_ms=1_711_000_000_000,
            last_completed_at_ms=1_710_999_000_000,
        )

        assert result["trigger_allowed"] is False
        assert result["trigger_reason"] == "training_already_running"
        assert result["status"] == "blocked"

    def test_evaluate_training_trigger_allows_when_threshold_reached(self) -> None:
        """R3: quando pendentes >= threshold e sem treino ativo, trigger permitido."""
        from core.model2.training_audit import evaluate_training_trigger_audit

        result = evaluate_training_trigger_audit(
            pending_episodes=101,
            retrain_threshold=100,
            is_running=False,
            now_ms=1_711_000_000_000,
            last_completed_at_ms=1_710_998_000_000,
        )

        assert result["trigger_allowed"] is True
        assert result["trigger_reason"] == "threshold_reached"
        assert result["status"] == "started"


class TestM20222TrainingStaleDetection:
    """R4: deteccao de stale > 6h para fail-safe operacional."""

    def test_detect_training_stale_true_when_last_train_older_than_6h(self) -> None:
        """R4: deve marcar stale quando ultimo treino excede janela de 6h."""
        from core.model2.training_audit import detect_training_stale

        now_ms = 1_711_000_000_000
        six_hours_ms = 6 * 60 * 60 * 1000
        result = detect_training_stale(
            now_ms=now_ms,
            last_completed_at_ms=now_ms - six_hours_ms - 1,
            max_stale_hours=6,
            operation_active=True,
        )

        assert result["stale"] is True
        assert result["reason"] == "training_stale"

    def test_detect_training_stale_false_when_recent_or_inactive(self) -> None:
        """R4: nao stale para treino recente ou operacao inativa."""
        from core.model2.training_audit import detect_training_stale

        now_ms = 1_711_000_000_000
        one_hour_ms = 60 * 60 * 1000

        recent = detect_training_stale(
            now_ms=now_ms,
            last_completed_at_ms=now_ms - one_hour_ms,
            max_stale_hours=6,
            operation_active=True,
        )
        inactive = detect_training_stale(
            now_ms=now_ms,
            last_completed_at_ms=now_ms - (10 * one_hour_ms),
            max_stale_hours=6,
            operation_active=False,
        )

        assert recent["stale"] is False
        assert inactive["stale"] is False
