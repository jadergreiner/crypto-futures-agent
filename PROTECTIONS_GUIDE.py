#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guia de Proteções Implementadas
"""

def print_guide():
    guide = """
╔══════════════════════════════════════════════════════════════════════════════════╗
║                     🛡️  GUIA DE PROTEÇÕES IMPLEMENTADAS                         ║
╚══════════════════════════════════════════════════════════════════════════════════╝

PROTEÇÕES AUTOMÁTICAS IMPLEMENTADAS:
════════════════════════════════════════════════════════════════════════════════════

1️⃣  STOP LOSS (-5% do entry)
    ├─ Objetivo: Limitar perdas máximas
    ├─ Acionamento: Quando preço atinge 5% abaixo do entry
    ├─ Ação: FECHA POSIÇÃO AUTOMÁTICAMENTE
    └─ Exemplo: Entry $0.004609 → SL $0.004378

2️⃣  TAKE PROFIT (+10% do entry)
    ├─ Objetivo: Capturar ganhos alvo
    ├─ Acionamento: Quando preço atinge 10% acima do entry
    ├─ Ação: FECHA POSIÇÃO AUTOMÁTICAMENTE
    └─ Exemplo: Entry $0.004609 → TP $0.005070

3️⃣  LIQUIDAÇÃO PREVENTIVA (<1% para liquidar)
    ├─ Objetivo: Evitar liquidação forçada
    ├─ Acionamento: Quando distância até liquidação < 1%
    ├─ Ação: FECHA POSIÇÃO URGENTEMENTE
    ├─ Cálculo: Entry × (1 - 1/Leverage) para LONG
    └─ Margem de Segurança: ~10% em ANKRUSDT 10x

4️⃣  TIMEOUT (máx 2 horas)
    ├─ Objetivo: Não deixar posições abertas indefinidamente
    ├─ Acionamento: Quando posição fica aberta > 2 horas
    ├─ Ação: FECHA POSIÇÃO AO PREÇO ATUAL
    └─ Risco: Pode fechar com loss se posição negativa

5️⃣  PnL EM TEMPO REAL
    ├─ Objetivo: Rastrear performance ao vivo
    ├─ Atualização: A cada scan do monitor_positions
    ├─ Armazenamento: Registrado em unrealized_pnl_at_snapshot
    └─ Uso: Para análise histórica e backtest


COMO USAR:
════════════════════════════════════════════════════════════════════════════════════

▶️  EXECUTAR UMA ORDEM COM POSIÇÃO INICIAL:
    $ python scripts/execute_1dollar_trade.py --symbol ANKRUSDT --direction LONG

    Saída esperada:
    ✓ Preço obtido de forma segura (sem fallbacks)
    ✓ Ordem executada no Binance LIVE
    ✓ Trade registrado em DB com stop_loss e take_profit
    ✓ Binance Order ID capturado e salvo

▶️  MONITORAR POSIÇÕES ABERTAS (UMA VEZ):
    $ python scripts/monitor_positions.py

    Saída esperada:
    ✓ Verifica todas as posições com timestamp_saida IS NULL
    ✓ Aplica todas as 5 proteções
    ✓ Executa stop loss / take profit se acionados
    ✓ Atualiza PnL em tempo real

▶️  MONITORAR CONTINUAMENTE (A CADA MINUTO):
    $ python scripts/schedule_monitor.py

    Opções:
    --interval 60  (padrão: 60 segundos / 1 minuto)
    --interval 30  (a cada 30 segundos)
    --once        (executar apenas uma vez)

    Para rodar em background (Windows PowerShell):
    $ python scripts/schedule_monitor.py
    (mantenha o terminal aberto)

    Para rodar em background (Linux/Mac):
    $ nohup python scripts/schedule_monitor.py > scheduler.log 2>&1 &

▶️  VER DASHBOARD DE PROTEÇÕES:
    $ python scripts/dashboard_protections.py

    Saída esperada:
    ✓ Todas as posições abertas listadas
    ✓ Status de cada proteção
    ✓ PnL atual
    ✓ Distância até liquidação


FLUXO DE OPERAÇÃO RECOMENDADO:
════════════════════════════════════════════════════════════════════════════════════

1️⃣  Terminal 1 - INICIAR SCHEDULER (monitoring contínuo):
    $ python scripts/schedule_monitor.py --interval 60
    (Mantém vigilando e executando SL/TP/Timeout automaticamente)

2️⃣  Terminal 2 - EXECUTAR PRIMEIRA POSIÇÃO:
    $ python scripts/execute_1dollar_trade.py --symbol ANKRUSDT --direction LONG

    Saída:
    ✓ Orderexecutada no Binance (Order No.XXXXX)
    ✓ Registrada em DB (Trade ID 1)
    ✓ Proteções prontas

3️⃣  Terminal 3 - VISUALIZAR STATUS (quando necessário):
    $ python scripts/dashboard_protections.py

    (Repita a cada 5-15 minutos para acompanhar)

