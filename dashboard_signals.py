#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard de Status - Sinais e Treinamento
Mostra status de treinamento e sinais gerados por símbolo
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DB_PATH
from config.symbols import ALL_SYMBOLS
from data.database import DatabaseManager


def format_timestamp(ts_ms):
    """Convert milliseconds timestamp to readable format"""
    if not ts_ms:
        return "N/A"
    return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def get_signal_status():
    """Obter status de sinais por símbolo"""
    try:
        db = DatabaseManager(DB_PATH)
    except Exception as e:
        print(f"[ERRO] Falha ao conectar ao banco de dados: {e}")
        return

    print("\n" + "=" * 100)
    print("STATUS DE SINAIS E TREINAMENTO - CRYPTO FUTURES AGENT")
    print("=" * 100)
    print()

    # Criar tabela de status
    data_rows = []

    for symbol in ALL_SYMBOLS:
        try:
            # Buscar todos os sinais do símbolo
            all_signals = db.get_signals_for_training(symbol)
            
            if not all_signals:
                data_rows.append({
                    'Símbolo': symbol,
                    'Sinais Totais': 0,
                    'Sinais Ativos': 0,
                    'Vitórias': 0,
                    'Derrotas': 0,
                    'Win Rate %': '0%',
                    'Último Sinal': 'Nenhum',
                    'Status Treino': 'NÃO TREINADO'
                })
                continue

            # Contar por status
            active_count = sum(1 for s in all_signals if s.get('status') == 'ACTIVE')
            won_count = sum(1 for s in all_signals if s.get('outcome_label') == 'win')
            lost_count = sum(1 for s in all_signals if s.get('outcome_label') == 'loss')
            total_count = len(all_signals)
            
            win_rate = (won_count / total_count * 100) if total_count > 0 else 0

            # Último sinal
            last_signal = None
            last_signal_time = None
            if all_signals:
                last_signal = all_signals[-1]
                last_signal_time = last_signal.get('created_at', 0)

            # Status de treinamento
            has_outcomes = won_count + lost_count > 0
            if not has_outcomes:
                train_status = "⏳ Aguardando dados"
            elif win_rate >= 55:
                train_status = f"✅ TREINADO ({win_rate:.0f}%)"
            elif win_rate >= 45:
                train_status = f"⚠️  MARGINAL ({win_rate:.0f}%)"
            else:
                train_status = f"❌ FRACO ({win_rate:.0f}%)"

            # Sinal claro?
            signal_direction = last_signal.get('direction', 'NONE') if last_signal else 'NENHUM'
            confluence = last_signal.get('confluence_score', 0) if last_signal else 0
            
            if confluence >= 10:
                signal_quality = f"🟢 FORTE ({signal_direction})"
            elif confluence >= 7:
                signal_quality = f"🟡 MÉDIO ({signal_direction})"
            else:
                signal_quality = f"🔴 FRACO ({signal_direction})"

            data_rows.append({
                'Símbolo': symbol,
                'Sinais Totais': total_count,
                'Sinais Ativos': active_count,
                'Vitórias': won_count,
                'Derrotas': lost_count,
                'Win Rate %': f"{win_rate:.1f}%",
                'Último Sinal': format_timestamp(last_signal_time),
                'Status Treino': train_status
            })

        except Exception as e:
            print(f"[AVISO] Erro ao processar {symbol}: {e}")
            continue

    # Exibir tabela formatada
    if data_rows:
        df = pd.DataFrame(data_rows)
        
        # Ordenar por sinais totais (descendente)
        df = df.sort_values('Sinais Totais', ascending=False)
        
        print(df.to_string(index=False))
        print()
    else:
        print("[INFO] Nenhum dado disponível")
        print()

    # Resumo geral
    print("=" * 100)
    print("RESUMO GERAL")
    print("=" * 100)
    
    total_signals = sum(d['Sinais Totais'] for d in data_rows)
    total_active = sum(d['Sinais Ativos'] for d in data_rows)
    total_wins = sum(d['Vitórias'] for d in data_rows)
    total_losses = sum(d['Derrotas'] for d in data_rows)
    
    if total_signals > 0:
        overall_win_rate = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0
        print(f"Total de Sinais Gerados: {total_signals}")
        print(f"Sinais Ativos: {total_active}")
        print(f"Vitórias: {total_wins}")
        print(f"Derrotas: {total_losses}")
        print(f"Win Rate Geral: {overall_win_rate:.1f}%")
    else:
        print("Nenhum sinal gerado ainda")

    # Símbolos prontos para trading
    print()
    print("=" * 100)
    print("SÍMBOLOS COM STATUS POSITIVO")
    print("=" * 100)
    ready_symbols = [d for d in data_rows if '✅' in str(d['Status Treino'])]
    if ready_symbols:
        for sym in ready_symbols:
            print(f"  ✅ {sym['Símbolo']:12} - {sym['Status Treino']:20} ({sym['Sinais Totais']} sinais)")
    else:
        print("  Nenhum símbolo com treinamento positivo ainda")

    print()


if __name__ == "__main__":
    get_signal_status()
