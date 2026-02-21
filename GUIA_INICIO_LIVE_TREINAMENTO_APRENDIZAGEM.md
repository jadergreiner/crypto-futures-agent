# � REFERÊNCIA TÉCNICA - GUIA COMPLETO

> ⚠️ **OPERADOR:** Se você quer começar, abra [COMECE_AQUI.md](COMECE_AQUI.md) (2 minutos)
>
> Este documento é para **DESENVOLVEDOR / REFERÊNCIA TÉCNICA** apenas.

---

# �🚀 GUIA COMPLETO - INICIAR LIVE + TREINAMENTO + APRENDIZAGEM

## Sumário Executivo

Este guia orienta como iniciar o **Agente Autônomo de Futuros Crypto** em modo **PRODUÇÃO TOTAL**:
- ✅ **LIVE TRADING** - Capital real em operação
- ✅ **TREINAMENTO CONCORRENTE** - Modelo aprendendo em paralelo
- ✅ **MONITORAMENTO INTEGRADO** - Posições gerenciadas automaticamente
- ✅ **PROTEÇÕES INVIOLÁVEIS** - Risk management garantido

---

## PARTE 1: PRÉ-REQUISITOS

### 1.1 Checklist de Pré-operação

Antes de iniciar, valide:

```bash
# Terminal PowerShell
════════════════════════════════════════════════════════════════

□ Ambiente Virtual Ativado
  Verificar: venv\Scripts\activate.bat já foi executado?

□ Arquivo .env Configurado
  Localização: .env
  Conteúdo: BINANCE_API_KEY, BINANCE_SECRET_KEY com valores (não vazio)
  TRADING_MODE=live (para produção)

□ Banco de Dados Inicializado
  Arquivo: db/crypto_agent.db
  Se NÃO existir, execute PRIMEIRO:
    python main.py --setup

□ Modelo RL Treinado
  Arquivo: models/crypto_agent_ppo_final.zip
  Se NÃO existir, execute PRIMEIRO:
    python main.py --train

□ Capital Disponível Configurado
  Arquivo: config/execution_config.py
  Parâmetro: max_margin_per_position_usd
  Validar: Alinhado com capital real em conta Binance

□ Proteções de Risco Validadas
  Arquivo: risk/risk_manager.py
  Validar: max_drawdown_daily, max_margin_utilizável

════════════════════════════════════════════════════════════════
```

### 1.2 Verificações Rápidas

```powershell
# Verificar ambiente virtual
python --version  # Deve retornar Python 3.9+

# Verificar dependências
pip list | grep -E "stable-baselines3|gymnasium|numpy|pandas|binance"

# Verificar database
ls db/
  # Deve ter: crypto_agent.db (ou crypto_futures.db)

# Verificar modelo
ls models/
  # Deve ter: crypto_agent_ppo_final.zip (ou phase2_refinement.zip)

# Verificar arquivo .env
cat .env
  # Deve ter: BINANCE_API_KEY=... não como placeholder

# Teste de conexão API Binance
python -c "from data.binance_client import create_binance_client; client = create_binance_client(mode='live'); print('✅ API Conectada')"
```

---

## PARTE 2: MODOS DE EXECUÇÃO

### Opção A: LIVE + INTEGRADO (Recomendado para Começar)

**Descrição:**
- ✅ Capital real em operação
- ✅ Monitora 20 posições antigas existentes
- ✅ Gera novos sinais a cada 5 minutos
- ❌ SEM treinamento paralelo (focus em trading)

**Comando:**
```powershell
python main.py --mode live --integrated --integrated-interval 300
```

**O que acontece:**
1. Sistema inicializa em modo LIVE (capital REAL)
2. Detecta 20 posições abertas (se existirem)
3. A cada 300 segundos (5 min):
   - Busca confluência em símbolos selecionados
   - Se score >7/14: abre nova posição
   - Gerencia SL/TP via algo orders Binance
4. Monitora continuamente

**Duração:** ∞ (roda indefinidamente até Ctrl+C)

**Ideal para:** Validação inicial, primeiras 4-24 horas de trading

---

### Opção B: LIVE + INTEGRADO + TREINAMENTO CONCORRENTE (FULL PRODUCTION)

**Descrição:**
- ✅ Capital real em operação
- ✅ Monitora 20 posições antigas
- ✅ Gera novos sinais a cada 5 minutos
- ✅ Treina modelo em paralelo a cada 4 horas