4️⃣  AGUARDAR - O scheduler fará o resto:
    • Monitor rodan a cada minuto
    • Se SL acionado → posição fecha automaticamente
    • Se TP acionado → posição fecha automaticamente
    • Se timeout → posição fecha após 2h
    • PnL atualizado em tempo real


EXEMPLO DE LIFETIME DE UMA POSIÇÃO:
════════════════════════════════════════════════════════════════════════════════════

[00:24:50] ✅ Ordem executada: ANKRUSDT LONG
           - Entry: $0.004609
           - Size: $10 (2169 ANKRUSDT @ 10x)
           - SL: $0.004379 | TP: $0.005070

[00:24:51] 📊 Trade ID 1 registrado em DB
           - Timestamp entrada: 2026-02-21 00:24:50
           - Binance Order ID: 5412770081

[00:25:00] 🔄 Monitor checou (ciclo 1)
           - Preço atual: $0.00460746
           - PnL: -$0.003 (-0.03%)
           - Status: ✅ Protegida

[XX:XX:XX] ✅ TP ACIONADO (quando preço ≥ $0.005070)
           - Exit Price: $0.00507X
           - PnL: +$0.XX (+10%)
           - Motivo Saída: TAKE PROFIT
           - Timestamp saída: [salvo em DB]


BANCO DE DADOS - CAMPOS IMPORTANTES:
════════════════════════════════════════════════════════════════════════════════════

trade_log table:
├─ trade_id               : ID único local
├─ timestamp_entrada      : Quando foi aberta
├─ timestamp_saida        : Quando foi fechada (NULL se aberta)
├─ symbol                 : Par (ex: ANKRUSDT)
├─ direcao                : LONG ou SHORT
├─ entry_price            : Preço de entrada
├─ exit_price             : Preço de saída (NULL se aberta)
├─ stop_loss              : Preço de SL
├─ take_profit            : Preço de TP
├─ leverage               : Alavancagem usada
├─ position_size_usdt     : Valor em USDT
├─ binance_order_id       : ID do Binance
├─ unrealized_pnl_at_snapshot : PnL não realizado (atualizado a cada scan)
├─ pnl_usdt               : PnL em USDT (NULL até fechar)
├─ pnl_pct                : PnL em % (NULL até fechar)
└─ motivo_saida           : Por que fechou (SL/TP/TIMEOUT/etc)


ALERTAS E AVISOS:
════════════════════════════════════════════════════════════════════════════════════

⚠️  NÍVEL 1 (INFO):
    Preço se movendo normalmente
    Status: ✅ PROTEGIDA

⚠️  NÍVEL 2 (AVISO):
    - PnL negativo > 3%
    - Distância até liquidação < 5%
    - Posição aberta > 1.5h

❌ NÍVEL 3 (CRÍTICO):
    - Distância até liquidação < 1% → FECHA URGENTEMENTE
    - PnL < -5% → Revisar (mas SL vai fechar)
    - Preço passa SL/TP → Fecha automaticamente


TROUBLESHOOTING:
════════════════════════════════════════════════════════════════════════════════════

❓ "Ordem não foi registrada em DB"
   → Run: check_trade_log.py
   → Verificar se binance_order_id está preenchido
   → Monitor vai atualizar PnL mesmo assim

❓ "SL/TP não fecha a posição"
   → Verificar se scheduler está rodando (sempre)
   → Check: dashboard_protections.py (status dos triggers)
   → Limite de tempo: 1 minuto entre checks (ou --interval 30)

❓ "PnL diferente do Binance"
   → PnL é calculado localmente (pode ter diferenças de decimal)
   → Verificar entry_price = preço real de execução no Binance
   → Diferenças < 0.1% são normais

❓ "Posição não fecha após 2h (timeout)"
   → Verificar se scheduler ainda está rodando
   → Sem monitor rodando, proteções não são aplicadas
   → Sempre deixe scheduler ativo!


MELHORIAS FUTURAS:
════════════════════════════════════════════════════════════════════════════════════

[ ] Trailing stop loss (dinâmico)
[ ] Partial take profit (sai em fases)
[ ] Alavancagem dinâmica (mais risco = mais alavanca)
[ ] Hedge com short (proteção bidirecional)
[ ] Alertas por email/SMS
[ ] WebSocket em tempo real (vs polling a cada minuto)
[ ] Backtesting com histórico
[ ] Machine learning para ajustar SL/TP


╔══════════════════════════════════════════════════════════════════════════════════╗
║                             ✅ SISTEMA PRONTO PARA USAR!                        ║
║                                                                                  ║
║  1. Execute: python scripts/schedule_monitor.py                 (Terminal 1)    ║
║  2. Execute: python scripts/execute_1dollar_trade.py            (Terminal 2)    ║
║  3. Check:   python scripts/dashboard_protections.py            (conforme needed)║
║                                                                                  ║
║  Proteções: Stop Loss | Take Profit | Liquidação | Timeout | PnL Real          ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""
    print(guide)

if __name__ == "__main__":
    print_guide()
