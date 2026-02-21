# 📊 Dashboard Auto-Sincronização

## 🎯 Visão Geral

O Dashboard do Projeto foi configurado com **sincronização automática bidirecional**:

- **Dashboard HTML** → Carrega dados de `dashboard_data.json` a cada 30 segundos
- **Script Python** → Sincroniza `dashboard_data.json` com documentação oficial (STATUS_ATUAL.md, DECISIONS.md, etc.)
- **Doc Advocate** → Fluxo de documentação incluído na equipe

---

## 📁 Componentes

### 1. **dashboard_projeto.html**
Página web interativa com:
- ✅ Gráficos em tempo real (Chart.js)
- ✅ Auto-refresh a cada 30 segundos
- ✅ Carrega dados de `dashboard_data.json` dinamicamente
- ✅ Inclui equipe com **Doc Advocate**

**Como abrir:**
```bash
# Windows — Duplo clique ou:
Start-Process "c:\repo\crypto-futures-agent\dashboard_projeto.html"

# Ou servir via HTTP:
python -m http.server 8000
# Depois: http://localhost:8000/dashboard_projeto.html
```

### 2. **dashboard_data.json**
Arquivo JSON centralizado com:
- Status do projeto
- Milestones e versões
- Decisões de board
- Bloqueadores críticos
- Métricas de backtest
- Timeline
- Equipe (com Doc Advocate)
- Componentes

**Estrutura:**
```json
{
  "project": { ... },
  "status_cards": [ ... ],
  "milestones": [ ... ],
  "decisions": [ ... ],
  "blockers": [ ... ],
  "metrics": [ ... ],
  "timeline": [ ... ],
  "team": [ ... ],
  "components": [ ... ]
}
```

### 3. **update_dashboard.py**
Script Python que sincroniza dados automaticamente:
- Lee `docs/STATUS_ATUAL.md` → Extrai métricas
- Lee `docs/DECISIONS.md` → Extrai decisões
- Atualiza `dashboard_data.json` com dados mais recentes
- Inclui **Doc Advocate** na equipe

---

## 🔄 Como Funciona a Auto-Sincronização

```
┌─────────────────────────────────────────────────┐
│        Documentação Oficial (Markdown)            │
│  ├─ docs/STATUS_ATUAL.md                        │
│  ├─ docs/DECISIONS.md                           │
│  ├─ docs/ROADMAP.md                             │
│  └─ docs/SYNCHRONIZATION.md                     │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓ (Python extrai dados)
┌──────────────────────────────────────────────────┐
│        dashboard_data.json (Centralizado)        │
│  ├─ Métricas                                    │
│  ├─ Decisões                                    │
│  ├─ Timeline                                    │
│  ├─ Equipe (com Doc Advocate)                   │
│  └─ Status                                      │
└──────────────────┬───────────────────────────────┘
                   │
                   ↓ (JavaScript carrega a cada 30s)
┌──────────────────────────────────────────────────┐
│      Dashboard HTML (Visualização em Tempo Real)  │
│  ├─ Gráficos atualizados                        │
│  ├─ Equipe renderizada dinamicamente            │
│  ├─ Timestamp refleito atualização              │
│  └─ Próxima sincronização: ~30s                 │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Configuração Necessária

### Pré-requisitos
- Python 3.7+
- Navegador moderno (Chrome, Firefox, Edge)

### Instalação
```bash
# 1. Os arquivos já estão na pasta:
ls -la dashboard_*.{html,json}
ls -la update_dashboard.py

# 2. Nenhuma dependência externa necessária!
# (O script usa apenas bibliotecas padrão Python)
```

---

## 📋 Uso

### Opção A: Auto-Sincronização Manual Periódica

Execute o script Python periodicamente (ex: via cron, task scheduler, etc.):

```bash
# Executar sincronização UMA VEZ
python update_dashboard.py

# Saída esperada:
# 🔄 Sincronizando Dashboard...
# 📊 Extraindo métricas de STATUS_ATUAL.md...
# ✅ 6 métricas atualizadas
# 🎯 Extraindo decisões de DECISIONS.md...
# ✅ 3 decisões atualizadas
# 👥 Atualizando equipe com Doc Advocate...
# ✅ Equipe atualizada (7 membros)
# ✅ Dashboard sincronizado com sucesso!
```

### Opção B: Agendar Sincronização Automática

#### **Windows (Task Scheduler)**
```batch
# Criar tarefa que executa a cada 5 minutos:
schtasks /create /tn "CryptoFuturesAgent-DashboardSync" /tr "python c:\repo\crypto-futures-agent\update_dashboard.py" /sc minute /mo 5
```

#### **Linux/macOS (Cron)**
```bash
# Editar crontab:
crontab -e

