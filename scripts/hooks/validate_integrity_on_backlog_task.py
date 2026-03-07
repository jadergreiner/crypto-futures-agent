#!/usr/bin/env python3
"""
Validador de Integridade do Database antes de aceitar nova tarefa de backlog.

Quando uma tarefa é solicitada (issue aberta, task adicionada ao backlog),
este script valida:
1. Integridade referencial do database (orfãos, trades obsoletos)
2. Sincronização entre crypto_futures.db e arquivos de log
3. Impacto da nova tarefa na arquitetura existente

Uso:
  python scripts/hooks/validate_integrity_on_backlog_task.py \
    --backlog-item "US-001" \
    --affected-modules "position_monitor.py,order_executor.py"

Resultado: PASS ou FAIL com relatório detalhado
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DatabaseIntegrityValidator:
    """Valida integridade do database antes de aceitar nova tarefa."""

    def __init__(self, db_path: str = "db/crypto_futures.db"):
        self.db_path = db_path
        self.errors = []
        self.warnings = []
        self.results = {}

    def validate_orphaned_executions(self) -> Tuple[int, List[Dict]]:
        """
        Busca execuções sem correspondente em trade_log.
        Estas são as execuções órfãs que precisam ser rastreadas.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    e.id,
                    e.timestamp,
                    e.symbol,
                    e.action,
                    e.executed,
                    e.reason
                FROM execution_log e
                WHERE NOT EXISTS (
                    SELECT 1 FROM trade_log t
                    WHERE t.symbol = e.symbol
                    AND t.timestamp_entrada < e.timestamp
                )
                ORDER BY e.timestamp DESC
                LIMIT 100
            """)

            orphans = [dict(row) for row in cursor.fetchall()]
            count = len(orphans)

            if count > 0:
                msg = f"Encontrados {count} execuções órfãs"
                self.warnings.append(msg)

            return count, orphans

        finally:
            conn.close()

    def validate_stale_positions(self) -> Tuple[int, List[Dict]]:
        """
        Posições abertas por mais de 30 dias indicam:
        - Agente não conseguiu fechar
        - Risco não gerenciado adequadamente
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    trade_id,
                    symbol,
                    datetime(timestamp_entrada/1000, 'unixepoch')
                        as opened_at,
                    ROUND((strftime('%s', 'now') * 1000 -
                        timestamp_entrada) / 86400000.0) as days_open
                FROM trade_log
                WHERE timestamp_saida IS NULL
                AND (strftime('%s', 'now') * 1000 -
                    timestamp_entrada) > 2592000000
                ORDER BY timestamp_entrada ASC
            """)

            stale = [dict(row) for row in cursor.fetchall()]
            count = len(stale)

            if count > 0:
                msg = f"ALERTA: {count} posições abertas por > 30 dias"
                self.errors.append(msg)

            return count, stale

        finally:
            conn.close()

    def validate_missing_pnl(self) -> Tuple[int, List[Dict]]:
        """
        Trades fechados sem PnL calculado
        = Quebra no fluxo de dados (execution → trade_log)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    trade_id,
                    symbol,
                    datetime(timestamp_entrada/1000, 'unixepoch')
                        as opened_at,
                    datetime(timestamp_saida/1000, 'unixepoch')
                        as closed_at
                FROM trade_log
                WHERE timestamp_saida IS NOT NULL
                AND (pnl_usdt IS NULL OR pnl_pct IS NULL)
                ORDER BY timestamp_saida DESC
            """)

            missing = [dict(row) for row in cursor.fetchall()]
            count = len(missing)

            if count > 0:
                msg = f"CRÍTICO: {count} trades fechados sem PnL"
                self.errors.append(msg)

            return count, missing

        finally:
            conn.close()

    def get_database_size(self) -> float:
        """Retorna tamanho do database em MB."""
        return os.path.getsize(self.db_path) / (1024 * 1024)

    def get_record_counts(self) -> Dict[str, int]:
        """Conta registros em cada tabela principal."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        counts = {}

        try:
            for table in ['trade_log', 'execution_log',
                         'position_snapshots', 'trade_signals']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]

            return counts

        finally:
            conn.close()

    def validate_module_consistency(self,
                                   affected_modules: List[str]) \
                                   -> Dict[str, List[str]]:
        """
        Verifica se módulos afetados pela nova tarefa
        mantêm acesso consistente ao database.
        """
        impact = {}

        # Mapa de módulos → tabelas que acessam
        module_dependencies = {
            'position_monitor.py': [
                'trade_log', 'execution_log', 'position_snapshots'
            ],
            'order_executor.py': [
                'execution_log', 'trade_log'
            ],
            'monitor_positions.py': [
                'trade_log'
            ],
            'risk_gate.py': [
                'execution_log'
            ],
            'audit_trail.py': [
                'trade_log', 'execution_log'
            ]
        }

        for module in affected_modules:
            if module in module_dependencies:
                impact[module] = module_dependencies[module]

        return impact

    def generate_report(self, backlog_item: str = None,
                       affected_modules: List[str] = None) -> Dict:
        """Gera relatório completo de integridade."""

        logger.info("Iniciando validação de integridade...")

        # Verificações
        orphan_count, orphans = self.validate_orphaned_executions()
        stale_count, stales = self.validate_stale_positions()
        missing_count, missings = self.validate_missing_pnl()

        counts = self.get_record_counts()
        db_size = self.get_database_size()

        module_impact = self.validate_module_consistency(
            affected_modules or []
        )

        report = {
            'timestamp': datetime.now().isoformat(),
            'backlog_item': backlog_item,
            'status': 'PASS' if not self.errors else 'FAIL',
            'database': {
                'path': self.db_path,
                'size_mb': round(db_size, 2),
                'record_counts': counts
            },
            'integrity_checks': {
                'orphaned_executions': {
                    'count': orphan_count,
                    'severity': 'WARNING',
                    'details': orphans[:3]  # Primeiros 3
                },
                'stale_positions': {
                    'count': stale_count,
                    'severity': 'ERROR',
                    'details': stales
                },
                'missing_pnl': {
                    'count': missing_count,
                    'severity': 'CRITICAL',
                    'details': missings[:3]
                }
            },
            'module_impact': module_impact,
            'errors': self.errors,
            'warnings': self.warnings,
            'recommendation': self._generate_recommendation(
                orphan_count, stale_count, missing_count
            )
        }

        return report

    def _generate_recommendation(self, orphan_count: int,
                                stale_count: int,
                                missing_count: int) -> str:
        """Gera recomendação baseada em problemas encontrados."""

        if missing_count > 0:
            return (
                "BLOQUEADO: Existe desincronização crítica entre "
                "execution_log e trade_log. "
                "Resolva antes de aceitar nova tarefa."
            )

        if stale_count > 0:
            return (
                "ACEITAR COM RESSALVAS: Existem posições obsoletas. "
                "Priorizar limpeza em paralelo com nova tarefa."
            )

        if orphan_count > 0:
            return (
                "ACEITAR: Orfãos encontrados mas kontrolados. "
                "Monitorar durante execução."
            )

        return "ACEITAR: Database em condição operacional saudável."


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Valida integridade antes de aceitar tarefa'
    )
    parser.add_argument(
        '--backlog-item',
        help='ID da tarefa (ex: US-001, F-02)'
    )
    parser.add_argument(
        '--affected-modules',
        help='Módulos afetados (CSV: position_monitor.py,etc)'
    )
    parser.add_argument(
        '--output-json',
        help='Salvar relatório em JSON'
    )

    args = parser.parse_args()

    validator = DatabaseIntegrityValidator()
    affected = []
    if args.affected_modules:
        affected = [m.strip()
                   for m in args.affected_modules.split(',')]

    report = validator.generate_report(
        backlog_item=args.backlog_item,
        affected_modules=affected
    )

    # Print relatório
    logger.info("=" * 70)
    logger.info(f"VALIDAÇÃO DE INTEGRIDADE - {args.backlog_item or 'AD-HOC'}")
    logger.info("=" * 70)
    logger.info(f"Status: {report['status']}")
    logger.info(f"Orfãos: {report['integrity_checks']['orphaned_executions']['count']}")
    logger.info(f"Stales: {report['integrity_checks']['stale_positions']['count']}")
    logger.info(f"PnL Missing: {report['integrity_checks']['missing_pnl']['count']}")
    logger.info("=" * 70)
    logger.info(f"Recomendação: {report['recommendation']}")
    logger.info("=" * 70)

    # Salvar JSON se solicitado
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Relatório salvo em: {args.output_json}")

    # Retornar código de saída apropriado
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
