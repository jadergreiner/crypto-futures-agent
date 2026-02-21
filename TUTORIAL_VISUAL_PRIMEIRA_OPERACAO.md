# 📚 REFERÊNCIA TÉCNICA - TUTORIAL COMPLETO

> ⚠️ **OPERADOR:** Se você quer começar, abra [COMECE_AQUI.md](COMECE_AQUI.md) (2 minutos)
>
> Este documento é para **DESENVOLVEDOR** - Tutorial detalhado com todas as opções.

## Cenário: Você está começando AGORA pela primeira vez

---

## 🟢 PASSO 1: PREPARAÇÃO (5 minutos)

### 1.1 Abrir PowerShell

```
Clique em:
  Windows → Buscar → PowerShell (as Admin)
```

**Saída esperada:**
```
C:\Windows\System32\WindowsPowerShell\v1.0> _
```

### 1.2 Navegar para Projeto

```powershell
cd C:\repo\crypto-futures-agent
```

**Saída esperada:**
```
C:\repo\crypto-futures-agent> _
```

### 1.3 Ativar Ambiente Virtual

```powershell
.\venv\Scripts\activate.bat
```

**Saída esperada:**
```
(venv) C:\repo\crypto-futures-agent> _
                          ↑
                    (venv) apareceu!
```

---

## 🔵 PASSO 2: VALIDAÇÃO PRÉ-VOO (3 minutos)

### 2.1 Verificar API Key

```powershell
python -c "
from data.binance_client import create_binance_client
import logging
logging.basicConfig(level=logging.ERROR)
try:
    client = create_binance_client(mode='live')
    positions = client.rest_api.position_information_v2()
    print(f'✅ API conectada! {len(positions)} posições detectadas.')
except Exception as e:
    print(f'❌ Erro: {e}')
"
```

**Saída esperada se OK:**
```
✅ API conectada! 20 posições detectadas.
```

**Saída esperada se ERRO:**
```
❌ Erro: Invalid API Key...
```

Se erro → Volte e corrija `.env`

### 2.2 Checar Modelo

```powershell
# Verificar se arquivo existe
if (Test-Path "models\crypto_agent_ppo_final.zip") {
    echo "✅ Modelo encontrado"
} else {
    echo "❌ Modelo não existe - execute: python main.py --train"
}
```

**Se mostrar ❌:**
```powershell
# Treinar modelo (vai levar ~2 horas)
python main.py --train

# Aguardar conclusão. Saída final esperada:
# 2026-02-21 11:30:00 - INFO - Model saved successfully
```

### 2.3 Checar Banco de Dados

```powershell
if (Test-Path "db\crypto_agent.db") {
    echo "✅ Database exists"
} else {
    echo "⚠️ Database missing - executar setup"
    python main.py --setup
}
```

**Se setup for necessário:** Vai levar 30-60 minutos (coleta dados históricos)

---

## 🟡 PASSO 3: MONITORAR POSIÇÕES ABERTAS (1 minuto)

Antes de começar, veja o que já está aberto:

```powershell
python main.py --mode live --monitor --monitor-interval 5
```

**Saída esperada:**
```
════════════════════════════════════════════════════════════════
MONITOR - POSIÇÕES ABERTAS (LIVE)
════════════════════════════════════════════════════════════════
Timestamp: 2026-02-21 11:45:00

═══════════════════════════════════════ POSIÇÕES (20) ═══════════════════════════════════════
Símbolo           Dir.   Margem(U)  Qty    e.Price PnL(U)   PnL(%)    Mode  ...
────────────────────────────────────────────────────────────────────────────────────────────
BROCCOLI714USDT   LONG      4,72    45  $0,105  -$45,33    -961%     CROSS
SOMIUSDT          SHORT     1,31     2  $0,655   -$1,81    -138%     CROSS
BREVUSDT          LONG      1,02    10  $0,102   -$1,08    -106%     CROSS
[... mais 17 posições ...]
────────────────────────────────────────────────────────────────────────────────────────────
TOTAL             -         65,00         -      -$182,00   -279%

Capital Total: $424,00 | Margem Livre: $359,00 | Risco: 15,3% (SEGURO)

Próxima atualização em 5s... (Ctrl+C para sair)
```

