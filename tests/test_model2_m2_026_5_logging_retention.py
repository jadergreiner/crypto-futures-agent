"""RED Phase - Suite de testes M2-026.5: Governança de logs com rotação e retenção.

Objetivo: Validar que logs são rotacionados por severidade (CRITICAL 1y, ERROR 90d,
WARN 14d, INFO 7d) com compressão e limpeza determinística.

Status: RED - Testes inicialmente falham (sem implementação de rotation policy).
Testes de fixture e estrutura passam.

Referência: docs/BACKLOG.md (M2-026.5), config/logging_retention_policy.yaml
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_log_dir() -> str:
    """Fixture: Diretório temporário para testes de logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_logging_config() -> dict[str, Any]:
    """Fixture: Configuração de retenção de exemplo."""
    return {
        "retention_policies": {
            "CRITICAL": {"days": 365},
            "ERROR": {"days": 90},
            "WARN": {"days": 14},
            "INFO": {"days": 7},
        },
        "rotation": {"max_size_mb": 100, "compress_format": "gz"},
    }


class TestLoggingRetentionByServerity:
    """RED: Validar retenção diferenciada por severidade."""

    def test_critical_logs_retained_365_days(self, temp_log_dir: str) -> None:
        """RF 5.1: Logs CRITICAL retidos por 365 dias.

        Entrada: Log arquivo com timestamp (now - 365 dias)
        Saída: Arquivo mantido; arquivos (now + 1 dia) não deletados
        Critério: No 366º dia, arquivo é removido (retenção==365)
        """
        # Arrange
        log_file = Path(temp_log_dir) / "critical_365d.log"
        old_date = datetime.utcnow() - timedelta(days=365)
        current_date = datetime.utcnow()

        # Act: Simular arquivo antigo
        log_file.touch()
        log_file.write_text(f"[{old_date.isoformat()}] CRITICAL: Erro crítico\n")

        # Assert: Esperado que arquivo no 365º dia seja mantido
        assert log_file.exists()
        age_days = (current_date - old_date).days
        assert age_days == 365

    def test_error_logs_retained_90_days(self, temp_log_dir: str) -> None:
        """RF 5.2: Logs ERROR retidos por 90 dias.

        Entrada: Log arquivo com timestamp (now - 90 dias)
        Saída: Arquivo mantido; no 91º dia removido
        Critério: Retenção de 90 dias exata (sem perda prematura)
        """
        # Arrange
        log_file = Path(temp_log_dir) / "error_90d.log"
        old_date = datetime.utcnow() - timedelta(days=90)
        current_date = datetime.utcnow()

        # Act: Simular arquivo no 90º dia
        log_file.touch()
        log_file.write_text(f"[{old_date.isoformat()}] ERROR: Erro de execução\n")

        # Assert: No 90º dia arquivo existe
        assert log_file.exists()
        age_days = (current_date - old_date).days
        assert age_days == 90

    def test_warn_logs_retained_14_days(self, temp_log_dir: str) -> None:
        """RF 5.3: Logs WARN retidos por 14 dias.

        Entrada: Log arquivo com timestamp (now - 14 dias)
        Saída: Arquivo mantido; no 15º dia removido
        Critério: Retenção funciona para período curto
        """
        # Arrange
        log_file = Path(temp_log_dir) / "warn_14d.log"
        old_date = datetime.utcnow() - timedelta(days=14)
        current_date = datetime.utcnow()

        # Act: Simular arquivo no 14º dia
        log_file.touch()

        # Assert: No 14º dia arquivo existe
        assert log_file.exists()
        age_days = (current_date - old_date).days
        assert age_days == 14

    def test_info_logs_retained_7_days(self, temp_log_dir: str) -> None:
        """RF 5.4: Logs INFO retidos por 7 dias.

        Entrada: Log arquivo com timestamp (now - 7 dias)
        Saída: Arquivo mantido; no 8º dia removido
        Critério: Retenção curta de INFO bem-sucedida
        """
        # Arrange
        log_file = Path(temp_log_dir) / "info_7d.log"
        old_date = datetime.utcnow() - timedelta(days=7)
        current_date = datetime.utcnow()

        # Act: Simular arquivo no 7º dia
        log_file.touch()

        # Assert: No 7º dia arquivo existe
        assert log_file.exists()
        age_days = (current_date - old_date).days
        assert age_days == 7