# Adicionar linha (a cada 5 minutos):
*/5 * * * * cd /path/to/crypto-futures-agent && python update_dashboard.py
```

### Opção C: Sincronização em Tempo Real (Recomendado)

Use um monitor de arquivos para sincronizar quando a documentação muda:

```bash
# Com watchdog (Python):
pip install watchdog

# Script de monitoramento:
python -c "
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

class DocsChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            print(f'📝 Documento modificado: {event.src_path}')
            subprocess.run(['python', 'update_dashboard.py'])

observer = Observer()
observer.schedule(DocsChangeHandler(), 'docs', recursive=True)
observer.start()
print('👁️  Monitorando docs/ para mudanças...')
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
"
```

---

## 👥 Doc Advocate — Novo Membro da Equipe

O **Doc Advocate** foi adicionado ao fluxo de equipe para:

1. **Manter Sincronização:** Garante que `dashboard_data.json` reflete documentação oficial
2. **Validar Protocolo [SYNC]:** Confirma que commits incluem tag `[SYNC]` quando há mudanças de docs
3. **Monitorar Integridade:** Verifica que STATUS_ATUAL.md, DECISIONS.md estão atualizados
4. **Fluxo de Documentação:** Integra-se ao processo de atualização contínua

**Responsabilidades Doc Advocate:**
- ✅ Executar `update_dashboard.py` após cada mudança em `/docs/`
- ✅ Validar que `dashboard_data.json` reflete estado atual
- ✅ Confirmar que equipe é renderizada corretamente no dashboard
- ✅ Monitorar próxima sincronização (timestamp no footer)

---

## 📊 Exemplo de Fluxo Completo

### Cenário: Engenheiro ML decide Option C

**1. Executar decisão**
```markdown
# docs/DECISIONS.md
## 🔔 DECISÃO #2 — MACHINE LEARNING

**Status:** IN PROGRESS
```

**2. Doc Advocate sincroniza**
```bash
python update_dashboard.py
# ✅ Decision #2 status atualizado em dashboard_data.json
```

**3. Dashboard carrega automaticamente**
```javascript
// A cada 30s:
fetch('dashboard_data.json?t=' + Date.now())
// ✅ Decision #2 mostra "IN PROGRESS" no board
```

**4. Investidor visualiza em tempo real**
```
Dashboard HTML → mostra Decision #2 atualizada
(sem necessidade de hard refresh)
```

---

## 🔧 Troubleshooting

### Problema: Dashboard não atualiza
**Solução:**
1. Abra Console (F12 → Console)
2. Verifique log: `Dashboard Auto-Sync Ativo: ...`
3. Confirme que `dashboard_data.json` existe na pasta de projeto
4. Execute `python update_dashboard.py` manualmente

### Problema: Dados não sincronizam
**Solução:**
1. Verifique se `docs/STATUS_ATUAL.md` existe
2. Verifique se `docs/DECISIONS.md` existe
3. Execute: `python update_dashboard.py` com output detalhado
4. Confirme que JSON é válido: `python -m json.tool dashboard_data.json`

### Problema: Equipe não mostra Doc Advocate
**Solução:**
1. Verifique se `update_dashboard.py` foi executado
2. Abra `dashboard_data.json` e procure por "Doc Advocate"
3. Hard refresh dashboard: `Ctrl+Shift+R` (Chrome) ou `Cmd+Shift+R` (Mac)
4. Verifique Console para erros de JavaScript

---

## 📈 Próximos Passos

1. **Ativar sincronização automatizada:**
   ```bash
   python update_dashboard.py  # Teste manual
   # Depois agendar via cron/Task Scheduler
   ```

2. **Integrar com CI/CD (GitHub Actions):**
   ```yaml
   # .github/workflows/update-dashboard.yml
   name: Update Dashboard
   on:
     push:
       paths:
         - 'docs/**'
   jobs:
     update:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - run: python update_dashboard.py
         - run: git add dashboard_data.json
         - run: git commit -m "[SYNC] Dashboard atualizado"
         - run: git push
   ```

3. **Monitorar em tempo real:**
   - Use ferramentas como `watchdog` para sincronização automática de arquivo
   - Implemente webhook para atualizar dashboard em eventos

---

## 📞 Suporte

- **Doc Advocate:** Responsável por sincronização e integridade
- **Facilitador:** Orquestração de decisões e documentação
- **Comando de teste:** `python update_dashboard.py --verbose`

---

**Dashboard criado em:** 23 FEV 2026
**Última sincronização:** Run `python update_dashboard.py` para atualizar