**Comando:**
```powershell
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

**O que acontece:**
1. Tudo da **Opção A**, MAIS:
2. A cada 14.400 segundos (4 horas):
   - Sistema PARA temporariamente novas operações
   - Coleta dados de performance das últimas 4 horas
   - Treina modelo com dados recentes via PPO
   - Valida modelo contra dados históricos
   - Reinicia com modelo aprimorado
3. Cicles de aprendizagem contínua

**Duração:** ∞ (roda indefinidamente)

**Ideal para:** Produção a longo prazo, otimização contínua

---

### Opção C: LIVE + TREINAMENTO COM INTERVALO CUSTOMIZADO

**Descrição:** Similar à Opção B mas permite ajustar intervalos

**Comando (Exemplo: Treinar a cada 2 horas):**
```powershell
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 7200
```

**Parâmetros Customizáveis:**

| Parâmetro | Padrão | Unidade | Função |
|-----------|--------|---------|--------|
| `--integrated-interval` | 300 | segundos | Periodicidade de decisão de trading |
| `--training-interval` | 14400 | segundos | Periodicidade de treinamento |

**Equivalências (para referência):**
```
1800   = 30 minutos
3600   = 1 hora
7200   = 2 horas
10800  = 3 horas
14400  = 4 horas (padrão)
21600  = 6 horas
28800  = 8 horas
43200  = 12 horas
86400  = 24 horas
```

---

### Opção D: PAPER MODE (Teste sem Capital Real)

**Descrição:** Simula trading em papel - útil para validação

**Comando:**
```powershell
python main.py --mode paper --integrated --integrated-interval 300 --concurrent-training --training-interval 3600
```

**O que acontece:**
- Mode "paper" = Simula trades SEM executar na Binance real
- Útil para testar lógica sem risco
- Treinamento funciona normalmente

**Risco:** ZERO (nenhum capital real movido)

---

## PARTE 3: GUIA PASSO A PASSO - INICIAR EM LIVE COMPLETO

### Cenário: Semana 1 de Operação

#### **PASSO 1: Verificação Pré-operacional (T-0h)**

```powershell
# Abrir PowerShell como Admin
cd C:\repo\crypto-futures-agent

# Ativar ambiente virtual
.\venv\Scripts\activate.bat

# Testar conexão API
python -c "
from data.binance_client import create_binance_client
client = create_binance_client(mode='live')
positions = client.rest_api.position_information_v2()
print(f'✅ Conectado. Posições detectadas: {len(positions)}')
"
```

**Saída esperada:**
```
✅ Conectado. Posições detectadas: 20
```

#### **PASSO 2: Validação de Capital (T-0h)**

```powershell
# Monitorar estado atual de posições
python main.py --mode live --monitor --monitor-interval 5
```

**Saída esperada:**
```
═════════════════════════════════════════════════════════════
MONITOR - POSIÇÕES ABERTAS (LIVE)
═════════════════════════════════════════════════════════════
Tempo: 2026-02-21 01:35:00

POSIÇÕES:
─────────────────────────────────────────────────────────────
BROCCOLI714USDT   LONG   Margem: $4,72   PnL: -$45,33
SOMIUSDT          SHORT  Margem: $1,31   PnL: -$1,81
[... demais 18 posições ...]
─────────────────────────────────────────────────────────────
TOTAL MARGEM: $65,00    TOTAL PnL: -$182,00    CAPITAL LIVRE: $359,00

Aguardando próximo ciclo (5s)...
```

Pressione **Ctrl+C** para sair.

#### **PASSO 3: Iniciar LIVE INTEGRADO (T+0h)**

```powershell
# Iniciar sistema em LIVE com trading automático
python main.py --mode live --integrated --integrated-interval 300
```

**Saída esperada (primeiras linhas):**
```
════════════════════════════════════════════════════════════════
CRYPTO FUTURES AUTONOMOUS AGENT
Reinforcement Learning + Smart Money Concepts
════════════════════════════════════════════════════════════════

2026-02-21 01:35:00,001 - INFO - Database initialized successfully
2026-02-21 01:35:00,050 - INFO - Binance client created in live mode
2026-02-21 01:35:00,051 - INFO - ========================================
2026-02-21 01:35:00,051 - INFO - STARTING OPERATION - MODE: LIVE
2026-02-21 01:35:00,051 - INFO - ========================================
2026-02-21 01:35:00,200 - INFO - Encontradas 20 posição(ões) aberta(s)
2026-02-21 01:35:00,250 - INFO - [OK] Ciclo #1 completo - 0 posições abertas
2026-02-21 01:35:01,000 - INFO - [AGUARDANDO] Próximo ciclo em 300s...
```

**Deixar rodando por 2-4 horas observando logs.**

---

#### **PASSO 4: Apertar para TREINAMENTO CONCORRENTE (T+4h)**

Após validar que:
- ✅ Nenhum erro de risco
- ✅ Sistema gerencia posições corretamente
- ✅ Capital dentro dos limites

**Parar sistema (Ctrl+C) e reiniciar com treinamento:**

```powershell
# Ctrl+C para parar o anterior