**Pressione Ctrl+C** para sair do monitor.

---

## 🟠 PASSO 4: INICIAR SISTEMA LIVE (FINALMENTE!)

### 4.1 Iniciar em Modo Básico (Dias 1-4)

```powershell
# Apenas LIVE, sem treinamento concorrente
python main.py --mode live --integrated --integrated-interval 300
```

**Saída esperada (primeiras 30 segundos):**
```
════════════════════════════════════════════════════════════════
CRYPTO FUTURES AUTONOMOUS AGENT
Reinforcement Learning + Smart Money Concepts
════════════════════════════════════════════════════════════════

2026-02-21 11:50:00,001 - INFO - Setting up database...
2026-02-21 11:50:00,050 - INFO - Database initialized successfully
2026-02-21 11:50:00,051 - INFO - Binance client created in live mode
2026-02-21 11:50:00,100 - INFO - ════════════════════════════════════════
2026-02-21 11:50:00,100 - INFO - STARTING OPERATION - MODE: LIVE
2026-02-21 11:50:00,100 - INFO - ════════════════════════════════════════
2026-02-21 11:50:00,200 - INFO - Concurrent training is disabled
2026-02-21 11:50:00,300 - INFO - INTEGRATED MODE ENABLED: monitor de posições ativo...
2026-02-21 11:50:00,350 - INFO - Pressione Ctrl+C para parar

2026-02-21 11:50:01,000 - INFO - ════════════════════════════════════════════════════════════════
2026-02-21 11:50:01,000 - INFO - CICLO #1
2026-02-21 11:50:01,001 - INFO - H4: Starting main decision logic
2026-02-21 11:50:01,100 - INFO - Processing BTCUSDT...
2026-02-21 11:50:02,500 - INFO - Fetching 30 days of 4h data for BTCUSDT

[... sistema processando ...]

2026-02-21 11:50:15,000 - INFO - H4: BTCUSDT - Confluence: 3/14, Direction: NONE, D1: NEUTRO
2026-02-21 11:50:16,000 - INFO - H4: ETHUSDT - Confluence: 4/14, Direction: NONE, D1: NEUTRO
2026-02-21 11:50:17,000 - INFO - H4: SOLUSDT - Confluence: 2/14, Direction: NONE, D1: NEUTRO

[... mais símbolos processados ...]

2026-02-21 11:50:30,000 - INFO - Escopo de execução: 0 símbolos na whitelist
2026-02-21 11:50:30,001 - INFO - Encontradas 20 posição(ões) aberta(s) para gestão neste ciclo
2026-02-21 11:50:30,002 - INFO - Posi├º├úo em gest├úo: BROCCOLI714USDT LONG [CROSS] Margem: 4.72 USDT
[... mais posições ...]
2026-02-21 11:50:35,000 - INFO - [OK] Ciclo #1 completo - 0 posições abertas
2026-02-21 11:50:35,001 - INFO - [AGUARDANDO] Próximo ciclo em 300s...
```

**✅ SUCESSO!**
- Sistema está LIVE
- Detectou 20 posições
- Está aguardando próximo ciclo (5 min)
- Processamento normal

### 4.2 Deixar Rodando (4-24 horas)

Agora:
1. **NÃO feche esta janela**
2. **Deixe rodando**
3. **Abra OUTRA janela PowerShell** para monitoramento

---

## 🟢 PASSO 5: MONITORAMENTO PARALELO (Em nova janela)

Abra **OUTRA** aba/janela do PowerShell (primeira continua rodando):

```powershell
cd C:\repo\crypto-futures-agent
.\venv\Scripts\activate.bat

# Ver posições em tempo real a cada 5 segundos:
python main.py --mode live --monitor --monitor-interval 5
```

Isso mostra:
- Posições abertas agora
- PnL de cada uma
- Capital disponível
- Atualiza a cada 5s

### Ou ver logs:

```powershell
# Em outra aba, ver logs em tempo real:
Get-Content "logs\agent.log" -Wait -Tail 20
```

Isso mostra:
- O que sistema está fazendo
- Confluências de cada símbolo
- Qualquer erro

---

## 🔴 PASSO 6: OBSERVAR COMPORTAMENTO (Próximas 4 horas)

### O que Esperar:

#### ✅ Sinais Normais:

```
[AGUARDANDO] Próximo ciclo em 300s...           ← Normal
H4: BTCUSDT - Confluence: 3/14, Direction: NONE ← Regime NEUTRO ok
Encontradas 20 posição(ões) aberta(s)           ← Detectando tudo ok
```

#### ⚠️ Sinais de Alerta (Não críticos):

```
[AVISO] Bootstrap de SL/TP ignorado para BROCCOLI714USDT ← Normal
Whitelist: [] (vazio)                          ← Era esperado
```

#### 🚨 Sinais Críticos (PARAR Sistema):

```
ERROR - Authentication failed                   ← API key inválida
ERROR - Database locked                         ← Disco problema
ERROR - Portfolio risk exceeded 10%             ← Risco violado
Drawdown > 5%                                   ← Limite ultrapassado
Position margin > 100%                          ← Margem problema
```

Se vir **🚨 críticos** → **Ctrl+C** imediatamente!

---

## 🎯 PASSO 7: UPGRADE PARA TREINAMENTO (Após 4 horas OK)

Se após 4 horas tudo funcionou bem:

### 7.1 Parar Sistema

Na janela onde sistema está rodando:

```
Pressione: Ctrl+C

Saída esperada:
2026-02-21 15:50:00 - INFO - Operation interrupted by user
[OK] Sistema parou com segurança
```

### 7.2 Reiniciar COM Treinamento Concorrente

```powershell
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

**Saída será:**
```
2026-02-21 15:51:00,001 - INFO - STARTING OPERATION - MODE: LIVE
2026-02-21 15:51:00,050 - INFO - CONCURRENT TRAINING ENABLED: Modelos serão treinados a cada 240 minutos em paralelo
2026-02-21 15:51:00,051 - INFO - INTEGRATED MODE ENABLED: monitor de posições...
```

Agora:
- ✅ Sistema traduz a cada 5 min
- ✅ Sistema treina a cada 4 horas
- ✅ Modelo aprendendo continuamente

---

## 📊 PASSO 8: MEDIR PERFORMANCE (Próximas 24h-7 dias)

### Dia 1 Checklist:
```
✓ Capital em risco: <50% do total ($212)
✓ Drawdown: <5% ($21,20)
✓ Nenhuma trade aberta ainda (esperado)
✓ Logs: 0 erros críticos
```

### Dia 2-3 Checklist:
```
✓ Primeira confluência >7/14 gerou sinal? (SIM/NÃO)
✓ Se SIM, abertura executada com SL/TP?
✓ Se NÃO, ok - mercado ainda NEUTRO
✓ Win rate começando: >= 40%?
```

### Dia 4-7 Checklist:
```
✓ Pelo menos 3-5 trades abertos
✓ Win rate >= 50%?  (forte)
✓ Win rate >= 45%?  (ok)
✓ Win rate >= 40%?  (continuar)
✓ Win rate < 40%?   (revisar modelo)
```

### Calcular Win Rate:

```powershell
python -c "
import sqlite3, datetime
conn = sqlite3.connect('db/crypto_agent.db')
cursor = conn.cursor()

# Win rate total
cursor.execute('SELECT COUNT(*) as total, SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins FROM execution_log')
total, wins = cursor.fetchone()
if total > 0:
    print(f'Win Rate Total: {wins}/{total} = {wins/total*100:.1f}%')
else:
    print('Nenhum trade ainda')

# Win rate últimas 24h
today = datetime.date.today()
cursor.execute(f'SELECT COUNT(*) as total, SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins FROM execution_log WHERE DATE(timestamp) = \"{today}\"')
total, wins = cursor.fetchone()
if total > 0:
    print(f'Win Rate 24h: {wins}/{total} = {wins/total*100:.1f}%')
