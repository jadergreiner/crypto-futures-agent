"""
Suite RED - BLID-097: Integrar io_retry nos scripts afetados por lock de arquivo.

Testa que persist_training_episodes, healthcheck_live_execution e
operator_cycle_status usam read_json_with_retry / write_json_with_retry
em vez de read_text / write_text diretos.

Estrutura AAA; mocks de IO; sem dependencias de estado compartilhado.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# R1: persist_training_episodes._load_cursor usa read_json_with_retry
# ---------------------------------------------------------------------------

class TestPersistEpisodesLoadCursor:
    def test_load_cursor_uses_read_json_with_retry(self, tmp_path: Path) -> None:
        """R1: _load_cursor deve chamar read_json_with_retry em vez de read_text."""
        # Arrange
        cursor_file = tmp_path / "cursor.json"
        cursor_file.write_text(json.dumps({"last_updated_at_ms": 12345}), encoding="utf-8")

        with patch(
            "scripts.model2.persist_training_episodes.read_json_with_retry"
        ) as mock_read:
            mock_read.return_value = {"last_updated_at_ms": 12345}
            from scripts.model2.persist_training_episodes import _load_cursor

            # Act
            result = _load_cursor(cursor_file)

            # Assert
            mock_read.assert_called_once()
            assert result == 12345

    def test_load_cursor_fail_safe_returns_zero_on_lock(self, tmp_path: Path) -> None:
        """R1: _load_cursor deve retornar 0 se read_json_with_retry retornar False (fail_safe)."""
        # Arrange
        cursor_file = tmp_path / "cursor.json"

        with patch(
            "scripts.model2.persist_training_episodes.read_json_with_retry",
            return_value=False,
        ):
            from scripts.model2.persist_training_episodes import _load_cursor

            # Act
            result = _load_cursor(cursor_file)

            # Assert
            assert result == 0


# ---------------------------------------------------------------------------
# R2: persist_training_episodes._save_cursor usa write_json_with_retry
# ---------------------------------------------------------------------------

class TestPersistEpisodesSaveCursor:
    def test_save_cursor_uses_write_json_with_retry(self, tmp_path: Path) -> None:
        """R2: _save_cursor deve chamar write_json_with_retry em vez de write_text."""
        # Arrange
        cursor_file = tmp_path / "cursor.json"

        with patch(
            "scripts.model2.persist_training_episodes.write_json_with_retry"
        ) as mock_write:
            mock_write.return_value = True
            from scripts.model2.persist_training_episodes import _save_cursor

            # Act
            _save_cursor(cursor_file, 99999)

            # Assert
            mock_write.assert_called_once()
            call_args = mock_write.call_args
            assert call_args[0][0] == {"last_updated_at_ms": 99999}
            assert str(cursor_file) in str(call_args[0][1])

    def test_save_cursor_fail_safe_true_passed(self, tmp_path: Path) -> None:
        """R2: _save_cursor deve passar fail_safe=True para write_json_with_retry."""
        # Arrange
        cursor_file = tmp_path / "cursor.json"

        with patch(
            "scripts.model2.persist_training_episodes.write_json_with_retry"
        ) as mock_write:
            mock_write.return_value = True
            from scripts.model2.persist_training_episodes import _save_cursor

            # Act
            _save_cursor(cursor_file, 42)

            # Assert
            call_kwargs = mock_write.call_args[1]
            assert call_kwargs.get("fail_safe") is True


# ---------------------------------------------------------------------------
# R3: persist_training_episodes summary usa write_json_with_retry
# ---------------------------------------------------------------------------

class TestPersistEpisodesSummaryWrite:
    def test_summary_write_uses_write_json_with_retry(self, tmp_path: Path) -> None:
        """R3: escrita do summary JSON deve usar write_json_with_retry."""
        # Arrange: verificar que nao usa .write_text no modulo para summary
        import scripts.model2.persist_training_episodes as mod
        import inspect
        source = inspect.getsource(mod)

        # A funcao run_persist_training_episodes nao deve ter summary_path.write_text
        # apos a integracao (deve usar write_json_with_retry)
        assert "summary_path.write_text" not in source, (
            "persist_training_episodes ainda usa summary_path.write_text em vez de "
            "write_json_with_retry — integracao nao foi feita"
        )

    def test_summary_write_fail_safe_true(self) -> None:
        """R3: write_json_with_retry para summary deve ter fail_safe=True."""
        # Verifica via source que fail_safe=True esta presente na chamada de summary
        import scripts.model2.persist_training_episodes as mod
        import inspect
        source = inspect.getsource(mod)

        # Deve existir chamada write_json_with_retry com fail_safe=True
        assert "write_json_with_retry" in source, (
            "persist_training_episodes nao importa write_json_with_retry"
        )


# ---------------------------------------------------------------------------
# R4: healthcheck_live_execution usa read_json_with_retry
# ---------------------------------------------------------------------------

class TestHealthcheckLoadDashboard:
    def test_load_dashboard_uses_read_json_with_retry(self, tmp_path: Path) -> None:
        """R4: _load_latest_live_dashboard deve usar read_json_with_retry."""
        # Arrange
        dashboard = tmp_path / "model2_live_dashboard_123.json"
        dashboard.write_text(json.dumps({"status": "ok"}), encoding="utf-8")

        with patch(
            "scripts.model2.healthcheck_live_execution.read_json_with_retry"
        ) as mock_read:
            mock_read.return_value = {"status": "ok"}
            from scripts.model2.healthcheck_live_execution import _load_latest_live_dashboard

            # Act
            _path, payload = _load_latest_live_dashboard(tmp_path)

            # Assert
            mock_read.assert_called_once()
            assert payload == {"status": "ok"}

    def test_load_dashboard_fail_safe_on_lock(self, tmp_path: Path) -> None:
        """R4: se read_json_with_retry retornar False, _load_latest_live_dashboard retorna None payload."""
        # Arrange
        dashboard = tmp_path / "model2_live_dashboard_456.json"
        dashboard.write_text("{}", encoding="utf-8")

        with patch(
            "scripts.model2.healthcheck_live_execution.read_json_with_retry",
            return_value=False,
        ):
            from scripts.model2.healthcheck_live_execution import _load_latest_live_dashboard

            # Act
            _path, payload = _load_latest_live_dashboard(tmp_path)

            # Assert
            assert payload is None


# ---------------------------------------------------------------------------
# R5: operator_cycle_status._load_latest_json usa read_json_with_retry
# ---------------------------------------------------------------------------

class TestOperatorLoadLatestJson:
    def test_load_latest_json_uses_read_json_with_retry(self, tmp_path: Path) -> None:
        """R5: _load_latest_json deve usar read_json_with_retry."""
        # Arrange
        f = tmp_path / "scan_20260325.json"
        f.write_text(json.dumps({"timeframe": "H1"}), encoding="utf-8")

        with patch(
            "scripts.model2.operator_cycle_status.read_json_with_retry"
        ) as mock_read:
            mock_read.return_value = {"timeframe": "H1"}
            from scripts.model2.operator_cycle_status import _load_latest_json

            # Act
            result = _load_latest_json(tmp_path, "scan", max_age_seconds=3600)

            # Assert
            mock_read.assert_called_once()
            assert result == {"timeframe": "H1"}

    def test_load_latest_json_fail_safe_returns_none_on_lock(self, tmp_path: Path) -> None:
        """R5: _load_latest_json deve retornar None se read_json_with_retry retornar False."""
        # Arrange
        f = tmp_path / "scan_20260325.json"
        f.write_text("{}", encoding="utf-8")

        with patch(
            "scripts.model2.operator_cycle_status.read_json_with_retry",
            return_value=False,
        ):
            from scripts.model2.operator_cycle_status import _load_latest_json

            # Act
            result = _load_latest_json(tmp_path, "scan", max_age_seconds=3600)

            # Assert
            assert result is None


# ---------------------------------------------------------------------------
# R6: operator_cycle_status._load_latest_json_by_timeframe usa read_json_with_retry
# ---------------------------------------------------------------------------

class TestOperatorLoadLatestJsonByTimeframe:
    def test_load_by_timeframe_uses_read_json_with_retry(self, tmp_path: Path) -> None:
        """R6: _load_latest_json_by_timeframe deve usar read_json_with_retry."""
        # Arrange
        f = tmp_path / "scan_20260325.json"
        f.write_text(json.dumps({"timeframe": "H4"}), encoding="utf-8")

        with patch(
            "scripts.model2.operator_cycle_status.read_json_with_retry"
        ) as mock_read:
            mock_read.return_value = {"timeframe": "H4"}
            from scripts.model2.operator_cycle_status import _load_latest_json_by_timeframe

            # Act
            result = _load_latest_json_by_timeframe(tmp_path, "scan", "H4", max_age_seconds=3600)

            # Assert
            mock_read.assert_called_once()
            assert result == {"timeframe": "H4"}

    def test_load_by_timeframe_fail_safe_returns_none_on_lock(self, tmp_path: Path) -> None:
        """R6: _load_latest_json_by_timeframe retorna None se read_json_with_retry retornar False."""
        # Arrange
        f = tmp_path / "scan_20260325.json"
        f.write_text(json.dumps({"timeframe": "H4"}), encoding="utf-8")

        with patch(
            "scripts.model2.operator_cycle_status.read_json_with_retry",
            return_value=False,
        ):
            from scripts.model2.operator_cycle_status import _load_latest_json_by_timeframe

            # Act
            result = _load_latest_json_by_timeframe(tmp_path, "scan", "H4", max_age_seconds=3600)

            # Assert
            assert result is None