# Reiniciar COM treinamento concorrente
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

**Saída esperada:**
```
2026-02-21 05:35:00,051 - INFO - STARTING OPERATION - MODE: LIVE
2026-02-21 05:35:00,051 - INFO - CONCURRENT TRAINING ENABLED: Modelos serão treinados a cada 240 minutos em paralelo
2026-02-21 05:35:00,051 - INFO - INTEGRATED MODE ENABLED: monitor de posições ativo em paralelo (intervalo=300s)
2026-02-21 05:35:00,051 - INFO - Pressione Ctrl+C para parar
```

---

### Cenário: Segunda Semana em Diante (Otimização)

#### **Ajuste 1: Aumentar Frequência de Treinamento (se Win Rate >60%)**

```powershell
# Treinar a cada 2 horas (mais aprendizagem)
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 7200
```

#### **Ajuste 2: Reduzir Intervalo de Decisão (se Capital >$1k)**

```powershell
# Decisão a cada 3 minutos (mais oportunidades)
python main.py --mode live --integrated --integrated-interval 180 --concurrent-training --training-interval 14400
```

#### **Ajuste 3: Monitoramento Crítico + Escalação de Capital**

Se operação estiver gerando lucros:

```powershell
# 1. Parar sistema
# Ctrl+C

# 2. Editar config/execution_config.py
# Aumentar max_margin_per_position_usd de $8,48 para $15 (exemplo)

# 3. Reiniciar com novo capital
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

---

## PARTE 4: MONITORAMENTO EM TEMPO REAL

### 4.1 Monitorar Logs em Outra Janela

Enquanto sistema está rodando, abrir OUTRA janela PowerShell:

```powershell
cd C:\repo\crypto-futures-agent

# Ver logs em tempo real
tail -f logs/agent.log

# Ou para PowerShell: Get-Content com -Wait
Get-Content -Path "logs\agent.log" -Wait -Tail 20
```

### 4.2 Dashboard de Execução

Para ver status consolidado:

```powershell
# Em outra janela (enquanto --mode live roda)
python -c "
import sqlite3
conn = sqlite3.connect('db/crypto_agent.db')
cursor = conn.cursor()

# Contar trades hoje
cursor.execute('SELECT COUNT(*) FROM execution_log WHERE DATE(timestamp) = DATE(\"now\")')
today_trades = cursor.fetchone()[0]

# Win rate
cursor.execute('SELECT COUNT(*) as win FROM execution_log WHERE pnl > 0 AND DATE(timestamp) = DATE(\"now\")')
wins = cursor.fetchone()[0]

print(f'Trades hoje: {today_trades}')
print(f'Vitórias: {wins}/{today_trades} ({(wins/today_trades*100 if today_trades > 0 else 0):.1f}%)')
"
```

### 4.3 Verificar Posições em Tempo Real

```powershell
# Enquanto sistema roda, verificar posições:
python main.py --mode live --monitor --monitor-interval 5
```

---

## PARTE 5: ESTRUTURA DE ARQUIVOS IMPORTANTES

Durante execução, o sistema cria/atualiza:

```
crypto-futures-agent/
├── logs/
│   ├── agent.log                  ← Logs de execução
│   └── training_metrics.json      ← Métricas de treino
├── db/
│   └── crypto_agent.db            ← Banco com trades
├── models/
│   ├── crypto_agent_ppo_final.zip ← Modelo RL atual
│   └── checkpoints/               ← Histórico de checkpoints
├── config/
│   ├── execution_config.py        ← Configuração de risco
│   └── settings.py                ← Modo de operação
└── .env                           ← Credenciais Binance
```

---

## PARTE 6: CRITÉRIOS DE DECISÃO - DEPOIS DE X HORAS

### Após 4 Horas (T+4h)

```
Métrica                 Esperado        Ação se <esperado
─────────────────────────────────────────────────────────
Nenhum erro de risco    100%            ABORTAR - valide config
Trades abertos          ≥1              Aumentar confiança threshold
Win rate                ≥45%            Continuar (normal)
Margem utilizada        <50%            OK
Drawdown diário         <5%             OK
```

### Após 24 Horas (T+1d)

```
Métrica                 Esperado        Ação se <esperado
─────────────────────────────────────────────────────────
Win rate                ≥50%            Ativar treinamento concorrente
Sharpe ratio            ≥0,3            Ajustar thresholds
Max drawdown            <5%             Revisar risco
Novas posições abertas  ≥3              Capital pode estar baixo
```

### Após 1 Semana (T+7d)

```
Métrica                 Esperado        Ação se <esperado
─────────────────────────────────────────────────────────
Win rate                ≥55%            Aumentar posição sizing
Curva de lucro          Crescente       Reajustar modelo
Sharpe ratio            ≥0,5            Parar treino concorrente
Drawdown máximo         <10%            Aumentar capital
```

---

## PARTE 7: TROUBLESHOOTING

### Erro: "API Key Inválida"

```powershell
# Verificar:
1. Arquivo .env contém BINANCE_API_KEY correto?
2. API key é para FUTURES (não SPOT)?
3. API key tem permissão de TRADING (não apenas READ)?

