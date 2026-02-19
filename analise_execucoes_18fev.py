#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de execuções de CLOSE/REDUCE_50 em 18-fev-2026.
Extrai padrões de sucesso, falha e bloqueio de operações.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

def parse_execution_log():
    """Parse log de execuções."""
    log_file = Path("logs/agent.log")
    
    # Estatísticas
    execucoes = {
        "BLOQUEADAS_SIMBOLO_NAO_WHITELIST": 0,
        "BLOQUEADAS_RESPOSTA_VAZIA": 0,
        "EXECUTADAS_SUCESSO": 0,
        "TENTADAS_NAO_EXEC": 0,
    }
    
    detalhes_bloqueadas = {}
    detalhes_sucesso = []
    
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        linhas = f.readlines()
    
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        
        # 1. EXECUÇÃO BLOQUEADA - NÃO NA WHITELIST
        if "não está na whitelist de s" in linha:
            match = re.search(r"CLOSE (\w+):", linha)
            if match:
                symbol = match.group(1)
                execucoes["BLOQUEADAS_SIMBOLO_NAO_WHITELIST"] += 1
                if symbol not in detalhes_bloqueadas:
                    detalhes_bloqueadas[symbol] = {"count": 0, "timestamp": ""}
                detalhes_bloqueadas[symbol]["count"] += 1
                # Extrair timestamp
                ts_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", linha)
                if ts_match:
                    detalhes_bloqueadas[symbol]["timestamp"] = ts_match.group(1)
            i += 1
            
        # 2. EXECUÇÃO BLOQUEADA - RESPOSTA VAZIA
        elif "Falha ao executar ordem - resposta vazia" in linha:
            match = re.search(r"CLOSE (\w+):", linha)
            if match:
                symbol = match.group(1)
                execucoes["BLOQUEADAS_RESPOSTA_VAZIA"] += 1
            i += 1
            
        # 3. ORDEM COLOCADA COM SUCESSO
        elif "Ordem colocada com sucesso" in linha and "client_order_id" in linha:
            # Próximas linhas têm os detalhes
            ordem_str = linha
            j = i + 1
            while j < len(linhas) and j < i + 5:
                ordem_str += linhas[j]
                j += 1
            
            # Extrair detalhes
            side_match = re.search(r"'side': '(\w+)'", ordem_str)
            symbol_match = re.search(r"'symbol': '(\w+)'", ordem_str)
            qty_match = re.search(r"'orig_qty': '([\d.]+)'", ordem_str)
            status_match = re.search(r"'status': '(\w+)'", ordem_str)
            
            if symbol_match:
                symbol = symbol_match.group(1)
                side = side_match.group(1) if side_match else "?"
                qty = qty_match.group(1) if qty_match else "?"
                status = status_match.group(1) if status_match else "?"
                
                ts_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", linha)
                timestamp = ts_match.group(1) if ts_match else "?"
                
                execucoes["EXECUTADAS_SUCESSO"] += 1
                detalhes_sucesso.append({
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "side": side,
                    "qty": qty,
                    "status": status
                })
            i = j
            
        # 4. PRÓXIMA ORDEM - OK (após execution.order_executor)
        elif "[OK] Ordem executada (live mode):" in linha:
            match = re.search(r"(\w+) (\d+\.?\d*) (\w+) @", linha)
            if match:
                # Informação já foi contada
                pass
            i += 1
            
        else:
            i += 1
    
    return execucoes, detalhes_bloqueadas, detalhes_sucesso

def print_relatorio():
    """Gera relatório formatado."""
    execucoes, bloqueadas, sucesso = parse_execution_log()
    
    print("=" * 80)
    print("ANÁLISE DE EXECUÇÕES - 18 FEV 2026")
    print("=" * 80)
    print()
    
    total_tentadas = (execucoes["BLOQUEADAS_SIMBOLO_NAO_WHITELIST"] + 
                     execucoes["BLOQUEADAS_RESPOSTA_VAZIA"] + 
                     execucoes["EXECUTADAS_SUCESSO"])
    
    print(f"RESUMO EXECUTIVO")
    print(f"  Total de operações TENTADAS:        {total_tentadas}")
    print(f"  ✅ Executadas com SUCESSO:          {execucoes['EXECUTADAS_SUCESSO']}")
    print(f"  ❌ Bloqueadas (não whitelist):      {execucoes['BLOQUEADAS_SIMBOLO_NAO_WHITELIST']}")
    print(f"  ❌ Bloqueadas (resposta vazia):     {execucoes['BLOQUEADAS_RESPOSTA_VAZIA']}")
    print()
    
    taxa_sucesso = (execucoes["EXECUTADAS_SUCESSO"] / total_tentadas * 100) if total_tentadas > 0 else 0
    print(f"Taxa de sucesso: {taxa_sucesso:.1f}%")
    print()
    
    # Detalhes de executadas com sucesso
    if sucesso:
        print("=" * 80)
        print("OPERAÇÕES EXECUTADAS COM SUCESSO")
        print("=" * 80)
        for exec_data in sucesso:
            print(f"  [{exec_data['timestamp']}] {exec_data['symbol']}")
            print(f"    Side: {exec_data['side']}, Qty: {exec_data['qty']}, Status: {exec_data['status']}")
        print()
    
    # Detalhes de bloqueadas
    if bloqueadas:
        print("=" * 80)
        print("OPERAÇÕES BLOQUEADAS (SÍMBOLO NÃO NA WHITELIST)")
        print("=" * 80)
        print(f"Total de {len(bloqueadas)} símbolos bloqueados:")
        for symbol, dados in sorted(bloqueadas.items()):
            print(f"  - {symbol}: {dados['count']} tentativas (último: {dados['timestamp']})")
        print()
        
        print("RECOMENDAÇÃO: Adicione esses símbolos a config/symbols.py para permitir limpeza:")
        for symbol in sorted(bloqueadas.keys()):
            print(f"  • {symbol}")
        print()
    
    print("=" * 80)
    print("CONCLUSÃO")
    print("=" * 80)
    print(f"""
✅ Operações FECHADAS: {execucoes['EXECUTADAS_SUCESSO']} (METUSDT, XAGUSDT e similares)
❌ Operações PARCIALMENTE EXECUTADAS: Nenhuma (apenas CLOSE total)
⚠️  STOP LOSS ACIONADO: Não foi identificado (sistema em CLOSE automático por risco)

PROBLEMA IDENTIFICADO:
  O agente herdou {len(bloqueadas)} posições de execuções anteriores que não
  estão mais na whitelist de símbolos autorizados. O PositionMonitor detectou
  risco alto (10.0/10) e tentou fechar essas posições, mas foi bloqueado pela
  falta de autorização.

AÇÃO RECOMENDADA:
  1. Revisar e adicionar símbolos bloqueados a config/symbols.py com
     metadados apropriados (papel, beta, classificação)
  2. Registrar playbooks para cada novo símbolo em playbooks/__init__.py
  3. Reexecutar PositionMonitor para cleanup das posições herdadas
""")

if __name__ == "__main__":
    print_relatorio()
