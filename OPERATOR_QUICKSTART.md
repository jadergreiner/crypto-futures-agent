# ⚡ Quick Start — Operador

## Passo 1: Iniciar

```bash
.\iniciar.bat
```

---

## Passo 2: Escolher Modo

| Opção | Modo | Risco | Tempo |
|-------|------|-------|-------|
| **1** | Paper (Simulação) | ✅ Nulo | Imediato |
| **2** | Live (Real) | ⚠️ Alto | Imediato |
| **3** | Monitor | ✅ Nulo | Contínuo |
| **4** | Backtest | ✅ Nulo | 10-30 min |
| **5** | Treinar | ✅ Nulo | 4-7 horas |
| **6** | Setup | ✅ Nulo | 15-30 min |
| **7** | Diagnóstico | ✅ Nulo | 2-3 min |
| **8** | Assumir Posição | ⚠️ Médio | Contínuo |
| **9** | Sair | — | — |

---

## Fluxo Recomendado (Primeira Vez)

```
1. Executar Setup (Opção 6)
   ↓
2. Executar Backtest (Opção 4)
   ↓
3. Treinar Modelo (Opção 5)
   ↓
4. Paper Trading (Opção 1)
   ↓
5. Live (Opção 2) — APENAS se satisfeito
```

---

## Fluxo Operacional (Diário)

```
Manhã:    Paper Trading (Opção 1) — 1-2 horas
Tarde:    Monitorar Posições (Opção 3) — Contínuo (se houver trades abertos)
Noite:    Revisar Logs (logs/agent.log)

MELHORADO COM TREINO CONCORRENTE:
├─ Live (Opção 2 + Treino) — Treina modelos a cada 4-6 horas automaticamente
├─ Monitor (Opção 3) — Acompanhar trades sem interrupção
└─ Backtest (Opção 4) — Validar melhorias semanalmente
```

---

## Atalhos de Comando Rápido

### Revisar última execução
```bash
Get-Content logs/agent.log -Tail 20
```

### Buscar erros
```bash
Select-String "ERRO|ERROR" logs/agent.log
```

### Diagnosticar (sem menu)
```bash
python main.py --test-connection
```

---

## 🚨 Situações Críticas

### ❌ Sistema Offline

1. Opção 7 → Diagnosticar
2. Se falhar, verifique `.env`
3. Se ainda falhar: `setup.bat`

### ❌ Trade em Risco

1. Opção 3 → Monitor posição
2. Opção 8 → Assumir e ajustar stops

### ❌ Modelo Ruim

1. Opção 5 → Treinar novamente
2. Opção 4 → Backtest antes de usar

---

## ✅ Check List Segurança

Antes de usar **Opção 2 (Live)**:

- [ ] Revisei `.env` e confirmei credenciais  
- [ ] Fiz backtest em últimos 90 dias (Opção 4)  
- [ ] Testei paper trading (Opção 1) por 1+ hora  
- [ ] Revisei logs recentes (logs/agent.log)  
- [ ] Confirmei montante de capital  
- [ ] Lembrei de 3 confirmações obrigatórias no menu  

---

## 📊 Métricas de Performance

**Paper Trading (verificar a cada dia):**
- Win Rate: ≥ 40%
- Profit Factor: ≥ 1.5
- Sharpe Ratio: ≥ 1.0
- Max Drawdown: ≤ 15%

Se alguma métrica estiver baixa → Treinar novamente (Opção 5)

---

## 📞 Suporte Rápido

| Problema | Solução |
|----------|---------|
| "Venv não encontrado" | `setup.bat` |
| ".env não encontrado" | Copie `.env.example` → `.env` |
| "BD não encontrado" | Opção 6 (Setup) |
| "Binance offline" | Opção 7 (Diagnóstico) |
| "Modelo ruim" | Opção 5 (Treinar) |
| "Quer revisar?" | Opção 4 (Backtest) |

---

**Criado em:** 20/02/2026  
**Status:** ✅ Pronto para operação  
**Próximo passo:** `.\iniciar.bat`
