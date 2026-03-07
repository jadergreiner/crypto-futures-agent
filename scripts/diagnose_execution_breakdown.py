#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico de Execuções - Fase 1: SQL Breakdown

Executa 7 queries SQL críticas para entender:
1. Qual tipo de execução (SET_SL, SET_TP, CLOSE, REDUCE_50)?
2. Sucesso vs bloqueadas?
3. Há posições abertas?
4. Há qualquer trade?
5. CLOSE/REDUCE bem-sucedidas?
6. Por que foram bloqueadas?
7. Sincronização entre bancos?

Saída: Console estruturado + JSON para análise posterior

Uso:
    python scripts/diagnose_execution_breakdown.py

Autor: GitHub Copilot
Data: 2026-03-07
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple


class ExecutionDiagnostics:
    """Diagnóstico de discrepância: 121 execuções vs 0 trades fechadas."""

    def __init__(self, db_path: str = "db/crypto_futures.db"):
        """
        Inicializa diagnóstico.

        Args:
            db_path: Caminho do banco de dados principal
        """
        self.db_path = db_path
        self.conn = None
        self.results = {}
        self.hypotheses = []

    def connect(self) -> bool:
        """Conecta ao banco de dados."""
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

    def execute_query(self, query: str, description: str) -> Tuple[List, str]:
        """
        Executa query e retorna resultados.

        Args:
            query: SQL query
            description: Descrição da query

        Returns:
            Tuple de (resultados, erro_se_houver)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows, None
        except Exception as e:
            return [], str(e)

    def query_1_execution_breakdown(self) -> Dict[str, Any]:
        """
        Query 1: Breakdown de execuções por action e executed status.

        Revela: Qual é o tipo das 121 execuções?
        """
        description = "Breakdowm de execuções por action e executed status"
        query = """
        SELECT
            action,
            executed,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM execution_log), 1) as pct
        FROM execution_log
        GROUP BY action, executed
        ORDER BY count DESC
        """

        rows, error = self.execute_query(query, description)

        if error:
            return {'erro': error}

        result = {
            'descricao': description,
            'query': query.strip(),
            'dados': []
        }

        for row in rows:
            action = row[0]
            executed = row[1]
            count = row[2]
            pct = row[3]

            status = "✅ Bem-sucedida" if executed == 1 else "❌ Bloqueada"
            result['dados'].append({
                'action': action,
                'executed': executed,
                'status': status,
                'count': count,
                'pct': pct
            })

        return result

    def query_2_open_positions(self) -> Dict[str, Any]:
        """
        Query 2: Contagem de posições abertas vs fechadas.

        Revela: Há posições em aberto no trade_log?
        """
        description = "Posições abertas vs fechadas"
        query = """
        SELECT
            SUM(CASE WHEN timestamp_saida IS NOT NULL THEN 1 ELSE 0 END) as fechadas,
            SUM(CASE WHEN timestamp_saida IS NULL THEN 1 ELSE 0 END) as abertas
        FROM trade_log
        """

        rows, error = self.execute_query(query, description)

        if error:
            return {'erro': error}

        row = rows[0] if rows else (0, 0)
        fechadas = row[0] or 0
        abertas = row[1] or 0
        total = fechadas + abertas

        return {
            'descricao': description,
            'query': query.strip(),
            'fechadas': int(fechadas),
            'abertas': int(abertas),
            'total': int(total),
            'summary': f"{abertas} abertas + {fechadas} fechadas = {total} total"
        }

    def query_3_total_trades(self) -> Dict[str, Any]:
        """
        Query 3: Contagem total de trades (baseline).

        Revela: O trade_log está vazio?
        """
        description = "Total de trades no banco"
        query = "SELECT COUNT(*) as total FROM trade_log"

        rows, error = self.execute_query(query, description)

        if error:
            return {'erro': error}

        total = rows[0][0] if rows else 0

        return {
            'descricao': description,
            'query': query.strip(),
            'total': int(total),
            'status': "✅ Banco tem dados" if total > 0 else "❌ BANCO VAZIO"
        }

    def query_4_close_reduce_status(self) -> Dict[str, Any]:
        """
        Query 4: Status de CLOSE/REDUCE_50 execuções.

        Revela: CLOSE/REDUCE bem-sucedidas existem?
        """
        description = "Status de execuções CLOSE/REDUCE_50"
        query = """
        SELECT
            action,
            executed,
            COUNT(*) as count
        FROM execution_log
        WHERE action IN ('CLOSE', 'REDUCE_50')
        GROUP BY action, executed
        ORDER BY action, executed DESC
        """

        rows, error = self.execute_query(query, description)

        if error:
            return {'erro': error}

        result = {
            'descricao': description,
            'query': query.strip(),
            'dados': []
        }

        for row in rows:
            action = row[0]
            executed = row[1]
            count = row[2]

            status = "✅ Bem-sucedida" if executed == 1 else "❌ Bloqueada"
            result['dados'].append({
                'action': action,
                'executed': executed,
                'status': status,
                'count': count
            })

        if not rows:
            result['alerta'] = "⚠️ CRÍTICO: Nenhuma CLOSE/REDUCE detectada!"

        return result

    def query_5_blocked_reasons(self) -> Dict[str, Any]:
        """
        Query 5: Motivos de bloqueio de execuções.

        Revela: Por que execuções foram bloqueadas?
        """
        description = "Motivos de bloqueio de execuções"
        query = """
        SELECT
            reason,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM execution_log WHERE executed=0), 1) as pct_of_blocked
        FROM execution_log
        WHERE executed = 0
        GROUP BY reason
        ORDER BY count DESC
        """

        rows, error = self.execute_query(query, description)

        if error:
            return {'erro': error}

        result = {
            'descricao': description,
            'query': query.strip(),
            'dados': [],
            'total_bloqueadas': 0
        }

        for row in rows:
            reason = row[0] or "Unknown"
            count = row[1]
            pct = row[2]

            result['dados'].append({
                'reason': reason,
                'count': count,
                'pct_of_blocked': pct
            })
            result['total_bloqueadas'] += count

        if not rows:
            result['status'] = "✅ Nenhuma execução bloqueada"

        return result

    def query_6_last_execution(self) -> Dict[str, Any]:
        """
        Query 6: Última execução registrada.

        Revela: Quando foi a última atividade?
        """
        description = "Última execução registrada"
        query = """
        SELECT
            MAX(timestamp) as last_ts_ms,
            datetime(MAX(timestamp)/1000, 'unixepoch') as last_ts_utc
        FROM execution_log
        """

        rows, error = self.execute_query(query, description)

        if error:
            return {'erro': error}

        row = rows[0] if rows else (None, None)
        ts_ms = row[0]
        ts_utc = row[1]

        return {
            'descricao': description,
            'query': query.strip(),
            'last_timestamp_ms': ts_ms,
            'last_timestamp_utc': ts_utc,
            'nota': "Indica atividade recente se < 24h"
        }

    def query_7_last_trade_update(self) -> Dict[str, Any]:
        """
        Query 7: Última atualização de trade_log.

        Revela: Quando foi a última atividade em trade_log?
        """
        description = "Última atualização de trade_log"
        query = """
        SELECT
            MAX(timestamp_entrada) as last_entrada_ms,
            datetime(MAX(timestamp_entrada)/1000, 'unixepoch') as last_entrada_utc,
            MAX(COALESCE(timestamp_saida, 0)) as last_saida_ms,
            datetime(MAX(COALESCE(timestamp_saida, 0))/1000, 'unixepoch') as last_saida_utc
        FROM trade_log
        """

        rows, error = self.execute_query(query, description)

        if error:
            return {'erro': error}

        row = rows[0] if rows else (None, None, None, None)
        entrada_ms = row[0]
        entrada_utc = row[1]
        saida_ms = row[2] or 0
        saida_utc = row[3] if saida_ms > 0 else None

        return {
            'descricao': description,
            'query': query.strip(),
            'ultima_entrada_ms': entrada_ms,
            'ultima_entrada_utc': entrada_utc,
            'ultima_saida_ms': saida_ms if saida_ms > 0 else None,
            'ultima_saida_utc': saida_utc,
            'nota': "Gap entre entrada e saída revela se posições estão se sincronizando"
        }

    def query_8_protection_orders_only(self) -> Dict[str, Any]:
        """
        Query 8: Todas execuções são proteção (SET_SL/SET_TP)?

        Revela: % de execuções que são apenas proteção
        """
        description = "Percentual de execuções que são proteção (SET_SL/SET_TP)"
        query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN action IN ('SET_SL', 'SET_TP') THEN 1 ELSE 0 END) as protection_orders,
            SUM(CASE WHEN action IN ('OPEN', 'CLOSE', 'REDUCE_50') THEN 1 ELSE 0 END) as position_orders,
            ROUND(
                SUM(CASE WHEN action IN ('SET_SL', 'SET_TP') THEN 1 ELSE 0 END) * 100.0 /
                COUNT(*),
                1
            ) as protection_pct
        FROM execution_log
        """

        rows, error = self.execute_query(query, description)

        if error:
            return {'erro': error}

        row = rows[0] if rows else (0, 0, 0, 0)
        total = row[0] or 0
        protection = row[1] or 0
        position_mgmt = row[2] or 0
        pct = row[3] or 0.0

        return {
            'descricao': description,
            'query': query.strip(),
            'total_executions': int(total),
            'protection_orders': int(protection),
            'position_management_orders': int(position_mgmt),
            'protection_pct': float(pct),
            'interpretation': (
                f"Se protection_pct > 80%, então #{protection} das 121 "
                f"execuções são apenas ordens de proteção (SET_SL/SET_TP), "
                f"NÃO closures de posições."
            )
        }

    def run_diagnostics(self) -> bool:
        """Executa todas as queries de diagnóstico."""
        if not self.connect():
            return False

        print("\n" + "="*80)
        print(" "*20 + "DIAGNÓSTICO FASE 1: SQL BREAKDOWN")
        print("="*80)
        print(f"Banco: {self.db_path}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
        print("="*80)

        # Executar queries
        self.results['q1_execution_breakdown'] = self.query_1_execution_breakdown()
        self.results['q2_open_positions'] = self.query_2_open_positions()
        self.results['q3_total_trades'] = self.query_3_total_trades()
        self.results['q4_close_reduce_status'] = self.query_4_close_reduce_status()
        self.results['q5_blocked_reasons'] = self.query_5_blocked_reasons()
        self.results['q6_last_execution'] = self.query_6_last_execution()
        self.results['q7_last_trade_update'] = self.query_7_last_trade_update()
        self.results['q8_protection_orders'] = self.query_8_protection_orders_only()

        self.disconnect()
        return True

    def print_console_report(self):
        """Imprime relatório formatado no console."""

        # Seção 1: Breakdown de Execuções
        print("\n📊 QUERY 1: BREAKDOWN DE EXECUÇÕES")
        print("-" * 80)
        q1 = self.results.get('q1_execution_breakdown', {})
        if 'erro' in q1:
            print(f"❌ {q1['erro']}")
        else:
            df_q1 = pd.DataFrame(q1.get('dados', []))
            if not df_q1.empty:
                print(df_q1[['action', 'status', 'count', 'pct']].to_string(index=False))
            else:
                print("(Sem dados)")

        # Seção 2: Posições Abertas vs Fechadas
        print("\n🔓 QUERY 2: POSIÇÕES ABERTAS VS FECHADAS")
        print("-" * 80)
        q2 = self.results.get('q2_open_positions', {})
        if 'erro' in q2:
            print(f"❌ {q2['erro']}")
        else:
            print(f"  Abertas:  {q2.get('abertas', 0)}")
            print(f"  Fechadas: {q2.get('fechadas', 0)}")
            print(f"  Total:    {q2.get('total', 0)}")

        # Seção 3: Total de Trades
        print("\n📈 QUERY 3: TOTAL DE TRADES")
        print("-" * 80)
        q3 = self.results.get('q3_total_trades', {})
        if 'erro' in q3:
            print(f"❌ {q3['erro']}")
        else:
            status = q3.get('status', '?')
            total = q3.get('total', 0)
            print(f"  Total Trades: {total}")
            print(f"  Status: {status}")

        # Seção 4: CLOSE/REDUCE Status
        print("\n🔒 QUERY 4: STATUS DE CLOSE/REDUCE_50")
        print("-" * 80)
        q4 = self.results.get('q4_close_reduce_status', {})
        if 'erro' in q4:
            print(f"❌ {q4['erro']}")
        else:
            if 'alerta' in q4:
                print(f"⚠️ {q4['alerta']}")
            df_q4 = pd.DataFrame(q4.get('dados', []))
            if not df_q4.empty:
                print(df_q4[['action', 'status', 'count']].to_string(index=False))
            else:
                print("(Sem CLOSE/REDUCE execuções)")

        # Seção 5: Motivos de Bloqueio
        print("\n🚫 QUERY 5: MOTIVOS DE BLOQUEIO")
        print("-" * 80)
        q5 = self.results.get('q5_blocked_reasons', {})
        if 'erro' in q5:
            print(f"❌ {q5['erro']}")
        else:
            if q5.get('total_bloqueadas', 0) == 0:
                print("✅ Nenhuma execução bloqueada (todas bem-sucedidas!)")
            else:
                df_q5 = pd.DataFrame(q5.get('dados', []))
                print(df_q5[['reason', 'count', 'pct_of_blocked']].to_string(index=False))

        # Seção 6: Última Execução
        print("\n⏰ QUERY 6: ÚLTIMA EXECUÇÃO")
        print("-" * 80)
        q6 = self.results.get('q6_last_execution', {})
        if 'erro' in q6:
            print(f"❌ {q6['erro']}")
        else:
            print(f"  Timestamp UTC: {q6.get('last_timestamp_utc', 'N/A')}")
            print(f"  Nota: {q6.get('nota', '')}")

        # Seção 7: Última Atualização de Trade
        print("\n⏰ QUERY 7: ÚLTIMA ATUALIZAÇÃO DE TRADE_LOG")
        print("-" * 80)
        q7 = self.results.get('q7_last_trade_update', {})
        if 'erro' in q7:
            print(f"❌ {q7['erro']}")
        else:
            print(f"  Última Entrada: {q7.get('ultima_entrada_utc', 'N/A')}")
            print(f"  Última Saída:   {q7.get('ultima_saida_utc', 'N/A')}")
            print(f"  Nota: {q7.get('nota', '')}")

        # Seção 8: Protection Orders
        print("\n🛡️ QUERY 8: PERCENTUAL DE ORDENS DE PROTEÇÃO")
        print("-" * 80)
        q8 = self.results.get('q8_protection_orders', {})
        if 'erro' in q8:
            print(f"❌ {q8['erro']}")
        else:
            total = q8.get('total_executions', 0)
            protection = q8.get('protection_orders', 0)
            position_mgmt = q8.get('position_management_orders', 0)
            pct = q8.get('protection_pct', 0)
            print(f"  Total Execuções:        {total}")
            print(f"  Proteção (SET_SL/SET_TP): {protection} ({pct}%)")
            print(f"  Gerencia Posição:       {position_mgmt}")
            print(f"\n  💡 Interpretação:")
            print(f"     {q8.get('interpretation', '')}")

        # Seção Final: Síntese de Hipóteses
        self.print_hypotheses()

    def print_hypotheses(self):
        """Imprime análise de hipóteses baseado em resultados."""
        print("\n" + "="*80)
        print("🔍 ANÁLISE DE HIPÓTESES")
        print("="*80)

        q1 = self.results.get('q1_execution_breakdown', {})
        q2 = self.results.get('q2_open_positions', {})
        q3 = self.results.get('q3_total_trades', {})
        q4 = self.results.get('q4_close_reduce_status', {})
        q5 = self.results.get('q5_blocked_reasons', {})
        q8 = self.results.get('q8_protection_orders', {})

        hypotheses = []

        # Hipótese 1
        if q8.get('protection_pct', 0) > 80:
            hypotheses.append({
                'numero': 1,
                'nome': 'Execuções são Proteção, não Closures',
                'prioridade': 'HIGH',
                'evidencia': f"SET_SL/SET_TP = {q8.get('protection_orders', 0)}% de todas as execuções",
                'acao': 'Verificar monitor_positions.py: está criando ordens de proteção sem fechar trades'
            })

        # Hipótese 2
        if q3.get('total', 0) == 0:
            hypotheses.append({
                'numero': 2,
                'nome': 'Banco de Trades Vazio',
                'prioridade': 'CRITICAL',
                'evidencia': 'trade_log.COUNT() = 0',
                'acao': 'Agent nunca abriu posições. Revisar risk_gate.py e agent decision logic'
            })

        # Hipótese 3
        if q2.get('abertas', 0) == 0 and q2.get('fechadas', 0) > 0:
            hypotheses.append({
                'numero': 3,
                'nome': 'Posições foram Fechadas (Histórico)',
                'prioridade': 'MEDIUM',
                'evidencia': f"Abertas = {q2.get('abertas')}, Fechadas = {q2.get('fechadas')}",
                'acao': 'Investigar: Por que nenhuma OPEN nova depois que todas foram fechadas?'
            })

        # Hipótese 4
        close_reduce_data = self.results.get('q4_close_reduce_status', {}).get('dados', [])
        close_success = sum(1 for d in close_reduce_data if d.get('executed') == 1 and d.get('action') in ['CLOSE', 'REDUCE_50'])
        if close_success > 0 and q2.get('abertas', 0) == 0:
            hypotheses.append({
                'numero': 4,
                'nome': 'CLOSE Executadas mas trade_log não Sincronizado',
                'prioridade': 'HIGH',
                'evidencia': f"CLOSE/REDUCE bem-sucedidas existem, mas timestamp_saida = NULL",
                'acao': 'Iniciar scripts/monitor_positions.py para sincronizar'
            })

        # Hipótese 5
        blocked_total = q5.get('total_bloqueadas', 0)
        if blocked_total > 50:
            hypotheses.append({
                'numero': 5,
                'nome': 'Execuções Massivamente Bloqueadas',
                'prioridade': 'CRITICAL',
                'evidencia': f"{blocked_total} execuções bloqueadas ({blocked_total/121*100:.0f}%)",
                'acao': 'Revisar reasons: procurar padrões em risk_gate.py bloqueios'
            })

        # Imprimir hipóteses
        for h in hypotheses:
            print(f"\n✓ Hipótese {h['numero']}: {h['nome']}")
            print(f"  Prioridade: {h['prioridade']}")
            print(f"  Evidência: {h['evidencia']}")
            print(f"  Ação: {h['acao']}")

        if not hypotheses:
            print("\n⚠️  Nenhuma hipótese clara identificada. Revisar dados manualmente.")

    def export_to_json(self, output_path: str = "reports/diagnostico_fase1.json"):
        """Exporta resultados para JSON."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        report = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'banco': self.db_path,
            'resultados': self.results
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Exportado: {output_path}")

    def run(self):
        """Executa diagnóstico completo."""
        if not self.run_diagnostics():
            return False

        self.print_console_report()
        self.export_to_json()

        return True


if __name__ == "__main__":
    diag = ExecutionDiagnostics()
    success = diag.run()
    exit(0 if success else 1)
