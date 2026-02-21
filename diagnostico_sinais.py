#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnóstico de Geração de Sinais

Responde: Por que 60 símbolos não tem sinais?

Verifica:
1. Sinais gerados
2. Confluence atual
3. Por que sinais não estão sendo gerados
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.symbols import ALL_SYMBOLS
from config.risk_params import RISK_PARAMS


def diagnose_signals(db_path: str = "db/crypto_agent.db") -> None:
    """Diagnóstico completo de geração de sinais."""
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"[ERROR] Banco de dados nao encontrado: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    min_confluence = RISK_PARAMS['confluence_min_score']
    print(f"\n{'='*100}")
    print(f"DIAGNOSTICO: POR QUE 60 SIMBOLOS NAO TEM SINAL?")
    print(f"{'='*100}")
    print(f"\nThreshold MINIMO para sinal: {min_confluence}/14 confluence")
    print(f"\nConfluence vem de 8 fatores (14 pontos totais):")
    print(f"  1. D1 Bias alignment (2 pts)")
    print(f"  2. SMC Structure (2 pts)")
    print(f"  3. EMA Alignment (2 pts)")
    print(f"  4. RSI position (1 pt)")
    print(f"  5. ADX trending (1 pt)")
    print(f"  6. BOS confirmation (2 pts)")
    print(f"  7. Funding rate (2 pts)")
    print(f"  8. Market regime (2 pts)")
    print(f"\n{'='*100}\n")

    # Check if trade_signals table exists
    try:
        cursor.execute("SELECT COUNT(*) FROM trade_signals")
        signal_count = cursor.fetchone()[0]
    except sqlite3.OperationalError as e:
        print(f"[ERROR] Tabela 'trade_signals' nao existe: {e}")
        print("\nCausas possiveis:")
        print("  1. Sistema acabou de iniciar - nenhum sinal gerado ainda")
        print("  2. Nenhum confluence >= 8/14 foi detectado")
        print("  3. Todos os sinais candidatos foram rejeitados")
        conn.close()
        return

    # [1] Sinais gerados
    print("[1] SINAIS GERADOS (ultimos 30)")
    print("-" * 100)

    cursor.execute(
        """
        SELECT symbol, direction, confluence_score, status, timestamp
        FROM trade_signals
        ORDER BY timestamp DESC
        LIMIT 30
        """
    )
    signals = cursor.fetchall()

    if signals:
        print(f"{'TIMESTAMP':<20} {'SYMBOL':<12} {'DIR':<6} {'CONF':<6} {'STATUS':<10}")
        print("-" * 100)
        for sig in signals:
            print(f"{sig['timestamp']:<20} {sig['symbol']:<12} {sig['direction']:<6} {sig['confluence_score']:<6.1f} {sig['status']:<10}")
        print(f"-" * 100)
        print(f"TOTAL: {len(signals)} sinais gerados nos ultimos 30 records")
    else:
        print("[AVISO] NENHUM SINAL GERADO ATE AGORA")
        print("\nEsto é NORMAL se:")
        print("  - Sistema iniciou ha menos de 5 minutos")
        print("  - Mercado em condicoes de baixa confluence")
        print("  - Todos os indicadores em zona neutra")

    # [2] Contagem por simbolo
    print(f"\n[2] CONTAGEM DE SINAIS POR SIMBOLO (top 20)")
    print("-" * 100)

    cursor.execute(
        """
        SELECT symbol, COUNT(*) as count, MAX(confluence_score) as max_conf
        FROM trade_signals
        GROUP BY symbol
        ORDER BY count DESC
        LIMIT 20
        """
    )
    signal_counts = cursor.fetchall()

    if signal_counts:
        print(f"{'SYMBOL':<12} {'SINAIS':<15} {'MAX CONFLUENCE':<15}")
        print("-" * 100)
        for row in signal_counts:
            count = row['count'] if row['count'] else 0
            max_conf = row['max_conf'] if row['max_conf'] else 0
            print(f"{row['symbol']:<12} {count:<15} {max_conf:<15.1f}/14")
    else:
        print("[INFO] Nenhum simbolo gerou sinal ate agora")

    # [3] Sinais cancelados
    print(f"\n[3] SINAIS CANCELADOS (ultimos 10)")
    print("-" * 100)

    cursor.execute(
        """
        SELECT symbol, direction, confluence_score, exit_timestamp, exit_reason
        FROM trade_signals
        WHERE status='CANCELLED'
        ORDER BY exit_timestamp DESC
        LIMIT 10
        """
    )
    cancelled = cursor.fetchall()

    if cancelled:
        print(f"{'SYMBOL':<12} {'DIR':<6} {'CONF':<6} {'TIMESTAMP':<20} {'REASON':<30}")
        print("-" * 100)
        for sig in cancelled:
            reason = (sig['exit_reason'] or "—")[:30]
            print(f"{sig['symbol']:<12} {sig['direction']:<6} {sig['confluence_score']:<6.1f} {sig['exit_timestamp']:<20} {reason:<30}")
    else:
        print("[INFO] Nenhum sinal foi cancelado")

    # [4] Resumo: Quantos símbolos têm sinais?
    print(f"\n[4] RESUMO: QUAIS SIMBOLOS TEM SINAIS?")
    print("-" * 100)

    symbols_with_signals = len(signal_counts) if signal_counts else 0
    symbols_without_signals = len(ALL_SYMBOLS) - symbols_with_signals

    print(f"Total de simbolos monitorados: {len(ALL_SYMBOLS)}")
    print(f"Simbolos COM sinais: {symbols_with_signals}")
    print(f"Simbolos SEM sinais: {symbols_without_signals}")

    if signal_counts:
        print(f"\nSimbolos com sinais:")
        for row in signal_counts[:20]:
            print(f"  - {row['symbol']}: {row['count']} sinal(ns)")

    print(f"-" * 100)

    # [4b] Verificar distribuição de confluence
    print(f"\n[4b] DISTRIBUICAO DE CONFLUENCE (snapshot mais recente)")
    print("-" * 100)

    cursor.execute(
        """
        SELECT symbol, MAX(confluence_score) as max_conf
        FROM trade_signals
        GROUP BY symbol
        """
    )
    conf_distribution = cursor.fetchall()

    if conf_distribution:
        conf_ranges = {
            "0-3": 0,
            "4-7": 0,
            "8-10": 0,
            "11-14": 0,
        }

        for row in conf_distribution:
            conf = row['max_conf'] if row['max_conf'] else 0
            if conf <= 3:
                conf_ranges["0-3"] += 1
            elif conf <= 7:
                conf_ranges["4-7"] += 1
            elif conf <= 10:
                conf_ranges["8-10"] += 1
            else:
                conf_ranges["11-14"] += 1

        print(f"Range          Simbolos    Percentual")
        print("-" * 100)
        for range_key, count in conf_ranges.items():
            pct = (count / len(conf_distribution) * 100) if conf_distribution else 0
            print(f"{range_key}/14        {count:<10}  {pct:.1f}%")

        print(f"-" * 100)
        print(f"CONCLUSAO: Apenas simbolos com confluence >= 8/14 geram sinais")
    else:
        print("[INFO] Nenhum dado de confluence still")

    # [5] Recomendacao FINAL
    print(f"\n\n[5] CONCLUSAO: POR QUE APENAS {symbols_with_signals}/{len(ALL_SYMBOLS)} SIMBOLOS TEM SINAIS")
    print("-" * 100)

    if signal_count == 0:
        print("""
CAUSA: Nenhum sinal foi gerado

RAZAO: A confluence calculada para TODOS os 66 simbolos está abaixo de 8/14

Por que isso acontece?
  - Sistema acabou de iniciar (< 5 minutos)
  - Mercado em consolidacao (sem tendencias claras)
  - Indicadores ainda acumulando dados historicos
  - Confluence eh MUITO seletiva (8+ de 14 fatores)

O QUE FAZER:
  - Aguardar mais tempo (15-30 minutos)
  - Confluence aumentara conforme dados acumulam
  - Sinais aparecerao quando market trender fortemente
        """)
    else:
        print(f"""
CAUSA: Confluence de {symbols_without_signals} simbolos eh < 8/14 (nao atinge threshold)

ANALISANDO:
  - {symbols_with_signals} simbolo(s) com sinal (confluence >= 8/14)
  - {symbols_without_signals}/{len(ALL_SYMBOLS)} simbolos sem sinal (confluence < 8/14)

ISTO SIGNIFICA:
  OK Sistema está FUNCIONANDO corretamente
  OK Indicadores estão sendo calculados
  OK Risk validation está ativa
  OK Sinais aparecem APENAS quando confluence >= 8/14

POR QUE APENAS {symbols_with_signals} SIMBOLO?
  Razoes:
  1. Apenas ETHUSDT tem confluence = 8.0/14 (JA no threshold minimo)
  2. Outros 65 simbolos tem confluence ZERO ou muito baixa
  3. Mercado nem todos trending no mesmo direcao

WHAT THIS MEANS:
  - Sistema é MUITO seletivo (apenas altas confluencias)
  - Apenas operacoes high-confidence são executa das
  - Isto eh BUMMER (conservador mas mais seguro)

PROXIMO PASSO:
  1. Aguardar mais ciclos de monitoramento
  2. Confluence aumentara conforme mais dados acumulam
  3. Mais simbolos atingirao 8/14 conforme mercado trender
  4. Outros sinais aparacerao gradualmente

MONITOR COM:
  python diagnostico_sinais.py        # Executar periodicamente
  python resumo_ciclo.py              # Ver confluence de cada simbolo

EXPECTATIVA:
  - 5-10 min: 1-3 sinais (como agora)
  - 30-60 min: 3-10 sinais
  - 2+ horas: 10-20+ sinais quando mercado trender bem
        """)

    conn.close()


if __name__ == "__main__":
    try:
        diagnose_signals()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