# Testar:
python -c "from data.binance_client import create_binance_client; create_binance_client(mode='live')"
```

### Erro: "Keine Daten / No Data"

```powershell
# Executar setup se ainda não fez:
python main.py --setup

# Isso coleta dados históricos de 30 dias (H4) para todos símbolos
```

### Erro: "Model Not Found"

```powershell
# Treinar modelo
python main.py --train

# Isso roda 3 fases de treinamento (~2 horas)
```

### Sistema Roda mas Não Abre Trades

```powershell
# Possíveis causas:
1. Confiança mínima > 0,7 → Confluence <7/14 (normal)
2. Whitelist vazia → Nenhum símbolo autorizado
3. Capital insuficiente → Aumentar max_margin_per_position_usd

# Debugar:
python -c "
from config.execution_config import EXECUTION_CONFIG
print(f'Min Confidence: {EXECUTION_CONFIG.get(\"min_confidence\", 0.7)}')
print(f'Max Margin: {EXECUTION_CONFIG.get(\"max_margin_per_position_usd\", 1)}')
print(f'Whitelist: {EXECUTION_CONFIG.get(\"whitelist\", \"EMPTY\")}')
"
```

---

## PARTE 8: ESCALAÇÃO DE CAPITAL

### Protocolo de Aumento de Risco (Semanal)

**SEMANA 1:** Capital = $424 → Win rate conseguido?

```
SIM (>55%):  Aumentar 10% capital → $466
NÃO (<45%):  Manter, revisar modelo
```

**SEMANA 2:** New capital margin

```python
# Editar config/execution_config.py
EXECUTION_CONFIG = {
    "max_margin_per_position_usd": 15,  # Era $8,48, agora $15
    "max_concurrent_positions": 30,
    # ... resto
}
```

Reiniciar sistema.

---

## PARTE 9: COMANDO RECOMENDADO FINAL

Para **produção a longo prazo**, use:

```powershell
# ╔════════════════════════════════════════════════════════════════╗
# ║       COMANDO DEFINITIVO - LIVE + TREINO + APRENDIZAGEM       ║
# ╚════════════════════════════════════════════════════════════════╝

python main.py `
  --mode live `
  --integrated `
  --integrated-interval 300 `
  --concurrent-training `
  --training-interval 14400

# Versão sem quebras (para copiar/colar direto):
# python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

---

## PARTE 10: ENCERRAMENTO SEGURO

### Parar Sistema sem Perder Dados

```powershell
# NUNCA: Fechar janela abruptamente
# SEMPRE: Usar Ctrl+C

# Ao pressionar Ctrl+C, o sistema:
1. Encerra scheduler de trading
2. Para treinamento se estiver rodando
3. Salva modelo atual
4. Grava último estado em DB
5. Fecha todas posições monitoradas (sem vender)

# Saída esperada:
# 2026-02-21 09:35:00,123 - INFO - Operation interrupted by user
# 2026-02-21 09:35:00,456 - INFO - Training scheduler stopped
# 2026-02-21 09:35:00,789 - INFO - Monitor stopped
# [OK] Sistema parado com segurança
```

---

## RESUMO: 3 MINUTOS PARA COMEÇAR

```
┌─────────────────────────────────────────────────────┐
│          RÁPIDO START (SEM COMPLICAÇÃO)             │
└─────────────────────────────────────────────────────┘

1. Abrir PowerShell em C:\repo\crypto-futures-agent

2. Ativar ambiente:
   .\venv\Scripts\activate.bat

3. Começar:
   python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400

4. RESULTADO:
   ✅ Sistema LIVE
   ✅ Monitorando 20 posições
   ✅ Gerando sinais a cada 5 min
   ✅ Treinando modelo a cada 4 horas
   ✅ Protegendo capital com risk management

5. Ver logs:
   Get-Content -Path "logs\agent.log" -Wait -Tail 20

════════════════════════════════════════════════════════════════
```

---

**Dúvidas? Verifique:**
- 📖 Documentação: `docs/`
- 📊 Logs: `logs/agent.log`
- 🎯 Configuração: `config/execution_config.py`
- 📱 Status: `python main.py --monitor`

🚀 **PRONTO PARA VOAR!**

