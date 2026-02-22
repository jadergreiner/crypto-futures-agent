"""
Sistema de auditoria para reconstrução de histórico operacional.

Permite análise retrospectiva de trades, PnL, estratégias e desempenho
com ferramentas de exportação e validação.

Padrão: Strategy pattern para diferentes formatos de export
"""

import pandas as pd
from datetime import datetime
from typing import Optional
from pathlib import Path

from logs.database_manager import DatabaseManager


class AuditTrail:
    """
    Auditoria strutturada para histórico de trades.

    Responsabilidades:
    - Reconstruir histórico de PnL por símbolo/período
    - Validar integridade transacional
    - Exportar dados para análise external (CSV, etc)
    - Gerar relatórios de desempenho

    Padrão de uso:
        audit = AuditTrail()
        pnl_df = audit.reconstruct_pnl_history('OGUSDT')
        audit.validate_trade_integrity()
        audit.export_to_csv('reports/trades.csv')
    """

    def __init__(self, db_path: str = "db/crypto_agent.db"):
        """
        Inicializa o sistema de auditoria.

        Args:
            db_path: Caminho do banco SQLite
        """
        self.db_manager = DatabaseManager(db_path)

    def reconstruct_pnl_history(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Reconstrói histórico de PnL para um símbolo ou todos.

        Calcula:
        - PnL acumulado
        - Win rate
        - Avg win/loss
        - ROI por trade

        Args:
            symbol: Símbolo para filtrar (None = todos)

        Returns:
            pd.DataFrame: Com colunas:
                - trade_id, symbol, side, qty
                - entry_price, exit_price, pnl
                - pnl_cumsum (PnL acumulado)
                - entry_timestamp, exit_timestamp

        Raises:
            ValueError: Se nenhuma trade encontrada
        """
        df = self.db_manager.query_trades(symbol=symbol)

        if df.empty:
            raise ValueError(
                f"Nenhuma trade encontrada para {symbol or 'todos os símbolos'}"
            )

        # Filtrar apenas trades fechadas (com PnL)
        closed = df[df['pnl'].notna()].copy()

        if closed.empty:
            raise ValueError("Nenhuma trade fechada encontrada")

        # Converter timestamps
        closed['entry_timestamp'] = pd.to_datetime(closed['entry_timestamp'])
        closed['exit_timestamp'] = pd.to_datetime(closed['exit_timestamp'])

        # Sort por entry_timestamp
        closed = closed.sort_values('entry_timestamp').reset_index(drop=True)

        # Calcular PnL acumulado
        closed['pnl_cumsum'] = closed['pnl'].cumsum()

        # Adicionar win/loss flag
        closed['winner'] = (closed['pnl'] > 0).astype(int)

        return closed[[
            'trade_id', 'symbol', 'side', 'qty',
            'entry_price', 'exit_price', 'pnl', 'pnl_cumsum',
            'winner', 'entry_timestamp', 'exit_timestamp'
        ]]

    def get_pnl_summary(self, symbol: Optional[str] = None) -> dict:
        """
        Retorna resumo de PnL (total, win rate, etc).

        Args:
            symbol: Símbolo para filtrar

        Returns:
            dict: Com métricas de performance
                - total_pnl: PnL total em USD
                - trade_count: Total de trades fechadas
                - win_rate: Percentual de trades vencedoras
                - avg_win: PnL médio das vencedoras
                - avg_loss: PnL médio das perdedoras
                - largest_win: Maior win
                - largest_loss: Maior loss
                - avg_roi: ROI médio por trade

        """
        try:
            pnl_df = self.reconstruct_pnl_history(symbol=symbol)
        except ValueError:
            return {
                'total_pnl': 0.0,
                'trade_count': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'avg_roi': 0.0,
            }

        total_pnl = pnl_df['pnl'].sum()
        trade_count = len(pnl_df)

        winners = pnl_df[pnl_df['pnl'] > 0]
        losers = pnl_df[pnl_df['pnl'] < 0]

        win_count = len(winners)
        loss_count = len(losers)

        win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0.0
        avg_win = winners['pnl'].mean() if len(winners) > 0 else 0.0
        avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0.0
        largest_win = winners['pnl'].max() if len(winners) > 0 else 0.0
        largest_loss = losers['pnl'].min() if len(losers) > 0 else 0.0

        # ROI por trade (PnL / valor investido)
        roi_values = (pnl_df['pnl'] / (pnl_df['entry_price'] * pnl_df['qty'])) * 100
        avg_roi = roi_values.mean() if len(roi_values) > 0 else 0.0

        return {
            'total_pnl': float(total_pnl),
            'trade_count': int(trade_count),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'largest_win': float(largest_win),
            'largest_loss': float(largest_loss),
            'avg_roi': float(avg_roi),
        }

    def validate_trade_integrity(self) -> bool:
        """
        Valida integridade completa de todos os trades.

        Executa validações:
        - DatabaseManager.validate_trade_integrity()
        - Timestamps em ordem correta
        - Sem gaps ou inconsistências

        Returns:
            bool: True se todas as validações passam

        Raises:
            AssertionError: Se alguma validação falha
        """
        # Validação base do banco
        self.db_manager.validate_trade_integrity()

        # Validações adicionais
        df = self.db_manager.query_trades()

        if df.empty:
            return True  # Sem dados, válido

        # Datas em ordem chronológica
        df['entry_timestamp'] = pd.to_datetime(df['entry_timestamp'])
        df['exit_timestamp'] = pd.to_datetime(df['exit_timestamp'])

        closed = df[df['exit_timestamp'].notna()]
        if not closed.empty:
            assert (closed['exit_timestamp'] >= closed['entry_timestamp']).all(), \
                "exit_timestamp antes de entry_timestamp encontrado"

        return True

    def export_to_csv(self, filepath: str) -> str:
        """
        Exporta todos os trades para CSV.

        Args:
            filepath: Caminho de destino (ex: 'reports/trades.csv')

        Returns:
            str: Caminho absoluto do arquivo criado

        Raises:
            IOError: Erro ao escrever arquivo

        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            df = self.db_manager.query_trades()

            if df.empty:
                # Criar arquivo vazio
                with open(filepath, 'w') as f:
                    f.write('')
                return filepath

            # Selecionar colunas relevantes
            cols_to_export = [
                'trade_id', 'symbol', 'side', 'qty',
                'entry_price', 'exit_price', 'pnl',
                'reason', 'entry_timestamp', 'exit_timestamp'
            ]

            # Filtrar apenas colunas que existem
            cols = [c for c in cols_to_export if c in df.columns]
            df_export = df[cols].copy()

            # Escrever CSV
            df_export.to_csv(filepath, index=False)

            return filepath

        except Exception as e:
            raise IOError(f"Erro ao exportar para CSV: {e}")

    def export_to_json(self, filepath: str) -> str:
        """
        Exporta todos os trades para JSON.

        Args:
            filepath: Caminho de destino (ex: 'reports/trades.json')

        Returns:
            str: Caminho absoluto do arquivo criado

        Raises:
            IOError: Erro ao escrever arquivo
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            df = self.db_manager.query_trades()

            if df.empty:
                with open(filepath, 'w') as f:
                    f.write('[]')
                return filepath

            # Converter para formato JSON
            cols_to_export = [
                'trade_id', 'symbol', 'side', 'qty',
                'entry_price', 'exit_price', 'pnl',
                'reason', 'entry_timestamp', 'exit_timestamp'
            ]

            cols = [c for c in cols_to_export if c in df.columns]
            df_export = df[cols].copy()

            # Serializar como JSON
            df_export.to_json(filepath, orient='records', indent=2)

            return filepath

        except Exception as e:
            raise IOError(f"Erro ao exportar para JSON: {e}")

    def get_trades_by_symbol(self, symbol: str, limit: int = None) -> pd.DataFrame:
        """
        Retorna todas as trades de um símbolo específico.

        Args:
            symbol: Símbolo (ex: 'OGUSDT')
            limit: Limite de registros

        Returns:
            pd.DataFrame: Com dados das trades

        Raises:
            ValueError: Se símbolo não encontrado
        """
        df = self.db_manager.query_trades(symbol=symbol, limit=limit)

        if df.empty:
            raise ValueError(f"Nenhuma trade encontrada para {symbol}")

        return df

    def get_open_trades(self) -> pd.DataFrame:
        """
        Retorna trades ainda abertas (sem exit_timestamp).

        Returns:
            pd.DataFrame: Com dados das trades abertas, ou vazio se nenhuma
        """
        df = self.db_manager.query_trades()

        if df.empty:
            return df

        return df[df['exit_timestamp'].isnull()].copy()

    def get_closed_trades(self) -> pd.DataFrame:
        """
        Retorna trades fechadas (com exit_timestamp e PnL).

        Returns:
            pd.DataFrame: Com dados das trades fechadas
        """
        df = self.db_manager.query_trades()

        if df.empty:
            return df

        return df[df['exit_timestamp'].notna()].copy()
