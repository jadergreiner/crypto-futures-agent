"""
Logger estruturado para o agente.
"""

import logging
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, Any
import sys

from config.settings import LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT


class SafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler resiliente a bloqueio de arquivo no Windows.

    Em cenários com múltiplos processos escrevendo no mesmo log, o rename durante
    rollover pode lançar PermissionError (WinError 32). Nesse caso, ignoramos a
    rotação neste ciclo para manter a escrita contínua e evitar traceback ruidoso.
    """

    def doRollover(self) -> None:
        try:
            super().doRollover()
        except PermissionError:
            sys.stderr.write(
                "[LOGGER] Rollover ignorado: arquivo de log em uso por outro processo.\n"
            )
            if self.stream is None:
                self.stream = self._open()


class AgentLogger:
    """Logger estruturado com rotação de arquivos."""

    @staticmethod
    def setup_context_logger(context: str = "operation", name: str = "crypto_agent") -> logging.Logger:
        """
        Configura logger com arquivo específico por contexto.

        Args:
            context: Contexto ('operation', 'training', 'backtest', 'collection')
            name: Nome do logger

        Returns:
            Logger configurado com arquivo de contexto
        """
        from config.settings import LOG_FILES

        log_file = LOG_FILES.get(context, LOG_FILES['operation'])
        return AgentLogger._setup_logger_internal(name=name, log_file=log_file)

    @staticmethod
    def _setup_logger_internal(name: str = "crypto_agent", log_file: str = None) -> logging.Logger:
        """
        Implementação interna comum para setup de loggers.

        Args:
            name: Nome do logger
            log_file: Caminho do arquivo de log (usa LOG_FILE se None)

        Returns:
            Logger configurado
        """
        if log_file is None:
            log_file = LOG_FILE

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, LOG_LEVEL))

        # Desabilitar propagação para evitar mensagens duplicadas
        logger.propagate = False

        # Evitar duplicação
        if logger.handlers:
            return logger

        # File handler com rotação
        file_handler = SafeRotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            delay=True,
            encoding='utf-8',
            errors='replace',
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler com suporte a Unicode
        console_handler = logging.StreamHandler(sys.stdout)
        if hasattr(console_handler.stream, 'reconfigure'):
            try:
                console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Configurar root logger para capturar logs de todos os módulos
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOG_LEVEL))

        # Adicionar os mesmos handlers ao root logger se ainda não existirem
        if not root_logger.handlers:
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

        return logger

    @staticmethod
    def setup_logger(name: str = "crypto_agent") -> logging.Logger:
        """
        Configura logger com handlers (usa LOG_FILE padrão).
        Também configura o root logger para capturar logs de todos os módulos.

        Args:
            name: Nome do logger

        Returns:
            Logger configurado
        """
        return AgentLogger._setup_logger_internal(name=name)

    @staticmethod
    def log_decision(logger: logging.Logger, decision: Dict[str, Any]) -> None:
        """Loga decisão do agente."""
        logger.info(f"DECISION: {json.dumps(decision)}")

    @staticmethod
    def log_risk_event(logger: logging.Logger, event: Dict[str, Any]) -> None:
        """Loga evento de risco."""
        logger.warning(f"RISK_EVENT: {json.dumps(event)}")

    @staticmethod
    def log_websocket_event(logger: logging.Logger, event: Dict[str, Any]) -> None:
        """Loga evento WebSocket."""
        logger.debug(f"WS_EVENT: {json.dumps(event)}")

    @staticmethod
    def log_performance(logger: logging.Logger, metrics: Dict[str, Any]) -> None:
        """Loga métricas de performance."""
        logger.info(f"PERFORMANCE: {json.dumps(metrics)}")
