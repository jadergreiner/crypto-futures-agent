#!/usr/bin/env python
"""
Análise: O que acontece quando escolhe opção 2 no iniciar.bat?
Verifica se realmente coloca TP/SL automaticamente na Binance.
"""

import sys

print("=" * 80)
print("ANÁLISE: OPÇÃO 2 - MODO LIVE INTEGRADO")
print("=" * 80)

print("""
COMANDO EXECUTADO:
```
python main.py --mode live --integrated --integrated-interval 300
```

DECODIFICAÇÃO:
---------
--mode live                    = Modo de operação em capital REAL
--integrated                   = Ativa monitor de posições em paralelo (segundo threads)
--integrated-interval 300      = Monitor verifica posições a cada 300 segundos (5 minutos)

""")

print("\n" + "=" * 80)
print("O QUE REALMENTE ACONTECE:")
print("=" * 80)

print("""
1️⃣ INIZIALIZA SCHEDULER PRINCIPAL
   - Inicia scheduler da aplicação
   - Monitora sinais técnicos em tempo real

2️⃣ ATIVA POSITION MONITOR EM 2º THREAD (em paralelo)
   - Classe: PositionMonitor (monitoring/position_monitor.py)
   - Intervalo: 300s (5 minutos)

   Position Monitor FAZ:
   ✓ Coleta dados de posições abertas na Binance
   ✓ Calcula indicadores técnicos
   ✓ Calcula SL/TP baseado em ATR e SMC
   ✓ Gera DECISÃO (HOLD, CLOSE, REDUCE_50)
   ✓ EXECUTA decisão via OrderExecutor (se não HOLD)

   ⚠ O que NÃO faz:
   ✗ NÃO coloca ordens de TP/SL automaticamente
   ✗ TP/SL são CALCULADOS mas aparecem como "_suggested"
   ✗ TP/SL usados APENAS para análise interna
   ✗ Ordens colocadas são APENAS: CLOSE ou REDUCE_50

3️⃣ EXECUÇÃO DE ORDENS
   - OrderExecutor (Profit Guardian Mode):
     * Filtra por safety guards (7 camadas)
     * Só permite: CLOSE, REDUCE_50
     * NÃO abre posições novas
     * NÃO coloca ordens de TP/SL

""")

print("\n" + "=" * 80)
print("EVIDÊNCIA NO CÓDIGO:")
print("=" * 80)

print("""
main.py (linhas 503-519):
```python
if enable_integrated_monitor:
    from monitoring.position_monitor import PositionMonitor

    monitor = PositionMonitor(client, db, mode=mode)
    monitor_thread = threading.Thread(
        target=monitor.run_continuous,
        kwargs={
            'symbol': None,
            'interval_seconds': integrated_interval_seconds,
        },
        daemon=True,
        name='position-monitor-thread',
    )
    monitor_thread.start()
    logger.info(
        f"INTEGRATED MODE ENABLED: monitor de posições ativo em paralelo "
        f"(intervalo={integrated_interval_seconds}s)"
    )
```

PositionMonitor (linhas 2802-2810):
```python
if decision['agent_action'] != 'HOLD':
    execution_result = self.order_executor.execute_decision(
        position=position,
        decision=decision,
        snapshot_id=snapshot_id
    )
```

Allowed Actions (config/execution_config.py):
```python
"allowed_actions": ["CLOSE", "REDUCE_50"],
```

⚠️ NÃO há nenhuma chamada para colocar ordens de TP/SL!
""")

print("\n" + "=" * 80)
print("O QUE ACONTECE COM TP/SL:")
print("=" * 80)

print("""
SL/TP são CALCULADOS (position_monitor.py linhas 850-912):
✓ Stop Loss = max(ATR-based, SMC-based)
✓ Take Profit = min/max(ATR-based, SMC-based, liquidation price)

SL/TP são ARMAZENADOS em:
✓ decision['stop_loss_suggested'] = <preço calculado>
✓ decision['take_profit_suggested'] = <preço calculado>
✓ decision['stop_loss_source'] = 'ATR' ou 'SMC'
✓ decision['take_profit_source'] = 'ATR' ou 'SMC'

MAS SÃO APENAS SUGESTÕES:
✗ NÃO são automaticamente colocados na Binance
✗ Aparecem no LOG para você VER e DECIDIR
✗ Sistema gerencia a POSIÇÃO, não as ORDENS de proteção

EXEMPLO DE LOG:
```
[DECISÃO] BNBUSDT LONG | Ação: HOLD | Confiança: 85%
  Stop Loss sugerido: 627.50 (ATR)
  Take Profit sugerido: 680.00 (SMC)
```

→ VOCÊ LÊ ISSO E COLOCA MANUALMENTE NA BINANCE UI SE QUISER
""")

print("\n" + "=" * 80)
print("RESUMO FINAL:")
print("=" * 80)

print("""
┌─────────────────────────────────────────────────────┐
│ OPÇÃO 2 - MODO LIVE INTEGRADO                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│ O QUE FAZ:                                          │
│ ✓ Gerencia posições abertas na Binance              │
│ ✓ Coloca ordens de CLOSE/REDUCE_50                 │
│ ✓ Calcula SL/TP sugeridos                          │
│ ✓ Monitora riscos e alertas                        │
│                                                     │
│ O QUE NÃO FAZ:                                      │
│ ✗ NÃO coloca ordens de TP/SL automaticamente        │
│ ✗ NÃO abre posições novas                          │
│ ✗ NÃO coloca ordens de entrada                     │
│                                                     │
│ AÇÃO NECESSÁRIA:                                    │
│ → Você precisa colocar TP/SL MANUALMENTE na        │
│   Binance UI para cada posição                     │
│                                                     │
└─────────────────────────────────────────────────────┘

                        ⚠⚠⚠ IMPORTANTE ⚠⚠⚠

         NÃO há automação de TP/SL na iniciar.bat

    O sistema funciona como "Profit Guardian"
    - Gerencia posições já abertas
    - Sugere TP/SL mas não os coloca automaticamente
    - Você controla a abertura/fechamento manualmente

""")

print("=" * 80)

# Verificação dos 10 pares
print("\nVERIFICAÇÃO DOS 10 PARES ADICIONADOS:")
print("-" * 80)

from config.symbols import SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS

pares = ['ZKUSDT', '1000WHYUSDT', 'XIAUSDT', 'GTCUSDT', 'CELOUSDT',
         'HYPERUSDT', 'MTLUSDT', 'POLYXUSDT', '1000BONKUSDT', 'DASHUSDT']

print(f"\n✓ {len(pares)} pares para gerenciamento:")
for p in pares:
    status = "✓" if p in AUTHORIZED_SYMBOLS else "✗"
    print(f"  [{status}] {p}")

print("""
TODOS ESTÃO CONFIGURADOS para serem gerenciados quando escolher OPÇÃO 2.
MAS AINDA SERÁ NECESSÁRIO COLOCAR TP/SL MANUALMENTE NA BINANCE.
""")

print("=" * 80)
