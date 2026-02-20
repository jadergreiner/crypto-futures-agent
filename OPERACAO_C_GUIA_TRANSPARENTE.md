╔════════════════════════════════════════════════════════════════╗
║ OPERAÇÃO PARALELA C — GUIA TRANSPARENTE PARA OPERADOR         ║
║ Implementado em iniciar.bat — Nenhuma mudança na interface    ║
╚════════════════════════════════════════════════════════════════╝

COMO FUNCIONA
═════════════════════════════════════════════════════════════════

1. EXECUÇÃO NORMAL (SEM AUTORIZAÇÃO C)
   ┌─────────────────────────────────┐
   │ $ iniciar.bat                   │
   │ [Verificações pré-operacionais] │
   │ [Menu interativo normal]        │
   │ (nenhuma mudança)               │
   └─────────────────────────────────┘

2. EXECUÇÃO COM AUTORIZAÇÃO C (TRANSPARENTE)
   ┌─────────────────────────────────────────────┐
   │ $ iniciar.bat                               │
   │ [Verificações pré-operacionais]             │
   │ [DETECÇÃO AUTOMÁTICA]                       │
   │   ✓ AUTHORIZATION_OPÇÃO_C_20FEV.txt         │
   │   ↓ Ativa Operação C em background         │
   │   ├─ LIVE Scheduler: RODANDO                │
   │   ├─ v0.3 Tests: BACKGROUND (isolado)      │
   │   └─ Monitor: ATIVO (60s checks)            │
   │ [Menu interativo normal — continua igual]   │
   │ (operador não percebe nada diferente)       │
   └─────────────────────────────────────────────┘

PASSO A PASSO
═════════════════════════════════════════════════════════════════

Para o OPERADOR, funciona assim:

1. Execute como sempre:
   C:\repo> iniciar.bat

2. Veja as verificações pré-operacionais (normal):
   [1/5] Ambiente virtual... [OK]
   [2/5] Configuração (.env)... [OK]
   [3/5] Banco de dados... [OK]
   [4/5] Logs... [OK]
   [5/5] Arquivos críticos... [OK]

3. NOVIDADE (TRANSPARENTE):
   Se Opção C foi autorizada, você verá:

   [VERIFICACAO AUTOMATICA] Operacao Paralela C detectada...
   [OK] Operacao Paralela C iniciada em background
       - LIVE Scheduler: RODANDO (16 pares USDT)
       - v0.3 Tests: EXECUTANDO (thread isolada)
       - Monitor Critico: ATIVO (60s checks, kill switch 2%)
       - Capital em Risco: $5,000 USD
       - Logs: logs/orchestrator_opção_c.log, logs/critical_monitor.log

   [!] Tela de menu disponivel abaixo. Siga normalmente.
   [!] Operacao C corre silenciosamente em background.

4. Menu continua normal (sem mudanças):
   Escolha o modo de execucao:
   1. Paper Trading...
   2. Live Integrado...
   3. Monitorar Posicoes...
   [etc...]

5. Operador escolhe opção normalmente (ex: opção 1 para paper):
   → Digite: 1
   → Executa: python main.py --mode paper

   ENQUANTO ISSO, em background:
   ✓ LIVE está rodando (se autorizado Opção C)
   ✓ v0.3 testes estão executando
   ✓ Monitor está checando health a cada 60s
   ✓ Kill switch está armado (2% loss)
   ✓ Tudo isolado e não interfere

MONITORAR STATUS
═════════════════════════════════════════════════════════════════

Se Operação C está rodando, você pode verificar logs:

1. Status da Operação C:
   $ tail -f logs/orchestrator_opção_c.log

   Verá:
   [ORCHESTRATOR] - OPERACAO PARALELA
   [ORCHESTRATOR] - LIVE Scheduler ATIVO
   [ORCHESTRATOR] - v0.3 Tests BACKGROUND
   [etc...]

2. Monitor crítico (health checks):
   $ tail -f logs/critical_monitor.log

   Verá a cada 60 segundos:
   [CRITICAL-MONITOR] Health OK | API: 150ms | Memory: 45% | Loss: 0% | LIVE: RUN

3. Logs normais do agent (LIVE):
   $ tail -f logs/agent.log

   (continua igual, mas LIVE está rodando em paralelo)

PARAR OPERAÇÃO C
═════════════════════════════════════════════════════════════════

Se precisar parar (interrupção):

1. CTRL+C no iniciar.bat
   → Para menu principal
   → Operação C continua em background

2. Para Operação C completamente:
   C:\repo> taskkill /F /FL "orchestrator_opção_c.py"

   Ou (mais seguro):
   C:\repo> python -c "
   from monitoring.critical_monitor_opção_c import CriticalMonitor
   m = CriticalMonitor()
   m.trigger_kill_switch('MANUAL_STOP')
   "

FALHAS E RECUPERAÇÃO
═════════════════════════════════════════════════════════════════

Se Operação C falha silenciosamente:

1. Verifique log:
   $ type logs/orchestrator_opção_c.log | tail -20

2. Se thread morreu:
   → Kill switch automático para LIVE
   → Verifique critical_monitor.log para motivo
   → Analise logs/agent.log para trades

3. Se quer retomar:
   → Remova: AUTHORIZATION_OPÇÃO_C_20FEV.txt
   → Edite: CHANGELOG.md e marque incidente
   → Próxima execução de iniciar.bat será normal

RESUMO PARA OPERADOR
═════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│ ✅ TUDO TRANSPARENTE — Operador NÃO precisa fazer nada     │
│                                                             │
│ • Execute iniciar.bat normalmente                           │
│ • Use menu como sempre                                      │
│ • Se Opção C autorizada, funciona silenciosamente           │
│ • Tudo isolado, sem interferência                           │
│ • Logs disponíveis para monitorar se desejar               │
│ • Kill switch automático se problemas                       │
│                                                             │
│ Resumo: "Set and forget" — sistema cuida de tudo          │
└─────────────────────────────────────────────────────────────┘

═════════════════════════════════════════════════════════════════
Data: 20/02/2026
Implementação: Transparente via iniciar.bat + orquestrador
Autorização: AUTHORIZATION_OPÇÃO_C_20FEV.txt
═════════════════════════════════════════════════════════════════
