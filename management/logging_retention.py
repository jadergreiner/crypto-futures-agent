"""Governança de logs com rotação temporal e por tamanho, retenção por severidade.

Módulo para gerenciar ciclo de vida de arquivos de log com:
- Retenção diferenciada por severity (CRITICAL→365d, ERROR→90d, WARN→14d, INFO→7d)
- Rotação automática por tamanho (default 100MB)
- Compressão .gz de arquivos antigos
- Limpeza determinística de logs expirados
- Política centralizada em config/logging_retention_policy.yaml

Referência: docs/BACKLOG.md (M2-026.5)
"""

from __future__ import annotations

import gzip
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class RetentionPolicy:
    """Política de retenção para um nível de severidade."""

    severity: str  # CRITICAL, ERROR, WARN, INFO
    retention_days: int
    compress: bool = False
    archive_format: str = "gz"  # gz, bz2, xz


class LogRotationManager:
    """Gerenciador de rotação e retenção de logs."""

    DEFAULT_CONFIG_PATH = "config/logging_retention_policy.yaml"
    DEFAULT_POLICIES = {
        "CRITICAL": RetentionPolicy("CRITICAL", 365, compress=True),
        "ERROR": RetentionPolicy("ERROR", 90, compress=True),
        "WARN": RetentionPolicy("WARN", 14, compress=False),
        "INFO": RetentionPolicy("INFO", 7, compress=False),
    }

    def __init__(self, policy_file: Optional[str] = None) -> None:
        """Inicializa gerenciador com arquivo de política.

        Args:
            policy_file: Caminho para config/logging_retention_policy.yaml.
                        Se None, usa DEFAULT_CONFIG_PATH.
        """
        self.policy_file = policy_file or self.DEFAULT_CONFIG_PATH
        self.policies: Dict[str, RetentionPolicy] = self._load_policies()

    def _load_policies(self) -> Dict[str, RetentionPolicy]:
        """Carrega políticas do arquivo YAML ou usa defaults.

        Returns:
            Dicionário de severity -> RetentionPolicy.
        """
        policy_path = Path(self.policy_file)

        if policy_path.exists():
            try:
                with open(policy_path, "r") as f:
                    config = yaml.safe_load(f)
                if config and "retention_policies" in config:
                    policies: Dict[str, RetentionPolicy] = {}
                    for severity, policy_dict in config["retention_policies"].items():
                        policies[severity] = RetentionPolicy(
                            severity=severity,
                            retention_days=policy_dict.get("days", 30),
                            compress=policy_dict.get("compress", False),
                            archive_format=policy_dict.get(
                                "archive_format", "gz"
                            ),
                        )
                    return policies
            except Exception as e:
                logging.error(f"Erro carregando política de retenção: {e}")

        # Fallback: usar defaults
        return self.DEFAULT_POLICIES

    def enforce_retention(self, logs_dir: str) -> None:
        """Remove logs antigos conforme política de retenção.

        Args:
            logs_dir: Diretório contendo arquivos de log.
        """
        logs_path = Path(logs_dir)
        if not logs_path.exists():
            return

        now = datetime.utcnow()

        for log_file in logs_path.glob("*.log*"):
            # Extrair severity do nome do arquivo (ex: "app_ERROR.log")
            severity = self._extract_severity_from_filename(log_file.name)
            if not severity or severity not in self.policies:
                continue

            policy = self.policies[severity]
            file_age = now - datetime.fromtimestamp(log_file.stat().st_mtime)

            # Se arquivo está além do retention_days, deletar
            if file_age > timedelta(days=policy.retention_days):
                log_file.unlink()
                logging.info(
                    f"Log removido por retenção: {log_file.name} "
                    f"(idade: {file_age.days}d > {policy.retention_days}d)"
                )

    def rotate_on_size(self, log_file: str, max_size_mb: int = 100) -> None:
        """Rotaciona log quando exceder tamanho máximo.

        Args:
            log_file: Caminho do arquivo de log.
            max_size_mb: Tamanho máximo em MB (default 100).
        """
        log_path = Path(log_file)
        if not log_path.exists():
            return

        max_size_bytes = max_size_mb * 1024 * 1024
        file_size = log_path.stat().st_size

        if file_size > max_size_bytes:
            # Rotacionar: renomear para .1, .2, etc.
            rotated_name = f"{log_path}.1"
            log_path.rename(rotated_name)

            logging.info(
                f"Log rotacionado por tamanho: {log_path.name} "
                f"({file_size / 1024 / 1024:.1f}MB)"
            )

            # Comprimir arquivo rotacionado
            severity = self._extract_severity_from_filename(log_path.name)
            if severity in self.policies and self.policies[severity].compress:
                self._compress_file(rotated_name)

    def _compress_file(self, file_path: str) -> None:
        """Comprime arquivo com gzip.

        Args:
            file_path: Caminho do arquivo a comprimir.
        """
        source = Path(file_path)
        if not source.exists():
            return

        destination = Path(f"{file_path}.gz")

        try:
            with open(source, "rb") as f_in:
                with gzip.open(destination, "wb") as f_out:
                    f_out.writelines(f_in)

            source.unlink()
            logging.info(f"Arquivo comprimido: {source.name} → {destination.name}")
        except Exception as e:
            logging.error(f"Erro comprimindo arquivo {source}: {e}")

    def get_compressed_logs(self, severity: str) -> List[str]:
        """Lista arquivos comprimidos (.gz) para uma severidade.

        Args:
            severity: Nível de severidade (CRITICAL, ERROR, etc).

        Returns:
            Lista de caminhos dos arquivos .gz.
        """
        if severity not in self.policies:
            return []

        # Procurar por arquivos .log.*.gz no diretório de logs
        # (Implementação simplificada; em produção, considerar logs_dir)
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return []

        pattern = f"*{severity}*.log.*.gz"
        return [str(f) for f in logs_dir.glob(pattern)]

    def _extract_severity_from_filename(self, filename: str) -> Optional[str]:
        """Extrai nível de severity do nome do arquivo.

        Convenção: <app>_<SEVERITY>.log ou <app>_<severity>.log

        Args:
            filename: Nome do arquivo.

        Returns:
            Severity (CRITICAL, ERROR, etc) ou None.
        """
        upper_name = filename.upper()
        for severity in ["CRITICAL", "ERROR", "WARN", "INFO"]:
            if severity in upper_name:
                return severity
        return None

    def reload_policies(self) -> None:
        """Recarrega políticas do arquivo (sem restart)."""
        self.policies = self._load_policies()
        logging.info("Políticas de retenção recarregadas")

    def get_policy_summary(self) -> Dict[str, Any]:
        """Retorna resumo das políticas ativas.

        Returns:
            Dicionário com severidades e dias de retenção.
        """
        return {
            severity: {
                "retention_days": policy.retention_days,
                "compress": policy.compress,
            }
            for severity, policy in self.policies.items()
        }
