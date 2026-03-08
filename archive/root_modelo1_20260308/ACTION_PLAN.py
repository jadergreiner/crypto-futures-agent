#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLANO DE AÇÃO - Próximos Passos
Resumo executivo para operação contínua
"""

def print_action_plan():
    plan = """

╔════════════════════════════════════════════════════════════════════════════════╗
║                      ✅ PROTEÇÕES IMPLEMENTADAS COM SUCESSO                   ║
║                                                                                ║
║  5 Proteções Automáticas:                                                     ║
║  1. Stop Loss (-5%)           ✅                                               ║
║  2. Take Profit (+10%)        ✅                                               ║
║  3. Liquidação Preventiva     ✅                                               ║
║  4. Timeout (2h)              ✅                                               ║
║  5. PnL Em Tempo Real         ✅                                               ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝


📋 PLANO DE AÇÃO - PRÓXIMOS PASSOS
════════════════════════════════════════════════════════════════════════════════

ETAPA 1: INICIAR SISTEMA (AGORA)
├─ Terminal 1: python scripts/schedule_monitor.py
│  └─ Deixe rodando SEMPRE (monitora proteções)
│
├─ Terminal 2: python scripts/execute_1dollar_trade.py --symbol ANKRUSDT
│  └─ Próxima ordem (ou outro símbolo)
│
└─ Terminal 3: python scripts/dashboard_protections.py
   └─ Visualizar status (a cada 5-15 min)


ETAPA 2: OPERAÇÃO CONTÍNUA (PRÓXIMAS HORAS)
├─ Rodar dashboard regularmente para acompanhar
├─ Deixar scheduler no Terminal 1 SEMPRE LIGADO
├─ Sistema vai fechar posições automaticamente (SL/TP/Timeout)
└─ Database registra cada transação automaticamente


ETAPA 3: SCALE UP (APÓS VALIDAÇÃO)
├─ Quando quiser 2+ posições simultâneas:
│  ├─ Executar 2ª ordem em outro símbolo
│  ├─ Executar 3ª ordem em outro símbolo
│  └─ Monitor rastreia TODAS automaticamente
│
└─ Cada posição tem proteções independentes:
   ├─ SL calculado para cada uma
   ├─ TP calculado para cada uma
   └─ Pode fechar em tempos diferentes


════════════════════════════════════════════════════════════════════════════════

🎯 COMANDOS RÁPIDOS
════════════════════════════════════════════════════════════════════════════════

NOVO TRADE (próxima moeda):
└─ python scripts/execute_1dollar_trade.py --symbol SOLUSDT --direction LONG
└─ python scripts/execute_1dollar_trade.py --symbol ETHERSL --direction SHORT

MONITORAR PROTEÇÕES (UMA VEZ):
└─ python scripts/monitor_positions.py

RODAR SCHEDULER (ABRIR EM NOVO TERMINAL):
└─ python scripts/schedule_monitor.py --interval 60

VER DASHBOARD:
└─ python scripts/dashboard_protections.py

VALIDAR TUDO:
└─ python test_protections.py


════════════════════════════════════════════════════════════════════════════════

📊 POSIÇÃO ATUAL
════════════════════════════════════════════════════════════════════════════════

Trade ID: 1
├─ Symbol: ANKRUSDT
├─ Tipo: LONG
├─ Entry: $0.004609
├─ Size: $10 (2169 tokens @ 10x)
├─ Status: ABERTA ✅
├─ Stop Loss: $0.004378 (-5%)
├─ Take Profit: $0.005070 (+10%)
├─ Binance Order ID: 5412770081
└─ Proteções: ATIVAS ✅


════════════════════════════════════════════════════════════════════════════════

💡 DICAS DE OPERAÇÃO
════════════════════════════════════════════════════════════════════════════════

✓ SCHEDULER = CORAÇÃO DO SISTEMA
  Sem scheduler rodando, proteções NÃO funcionam
  Deixe sempre em um terminal dedicado

✓ DASHBOARD = SEUS OLHOS
  Use para monitorar situação das posições
  Atualiza status completo em tempo real

✓ MÚLTIPLAS POSIÇÕES
  Cada uma tem proteções independentes
  Podem fechar em tempos diferentes
  Database rastreia TUDO automaticamente

✓ PARAR SISTEMA
  Feche manual as posições no Binance antes de desligar
  Ou deixe scheduler rodando e ele fecha com timeout (2h)
  Sempre confirme que status fica "FECHADA" e não "PENDENTE"

✓ ANÁLISE PÓS-OPERAÇÃO
  Abra: python check_trade_log.py
  Ver todos os trades (abertos, fechados, PnL)


════════════════════════════════════════════════════════════════════════════════

📝 ROADMAP - O QUE VÊEM A SEGUIR
════════════════════════════════════════════════════════════════════════════════

SEMANA 1 (AGORA):
  ✅ 1 posição de teste ($1 margin)
  ✅ Validar que SL/TP funcionam
  ✅ Validar que PnL registra em DB
  ⏳ Executar 3-5 pequenas posições

SEMANA 2:
  ⏳ 3 posições simultâneas diferentes symblos
  ⏳ Validar que cada uma tem proteções
  ⏳ Testar scenario: 2 lucro, 1 perda

SEMANA 3-4:
  ⏳ Scale up: $5 por posição (ao invés de $1)
  ⏳ 5-10 pares simultâneos
  ⏳ Análise histórica (PnL agregado)

SEMANA 5+:
  ⏳ Otimizar SL/TP baseado em histórico
  ⏳ Machine learning para símbolos mais lucrativos
  ⏳ Trailing stops ao invés de fixo
  ⏳ Alertas em tempo real

════════════════════════════════════════════════════════════════════════════════

🚨 CASOS DE EMERGÊNCIA
════════════════════════════════════════════════════════════════════════════════

"Preço caiu muito rápido, preciso fechar AGORA"
  → Abra Binance.com, feche posição manual
  → Depois: python monitor_positions.py (vai registrar)

"Scheduler travou, preciso reiniciar"
  → Ctrl+C no Terminal onde scheduler está
  → Reabra: python scripts/schedule_monitor.py

"Acho que ordem não registrou"
  → python test_protections.py (valida DB)
  → Se não tiver, use scripts/register_past_order.py pra adicionar

"Sistema ficou lento/travou"
  → Pode ser lag de API do Binance
  → Aguarde 2-3 minutos
  → Se continuar: reinicie scheduler


════════════════════════════════════════════════════════════════════════════════

✅ CHECKLIST DE LANÇAMENTO
════════════════════════════════════════════════════════════════════════════════

ANTES DE USAR:
  □ Confirmar que API key Binance está configurada (live mode)
  □ Confirmar que $1 de saldo está disponível na conta
  □ Lançar scheduler em novo terminal: python scripts/schedule_monitor.py
  □ Aguardar 30 segundos para garantir que scheduler está rodando
  □ Abrir novo terminal
  □ Executar primeira ordem: python scripts/execute_1dollar_trade.py

DURANTE OPERAÇÃO:
  □ Scheduler rodando (Terminal 1)
  □ Dashboard acessível (Terminal 3, rodá conforme necessário)
  □ Telefone próximo para emergências
  □ Verificar a cada 15 minutos se tudo está OK

APÓS OPERAÇÃO:
  □ Confirmar que posição foi registrada
  □ Conferir PnL em scripts/dashboard_protections.py
  □ Salvar histórico: python check_trade_log.py


════════════════════════════════════════════════════════════════════════════════

🎓 LEITURA RECOMENDADA
════════════════════════════════════════════════════════════════════════════════

Documentação técnica:
  • PROTECTIONS_STATUS.md - Sumário executivo das proteções
  • PROTECTIONS_IMPLEMENTED.md - Detalhes técnicos

Código principal:
  • scripts/execute_1dollar_trade.py - Execução de ordens
  • scripts/monitor_positions.py - Lógica de proteções
  • scripts/schedule_monitor.py - Scheduler

Database:
  • check_trade_log.py - Inspeciona registros
  • test_protections.py - Valida integridade


════════════════════════════════════════════════════════════════════════════════

📞 SUPORTE / QUERIES
════════════════════════════════════════════════════════════════════════════════

Ver última posição:
  python -c "import sqlite3; conn = sqlite3.connect('db/crypto_futures.db'); \\
  cursor = conn.cursor(); cursor.execute('SELECT * FROM trade_log ORDER BY \\
  trade_id DESC LIMIT 1'); print(cursor.fetchone()); conn.close()"

Ver todas as ordens hoje:
  python check_trade_log.py

Ver PnL agregado:
  python -c "import sqlite3; conn = sqlite3.connect('db/crypto_futures.db'); \\
  cursor = conn.cursor(); cursor.execute('SELECT SUM(pnl_usdt) FROM trade_log'); \\
  print(f'Total PnL: ${cursor.fetchone()[0]:.2f}'); conn.close()"


════════════════════════════════════════════════════════════════════════════════

🏁 RESUMO FINAL
════════════════════════════════════════════════════════════════════════════════

✅ SISTEMA PRONTO PARA OPERAÇÃO 24/7

5 Proteções automáticas implementadas e validadas
Database com auditoria completa de cada trade
Scheduler monitorando a cada minuto
Dashboard visual para acompanhamento
Suporte para múltiplas posições simultâneas

Próximo comando:
  1. python scripts/schedule_monitor.py
  2. python scripts/execute_1dollar_trade.py --symbol ANKRUSDT
  3. python scripts/dashboard_protections.py

BOA SORTE! 🚀

════════════════════════════════════════════════════════════════════════════════
"""
    print(plan)


if __name__ == "__main__":
    print_action_plan()
