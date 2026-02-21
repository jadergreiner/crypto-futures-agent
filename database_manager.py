"""
Gerenciador de Persistência de Dados para Orquestrador de Reuniões.

Este módulo implementa a camada de persistência SQLite para armazenar
histórico de sessões de reuniões e snapshots de decisões tomadas pelos
agentes autônomos.

Módulos:
    sqlite3: biblioteca nativa para gerenciar banco de dados SQLite
    json: biblioteca nativa para serialização de dados estruturados
    datetime: biblioteca nativa para manipulação de timestamps
    os: biblioteca nativa para validação de caminhos
"""

import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple


class DatabaseManager:
    """
    Gerenciador central de persistência de dados para reuniões e backlog.

    Responsabilidades:
    - Inicializar e validar schema do banco de dados
    - Salvar snapshots de decisões e contexto de reuniões
    - Recuperar histórico formatado para injeção em prompts

    Atributos:
        db_path (str): Caminho absoluto ao arquivo database.db
    """

    def __init__(self, db_path: str = "reunioes.db"):
        """
        Inicializa o gerenciador de banco de dados.

        Args:
            db_path (str): Caminho do arquivo SQLite. Padrão: "reunioes.db"

        Raises:
            IOError: Se não conseguir criar ou acessar o diretório
        """
        self.db_path = os.path.abspath(db_path)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """
        Garante que o diretório do banco de dados existe.

        Raises:
            IOError: Se não conseguir criar o diretório
        """
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError as erro:
                raise IOError(f"Não foi possível criar diretório: {db_dir}") from erro

    @contextmanager
    def _get_connection(self, timeout: int = 10):
        """
        Context manager para gerenciar conexões SQLite com segurança.

        Args:
            timeout (int): Tempo máximo de espera por lock do banco em segundos

        Yields:
            sqlite3.Connection: Conexão com o banco de dados

        Raises:
            sqlite3.OperationalError: Se não conseguir conectar ao banco
        """
        conexao = None
        try:
            conexao = sqlite3.connect(self.db_path, timeout=timeout)
            conexao.row_factory = sqlite3.Row  # Retorna resultados como dicionários
            yield conexao
            conexao.commit()
        except sqlite3.Error as erro:
            if conexao:
                conexao.rollback()
            raise sqlite3.OperationalError(
                f"Erro ao acessar banco de dados {self.db_path}: {str(erro)}"
            ) from erro
        finally:
            if conexao:
                conexao.close()

    def initialize_db(self) -> bool:
        """
        Inicializa o banco de dados com schema padrão.

        Cria as tabelas 'meetings' e 'backlog' se não existirem.
        Valida integridade do arquivo .db após criação.

        Returns:
            bool: True se inicialização foi bem-sucedida, False caso contrário

        Raises:
            sqlite3.Error: Se ocorrer erro ao criar tabelas
        """
        try:
            with self._get_connection() as conexao:
                cursor = conexao.cursor()

                # Criar tabela de reuniões
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS meetings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        executive_summary TEXT NOT NULL,
                        decisions JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Criar tabela de backlog
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS backlog (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task TEXT NOT NULL,
                        owner TEXT,
                        priority TEXT DEFAULT 'MEDIUM',
                        status TEXT DEFAULT 'OPEN',
                        meeting_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                    )
                """)

                # Criar índices para otimizar queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_meetings_date 
                    ON meetings(date DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_backlog_meeting_id 
                    ON backlog(meeting_id)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_backlog_status 
                    ON backlog(status)
                """)

            # Validar integridade
            return self._validate_database()

        except sqlite3.Error as erro:
            print(f"ERRO: Inicialização de banco de dados falhou: {str(erro)}")
            return False

    def _validate_database(self) -> bool:
        """
        Valida a integridade do banco de dados.

        Returns:
            bool: True se o banco está íntegro, False caso contrário
        """
        try:
            with self._get_connection() as conexao:
                cursor = conexao.cursor()

                # Verificar se as tabelas existem
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='meetings'"
                )
                if not cursor.fetchone():
                    return False

                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='backlog'"
                )
                if not cursor.fetchone():
                    return False

                # Executar PRAGMA check
                cursor.execute("PRAGMA integrity_check")
                resultado = cursor.fetchone()
                return resultado[0] == "ok"

        except sqlite3.Error:
            return False

    def get_last_context(self) -> str:
        """
        Recupera o contexto da última reunião registrada.

        Formata uma string contendo:
        1. Resumo executivo da última reunião
        2. Decisões tomadas
        3. Lista de itens pendentes no backlog

        Útil para injetar em prompts de IA para referência de contexto anterior.

        Returns:
            str: Contexto formatado pronto para injeção em prompt, ou
                 string vazia se não houver histórico

        Raises:
            sqlite3.Error: Se ocorrer erro ao consultar banco
        """
        try:
            with self._get_connection() as conexao:
                cursor = conexao.cursor()

                # Recuperar última reunião
                cursor.execute("""
                    SELECT id, date, executive_summary, decisions 
                    FROM meetings 
                    ORDER BY date DESC 
                    LIMIT 1
                """)
                ultima_reuniao = cursor.fetchone()

                if not ultima_reuniao:
                    return ""

                meeting_id, data_reuniao, resumo, decisoes_json = ultima_reuniao

                # Recover itens de backlog abertos dessa reunião
                cursor.execute("""
                    SELECT task, owner, priority, status 
                    FROM backlog 
                    WHERE meeting_id = ? 
                    AND status IN ('OPEN', 'IN_PROGRESS')
                    ORDER BY priority DESC, created_at ASC
                """, (meeting_id,))
                itens_backlog = cursor.fetchall()

                # Formatar contexto
                contexto = f"""
═══════════════════════════════════════════════════════════════
CONTEXTO DE REUNIÃO ANTERIOR
═══════════════════════════════════════════════════════════════

📅 Data da Última Reunião: {data_reuniao}

📋 RESUMO EXECUTIVO:
{resumo}

🎯 DECISÕES TOMADAS:
"""
                try:
                    decisoes = json.loads(decisoes_json)
                    if isinstance(decisoes, list):
                        for i, decisao in enumerate(decisoes, 1):
                            contexto += f"\n  {i}. {decisao}"
                    elif isinstance(decisoes, dict):
                        for chave, valor in decisoes.items():
                            contexto += f"\n  • {chave}: {valor}"
                except json.JSONDecodeError:
                    contexto += f"\n  {decisoes_json}"

                # Adicionar backlog
                if itens_backlog:
                    contexto += "\n\n📌 ITENS PENDENTES DO BACKLOG:\n"
                    for i, item in enumerate(itens_backlog, 1):
                        task, owner, priority, status = item
                        contexto += f"\n  [{i}] ({priority}) {task}"
                        if owner:
                            contexto += f"\n      Responsável: {owner}"
                        contexto += f"\n      Status: {status}"
                else:
                    contexto += "\n\n✅ Sem itens pendentes no backlog\n"

                contexto += "\n═══════════════════════════════════════════════════════════════\n"
                return contexto

        except sqlite3.Error as erro:
            print(f"ERRO ao recuperar contexto: {str(erro)}")
            return ""

    def save_snapshot(
        self,
        executive_summary: str,
        decisions: List[str] | Dict,
        backlog_items: List[Dict] | None = None,
    ) -> Optional[int]:
        """
        Salva um snapshot de reunião e backlog no banco de dados.

        Operação atômica: insere reunião e todos os itens de backlog
        em uma única transação. Se qualquer operação falhar, toda a
        transação é desfeita (rollback).

        Args:
            executive_summary (str): Resumo executivo da reunião
            decisions (List[str] | Dict): Decisões tomadas (lista ou dicionário)
            backlog_items (List[Dict], optional): Lista de itens do backlog.
                Cada item deve ter chaves: 'task', 'owner' (opcional),
                'priority' (opcional, padrão 'MEDIUM'), 'status' (opcional, padrão 'OPEN').

        Returns:
            Optional[int]: ID da reunião inserida se bem-sucedido, None se falhar

        Raises:
            ValueError: Se executive_summary estiver vazio ou decisões inválidas
            sqlite3.Error: Se ocorrer erro ao inserir no banco

        Exemplo:
            snapshot = database_manager.save_snapshot(
                executive_summary="Reunião P&L: Análise de performance Q1",
                decisions={
                    "Ação 1": "Aumentar alavancagem em BTC",
                    "Ação 2": "Reduzir risco sistêmico"
                },
                backlog_items=[
                    {
                        "task": "Auditar modelo de risk management",
                        "owner": "Engenheiro de Risk",
                        "priority": "HIGH",
                        "status": "IN_PROGRESS"
                    },
                    {
                        "task": "Backtest com novos parâmetros",
                        "owner": "Engenheiro de ML",
                        "priority": "MEDIUM",
                        "status": "OPEN"
                    }
                ]
            )
        """
        if not executive_summary or not executive_summary.strip():
            raise ValueError("executive_summary não pode estar vazio")

        if not decisions:
            raise ValueError("decisions não pode estar vazia")

        if not isinstance(decisions, (list, dict)):
            raise ValueError("decisions deve ser uma lista ou dicionário")

        try:
            with self._get_connection() as conexao:
                cursor = conexao.cursor()

                # Inserir reunião
                decisions_json = json.dumps(decisions, ensure_ascii=False, indent=2)
                cursor.execute("""
                    INSERT INTO meetings (executive_summary, decisions)
                    VALUES (?, ?)
                """, (executive_summary, decisions_json))

                meeting_id = cursor.lastrowid

                # Inserir itens de backlog se fornecidos
                if backlog_items:
                    for item in backlog_items:
                        task = item.get("task", "").strip()
                        owner = item.get("owner", "").strip()
                        priority = item.get("priority", "MEDIUM").upper()
                        status = item.get("status", "OPEN").upper()

                        if not task:
                            print(
                                "AVISO: Item do backlog sem 'task' foi ignorado"
                            )
                            continue

                        # Validar prioridade
                        if priority not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
                            priority = "MEDIUM"

                        # Validar status
                        if status not in ("OPEN", "IN_PROGRESS", "DONE", "BLOCKED"):
                            status = "OPEN"

                        cursor.execute("""
                            INSERT INTO backlog (task, owner, priority, status, meeting_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, (task, owner if owner else None, priority, status, meeting_id))

                return meeting_id

        except ValueError as erro:
            print(f"ERRO de validação: {str(erro)}")
            return None
        except sqlite3.Error as erro:
            print(f"ERRO ao salvar snapshot: {str(erro)}")
            return None

    def get_backlog(
        self, status_filter: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        """
        Recupera itens do backlog com filtro opcional de status.

        Args:
            status_filter (Optional[str]): Filtro por status
                (OPEN, IN_PROGRESS, DONE, BLOCKED). None = todos.
            limit (int): Número máximo de itens a retornar

        Returns:
            List[Dict]: Lista de itens do backlog ou lista vazia

        Raises:
            sqlite3.Error: Se ocorrer erro ao consultar banco
        """
        try:
            with self._get_connection() as conexao:
                cursor = conexao.cursor()

                if status_filter and status_filter.upper() in (
                    "OPEN",
                    "IN_PROGRESS",
                    "DONE",
                    "BLOCKED",
                ):
                    cursor.execute("""
                        SELECT id, task, owner, priority, status, meeting_id, created_at
                        FROM backlog
                        WHERE status = ?
                        ORDER BY priority DESC, created_at ASC
                        LIMIT ?
                    """, (status_filter.upper(), limit))
                else:
                    cursor.execute("""
                        SELECT id, task, owner, priority, status, meeting_id, created_at
                        FROM backlog
                        ORDER BY priority DESC, created_at ASC
                        LIMIT ?
                    """, (limit,))

                resultados = cursor.fetchall()
                return [dict(row) for row in resultados]

        except sqlite3.Error as erro:
            print(f"ERRO ao recuperar backlog: {str(erro)}")
            return []

    def update_backlog_status(self, item_id: int, novo_status: str) -> bool:
        """
        Atualiza o status de um item do backlog.

        Args:
            item_id (int): ID do item do backlog
            novo_status (str): Novo status (OPEN, IN_PROGRESS, DONE, BLOCKED)

        Returns:
            bool: True se atualização foi bem-sucedida, False caso contrário

        Raises:
            ValueError: Se status for inválido
            sqlite3.Error: Se ocorrer erro ao atualizar banco
        """
        novo_status_upper = novo_status.upper()
        if novo_status_upper not in ("OPEN", "IN_PROGRESS", "DONE", "BLOCKED"):
            raise ValueError(f"Status inválido: {novo_status}")

        try:
            with self._get_connection() as conexao:
                cursor = conexao.cursor()
                cursor.execute("""
                    UPDATE backlog
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (novo_status_upper, item_id))

                return cursor.rowcount > 0

        except sqlite3.Error as erro:
            print(f"ERRO ao atualizar status do backlog: {str(erro)}")
            return False

    def get_meeting_history(self, limit: int = 10) -> List[Dict]:
        """
        Recupera histórico de reuniões anteriores.

        Args:
            limit (int): Número máximo de reuniões a retornar

        Returns:
            List[Dict]: Lista de reuniões com id, date e executive_summary

        Raises:
            sqlite3.Error: Se ocorrer erro ao consultar banco
        """
        try:
            with self._get_connection() as conexao:
                cursor = conexao.cursor()
                cursor.execute("""
                    SELECT id, date, executive_summary
                    FROM meetings
                    ORDER BY date DESC
                    LIMIT ?
                """, (limit,))

                resultados = cursor.fetchall()
                return [dict(row) for row in resultados]

        except sqlite3.Error as erro:
            print(f"ERRO ao recuperar histórico de reuniões: {str(erro)}")
            return []


# Instância global para facilitar uso em módulos
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(db_path: str = "reunioes.db") -> DatabaseManager:
    """
    Factory para obter instância do gerenciador de banco de dados.

    Implementa padrão Singleton para evitar múltiplas conexões.

    Args:
        db_path (str): Caminho do arquivo SQLite. Padrão: "reunioes.db"

    Returns:
        DatabaseManager: Instância do gerenciador

    Exemplo:
        db = get_database_manager()
        db.initialize_db()
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager
