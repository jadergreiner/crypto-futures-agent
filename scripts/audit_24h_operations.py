#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria de operações do Agente - Últimas 24 horas

Consolida dados de trade_log, execution_log, trade_signals e position_snapshots
para análise integrada com métricas financeiras, estatísticas de execução,
análise de risco e recomendações de ação.

Saídas:
- Console: Relatório formatado com tabelas ASCII
- CSV: 3 arquivos (trades, executions, signals) em reports/audit_24h/
- JSON: Dump estruturado para integração com sistemas

Uso:
    python scripts/audit_24h_operations.py

Autor: GitHub Copilot
Data: 2026-03-07
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np
import sys


class AuditOperations24h:
    """
    Auditoria integrada de operações das últimas 24 horas.

    Consolida:
    - Trade log (trades abertas/fechadas, PnL)
    - Execution log (execuções bloqueadas/bem-sucedidas)
    - Trade signals (sinais gerados e seu status)
    - Position snapshots (snapshot das decisões do agente)

    Responsabilidades:
    - Calcular janela de 24 horas
    - Executar queries SQL paralelas
    - Gerar métricas consolidadas
    - Detectar anomalias
    - Produzir relatórios em múltiplos formatos
    - Emitir recomendações
    """

    def __init__(self, db_path: str = "db/crypto_agent.db"):
        """
        Inicializa auditoria.

        Args:
            db_path: Caminho do banco SQLite
        """
        self.db_path = db_path
        self.conn = None
        self.now_ms = int(datetime.utcnow().timestamp() * 1000)
        self.hours_24_ago_ms = self.now_ms - (24 * 60 * 60 * 1000)

        # DataFrames de dados brutos
        self.df_trades = None
        self.df_executions = None
        self.df_signals = None
        self.df_snapshots = None

        # Resultados de análises
        self.metrics = {}
        self.anomalies = []
        self.recommendations = []

    def connect(self) -> bool:
        """Conecta ao banco de dados."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            print(f"❌ Erro ao conectar ao banco: {e}", file=sys.stderr)
            return False

    def disconnect(self):
        """Desconecta do banco."""
        if self.conn:
            self.conn.close()

    def _fetch_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Executa query e retorna DataFrame."""
        try:
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        except Exception as e:
            print(f"❌ Erro na query: {e}", file=sys.stderr)
            return pd.DataFrame()

    def load_data(self) -> bool:
        """
        Carrega dados das últimas 24 horas do banco.

        Returns:
            bool: True se sucesso, False se erro
        """
        if not self.connect():
            return False

        try:
            # Query 1: Trade log (últimas 24h)
            self.df_trades = self._fetch_query(f"""
                SELECT
                    trade_id, timestamp_entrada, timestamp_saida, symbol, direcao,
                    entry_price, exit_price, stop_loss, take_profit,
                    pnl_usdt, pnl_pct, r_multiple, leverage, margin_type,
                    liquidation_price, position_size_usdt, motivo_saida
                FROM trade_log
                WHERE timestamp_entrada >= ?
                ORDER BY timestamp_entrada DESC
            """, (self.hours_24_ago_ms,))

            # Query 2: Execution log (últimas 24h)
            self.df_executions = self._fetch_query(f"""
                SELECT
                    id, timestamp, symbol, direction, action, side, quantity,
                    executed, mode, reason, order_id, fill_price, fill_quantity,
                    entry_price, mark_price, unrealized_pnl, unrealized_pnl_pct,
                    risk_score, decision_confidence, decision_reasoning
                FROM execution_log
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (self.hours_24_ago_ms,))

            # Query 3: Trade signals (últimas 24h)
            self.df_signals = self._fetch_query(f"""
                SELECT
                    id, timestamp, symbol, direction, entry_price, stop_loss,
                    take_profit_1, take_profit_2, take_profit_3,
                    position_size_suggested, risk_pct, risk_reward_ratio,
                    leverage_suggested, confluence_score, rsi_14, ema_17, ema_34,
                    market_structure, funding_rate, long_short_ratio,
                    execution_mode, executed_at, executed_price
                FROM trade_signals
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (self.hours_24_ago_ms,))

            # Query 4: Position snapshots (últimas 5 por símbolo nas últimas 24h)
            self.df_snapshots = self._fetch_query(f"""
                SELECT
                    id, timestamp, symbol, direction, entry_price, mark_price,
                    position_size_qty, position_size_usdt, leverage,
                    unrealized_pnl, unrealized_pnl_pct, liquidation_price,
                    rsi_14, ema_17, agent_action, decision_confidence,
                    risk_score, funding_rate, long_short_ratio
                FROM position_snapshots
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (self.hours_24_ago_ms,))

            self.disconnect()
            return True

        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}", file=sys.stderr)
            self.disconnect()
            return False

    def _ms_to_iso(self, ms: int) -> str:
        """Converte timestamp Unix ms para ISO8601 UTC."""
        if pd.isna(ms):
            return None
        dt = datetime.utcfromtimestamp(ms / 1000)
        return dt.isoformat() + 'Z'

    def _normalize_trades(self):
        """Normaliza DataFrame de trades com conversões de timestamp."""
        if self.df_trades.empty:
            return

        self.df_trades['timestamp_entrada'] = self.df_trades['timestamp_entrada'].apply(self._ms_to_iso)
        self.df_trades['timestamp_saida'] = self.df_trades['timestamp_saida'].apply(self._ms_to_iso)
        self.df_trades['pnl_usdt'] = pd.to_numeric(self.df_trades['pnl_usdt'], errors='coerce')
        self.df_trades['pnl_pct'] = pd.to_numeric(self.df_trades['pnl_pct'], errors='coerce')

    def _normalize_executions(self):
        """Normaliza DataFrame de execuções."""
        if self.df_executions.empty:
            return

        self.df_executions['timestamp'] = self.df_executions['timestamp'].apply(self._ms_to_iso)
        self.df_executions['executed'] = self.df_executions['executed'].astype(int)
        self.df_executions['fill_price'] = pd.to_numeric(self.df_executions['fill_price'], errors='coerce')

    def _normalize_signals(self):
        """Normaliza DataFrame de sinais."""
        if self.df_signals.empty:
            return

        self.df_signals['timestamp'] = self.df_signals['timestamp'].apply(self._ms_to_iso)
        self.df_signals['entry_price'] = pd.to_numeric(self.df_signals['entry_price'], errors='coerce')
        self.df_signals['executed_at'] = self.df_signals['executed_at'].apply(self._ms_to_iso)

    def _normalize_snapshots(self):
        """Normaliza DataFrame de snapshots."""
        if self.df_snapshots.empty:
            return

        self.df_snapshots['timestamp'] = self.df_snapshots['timestamp'].apply(self._ms_to_iso)
        self.df_snapshots['unrealized_pnl'] = pd.to_numeric(self.df_snapshots['unrealized_pnl'], errors='coerce')

    def analyze_financial_summary(self) -> Dict[str, Any]:
        """
        Calcula resumo financeiro das trades.

        Returns:
            Dict com métricas: total_pnl, taxa_acerto, maior_ganho, maior_perda, etc
        """
        if self.df_trades.empty:
            return {
                'total_pnl_usdt': 0.0,
                'total_pnl_pct': 0.0,
                'trade_count': 0,
                'trades_abertas': 0,
                'trades_fechadas': 0,
                'win_rate_pct': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'maior_ganho': 0.0,
                'maior_perda': 0.0,
                'r_multiple_medio': 0.0,
                'expectativa_positiva': False,
            }

        # Trades fechadas (com PnL)
        closed_trades = self.df_trades[self.df_trades['pnl_usdt'].notna()].copy()
        open_trades = self.df_trades[self.df_trades['pnl_usdt'].isna()]

        total_pnl = closed_trades['pnl_usdt'].sum()
        trade_count = len(self.df_trades)
        trades_fechadas = len(closed_trades)
        trades_abertas = len(open_trades)

        if trades_fechadas == 0:
            return {
                'total_pnl_usdt': 0.0,
                'total_pnl_pct': 0.0,
                'trade_count': trade_count,
                'trades_abertas': trades_abertas,
                'trades_fechadas': trades_fechadas,
                'win_rate_pct': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'maior_ganho': 0.0,
                'maior_perda': 0.0,
                'r_multiple_medio': 0.0,
                'expectativa_positiva': False,
            }

        winners = closed_trades[closed_trades['pnl_usdt'] > 0]
        losers = closed_trades[closed_trades['pnl_usdt'] < 0]

        win_rate = (len(winners) / trades_fechadas * 100) if trades_fechadas > 0 else 0.0
        avg_win = winners['pnl_usdt'].mean() if len(winners) > 0 else 0.0
        avg_loss = losers['pnl_usdt'].mean() if len(losers) > 0 else 0.0
        maior_ganho = winners['pnl_usdt'].max() if len(winners) > 0 else 0.0
        maior_perda = losers['pnl_usdt'].min() if len(losers) > 0 else 0.0

        # R múltiplo médio
        r_values = closed_trades['r_multiple'].dropna()
        r_multiple_medio = r_values.mean() if len(r_values) > 0 else 0.0

        # Expectativa: (prob_win * avg_win) + (prob_loss * avg_loss)
        prob_win = win_rate / 100
        prob_loss = 1 - prob_win
        expectativa = (prob_win * avg_win) + (prob_loss * avg_loss)

        return {
            'total_pnl_usdt': float(total_pnl),
            'total_pnl_pct': float(closed_trades['pnl_pct'].sum()),
            'trade_count': int(trade_count),
            'trades_abertas': int(trades_abertas),
            'trades_fechadas': int(trades_fechadas),
            'win_rate_pct': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'maior_ganho': float(maior_ganho),
            'maior_perda': float(maior_perda),
            'r_multiple_medio': float(r_multiple_medio),
            'expectativa_positiva': float(expectativa) > 0,
        }

    def analyze_execution_statistics(self) -> Dict[str, Any]:
        """
        Calcula estatísticas de execução.

        Returns:
            Dict com executadas, bloqueadas, erros, por modo, etc
        """
        if self.df_executions.empty:
            return {
                'total_executions': 0,
                'executions_success': 0,
                'executions_blocked': 0,
                'success_rate_pct': 0.0,
                'by_mode': {'paper': 0, 'live': 0},
                'blocked_reasons': {},
                'symbols_count': 0,
            }

        total = len(self.df_executions)
        success = (self.df_executions['executed'] == 1).sum()
        blocked = (self.df_executions['executed'] == 0).sum()

        success_rate = (success / total * 100) if total > 0 else 0.0

        by_mode = {
            'paper': int((self.df_executions['mode'] == 'paper').sum()),
            'live': int((self.df_executions['mode'] == 'live').sum()),
        }

        # Motivos de bloqueio
        blocked_only = self.df_executions[self.df_executions['executed'] == 0]
        blocked_reasons = {}
        for reason in blocked_only['reason'].fillna('Unknown'):
            blocked_reasons[reason] = blocked_reasons.get(reason, 0) + 1

        symbols_count = self.df_executions['symbol'].nunique()

        return {
            'total_executions': int(total),
            'executions_success': int(success),
            'executions_blocked': int(blocked),
            'success_rate_pct': float(success_rate),
            'by_mode': by_mode,
            'blocked_reasons': blocked_reasons,
            'symbols_count': int(symbols_count),
        }

    def analyze_risk_metrics(self) -> Dict[str, Any]:
        """
        Calcula métricas de risco.

        Returns:
            Dict com drawdown, circuit breaker ativações, stops, etc
        """
        if self.df_trades.empty:
            return {
                'circuit_breaker_activations': 0,
                'stop_loss_triggered': 0,
                'max_leverage': 0,
                'avg_leverage': 0.0,
                'liquidation_risk_count': 0,
            }

        # Circuit breaker (motivo_saida = 'circuit_breaker')
        cb_activations = (self.df_trades['motivo_saida'] == 'circuit_breaker').sum()

        # Stop loss acionados
        sl_triggered = (self.df_trades['motivo_saida'] == 'stop_loss').sum()

        # Alavancagem
        leverage_values = self.df_trades['leverage'].dropna()
        max_leverage = int(leverage_values.max()) if len(leverage_values) > 0 else 0
        avg_leverage = float(leverage_values.mean()) if len(leverage_values) > 0 else 0.0

        # Risco de liquidação (unrealized_pnl < 0 e liquidation_price breached)
        liquidation_risk = 0
        for idx, row in self.df_trades.iterrows():
            if (pd.notna(row['liquidation_price']) and
                pd.notna(row['mark_price']) and
                row['direcao'] == 'LONG' and row['liquidation_price'] > row['mark_price']):
                liquidation_risk += 1
            elif (pd.notna(row['liquidation_price']) and
                  pd.notna(row['mark_price']) and
                  row['direcao'] == 'SHORT' and row['liquidation_price'] < row['mark_price']):
                liquidation_risk += 1

        return {
            'circuit_breaker_activations': int(cb_activations),
            'stop_loss_triggered': int(sl_triggered),
            'max_leverage': int(max_leverage),
            'avg_leverage': float(avg_leverage),
            'liquidation_risk_count': int(liquidation_risk),
        }

    def analyze_performance_by_symbol(self) -> Dict[str, Any]:
        """
        Calcula performance por ativo (symbol).

        Returns:
            Dict com breakdown por ímbolo
        """
        if self.df_trades.empty:
            return {}

        result = {}
        for symbol in self.df_trades['symbol'].unique():
            trades_symbol = self.df_trades[self.df_trades['symbol'] == symbol]
            closed = trades_symbol[trades_symbol['pnl_usdt'].notna()]

            pnl = closed['pnl_usdt'].sum()
            count = len(trades_symbol)
            closed_count = len(closed)

            result[symbol] = {
                'total_pnl': float(pnl),
                'trade_count': int(count),
                'trades_fechadas': int(closed_count),
                'win_rate': float(
                    (len(closed[closed['pnl_usdt'] > 0]) / closed_count * 100)
                    if closed_count > 0 else 0.0
                ),
            }

        return result

    def detect_anomalies(self):
        """
        Detecta anomalias nos dados:
        - Outliers de PnL
        - Execuções bloqueadas incomuns
        - Sinais não-executados
        - Alavancagem anormal
        """
        self.anomalies = []

        # Anomalia 1: Outliers de PnL (> 3σ)
        if not self.df_trades.empty:
            closed = self.df_trades[self.df_trades['pnl_usdt'].notna()].copy()
            if len(closed) > 3:
                mean_pnl = closed['pnl_usdt'].mean()
                std_pnl = closed['pnl_usdt'].std()
                threshold = 3 * std_pnl

                for idx, row in closed.iterrows():
                    if abs(row['pnl_usdt'] - mean_pnl) > threshold:
                        self.anomalies.append({
                            'tipo': 'OUTLIER_PNL',
                            'severidade': 'MEDIUM',
                            'descricao': f"Trade {row['trade_id']} ({row['symbol']}) "
                                       f"com PnL outlier: ${row['pnl_usdt']:.2f}"
                        })

        # Anomalia 2: Execuções bloqueadas por risk
        if not self.df_executions.empty:
            blocked = self.df_executions[self.df_executions['executed'] == 0]
            for reason in ['exceeded_drawdown', 'max_daily_limit', 'risk_too_high']:
                count = (blocked['reason'] == reason).sum()
                if count > 0:
                    self.anomalies.append({
                        'tipo': 'EXECUTIONS_BLOCKED',
                        'severidade': 'HIGH',
                        'descricao': f"{count} execuções bloqueadas por '{reason}'"
                    })

        # Anomalia 3: Sinais não-executados
        if not self.df_signals.empty:
            non_executed = self.df_signals[
                self.df_signals['execution_mode'].isin(['PENDING', 'CANCELLED'])
            ]
            if len(non_executed) > 0:
                self.anomalies.append({
                    'tipo': 'SIGNALS_NOT_EXECUTED',
                    'severidade': 'MEDIUM',
                    'descricao': f"{len(non_executed)} sinais pendentes ou cancelados"
                })

        # Anomalia 4: Alavancagem muito alta
        if not self.df_trades.empty:
            high_leverage = self.df_trades[self.df_trades['leverage'] > 10]
            if len(high_leverage) > 0:
                self.anomalies.append({
                    'tipo': 'HIGH_LEVERAGE',
                    'severidade': 'CRITICAL',
                    'descricao': f"{len(high_leverage)} trades com alavancagem > 10x"
                })

    def generate_recommendations(self):
        """
        Gera recomendações baseadas em métricas e anomalias.
        """
        self.recommendations = []
        metrics = self.metrics

        # Recomendação 1: Taxa de acerto baixa
        if metrics.get('financial_summary', {}).get('win_rate_pct', 0) < 40:
            self.recommendations.append({
                'prioridade': 'HIGH',
                'topico': 'Taxa de Acerto',
                'descricao': 'Taxa de acerto < 40%. Investigar confiança de sinais e ajustar filtros de entrada.'
            })

        # Recomendação 2: Muitos bloqueios
        executions = metrics.get('execution_statistics', {})
        if executions.get('executions_blocked', 0) > 5:
            self.recommendations.append({
                'prioridade': 'MEDIUM',
                'topico': 'Frequência de Execuções',
                'descricao': f"{executions['executions_blocked']} execuções bloqueadas. "
                           'Revisar cooldown e limites diários.'
            })

        # Recomendação 3: Expectativa negativa
        if not metrics.get('financial_summary', {}).get('expectativa_positiva', False):
            self.recommendations.append({
                'prioridade': 'CRITICAL',
                'topico': 'Expectativa Matemática',
                'descricao': 'Expectativa negativa detectada. Pausar operações e revisar lógica do agente.'
            })

        # Recomendação 4: Circuit breaker ativado
        if metrics.get('risk_metrics', {}).get('circuit_breaker_activations', 0) > 0:
            self.recommendations.append({
                'prioridade': 'CRITICAL',
                'topico': 'Circuit Breaker',
                'descricao': 'Circuit breaker foi ativado. Revisar gestão de risco.'
            })

    def analyze(self) -> bool:
        """
        Executa análise completa.

        Returns:
            bool: True se sucesso
        """
        if not self.load_data():
            return False

        # Normalizar dados
        self._normalize_trades()
        self._normalize_executions()
        self._normalize_signals()
        self._normalize_snapshots()

        # Análises
        self.metrics['financial_summary'] = self.analyze_financial_summary()
        self.metrics['execution_statistics'] = self.analyze_execution_statistics()
        self.metrics['risk_metrics'] = self.analyze_risk_metrics()
        self.metrics['performance_by_symbol'] = self.analyze_performance_by_symbol()

        # Detecção de anomalias
        self.detect_anomalies()

        # Recomendações
        self.generate_recommendations()

        return True

    def print_console_report(self):
        """Imprime relatório formatado no console."""
        print("\n" + "="*80)
        print(" " * 20 + "AUDITORIA DE OPERAÇÕES - ÚLTIMAS 24 HORAS")
        print("="*80)
        print(f"Data/Hora: {datetime.utcnow().isoformat()}Z")
        print(f"Período: {self._ms_to_iso(self.hours_24_ago_ms)} até {self._ms_to_iso(self.now_ms)}")
        print("="*80)

        # Seção 1: Resumo Financeiro
        print("\n📊 RESUMO FINANCEIRO")
        print("-" * 80)
        fin = self.metrics.get('financial_summary', {})
        print(f"  Total PnL:              ${fin.get('total_pnl_usdt', 0):>10.2f} USDT "
              f"({fin.get('total_pnl_pct', 0):>6.2f}%)")
        print(f"  Total Trades:           {fin.get('trade_count', 0):>10} "
              f"(Abertas: {fin.get('trades_abertas', 0)}, Fechadas: {fin.get('trades_fechadas', 0)})")
        print(f"  Taxa de Acerto:         {fin.get('win_rate_pct', 0):>10.1f}%")
        print(f"  Maior Ganho:            ${fin.get('maior_ganho', 0):>10.2f} USDT")
        print(f"  Maior Perda:            ${fin.get('maior_perda', 0):>10.2f} USDT")
        print(f"  Ganho Médio:            ${fin.get('avg_win', 0):>10.2f} USDT")
        print(f"  Perda Média:            ${fin.get('avg_loss', 0):>10.2f} USDT")
        print(f"  R Múltiplo Médio:       {fin.get('r_multiple_medio', 0):>10.2f}")
        status = "✅ POSITIVA" if fin.get('expectativa_positiva', False) else "❌ NEGATIVA"
        print(f"  Expectativa:            {status}")

        # Seção 2: Estatísticas de Execução
        print("\n⚙️  ESTATÍSTICAS DE EXECUÇÃO")
        print("-" * 80)
        exec_stats = self.metrics.get('execution_statistics', {})
        print(f"  Total Execuções:        {exec_stats.get('total_executions', 0):>10}")
        print(f"  Sucesso:                {exec_stats.get('executions_success', 0):>10} "
              f"({exec_stats.get('success_rate_pct', 0):>6.1f}%)")
        print(f"  Bloqueadas:             {exec_stats.get('executions_blocked', 0):>10}")
        print(f"  Modo Paper:             {exec_stats.get('by_mode', {}).get('paper', 0):>10}")
        print(f"  Modo Live:              {exec_stats.get('by_mode', {}).get('live', 0):>10}")
        print(f"  Símbolos Únicos:        {exec_stats.get('symbols_count', 0):>10}")

        if exec_stats.get('blocked_reasons'):
            print("\n  Motivos de Bloqueio:")
            for reason, count in exec_stats['blocked_reasons'].items():
                print(f"    - {reason}: {count}")

        # Seção 3: Análise de Risco
        print("\n⚠️ ANÁLISE DE RISCO")
        print("-" * 80)
        risk = self.metrics.get('risk_metrics', {})
        print(f"  Ativações Circuit Breaker: {risk.get('circuit_breaker_activations', 0):>6}")
        print(f"  Stop Loss Disparados:      {risk.get('stop_loss_triggered', 0):>6}")
        print(f"  Alavancagem Máxima:        {risk.get('max_leverage', 0):>6}x")
        print(f"  Alavancagem Média:         {risk.get('avg_leverage', 0):>6.1f}x")
        print(f"  Posições em Risco Liquidação: {risk.get('liquidation_risk_count', 0):>6}")

        # Seção 4: Performance por Ativo
        print("\n📈 PERFORMANCE POR ATIVO")
        print("-" * 80)
        perf_by_symbol = self.metrics.get('performance_by_symbol', {})
        if perf_by_symbol:
            df_perf = pd.DataFrame(perf_by_symbol).T
            df_perf = df_perf.sort_values('total_pnl', ascending=False)
            print(df_perf.to_string())
        else:
            print("  (Nenhuma trade encontrada)")

        # Seção 5: Anomalias
        if self.anomalies:
            print("\n🚨 ANOMALIAS DETECTADAS")
            print("-" * 80)
            for i, anom in enumerate(self.anomalies, 1):
                print(f"  {i}. [{anom['severidade']}] {anom['tipo']}")
                print(f"     {anom['descricao']}")
        else:
            print("\n✅ Nenhuma anomalia detectada")

        # Seção 6: Recomendações
        if self.recommendations:
            print("\n💡 RECOMENDAÇÕES PÓS-AUDITORIA")
            print("-" * 80)
            for i, rec in enumerate(self.recommendations, 1):
                print(f"  {i}. [{rec['prioridade']}] {rec['topico']}")
                print(f"     {rec['descricao']}")

        print("\n" + "="*80)

    def export_to_csv(self, output_dir: str = "reports/audit_24h"):
        """
        Exporta dados para CSV.

        Args:
            output_dir: Diretório de saída
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Arquivo 1: Trades
        if not self.df_trades.empty:
            trades_export = self.df_trades.copy()
            trades_export.to_csv(
                output_path / "trades_24h.csv",
                index=False,
                encoding='utf-8'
            )
            print(f"✅ Exportado: {output_path / 'trades_24h.csv'}")

        # Arquivo 2: Execuções
        if not self.df_executions.empty:
            executions_export = self.df_executions.copy()
            executions_export.to_csv(
                output_path / "executions_24h.csv",
                index=False,
                encoding='utf-8'
            )
            print(f"✅ Exportado: {output_path / 'executions_24h.csv'}")

        # Arquivo 3: Sinais
        if not self.df_signals.empty:
            signals_export = self.df_signals.copy()
            signals_export.to_csv(
                output_path / "signals_24h.csv",
                index=False,
                encoding='utf-8'
            )
            print(f"✅ Exportado: {output_path / 'signals_24h.csv'}")

    def export_to_json(self, output_path: str = "reports/audit_24h_report.json"):
        """
        Exporta relatório estruturado para JSON.

        Args:
            output_path: Caminho do arquivo de saída
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        report = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'periodo_inicio': self._ms_to_iso(self.hours_24_ago_ms),
            'periodo_fim': self._ms_to_iso(self.now_ms),
            'metricas': self.metrics,
            'anomalias': self.anomalies,
            'recomendacoes': self.recommendations,
            'dados_brutos': {
                'total_trades': len(self.df_trades),
                'total_executions': len(self.df_executions),
                'total_signals': len(self.df_signals),
                'total_snapshots': len(self.df_snapshots),
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ Exportado: {output_path}")

    def run(self):
        """Executa auditoria completa e gera todos os outputs."""
        print("🔍 Iniciando auditoria de operações (últimas 24 horas)...")

        if not self.analyze():
            print("❌ Falha na auditoria")
            return False

        # Outputs
        self.print_console_report()
        self.export_to_csv()
        self.export_to_json()

        print("\n✅ Auditoria concluída com sucesso!")
        return True


def main():
    """Função principal."""
    audit = AuditOperations24h()
    success = audit.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
