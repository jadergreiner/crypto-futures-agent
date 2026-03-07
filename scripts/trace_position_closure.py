#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rastreamento de Closagem de Posições - Fase 2

Rastreia cada posição aberta e tenta encontrar:
1. Sua entrada (timestamp_entrada em trade_log)
2. Sua saída esperada (execução CLOSE/REDUCE em execution_log)
3. Se está refletida em trade_log (timestamp_saida preenchido)
4. Identificar gaps de sincronização

Saída: Relatório detalhado + CSV para análise forensica

Uso:
    python scripts/trace_position_closure.py

Autor: GitHub Copilot
Data: 2026-03-07
"""

import sqlite3
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple


class PositionClosureTracer:
    """Rastreia closagem de posições e identifica gaps de sincronização."""

    def __init__(self, db_path: str = "db/crypto_futures.db"):
        """
        Inicializa rastreador.

        Args:
            db_path: Caminho do banco de dados
        """
        self.db_path = db_path
        self.conn = None
        self.open_positions = []
        self.closed_positions = []
        self.orphaned_executions = []
        self.sync_gaps = []
        self.summary = {}

    def connect(self) -> bool:
        """Conecta ao banco."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            print(f"❌ Erro ao conectar: {e}")
            return False

    def disconnect(self):
        """Desconecta."""
        if self.conn:
            self.conn.close()

    def fetch_all(self, query: str) -> List:
        """Executa query e retorna todos os resultados."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Erro na query: {e}")
            return []

    def analyze_open_positions(self):
        """
        Analisa todas posições abertas e tenta rastrear sua closagem.
        """
        print("\n🔓 Analisando POSIÇÕES ABERTAS...")

        query = """
        SELECT
            trade_id,
            timestamp_entrada,
            symbol,
            direcao,
            entry_price,
            position_size_usdt
        FROM trade_log
        WHERE timestamp_saida IS NULL
        ORDER BY timestamp_entrada DESC
        """

        rows = self.fetch_all(query)

        if not rows:
            print("   ✅ Nenhuma posição aberta")
            return

        print(f"   📍 {len(rows)} posições abertas encontradas\n")

        for row in rows:
            trade_id = row[0]
            entrada_ms = row[1]
            symbol = row[2]
            direcao = row[3]
            entry_price = row[4]
            position_size = row[5]

            # Procurar execução CLOSE/REDUCE para esta posição
            exec_query = f"""
            SELECT
                id,
                timestamp,
                action,
                executed,
                reason,
                fill_price
            FROM execution_log
            WHERE symbol = '{symbol}'
            AND timestamp > {entrada_ms}
            AND action IN ('CLOSE', 'REDUCE_50')
            ORDER BY timestamp DESC
            LIMIT 1
            """

            exec_rows = self.fetch_all(exec_query)

            position_record = {
                'trade_id': trade_id,
                'symbol': symbol,
                'direcao': direcao,
                'entrada_ms': entrada_ms,
                'entrada_utc': self._ms_to_iso(entrada_ms),
                'entry_price': entry_price,
                'position_size': position_size,
                'status': 'ABERTA'
            }

            if exec_rows:
                exec_row = exec_rows[0]
                exec_id = exec_row[0]
                exec_timestamp = exec_row[1]
                exec_action = exec_row[2]
                exec_executed = exec_row[3]
                exec_reason = exec_row[4]
                exec_fill_price = exec_row[5]

                position_record['close_execution'] = {
                    'id': exec_id,
                    'timestamp_ms': exec_timestamp,
                    'timestamp_utc': self._ms_to_iso(exec_timestamp),
                    'action': exec_action,
                    'executed': exec_executed,
                    'executed_status': '✅ Bem-sucedida' if exec_executed == 1 else '❌ Bloqueada',
                    'reason': exec_reason,
                    'fill_price': exec_fill_price,
                    'time_to_close_min': (exec_timestamp - entrada_ms) / (60 * 1000)
                }

                if exec_executed == 1:
                    position_record['sync_status'] = (
                        '⚠️ EXECUTADA MAS NÃO SINCRONIZADA'
                        if exec_timestamp < datetime.utcnow().timestamp() * 1000 - 300000
                        else '🔄 Sincronia pendente'
                    )
                else:
                    position_record['sync_status'] = '❌ Execução bloqueada'
            else:
                position_record['close_execution'] = None
                position_record['sync_status'] = '❓ Nenhuma tentativa CLOSE/REDUCE encontrada'

            self.open_positions.append(position_record)

            # Print resume
            status_icon = "✅" if position_record.get('close_execution') and position_record['close_execution']['executed'] == 1 else "❌"
            close_action = position_record.get('close_execution', {}).get('action', 'N/A') if position_record.get('close_execution') else 'N/A'
            print(f"{status_icon} Trade #{trade_id} ({symbol}): {close_action if close_action != 'N/A' else 'Sem tentativa de close'}")

    def analyze_closed_positions(self):
        """
        Analisa posições fechadas para validar sincronização.
        """
        print("\n🔒 Analisando POSIÇÕES FECHADAS...")

        query = """
        SELECT
            trade_id,
            timestamp_entrada,
            timestamp_saida,
            symbol,
            pnl_usdt,
            motivo_saida
        FROM trade_log
        WHERE timestamp_saida IS NOT NULL
        ORDER BY timestamp_saida DESC
        LIMIT 100
        """

        rows = self.fetch_all(query)

        if not rows:
            print("   ✅ Nenhuma posição fechada")
            return

        print(f"   📍 {len(rows)} posições fechadas encontradas (mostrando últimas 100)\n")

        for row in rows:
            trade_id = row[0]
            entrada_ms = row[1]
            saida_ms = row[2]
            symbol = row[3]
            pnl = row[4]
            motivo = row[5]

            duration_min = (saida_ms - entrada_ms) / (60 * 1000)

            position_record = {
                'trade_id': trade_id,
                'symbol': symbol,
                'entrada_utc': self._ms_to_iso(entrada_ms),
                'saida_utc': self._ms_to_iso(saida_ms),
                'duration_min': duration_min,
                'pnl_usdt': pnl,
                'motivo_saida': motivo,
                'status': 'FECHADA'
            }

            self.closed_positions.append(position_record)

    def analyze_orphaned_executions(self):
        """
        Procura por execuções CLOSE/REDUCE que não têm tradeログ correspondente.
        """
        print("\n🎯 Analisando EXECUÇÕES ÓRFÃS...")

        query = """
        SELECT
            id,
            timestamp,
            symbol,
            action,
            executed,
            reason
        FROM execution_log
        WHERE action IN ('CLOSE', 'REDUCE_50')
        AND executed = 1
        ORDER BY timestamp DESC
        """

        rows = self.fetch_all(query)

        if not rows:
            print("   ✅ Nenhuma execução CLOSE/REDUCE")
            return

        print(f"   📍 {len(rows)} execuções CLOSE/REDUCE bem-sucedidas encontradas\n")

        orphans_count = 0

        for row in rows:
            exec_id = row[0]
            exec_timestamp = row[1]
            symbol = row[2]
            action = row[3]
            executed = row[4]
            reason = row[5]

            # Procurar trade_log correspondente
            trade_query = f"""
            SELECT COUNT(*) as count
            FROM trade_log
            WHERE symbol = '{symbol}'
            AND timestamp_entrada < {exec_timestamp}
            AND (timestamp_saida IS NULL OR timestamp_saida >= {exec_timestamp})
            """

            trade_rows = self.fetch_all(trade_query)
            has_trade = trade_rows[0][0] > 0 if trade_rows else False

            if not has_trade:
                orphans_count += 1
                self.orphaned_executions.append({
                    'exec_id': exec_id,
                    'timestamp_utc': self._ms_to_iso(exec_timestamp),
                    'symbol': symbol,
                    'action': action,
                    'reason': reason
                })

        if orphans_count > 0:
            print(f"   ⚠️ {orphans_count} EXECUÇÕES ÓRFÃS (executadas mas sem trade_log correspondente)")
        else:
            print("   ✅ Todas execuções têm trade_log correspondente")

    def identify_sync_gaps(self):
        """
        Identifica gaps entre execution_log e trade_log.
        """
        print("\n🔄 Analisando GAPS DE SINCRONIZAÇÃO...")

        # Comparar últimas 24h
        gap_query = """
        SELECT
            (SELECT COUNT(*) FROM execution_log WHERE timestamp > strftime('%s', 'now', '-1 day') * 1000) as exec_24h,
            (SELECT COUNT(*) FROM trade_log WHERE timestamp_entrada > strftime('%s', 'now', '-1 day') * 1000) as trades_24h,
            (SELECT COUNT(*) FROM trade_log WHERE timestamp_saida > strftime('%s', 'now', '-1 day') * 1000) as closes_24h
        """

        rows = self.fetch_all(gap_query)

        if rows:
            row = rows[0]
            exec_24h = row[0]
            trades_24h = row[1]
            closes_24h = row[2]

            print(f"   Últimas 24 horas:")
            print(f"   - Execuções: {exec_24h}")
            print(f"   - Trades Abertas: {trades_24h}")
            print(f"   - Trades Fechadas: {closes_24h}")

            # Análise de gap
            if exec_24h > 0 and closes_24h == 0:
                gap_record = {
                    'tipo': 'EXECUÇÕES SEM CLOSES',
                    'severidade': 'CRITICAL',
                    'descricao': f'{exec_24h} execuções registradas mas 0 trades fechadas',
                    'possivel_causa': 'Monitor de posições não rodando ou não sincronizando'
                }
                self.sync_gaps.append(gap_record)
                print(f"\n   ⚠️ {gap_record['descricao']}")

            if trades_24h > closes_24h and trades_24h > 0:
                gap_record = {
                    'tipo': 'POSIÇÕES NÃO FECHADAS',
                    'severidade': 'HIGH',
                    'descricao': f'{trades_24h - closes_24h} posições abertas nas últimas 24h que não foram fechadas',
                    'possivel_causa': 'Lóg ica de closagem não está gerando sinais ou bloqueios impedem closes'
                }
                self.sync_gaps.append(gap_record)
                print(f"   ⚠️ {gap_record['descricao']}")

    def generate_summary(self):
        """Gera resumo executivo."""
        print("\n" + "="*80)
        print("📋 RESUMO EXECUTIVO")
        print("="*80)

        self.summary = {
            'open_positions': len(self.open_positions),
            'closed_positions': len(self.closed_positions),
            'orphaned_executions': len(self.orphaned_executions),
            'sync_gaps': len(self.sync_gaps),
            'diagnostico': None
        }

        print(f"\n Posições Abertas:        {self.summary['open_positions']}")
        print(f" Posições Fechadas:      {self.summary['closed_positions']}")
        print(f" Execuções Órfãs:        {self.summary['orphaned_executions']}")
        print(f" Gaps de Sincronização:  {self.summary['sync_gaps']}")

        # Diagnóstico
        if self.summary['orphaned_executions'] > 0:
            self.summary['diagnostico'] = (
                "CRÍTICO: Execuções bem-sucedidas não estão refletidas em trade_log. "
                "Monitor de posições provavelmente não está sincronizando."
            )
        elif self.summary['open_positions'] > 0 and self.summary['sync_gaps'] > 0:
            self.summary['diagnostico'] = (
                "Posições abertas encontradas. Verificar se há tentativas de close "
                "que não foram bem-sucedidas."
            )
        else:
            self.summary['diagnostico'] = "Sincronização aparentemente consistente."

        print(f"\n💡 Diagnóstico: {self.summary['diagnostico']}")

    def export_to_csv(self, output_dir: str = "reports/fase2_diagnostico"):
        """Exporta detalhes para CSV."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Arquivo 1: Posições Abertas
        if self.open_positions:
            df = pd.DataFrame(self.open_positions)
            csv_path = Path(output_dir) / "open_positions.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8')
            print(f"✅ Exportado: {csv_path}")

        # Arquivo 2: Posições Fechadas
        if self.closed_positions:
            df = pd.DataFrame(self.closed_positions)
            csv_path = Path(output_dir) / "closed_positions.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8')
            print(f"✅ Exportado: {csv_path}")

        # Arquivo 3: Execuções Órfãs
        if self.orphaned_executions:
            df = pd.DataFrame(self.orphaned_executions)
            csv_path = Path(output_dir) / "orphaned_executions.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8')
            print(f"✅ Exportado: {csv_path}")

    def export_to_json(self, output_path: str = "reports/diagnostico_fase2.json"):
        """Exporta relatório para JSON."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        report = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'banco': self.db_path,
            'summary': self.summary,
            'open_positions': self.open_positions,
            'closed_positions': self.closed_positions[:20],  # Limitar a 20 mais recentes
            'orphaned_executions': self.orphaned_executions,
            'sync_gaps': self.sync_gaps
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ Exportado: {output_path}")

    def _ms_to_iso(self, ms: int) -> str:
        """Converte timestamp Unix ms para ISO8601."""
        if not ms:
            return "N/A"
        try:
            dt = datetime.utcfromtimestamp(ms / 1000)
            return dt.isoformat() + 'Z'
        except:
            return "Invalid"

    def run(self):
        """Executa análise completa."""
        if not self.connect():
            return False

        print("\n" + "="*80)
        print(" "*20 + "RASTREAMENTO FASE 2: CLOSAGEM DE POSIÇÕES")
        print("="*80)

        self.analyze_open_positions()
        self.analyze_closed_positions()
        self.analyze_orphaned_executions()
        self.identify_sync_gaps()
        self.generate_summary()

        self.export_to_csv()
        self.export_to_json()

        self.disconnect()
        return True


if __name__ == "__main__":
    tracer = PositionClosureTracer()
    success = tracer.run()
    exit(0 if success else 1)