else:
    print('Nenhum trade hoje')
"
```

---

## 🚀 PASSO 9: ESCALAÇÃO (Após 1 semana sucesso)

Se após 7 dias:
- ✅ Win rate >= 55%
- ✅ Sharpe >= 0,5
- ✅ Drawdown nunca > 5%

**Então escale capital:**

### 9.1 Parar Sistema

```powershell
# Ctrl+C
```

### 9.2 Editar config

```powershell
# Abrir: config/execution_config.py
# Mudar:
# "max_margin_per_position_usd": 8.48
# Para:
# "max_margin_per_position_usd": 15

# Salvar
```

### 9.3 Reiniciar

```powershell
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 7200
```

Nova velocidade:
- Treina a cada 2 horas (mais agressivo)
- Capital por trade: $15 ao invés de $8,48
- Risco: Aumenta proporcional

---

## 📋 PASSO 10: ENCERRAMENTO SEGURO

### Quando Parar:

1. **Programado:**
   ```
   24h operação OK → (Ctrl+C)
   7 dias operação OK → Avaliar
   28 dias operação OK → Otimizar
   ```

2. **Por erro:**
   ```
   Drawdown > 5% → (Ctrl+C) imediatamente
   Erro de API → (Ctrl+C), investigar
   ```

3. **Por suspensão:**
   ```
   Windows update → (Ctrl+C) antes
   Manutenção Binance → (Ctrl+C) antes
   ```

### Parar Corretamente:

```powershell
# Na janela onde sistema roda:
Ctrl+C

# Saída esperada:
# 2026-02-21 19:30:00 - INFO - Operation interrupted by user
# 2026-02-21 19:30:01 - INFO - Training scheduler stopped
# 2026-02-21 19:30:02 - INFO - [OK] Encerramento seguro
```

⚠️ **NUNCA feche janela abruptamente!** Sempre Ctrl+C!

---

## 🎓 TABELA: O que Cada Linha de Log Significa

| Log | Significado | Ação |
|-----|-------------|------|
| `CICLO #1` | Começando novo ciclo | Observar |
| `H4: Processing BTCUSDT` | Analisando símbolo | Observar |
| `Confluence: 5/14, Direction: NONE` | Sem sinal ainda | Normal |
| `Confluence: 8/14, Direction: LONG` | ✅ SINAL! Procurando abrir | Observar risco |
| `Escopo de execução: 0 símbolos` | Nenhum na whitelist | Normal |
| `Encontradas 20 posição(ões)` | Detectou tudo certo | OK |
| `[OK] Ciclo #1 completo - 0 posições abertas` | Não abriu trade | Normal |
| `[AGUARDANDO] Próximo ciclo em 300s` | Aguardando proximamente | OK |
| `[AVISO] Bootstrap de SL/TP ignorado` | Proteção não aplicada | ⚠️ Revisar |
| `ERROR - Database locked` | 🚨 Erro crítico | PARAR |
| `Drawdown: -6% (LIMITE ULTRAPASSADO)` | 🚨 Risco violado | PARAR |

---

## 🎯 RESUMO: 10 MINUTOS DE AÇÃO

```
┌────────────────────────────────────────┐
│    COMEÇAR AGORA - QUICK START         │
└────────────────────────────────────────┘

1. PowerShell Admin → cd C:\repo\crypto-futures-agent
2. .\venv\Scripts\activate.bat
3. python main.py --mode live --integrated --integrated-interval 300
4. [Deixar rodando 4-24 horas]
5. [Após validação] Ctrl+C
6. python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
7. [Rodar indefinidamente com aprendizagem]
8. Get-Content "logs\agent.log" -Wait (acompanhar)
9. python main.py --mode live --monitor (em outra aba)
10. [Escalação após 1 semana sucesso]

════════════════════════════════════════════
✅ PRONTO! Sistema está VIVO e aprendendo!
════════════════════════════════════════════
```

🎊 **Bem-vindo à produção!**

