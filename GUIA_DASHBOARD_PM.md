# 🎯 GUIA RÁPIDO — Dashboard Auto-Sincronizado

**Gerente de Projetos:** Seu dashboard de projeto está pronto para uso em tempo real.

---

## ⚡ Início Rápido

### 1️⃣ Abrir Dashboard
```bash
# Windows
Start-Process "dashboard_projeto.html"

# Ou acesse via navegador
# file:///c:/repo/crypto-futures-agent/dashboard_projeto.html
```

### 2️⃣ Dashboard Atualiza Automaticamente
- ✅ Carrega novos dados a cada **30 segundos**
- ✅ Sem necessidade de apertar F5 (refresh)
- ✅ Equipada com **Doc Advocate** para fluxo de documentação

### 3️⃣ Sincronizar Dados Manualmente
```bash
cd c:\repo\crypto-futures-agent
python update_dashboard.py
```

---

## 📊 O Que Você Verifica

O dashboard mostra em tempo real:

| Elemento | Atualização | Fonte |
|----------|------------|-------|
| **Métricas Backtest** | 30s | `docs/STATUS_ATUAL.md` |
| **Decisões de Board** | 30s | `docs/DECISIONS.md` |
| **Timeline** | 30s | Hardcoded (planning) |
| **Equipe + Doc Advocate** | 30s | `docs/DECISIONS.md` |
| **Milestones** | Manual | `docs/ROADMAP.md` |
| **Gráficos** | 30s | `dashboard_data.json` |

---

## 🔄 Como Funciona a Sincronização

```
1. Documentação Markdown muda (ex: STATUS_ATUAL.md)
   ↓
2. Você executa: python update_dashboard.py
   (ou espera por GitHub Actions se commitou)
   ↓
3. dashboard_data.json é atualizado
   ↓
4. Dashboard HTML carrega novos dados a cada 30s
   ↓
5. Você vê visualização em tempo real
```

---

## 👥 Doc Advocate — Novo Membro da Equipe

O **Doc Advocate** está incluído no dashboard com responsabilidades de:

- 🔄 **Sincronização:** Executar `update_dashboard.py` após mudanças de docs
- 📖 **Monitoramento:** Garantir que STATUS_ATUAL.md e DECISIONS.md estão atualizados
- ✅ **Validação:** Confirmar protocolo [SYNC] em commits
- 🎯 **Fluxo:** Integrar documentação no processo de decisão

**Onde ver**: Seção "👥 Equipe & Responsabilidades" no dashboard

---

## 📈 Exemplo: Você Atualiza uma Decisão

### Cenário
Decision #2 (ML) foi votada e aprovada.

### Passo-a-Passo

**1. Atualizar documentação:**
```markdown
# docs/DECISIONS.md

## 🔔 DECISÃO #2 — MACHINE LEARNING

**Status:** ✅ APROVADO (Option C - Híbrido 3-4d)
**Votação:** 23 FEV 2026
```

**2. Commit com [SYNC] tag:**
```bash
git add docs/DECISIONS.md
git commit -m "[SYNC] Decision #2 aprovada - Option C (Híbrido) selecionada"
git push
```

**3. GitHub Actions sincroniza automaticamente:**
- Detecta mudança em `docs/DECISIONS.md`
- Executa `update_dashboard.py`
- Atualiza `dashboard_data.json`
- Faz commit automático

**4. Você abre dashboard:**
- Vê Decision #2 como "APROVADO"
- Equipe com Doc Advocate renderizada
- Timeline atualizada

---

## ⚙️ Configuração

### Sincronização Manual (Sempre Funciona)
```bash
python update_dashboard.py
```

### GitHub Actions (Automático ao Push)
☑️ Já configurado em `.github/workflows/dashboard-sync.yml`
- Dispara quando: `push` em `docs/**`
- Atualiza: `dashboard_data.json`
- Commit: Automático com tag `[SYNC]`

### Agendamento (Opcional)

**Windows — Task Scheduler:**
```bash
# Run PowerShell como Admin:
schtasks /create /tn "DashboardSync" /tr "python C:\repo\crypto-futures-agent\update_dashboard.py" /sc minute /mo 5
```

**Linux/Mac — Cron:**
```bash
crontab -e
# Adicionar: */5 * * * * cd /path/to/project && python update_dashboard.py
```

---

## 🚀 Recurso: Relatório de Sincronização

Após cada execução, você vê:

```
✅ Dashboard sincronizado com sucesso!
📁 Arquivo: dashboard_data.json
🕐 Atualizado: 2026-02-21T13:03:29.321695

📊 DASHBOARD SYNC REPORT
═════════════════════════════════════════
Versão: v0.4
Status: BLOQUEADO
Atualizado: 2026-02-21T13:03:29Z
Membros equipe: 7 (com Doc Advocate ✓)
Milestones: 7
Decisões: 3
Bloqueadores: 3
═════════════════════════════════════════
```

---

## ❓ FAQ

### P: Preciso dar refresh no navegador?
**R:** NÃO! Dashboard auto-carrega a cada 30s. Deixe aberto e volte a verificar.

### P: Como garantir que dados são sempre atualizados?
**R:** Use GitHub Actions (automático) ou execute `python update_dashboard.py` em intervalo regular.

### P: Onde ver quando foi a última sincronização?
**R:** Footer do dashboard mostra timestamp e próxima atualização (~30s)

### P: Doc Advocate faz... o quê exatamente?
**R:** Mantém `dashboard_data.json` sincronizado com documentação. Você executa o script ou GitHub Actions faz automaticamente.

### P: Posso customizar frequência de atualização?
**R:** Sim! No `dashboard_projeto.html`, mude `REFRESH_INTERVAL`:
```javascript
const REFRESH_INTERVAL = 30000; // 30 segundos (edite aqui)
```

---

## 🎯 Recomendação Final

### Para você (Gerente de Projetos):
1. ✅ Abra `dashboard_projeto.html` e deixe aberto todo dia
2. ✅ Quando houver mudanças de docs, execute: `python update_dashboard.py`
3. ✅ Compartilhe link do dashboard com equipe
4. ✅ Dashboard atualiza em tempo real — você fica ciente de mudanças

### Para a equipe:
1. ✅ Mude `docs/STATUS_ATUAL.md` → Sincronização automática
2. ✅ Mude `docs/DECISIONS.md` → GitHub Actions atualiza dashboard
3. ✅ Use tag `[SYNC]` em commits de documentação
4. ✅ Doc Advocate garante integridade

---

**Dashboard criado:** 23 FEV 2026  
**Próxima sincronização:** A cada 30s (automático)  
**Comando:** `python update_dashboard.py`  
**Status:** 🟢 ATIVO
