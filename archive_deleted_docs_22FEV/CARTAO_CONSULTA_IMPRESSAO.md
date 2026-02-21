# � REFERÊNCIA TÉCNICA - CARTÃO DE CONSULTA

> ⚠️ **OPERADOR:** Se você quer começar, abra [COMECE_AQUI.md](COMECE_AQUI.md) (2 minutos)
>
> Use este documento como referência impressa para **DESENVOLVEDOR** que fica perto do computador.

---

## ⚡ 5 COMANDOS ESSENCIAIS

### 1️⃣ COMEÇAR (Primeira Vez)
```
python main.py --mode live --integrated --integrated-interval 300
```
**Quando:** Dias 1-4
**Duração:** Deixe rodando
**Risco:** Médio (sem treino)

---

### 2️⃣ PRODUÇÃO COMPLETA (Após 4h validação)
```
python main.py --mode live --integrated --integrated-interval 300 --concurrent-training --training-interval 14400
```
**Quando:** Dia 1+ (após validar)
**Duração:** Deixe rodando
**Risco:** Médio-Alto (com treino 4h)

---

### 3️⃣ VER POSIÇÕES AGORA
```
python main.py --mode live --monitor --monitor-interval 5
```
**Quando:** Anytime
**Duração:** Até Ctrl+C
**Risco:** ZERO (apenas monitoramento)

---

### 4️⃣ VER LOGS AGORA
```
Get-Content "logs\agent.log" -Wait -Tail 30
```
**Quando:** Em outra janela
**Duração:** Até Ctrl+C
**Risco:** ZERO

---

### 5️⃣ TESTE SEM RISCO
```
python main.py --mode paper --integrated --integrated-interval 300
```
**Quando:** Validação antes de usar real
**Duração:** Até Ctrl+C
**Risco:** ZERO (simula)

---

## ✅ PRÉ-VOO (2 MINUTOS)

```
□ PowerShell aberto: cd C:\repo\crypto-futures-agent
□ Venv ativado: .\venv\Scripts\activate.bat
□ API key válida: python -c "from data.binance_client import create_binance_client; create_binance_client(mode='live')"
□ Posições detectadas: python main.py --mode live --monitor (vê 20 posições?)
□ Modelo existe: ls models/crypto* (vê arquivo .zip?)
□ Database existe: ls db/ (vê crypto*.db?)

✅ SUCESSO = Todas as caixas marcadas!
```

---

## 🎯 FLUXO DO DIA

```
MANHÃ (T+0h):
├─ Executar Comando #1 ou #2
└─ Deixar rodando (não mexer!)

TARDE (T+4h):
├─ Ver posições (Comando #3)
├─ Ver logs (Comando #4)
└─ Validar: Nenhum erro? Sucesso? → Continuar

NOITE (T+24h):
├─ Calcular win rate
├─ Se >55%: considerar escalar capital
└─ Se <45%: revisar modelo

AMANHÃ+:
├─ Deixar rodando
├─ Monitorar 2x dia
└─ Escalar conforme performance
```

---

## 📊 MÉTRICAS RÁPIDAS

### Hoje:
```powershell
python -c "
import sqlite3, datetime
conn = sqlite3.connect('db/crypto_agent.db')
cursor = conn.cursor()
today = datetime.date.today()
cursor.execute(f'SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) FROM execution_log WHERE DATE(timestamp)=\"{today}\"')
total, wins = cursor.fetchone()
print(f'{wins or 0}/{total or 0} vitórias ({(wins or 0)/(total or 1)*100:.0f}%)' if total else 'Sem trades')
"
```

### Tudo:
```powershell
python -c "
import sqlite3
conn = sqlite3.connect('db/crypto_agent.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(pnl) FROM execution_log')
total, wins, pnl = cursor.fetchone()
print(f'Total: {total or 0} trades | Win Rate: {(wins or 0)/(total or 1)*100:.0f}% | PnL: ${pnl or 0:.2f}')
"
```

---

## 🚨 ERROS COMUNS

| Erro | Solução |
|------|---------|
| `API Key Inválida` | Verificar `.env` |
| `No Module Named` | `pip install -r requirements.txt` |
| `Database locked` | Parar outros processos Python |
| `Model not found` | `python main.py --train` |
| `Nenhum trade` | Concordância >7/14 não atingida (normal) |
| `Drawdown >5%` | ⚠️ PARAR (`Ctrl+C`) imediatamente |

---

## 🔄 PARAR SISTEMA

```
Na janela que roda o comando principal:

Pressione: Ctrl+C

Resultado:
✅ Sistema salva estado
✅ Modelo salvo
✅ Posições não vendidas (apenas monitoradas)
✅ Safe shutdown
```

---

## 📈 DEPOIS DA PRIMEIRA SEMANA

**Se Win Rate ≥55%:**
1. Ctrl+C (parar)
2. Editar: `config/execution_config.py`
3. Mudar: `max_margin_per_position_usd` de 8.48 → 15
4. Reiniciar com Comando #2
5. Monitorar 7 dias mais

**Se Win Rate <50%:**
1. Deixar rodando
2. Aguardar 7 dias mais
3. Se ainda <50%: `python main.py --train` (retreinar)

---

## 📞 SUPORTE RÁPIDO

### "Não abre trades"
→ Confluence <7/14? (Normal! Mercado NEUTRO)

### "Recebo erro de API"
→ Verificar `.env` BINANCE_API_KEY

### "Sistema está lento"
→ Aumentar `--integrated-interval` de 300 → 600

### "Quero treinar mais"
→ Reduzir `--training-interval` de 14400 → 7200

### "Recebi liquidação aviso"
→ ⚠️ PARAR com Ctrl+C, revisar capital

---

## 🎯 REFERÊNCIA RÁPIDA - PARÂMETROS

```
--mode live                    = Capital REAL (viver ou morrer!)
--mode paper                   = Simula (sem risco)
--integrated                   = Monitora posições abertas
--integrated-interval 300      = Decisão a cada 5 min (padrão)
--integrated-interval 180      = Decisão a cada 3 min (rápido)
--integrated-interval 600      = Decisão a cada 10 min (lento)
--concurrent-training          = Treina modelo em paralelo
--training-interval 14400      = Treina a cada 4 horas (padrão)
--training-interval 7200       = Treina a cada 2 horas (agressivo)
--training-interval 28800      = Treina a cada 8 horas (conservador)
```

---

## 📋 CHECKLIST SEMANAL

### Dia 1 ✓
- [ ] Sistema roda sem erro
- [ ] Detecta 20 posições
- [ ] Logs sem WARNING crítico
- [ ] Capital dentro do limite

### Dias 2-3 ✓
- [ ] Primeiro ciclo de treinamento rodou
- [ ] Pelo menos 1 sinal gerado
- [ ] Win rate >40%

### Dias 4-7 ✓
- [ ] 3+ trades abertos
- [ ] Win rate >50%
- [ ] Drawdown <5%
- [ ] Sharpe >0,3

### Semana 2+ ✓
- [ ] Win rate >55%
- [ ] Considerar escalar capital
- [ ] Modelo aprimorado
- [ ] Curva de lucro subindo

---

## 🎬 PRÓXIMO PASSO

```
1. Copie Comando #1 ↑
2. Cole no PowerShell
3. Pressione Enter
4. Deixe rodando
5. Volte em 4 horas

════════════════════════════════
✅ Sistema vivo & aprendendo!
════════════════════════════════
```

---

**Última atualização:** 21 de Fevereiro, 2026
**Versão Sistema:** 1.0 (LIVE + RL + Risk Management)