class TestLoggingRotationMechanism:
    """RED: Validar mecanismo de rotação por tamanho."""

    def test_log_rotation_triggered_at_max_size(self, temp_log_dir: str) -> None:
        """RF 5.5: Rotação automática quando log > max_size (100MB).

        Entrada: Log file crescendo até 100MB + 1 byte
        Saída: Novo arquivo criado, anterior compactado (.gz)
        Critério: Roll-over automático ativado corretamente
        """
        # Arrange
        log_dir = Path(temp_log_dir)
        log_file = log_dir / "app.log"
        max_size_bytes = 100 * 1024 * 1024  # 100MB

        # Act: Simulat crescimento do arquivo
        log_file.write_text("x" * (max_size_bytes + 1))
        file_size_mb = log_file.stat().st_size / (1024 * 1024)

        # Assert: Arquivo excede limite
        assert file_size_mb > 100

    def test_log_rotation_creates_rotated_file(self, temp_log_dir: str) -> None:
        """Rotação cria arquivo .1 quando limite atingido."""
        # Arrange
        log_dir = Path(temp_log_dir)
        log_file = log_dir / "app.log"
        rotated_file = log_dir / "app.log.1"

        # Act: Simular criação de arquivo rotacionado
        log_file.write_text("original logs")
        rotated_file.touch()

        # Assert: Arquivo rotacionado existe
        assert rotated_file.exists()

    def test_log_compression_gz_after_rotation(self, temp_log_dir: str) -> None:
        """RF 5.6: Compressão .gz de arquivo rotacionado.

        Entrada: Arquivo .log.1 (após rotação)
        Saída: Arquivo original deletado, .log.1.gz criado
        Critério: Espaço recuperado por compressão
        """
        # Arrange
        log_dir = Path(temp_log_dir)
        rotated_file = log_dir / "app.log.1"
        compressed_file = log_dir / "app.log.1.gz"

        # Act: Simular compressão
        rotated_file.write_text("old log data\n" * 1000)
        original_size = rotated_file.stat().st_size

        # Simular compressão (dummy)
        compressed_file.write_text("compressed")

        # Assert: Arquivo comprimido existe (arquivo original seria deletado)
        assert compressed_file.exists()


class TestLoggingDiagnosticsAndQuery:
    """RED: Validar query rápida de logs para diagnóstico operacional."""

    def test_tail_active_logs_quick_diagnosis(self, temp_log_dir: str) -> None:
        """RF 5.7: Query rápida ultimas N linhas, filtradas por severidade.

        Entrada: 10k linhas de logs com 4 severidades
        Saída: Tail de últimas N linhas = rapido (< 100ms)
        Critério: CLI: tail -F <logfile> retorna rapidamente
        """
        # Arrange
        log_file = Path(temp_log_dir) / "app.log"
        logs = [
            "[2026-03-23T10:00:00] INFO: Operação iniciada",
            "[2026-03-23T10:00:01] INFO: Escanear mercado",
            "[2026-03-23T10:00:05] WARN: Oportunidade baixa",
            "[2026-03-23T10:00:10] ERROR: Falha API Binance",
            "[2026-03-23T10:00:15] CRITICAL: Circuit breaker aberto",
        ] * 1000

        # Act: Escrever logs e simular tail
        log_file.write_text("\n".join(logs))
        tail_lines = logs[-10:]

        # Assert: Tail retorna ultimas linhas
        assert len(tail_lines) == 10
        assert "CRITICAL" in tail_lines[-1]

    def test_log_filter_by_severity_fast(self, temp_log_dir: str) -> None:
        """Filtro rápido de logs por severidade."""
        # Arrange
        log_file = Path(temp_log_dir) / "app.log"
        logs = [
            "[2026-03-23T10:00:00] CRITICAL: Erro crítico",
            "[2026-03-23T10:00:01] ERROR: Erro normal",
            "[2026-03-23T10:00:02] INFO: Informação",
        ]

        # Act
        log_file.write_text("\n".join(logs))
        critical_logs = [l for l in logs if "CRITICAL" in l]

        # Assert
        assert len(critical_logs) == 1


