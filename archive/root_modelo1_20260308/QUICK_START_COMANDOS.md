# 📚 REFERÊNCIA TÉCNICA - QUICK REFERENCE

> ⚠️ **OPERADOR:** Se você quer começar, abra [COMECE_AQUI.md](COMECE_AQUI.md) (2 minutos)
>
> Este documento é para **DESENVOLVEDOR** - Lista todos os comandos possíveis.

## Cartão de Referência Rápida - Copie e Cole

---

## 1️⃣ VERIFICAÇÕES INICIAIS

### ✅ Testar conexão API
```powershell
python -c "from data.binance_client import create_binance_client; client = create_binance_client(mode='live'); print('✅ API OK')"
```

### ✅ Verificar posições abertas
```powershell
python main.py --mode live --monitor --monitor-interval 5
```

### ✅ Ver logs em tempo real
```powershell
Get-Content -Path "logs\agent.log" -Wait -Tail 30
```

---

## 2️⃣ INICIAR SISTEMA (Escolha UMA)

### 🟢 INICIANTE - Apenas LIVE (Sem Treinamento)
```powershell
python main.py --mode live --integrated --integrated-interval 300
```
**Uso:** Dias 1-4 de operação, validação inicial
**Duração:** Indefinido até Ctrl+C
**Risco:** Baixo (semaforo verde para começar)

---

### 🟡 INTERMEDIÁRIO - LIVE + Treinamento a Cada 4 Horas
```powershell
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```
**Uso:** A partir do dia 2-3 (após validação)
**Duração:** Indefinido até Ctrl+C
**Risco:** Médio (otimização contínua)

---

### 🔴 AVANÇADO - LIVE + Treinamento Cada 2 Horas
```powershell
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 7200
```
**Uso:** Depois de 1 semana com sucesso
**Duração:** Indefinido até Ctrl+C
**Risco:** Alto (mais agressivo, mais aprendizado)

---

### 🔵 TESTE - Paper Mode (Sem Capital Real)
```powershell
python main.py --mode paper --integrated --integrated-interval 300 --concurrent-training --training-interval 3600
```
**Uso:** Validação antes de ir LIVE
**Duração:** Indefinido até Ctrl+C
**Risco:** ZERO (simulado)

---

## 3️⃣ OPERAÇÕES ADICIONAIS

### 📊 Apenas Monitoramento (Ver Posições)
```powershell
python main.py --mode live --monitor --monitor-interval 5
```
Atualiza a cada 5 segundos. Pressione Ctrl+C para sair.

---

### 🛠️ Setup Inicial (Coletar Dados Históricos)
```powershell
python main.py --setup
```
Executa UMA VEZ no início (30-60 min). Collect 30 dias dados para cada símbolo.

---

### 🤖 Treinar Modelo Manualmente
```powershell
python main.py --train
```
Executa UMA VEZ quando quiser reforçar o modelo (~2 horas).

---

### 📈 Backtest Histórico (Validar Estratégia)
```powershell
python main.py --backtest --start-date 2026-01-01 --end-date 2026-02-20
```
Simula trading em dados históricos. Mostra performance.

---

### 🏥 Testar Pipeline (Sem Binance)
```powershell
python main.py --dry-run
```
Validação sintética do código. Sem API keys necessárias.

---

## 4️⃣ ADOTAR POSIÇÃO JÁ ABERTA

Se há posição aberta na Binance que quer gerenciar:

```powershell
# Exemplo: Adotar BTCUSDT já aberto
python main.py --mode live --adopt-position BTCUSDT
```

Isso:
1. Detecta a posição
2. Cria SL/TP de proteção automático
3. Inicia monitoramento contínuo

---

## 5️⃣ PARÂMETROS DE CUSTOMIZAÇÃO

### Intervalo de Decisão (Trading Loop)
```powershell
--integrated-interval 60    # Decidir a cada 1 minuto (rápido)
--integrated-interval 300   # Decidir a cada 5 minutos (normal) ← RECOMENDADO
--integrated-interval 600   # Decidir a cada 10 minutos (calmo)
```

### Intervalo de Treinamento
```powershell
--training-interval 3600    # Treinar a cada 1 hora (muito frequente)
--training-interval 7200    # Treinar a cada 2 horas (frequente)
--training-interval 14400   # Treinar a cada 4 horas (recomendado) ← PADRÃO
--training-interval 28800   # Treinar a cada 8 horas (raro)
--training-interval 86400   # Treinar uma vez por dia (conservador)
```

### Combinação Recomendada
```powershell
python main.py \
  --mode live \
  --integrated \
  --integrated-interval 300 \
  --concurrent-training \
  --training-interval 14400
```

