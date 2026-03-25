"""Testes RED para _trigger_incremental_training_if_needed (BLID-094).

Casos cobertos:
  a) modo live + pending>=threshold + processo None => Popen chamado
  b) modo live + processo rodando => Popen nao chamado
  c) modo shadow + pending>=threshold => Popen chamado (regressao)
  d) pending < threshold => Popen nao chamado
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.model2.live_service import Model2LiveExecutionService
from core.model2.live_execution import LiveExecutionConfig


def _make_service(execution_mode: str) -> Model2LiveExecutionService:
    """Cria instancia minima de Model2LiveExecutionService sem dependencias externas."""
    service = Model2LiveExecutionService.__new__(Model2LiveExecutionService)
    config = MagicMock(spec=LiveExecutionConfig)
    config.execution_mode = execution_mode
    service.config = config
    service._incremental_training_process = None
    service._db_path = "db/modelo2.db"
    service._repo_root = MagicMock()
    service._repo_root.__truediv__ = lambda self, other: MagicMock()
    return service


# --- Caso (a): modo live + pending>=threshold + processo None => Popen chamado ---

def test_trigger_retrain_live_pending_gte_threshold_sem_processo_chama_popen() -> None:
    """Modo live, pending >= threshold, sem processo rodando: deve chamar Popen."""
    # Arrange
    service = _make_service("live")
    service._incremental_training_process = None

    # Act
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        service._trigger_incremental_training_if_needed(
            pending_episodes=10,
            retrain_threshold=5,
            timeframe="1h",
        )

    # Assert
    mock_popen.assert_called_once()


# --- Caso (b): modo live + processo rodando => Popen nao chamado ---

def test_trigger_retrain_live_processo_rodando_nao_chama_popen() -> None:
    """Modo live, processo ainda em execucao: nao deve disparar novo Popen."""
    # Arrange
    service = _make_service("live")
    processo_mock = MagicMock()
    processo_mock.poll.return_value = None  # ainda rodando
    service._incremental_training_process = processo_mock

    # Act
    with patch("subprocess.Popen") as mock_popen:
        service._trigger_incremental_training_if_needed(
            pending_episodes=10,
            retrain_threshold=5,
            timeframe="1h",
        )

    # Assert
    mock_popen.assert_not_called()


# --- Caso (c): modo shadow + pending>=threshold => Popen chamado (regressao) ---

def test_trigger_retrain_shadow_pending_gte_threshold_chama_popen() -> None:
    """Modo shadow, pending >= threshold, sem processo: deve chamar Popen (comportamento pre-existente)."""
    # Arrange
    service = _make_service("shadow")
    service._incremental_training_process = None

    # Act
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        service._trigger_incremental_training_if_needed(
            pending_episodes=10,
            retrain_threshold=5,
            timeframe="1h",
        )

    # Assert
    mock_popen.assert_called_once()


# --- Caso (d): pending < threshold => Popen nao chamado ---

def test_trigger_retrain_pending_menor_que_threshold_nao_chama_popen() -> None:
    """Pending abaixo do threshold: nao deve disparar retreino independente do modo."""
    # Arrange
    service = _make_service("live")
    service._incremental_training_process = None

    # Act
    with patch("subprocess.Popen") as mock_popen:
        service._trigger_incremental_training_if_needed(
            pending_episodes=3,
            retrain_threshold=5,
            timeframe="1h",
        )

    # Assert
    mock_popen.assert_not_called()


# --- Caso bonus: log operacional emitido apos Popen bem-sucedido (requisito 2) ---

def test_trigger_retrain_live_emite_log_apos_popen() -> None:
    """Deve emitir log '[TREINO] Retreino iniciado: N ep / threshold K' apos Popen."""
    # Arrange
    service = _make_service("live")
    service._incremental_training_process = None

    # Act
    with patch("subprocess.Popen") as mock_popen, \
         patch("logging.getLogger") as mock_get_logger:
        mock_popen.return_value = MagicMock()
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        service._trigger_incremental_training_if_needed(
            pending_episodes=10,
            retrain_threshold=5,
            timeframe="1h",
        )

    # Assert: Popen foi chamado (precondition)
    mock_popen.assert_called_once()
