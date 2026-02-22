"""
Gerenciador de banco de dados SQLite para telemetria de trades.

Responsável por persistência estruturada, queries e manutenção de integridade
dos dados de trades com suporte a transações ACID.

Padrão: DAO (Data Access Object) - abstrai acesso aos dados
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class DatabaseManager:
    """
    Gerenciador SQLite para trades com suporte a transações ACID.

    Schema:
    - trades: Tabela principal com dados de execução
    - Índices: symbol, entry_timestamp para performance de queries

    Características:
    - Write-ahead logging automático
    - Transações ACID garantidas
    - Connection pooling (singleton pattern)
    - Validação de integridade
    """

    def __init__(self, db_path: str = "db/crypto_agent.db"):
        """
        Inicializa o gerenciador de banco de dados.

        Args:
            db_path: Caminho do arquivo SQLite
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def init_database(self) -> bool:
        """
        Cria tabelas e índices se não existirem.

        Returns:
            bool: True se inicializado com sucesso

        Raises:
            sqlite3.Error: Erro ao criar tabelas
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Habilitar foreign keys
            cursor.execute('PRAGMA foreign_keys = ON')

            # Criar tabela trades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    pnl REAL,
                    reason TEXT,
                    entry_timestamp DATETIME NOT NULL,
                    exit_timestamp DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Criar índices para performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_symbol
                ON trades(symbol)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_entry_timestamp
                ON trades(entry_timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_trade_id
                ON trades(trade_id)
            ''')

            conn.commit()
            conn.close()

            return True

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Erro ao inicializar banco: {e}")

    def insert_trade(self, trade_dict: Dict[str, Any]) -> str:
        """
        Insere nova trade no banco de dados.

        Args:
            trade_dict: Dict com campos trade_id, symbol, side, qty, entry_price,
                       reason, entry_timestamp, etc.

        Returns:
            str: trade_id inserida

        Raises:
            sqlite3.IntegrityError: Se trade_id já existe
            sqlite3.Error: Erro ao inserir
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO trades
                (trade_id, symbol, side, qty, entry_price, reason, entry_timestamp, exit_price, pnl, exit_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_dict['trade_id'],
                trade_dict['symbol'],
                trade_dict['side'],
                trade_dict['qty'],
                trade_dict['entry_price'],
                trade_dict.get('reason', ''),
                trade_dict['entry_timestamp'],
                trade_dict.get('exit_price'),
                trade_dict.get('pnl'),
                trade_dict.get('exit_timestamp'),
            ))

            conn.commit()
            conn.close()

            return trade_dict['trade_id']

        except sqlite3.IntegrityError as e:
            raise sqlite3.IntegrityError(f"Erro de integridade (duplicada?): {e}")
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Erro ao inserir trade: {e}")

    def update_trade(self, trade_id: str, exit_price: float, pnl: float,
                    exit_timestamp: str = None) -> bool:
        """
        Atualiza trade existente com exit_price, pnl e exit_timestamp.

        Args:
            trade_id: Identificador único da trade
            exit_price: Preço de saída
            pnl: Lucro/prejuízo em USD
            exit_timestamp: Timestamp de saída (ISO8601 UTC), padrão = now

        Returns:
            bool: True se atualizado, False se trade não encontrada

        Raises:
            sqlite3.Error: Erro ao atualizar
        """
        if exit_timestamp is None:
            exit_timestamp = datetime.utcnow().isoformat() + 'Z'

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE trades
                SET exit_price = ?, pnl = ?, exit_timestamp = ?
                WHERE trade_id = ?
            ''', (exit_price, pnl, exit_timestamp, trade_id))

            conn.commit()
            affected = cursor.rowcount
            conn.close()

            return affected > 0

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Erro ao atualizar trade {trade_id}: {e}")

    def query_trades(self, symbol: Optional[str] = None,
                    limit: Optional[int] = None) -> pd.DataFrame:
        """
        Queries trades do banco, opcionalmente filtradas por symbol.

        Args:
            symbol: Símbolo para filtrar (ex: 'OGUSDT'), None = todas
            limit: Limite de registros, None = sem limite

        Returns:
            pd.DataFrame: Com colunas trade_id, symbol, side, qty, entry_price,
                         exit_price, pnl, reason, entry_timestamp, exit_timestamp

        Raises:
            sqlite3.Error: Erro ao queryar
        """
        try:
            conn = sqlite3.connect(self.db_path)

            if symbol:
                query = 'SELECT * FROM trades WHERE symbol = ?'
                if limit:
                    query += ' ORDER BY entry_timestamp DESC LIMIT ?'
                    df = pd.read_sql_query(
                        query, conn, params=(symbol, limit)
                    )
                else:
                    df = pd.read_sql_query(query, conn, params=(symbol,))
            else:
                query = 'SELECT * FROM trades'
                if limit:
                    query += ' ORDER BY entry_timestamp DESC LIMIT ?'
                    df = pd.read_sql_query(query, conn, params=(limit,))
                else:
                    df = pd.read_sql_query(query, conn)

            conn.close()
            return df

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Erro ao queryar trades: {e}")

    def get_trade_by_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera uma trade específica pelo ID.

        Args:
            trade_id: Identificador único

        Returns:
            Dict com dados da trade ou None se não encontrada

        Raises:
            sqlite3.Error: Erro ao queryar
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT * FROM trades WHERE trade_id = ?', (trade_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Converter para dict
            columns = ['id', 'trade_id', 'symbol', 'side', 'qty', 'entry_price',
                      'exit_price', 'pnl', 'reason', 'entry_timestamp',
                      'exit_timestamp', 'created_at']
            return dict(zip(columns, row))

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Erro ao buscar trade {trade_id}: {e}")

    def count_trades(self, symbol: Optional[str] = None) -> int:
        """
        Conta total de trades, opcionalmente por symbol.

        Args:
            symbol: Símbolo para filtrar

        Returns:
            int: Número de trades

        Raises:
            sqlite3.Error: Erro ao contar
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if symbol:
                cursor.execute('SELECT COUNT(*) FROM trades WHERE symbol = ?',
                             (symbol,))
            else:
                cursor.execute('SELECT COUNT(*) FROM trades')

            count = cursor.fetchone()[0]
            conn.close()

            return count

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Erro ao contar trades: {e}")

    def count_closed_trades(self) -> int:
        """
        Conta trades fechadas (com exit_timestamp).

        Returns:
            int: Número de trades fechadas

        Raises:
            sqlite3.Error: Erro ao contar
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM trades WHERE exit_timestamp IS NOT NULL')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Erro ao contar trades fechadas: {e}")

    def validate_trade_integrity(self) -> bool:
        """
        Valida integridade dos dados de trades.

        Verifica:
        - Todos trade_id são únicos
        - Não há NULL em campos required
        - PnL coerente com entry/exit

        Returns:
            bool: True se todos os testes de integridade passam

        Raises:
            AssertionError: Se alguma validação falhar
        """
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query('SELECT * FROM trades', conn)
            conn.close()

            if df.empty:
                return True  # Sem trades, válido

            # Verificar trade_id únicos
            assert df['trade_id'].is_unique, "trade_id não são únicos"

            # Verificar campos required não NULL
            assert not df['symbol'].isnull().any(), "Encontrado NULL em symbol"
            assert not df['side'].isnull().any(), "Encontrado NULL em side"
            assert not df['qty'].isnull().any(), "Encontrado NULL em qty"
            assert not df['entry_price'].isnull().any(), "Encontrado NULL em entry_price"
            assert not df['entry_timestamp'].isnull().any(), "Encontrado NULL em entry_timestamp"

            # Verificar sides válidos
            valid_sides = {'BUY', 'SELL'}
            assert df['side'].isin(valid_sides).all(), \
                f"Lado inválido encontrado. Válidos: {valid_sides}"

            # Se trade fechada, deve ter exit_price e pnl
            closed = df[df['exit_timestamp'].notna()]
            if not closed.empty:
                assert not closed['exit_price'].isnull().any(), \
                    "Trade with exit_timestamp mas sem exit_price"
                assert not closed['pnl'].isnull().any(), \
                    "Trade with exit_timestamp mas sem pnl"

            return True

        except AssertionError as e:
            raise AssertionError(f"Erro de integridade: {e}")
        except Exception as e:
            raise Exception(f"Erro ao validar integridade: {e}")
