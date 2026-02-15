"""
Logger estruturado para o agente.
"""

import logging
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, Any

from config.settings import LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT


class AgentLogger:
    """Logger estruturado com rotação de arquivos."""
    
    @staticmethod
    def setup_logger(name: str = "crypto_agent") -> logging.Logger:
        """
        Configura logger com handlers.
        Também configura o root logger para capturar logs de todos os módulos.
        
        Args:
            name: Nome do logger
            
        Returns:
            Logger configurado
        """
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Evitar duplicação
        if logger.handlers:
            return logger
        
        # File handler com rotação
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler com suporte a Unicode
        # No Windows, o sys.stdout pode usar cp1252 por padrão.
        # Usar errors='replace' garante que caracteres não suportados sejam substituídos
        # em vez de causar UnicodeEncodeError.
        import sys
        console_handler = logging.StreamHandler(sys.stdout)
        # Configurar o stream para lidar com erros de codificação graciosamente
        if hasattr(console_handler.stream, 'reconfigure'):
            # Python 3.7+ permite reconfigurar a codificação do stream
            try:
                console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                # Se falhar, continuamos com o comportamento padrão mas com errors='replace'
                pass
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Configurar root logger para capturar logs de todos os módulos
        # (monitoring.position_monitor, data.collector, etc.)
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Adicionar os mesmos handlers ao root logger se ainda não existirem
        if not root_logger.handlers:
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)
        
        return logger
    
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
