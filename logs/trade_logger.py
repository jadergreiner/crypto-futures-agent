"""
Sistema de logs estruturado para telemetria de trades.

Responsável por registrar execuções de trades com formato JSON estruturado,
permitindo auditoria completa e reconstrução de histórico operacional.

Padrão: Observer pattern - logger callback integrado com OrderExecutor
"""

import json
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from logs.database_manager import DatabaseManager


class StructuredLogger:
    """
    Logger estruturado para trades com persistência em JSON + SQLite.

    Características:
    - Logs JSON válidos com timestamps ISO8601 UTC
    - Banco de dados SQLite para queries estruturadas
    - Identificadores únicos (UUID) para cada trade
    - Integração automática via callback com OrderExecutor

    Padrão de uso:
        logger = StructuredLogger()
        trade_id = logger.log_trade_execution(
            symbol='OGUSDT',
            side='BUY',
            qty=10.5,
            entry_price=156.23,
            reason='BoS detected'
        )
        # ... later, quando fechar a posição ...
        logger.log_trade_close(trade_id, exit_price=158.10, pnl=189.35)
    """

    def __init__(self, log_file: str = "logs/trades.json",
                 db_path: str = "db/crypto_agent.db"):
        """
        Inicializa o logger estruturado.

        Args:
            log_file: Caminho do arquivo JSON com logs de trades
            db_path: Caminho do banco SQLite
        """
        self.log_file = log_file
        self.db_manager = DatabaseManager(db_path)

        # Criar diretórios se não existirem
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Inicializar banco de dados
        self.db_manager.init_database()

        # Inicializar arquivo JSON se não existir
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)

    def log_trade_execution(self, symbol: str, side: str, qty: float,
                           entry_price: float, reason: str) -> str:
        """
        Registra execução de trade no entry.

        Args:
            symbol: Símbolo da moeda (ex: 'OGUSDT')
            side: Lado da operação ('BUY' ou 'SELL')
            qty: Quantidade em moeda
            entry_price: Preço de entrada
            reason: Motivo da execução (ex: 'BoS detected', 'market_order_executed')

        Returns:
            trade_id: Identificador único da trade

        Raises:
            ValueError: Se side não for 'BUY' ou 'SELL'
            IOError: Se não conseguir escrever no arquivo ou banco
        """
        if side not in ('BUY', 'SELL'):
            raise ValueError(f"side deve ser 'BUY' ou 'SELL', recebido: {side}")

        # Gerar identificador único da trade
        trade_id = str(uuid.uuid4())
        entry_timestamp = datetime.utcnow().isoformat() + 'Z'

        # Estrutura de dados da trade
        trade_data = {
            'trade_id': trade_id,
            'symbol': symbol,
            'side': side,
            'qty': qty,
            'entry_price': entry_price,
            'exit_price': None,
            'pnl': None,
            'reason': reason,
            'entry_timestamp': entry_timestamp,
            'exit_timestamp': None,
        }

        # Persistir em JSON
        self._append_to_json_log(trade_data)

        # Persistir em SQLite
        db_trade_id = self.db_manager.insert_trade(trade_data)

        return trade_id

    def log_trade_close(self, trade_id: str, exit_price: float,
                       pnl: float) -> bool:
        """
        Atualiza trade no fechamento com exit_price e pnl.

        Args:
            trade_id: Identificador da trade (retornado em log_trade_execution)
            exit_price: Preço de saída
            pnl: Lucro/prejuízo em USD

        Returns:
            bool: True se atualizado com sucesso

        Raises:
            ValueError: Se trade_id não encontrada
        """
        exit_timestamp = datetime.utcnow().isoformat() + 'Z'

        # Atualizar no JSON
        self._update_json_log(trade_id, exit_price, pnl, exit_timestamp)

        # Atualizar no SQLite
        success = self.db_manager.update_trade(
            trade_id=trade_id,
            exit_price=exit_price,
            pnl=pnl,
            exit_timestamp=exit_timestamp
        )

        return success

    def get_audit_trail(self, symbol: Optional[str] = None) -> list:
        """
        Retorna trail de auditoria (todos os trades ou filtrados por symbol).

        Args:
            symbol: Símbolo para filtrar (None = todos)

        Returns:
            list: Lista de dicts com dados das trades
        """
        return self._read_json_log(symbol=symbol)

    def _append_to_json_log(self, trade_data: dict) -> None:
        """Append de novo trade no arquivo JSON."""
        try:
            # Ler existentes
            with open(self.log_file, 'r') as f:
                trades = json.load(f)

            # Adicionar novo
            trades.append(trade_data)

            # Escrever de volta (write-through)
            with open(self.log_file, 'w') as f:
                json.dump(trades, f, indent=2)

        except Exception as e:
            raise IOError(f"Erro ao escrever log JSON: {e}")

    def _update_json_log(self, trade_id: str, exit_price: float,
                        pnl: float, exit_timestamp: str) -> None:
        """Atualiza trade existente no JSON com exit_price e pnl."""
        try:
            # Ler existentes
            with open(self.log_file, 'r') as f:
                trades = json.load(f)

            # Encontrar e atualizar
            found = False
            for trade in trades:
                if trade['trade_id'] == trade_id:
                    trade['exit_price'] = exit_price
                    trade['pnl'] = pnl
                    trade['exit_timestamp'] = exit_timestamp
                    found = True
                    break

            if not found:
                raise ValueError(f"Trade {trade_id} não encontrada")

            # Escrever de volta
            with open(self.log_file, 'w') as f:
                json.dump(trades, f, indent=2)

        except Exception as e:
            raise IOError(f"Erro ao atualizar log JSON: {e}")

    def _read_json_log(self, symbol: Optional[str] = None) -> list:
        """Lê arquivo JSON, opcionalmente filtrado por symbol."""
        try:
            with open(self.log_file, 'r') as f:
                trades = json.load(f)

            if symbol:
                trades = [t for t in trades if t['symbol'] == symbol]

            return trades

        except Exception as e:
            raise IOError(f"Erro ao ler log JSON: {e}")