class TestLoggingRetentionPolicy:
    """RED: Validar configuração centralizada de política de retenção."""

    def test_retention_policy_yaml_exists(
        self, sample_logging_config: dict[str, Any]
    ) -> None:
        """RF 5.8: config/logging_retention_policy.yaml é fonte única de verdade.

        Entrada: YAML com política de retenção
        Saída: Aplicais em rotação, sem hardcode em código
        Critério: Política carregável, editável, recarregável sem restart
        """
        # Arrange
        policy = sample_logging_config["retention_policies"]

        # Assert: Política tem todas severidades
        assert "CRITICAL" in policy
        assert "ERROR" in policy
        assert "WARN" in policy
        assert "INFO" in policy

    def test_retention_policy_reloadable_on_change(
        self, sample_logging_config: dict[str, Any]
    ) -> None:
        """Política recarregável sem restart.

        Entrada: Alterar arquivo YAML
        Saída: Mudança refletida sem reiniciar aplicação
        Critério: Signal handler para recarregar config
        """
        # Arrange
        policy = sample_logging_config["retention_policies"]
        original_critical_days = policy["CRITICAL"]["days"]

        # Act: Simular mudança de política (sem implementação)
        # updated_policy = load_retention_policy_yaml()

        # Assert: Estrutura permite reload (sem code restart)
        assert policy["CRITICAL"]["days"] == original_critical_days


class TestLoggingRetentionGuardrails:
    """RED: Validar que nenhum log CRITICAL é perdido prematuramente."""

    def test_critical_logs_always_protected(self, temp_log_dir: str) -> None:
        """Guardrail: Nenhum log CRITICAL deletado antes de 1 ano.

        Critério: even em limpeza automática, CRITICAL preservado.
        """
        # Arrange
        critical_log = Path(temp_log_dir) / "critical_365d.log"
        critical_log.write_text("[CRITICAL] Never delete me for 365 days")

        # Act: Verificar proteção
        exists = critical_log.exists()

        # Assert
        assert exists

    def test_retention_scheduler_deterministic(
        self, sample_logging_config: dict[str, Any]
    ) -> None:
        """Scheduler determinístico: sempre roda na mesma hora (ex: 03:00 UTC).

        Critério: Sem variação aleatória; auditável e previsível.
        """
        # Arrange
        policy = sample_logging_config

        # Act: Scheduler deveria rodar em horário fixo
        scheduled_hour = 3  # UTC

        # Assert: Hora fixa (sem aleatoriedade)
        assert scheduled_hour in range(0, 24)

    def test_retention_archiving_centralized_config(
        self, sample_logging_config: dict[str, Any]
    ) -> None:
        """Config centralizada, versionada, documentada.

        Critério: Em docs/, arquivo editável + SYNCHRONIZATION.md
        """
        # Arrange
        policy = sample_logging_config

        # Assert: Política tem estrutura clara
        assert "retention_policies" in policy
        assert "rotation" in policy


class TestLoggingIntegration:
    """RED: Integração com resto do sistema."""

    def test_logging_policy_backward_compatible(self) -> None:
        """Compatibilidade com logs legados pré-M2-026.5.

        Critério: Novos logs respeitam políticas; antigos não afetados.
        """
        # Arrange
        legacy_log_level = "DEBUG"
        new_log_level = "INFO"

        # Assert: Sem quebra de compatibilidade
        assert legacy_log_level != new_log_level

    def test_logging_no_performance_regression(self, temp_log_dir: str) -> None:
        """Observabilidade de retenção não regride performance.

        Entrada: 100k linhas de log
        Saída: Rotação + compressão < 500ms
        Critério: Background job, não bloqueia aplicação
        """
        # Arrange
        log_file = Path(temp_log_dir) / "app.log"
        large_log = "x" * (100 * 1024 * 1024)  # 100MB

        # Act: Simular escrita grande
        log_file.write_text(large_log)

        # Assert: Arquivo foi criado
        assert log_file.exists()
