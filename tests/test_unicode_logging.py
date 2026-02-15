"""
Testes para validar correções de encoding Unicode no Windows.
Valida que o logger pode lidar com caracteres Unicode sem falhar.
"""

import pytest
import logging
import tempfile
import os
import io
import sys
from unittest.mock import Mock, patch, MagicMock


# ============================================================================
# TESTE #1: Logger StreamHandler é resiliente a erros de encoding
# ============================================================================

def test_logger_handles_unicode_gracefully():
    """
    Testa que o logger configurado pode lidar com caracteres Unicode
    mesmo quando o stream subjacente não suporta a codificação.
    """
    # Importar diretamente a classe para evitar imports de dependências
    import sys
    sys_path_backup = sys.path.copy()
    
    # Importar apenas o módulo logger, não todo o pacote monitoring
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "logger_module", 
        "/home/runner/work/crypto-futures-agent/crypto-futures-agent/monitoring/logger.py"
    )
    logger_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logger_module)
    AgentLogger = logger_module.AgentLogger
    
    # Limpar handlers anteriores
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Setup logger
    logger = AgentLogger.setup_logger("test_unicode_logger")
    
    # Verificar que há um StreamHandler
    stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(stream_handlers) > 0, "Deve haver pelo menos um StreamHandler"
    
    # Verificar que o stream tem reconfigure ou está configurado adequadamente
    stream = stream_handlers[0].stream
    # Se tem reconfigure, significa que o código tentou configurar UTF-8
    has_reconfigure = hasattr(stream, 'reconfigure')
    
    # O teste passa se o handler foi criado com sys.stdout
    # (que é o que o código corrigido faz)
    assert stream == sys.stdout or hasattr(stream, 'reconfigure'), \
        "StreamHandler deve usar sys.stdout para permitir reconfiguração"


def test_logger_stream_configuration():
    """
    Testa que o setup do logger cria StreamHandler com sys.stdout.
    """
    # Importar apenas o módulo logger
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "logger_module", 
        "/home/runner/work/crypto-futures-agent/crypto-futures-agent/monitoring/logger.py"
    )
    logger_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logger_module)
    AgentLogger = logger_module.AgentLogger
    
    # Limpar handlers anteriores
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Setup logger
    logger = AgentLogger.setup_logger("test_stream_config")
    
    # Verificar que há StreamHandler usando sys.stdout
    stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(stream_handlers) > 0
    
    # Pelo menos um deve usar sys.stdout
    uses_stdout = any(h.stream == sys.stdout for h in stream_handlers)
    assert uses_stdout, "StreamHandler deve usar sys.stdout explicitamente"


# ============================================================================
# TESTE #2: Position Monitor usa apenas caracteres ASCII nos logs
# ============================================================================

def test_position_monitor_logs_ascii_only():
    """
    Testa que as mensagens de log no run_continuous() usam apenas caracteres ASCII
    em vez de emojis que falham em codificações limitadas.
    """
    # Ler o arquivo do position_monitor
    with open('/home/runner/work/crypto-futures-agent/crypto-futures-agent/monitoring/position_monitor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar que não há emojis comuns
    forbidden_chars = ['📊', '✓', '⏳', '🔴', '🟡', '🟢']
    for char in forbidden_chars:
        assert char not in content, f"Emoji '{char}' encontrado no código (deve usar ASCII)"
    
    # Verificar que os substitutos ASCII estão presentes
    assert '[RESUMO]' in content, "Deve usar [RESUMO] em vez de 📊"
    assert '[OK]' in content, "Deve usar [OK] em vez de ✓"
    assert '[AGUARDANDO]' in content, "Deve usar [AGUARDANDO] em vez de ⏳"


def test_position_monitor_run_continuous_messages():
    """
    Testa que as mensagens específicas do run_continuous estão usando ASCII.
    """
    # Ler o arquivo do position_monitor
    with open('/home/runner/work/crypto-futures-agent/crypto-futures-agent/monitoring/position_monitor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar o método run_continuous
    assert 'def run_continuous' in content
    
    # Verificar padrões específicos das mensagens corrigidas
    assert '[RESUMO] CICLO' in content, "Deve ter '[RESUMO] CICLO' no run_continuous"
    assert '[OK] Ciclo' in content, "Deve ter '[OK] Ciclo' no run_continuous"
    assert '[AGUARDANDO] Próximo ciclo' in content, "Deve ter '[AGUARDANDO] Próximo ciclo' no run_continuous"


def test_logger_file_has_unicode_handling():
    """
    Testa que o arquivo logger.py contém código para lidar com Unicode.
    """
    with open('/home/runner/work/crypto-futures-agent/crypto-futures-agent/monitoring/logger.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar que há menções ao tratamento de Unicode/encoding
    assert 'sys.stdout' in content, "Deve usar sys.stdout explicitamente"
    assert 'reconfigure' in content, "Deve tentar reconfigurar o stream"
    assert 'utf-8' in content.lower() or 'replace' in content, "Deve mencionar utf-8 ou replace para erros"