---

## 6️⃣ MONITORAMENTO PARALELO

Enquanto sistema está rodando em UMA janela, abrir OUTRA:

```powershell
# Janela 1: Sistema rodando (não mexer)
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400

# Janela 2: Abrir nova aba PowerShell
cd C:\repo\crypto-futures-agent

# Ver posições:
python main.py --mode live --monitor --monitor-interval 5

# Ou ver logs:
Get-Content -Path "logs\agent.log" -Wait -Tail 30
```

---

## 7️⃣ PARAR SISTEMA COM SEGURANÇA

```powershell
# Pressionar na janela onde sistema roda:
Ctrl+C

# Esperado:
# 2026-02-21 10:00:00 - INFO - Operation interrupted by user
# 2026-02-21 10:00:01 - INFO - Training scheduler stopped
# 2026-02-21 10:00:02 - INFO - Encerramento seguro completo
```

⚠️ **NUNCA feche a janela abruptamente!** Sempre Ctrl+C para salvar dados.

---

## 8️⃣ ESCALAÇÃO DE CAPITAL

Após uma semana com WIN RATE >55%:

```powershell
# 1. Parar sistema (Ctrl+C)

# 2. Editar arquivo:
# config/execution_config.py
# Trocar: "max_margin_per_position_usd": 8.48
# Por: "max_margin_per_position_usd": 15

# 3. Reiniciar:
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

---

## 9️⃣ DIAGNÓSTICO RÁPIDO

### Se não abre trades:

```powershell
# A. Ver configuração:
python -c "from config.execution_config import EXECUTION_CONFIG; print(EXECUTION_CONFIG)"

# B. Ver whitelist:
python -c "from config.execution_config import EXECUTION_CONFIG; print(EXECUTION_CONFIG.get('whitelist', []))"

# C. Ver confiança mínima:
python -c "from config.execution_config import EXECUTION_CONFIG; print(f'Min confidence: {EXECUTION_CONFIG.get(\"min_confidence\", 0.7)}')"

# D. Ver último log de erro:
Get-Content -Path "logs\agent.log" -Tail 50 | Where-Object {$_ -like "*ERROR*"}
```

### Se treino não executa:

```powershell
# A. Verifica se modelo existe:
ls models/ | Where-Object {$_.Name -like "*final*"}

# B. Checa disco livre:
Get-Volume

# C. Vê erros de treino:
Get-Content -Path "logs\agent.log" | Where-Object {$_ -like "*training*"}
```

---

## 🔟 ATALHOS DE POWER USER

### Reiniciar após erro de API:
```powershell
# Ctrl+C, espera 10s, depois:
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

### Resetar logs (limpar arquivo antigo):
```powershell
# PowerShell Admin:
Remove-Item logs\agent.log
# Sistema recria ao iniciar
```

### Ver última trade executada:
```powershell
python -c "
import sqlite3
conn = sqlite3.connect('db/crypto_agent.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM execution_log ORDER BY timestamp DESC LIMIT 1')
print(cursor.fetchone())
"
```

### Ver win rate do dia:
```powershell
python -c "
import sqlite3, datetime
conn = sqlite3.connect('db/crypto_agent.db')
cursor = conn.cursor()
today = datetime.date.today()
cursor.execute(f'SELECT COUNT(*) as total, SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins FROM execution_log WHERE DATE(timestamp) = \"{today}\"')
total, wins = cursor.fetchone()
print(f'Hoje: {wins}/{total} vitórias ({wins/total*100:.1f}%)' if total > 0 else 'Nenhum trade hoje')
"
```

---

## 📋 CHECKLIST PRÉ-OPERAÇÃO (2 MIN)

```
□ PowerShell aberto em C:\repo\crypto-futures-agent
□ Ambiente virtual ativado: .\venv\Scripts\activate.bat
□ Arquivo .env existe com credenciais
□ Database existe: db/crypto_agent.db
□ Modelo existe: models/crypto_agent_ppo_final.zip
□ API conecta: python -c "from data.binance_client import create_binance_client; create_binance_client(mode='live')"
□ Posições detectadas: python main.py --mode live --monitor (vê 20 posições)
□ Capital configurado em config/execution_config.py
□ Pronto! Execute comando de início
```

---

## 🎯 COMANDO FINAL (COPIAR E COLAR)

```powershell
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```

**PRONTO! Sistema vai:**
- ✅ Operar com capital REAL
- ✅ Monitorar 20 posições abertas
- ✅ Gerar sinais a cada 5 minutos
- ✅ Treinar modelo a cada 4 horas
- ✅ Aprender continuamente
- ✅ Proteger com risk management inviolável

🚀 **BOA SORTE!**

