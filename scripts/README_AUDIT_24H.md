# 📊 Auditoria de Operações - Últimas 24 Horas

Script de auditoria integrado que consolida dados das últimas 24 horas do Agente de Trading, gerando relatórios em múltiplos formatos (console, CSV, JSON) com análise financeira, estatísticas de execução, métricas de risco e recomendações automatizadas.

## ⚡ Uso Rápido

```bash
python scripts/audit_24h_operations.py
```

**Outputs gerados:**
- `reports/audit_24h_report.json` — Relatório estruturado (JSON)
- `reports/audit_24h/executions_24h.csv` — Log de execuções (CSV)
- `reports/audit_24h/trades_24h.csv` — Histórico de trades (CSV, se existir)
- `reports/audit_24h/signals_24h.csv` — Sinais gerados (CSV, se existir)

## 📋 O Que É Auditado

### 1. **Resumo Financeiro**
- Total PnL (USDT + %)
- Count de trades (abertas + fechadas)
- Taxa de acerto (win rate)
- Maior ganho/perda
- Ganho/perda médio
- R múltiplo médio
- Expectativa matemática (positiva/negativa)

**Exemplo:**
```
Total PnL:              $      1,234.56 USDT (5.67%)
Taxa de Acerto:         45.0%
Maior Ganho:            $      234.50 USDT
Maior Perda:            $      -45.30 USDT
```

### 2. **Estatísticas de Execução**
- Total de execuções
- Taxa de sucesso vs. bloqueadas
- Execuções por modo (paper/live)
- Símbolos únicos executados
- Motivos de bloqueio (se houver)

**Exemplo:**
```
Total Execuções:        121
Sucesso:                121 (100.0%)
Bloqueadas:             0
Modo Live:              121
Símbolos Únicos:        11
```

### 3. **Análise de Risco**
- Ativações do circuit breaker
- Stop losses disparados
- Alavancagem máxima/média
- Posições em risco de liquidação

**Exemplo:**
```
Alavancagem Máxima:     5x
Alavancagem Média:      2.5x
Ativações Circuit Breaker: 0
Posições em Risco:      0
```

### 4. **Performance por Ativo** (Symbol-by-Symbol)
```
          total_pnl  trade_count  trades_fechadas  win_rate
OGUSDT       123.45           10                5     50.0%
SKRUSDT       56.78            8                4     50.0%
```

### 5. **Anomalias Detectadas**
- **Outliers de PnL** — Trades com PnL > 3σ (desvio padrão)
- **Execuções Bloqueadas** — Razões (risk_gate, max_daily_limit, etc)
- **Sinais Não-Executados** — Sinais em status PENDING ou CANCELLED
- **Alavancagem Anormal** — Leverage > 10x

**Exemplo:**
```
🚨 ANOMALIAS DETECTADAS
1. [HIGH] EXECUTIONS_BLOCKED
   5 execuções bloqueadas por 'exceeded_drawdown'
```

### 6. **Recomendações Pós-Auditoria**
Geradas automaticamente baseadas em métricas:

| Condição | Recomendação |
|----------|--------------|
| Win rate < 40% | Investigar confiança de sinais |
| Execuções bloqueadas > 5 | Revisar cooldown e limites diários |
| Expectativa negativa | Pausar operações e revisar agente |
| Circuit breaker ativado | Revisar gestão de risco |

## 📊 Formatos de Saída

### Console (Stdout)
Relatório formatado com:
- Tabelas ASCII coloridas
- Emojis para status visual
- Readability otimizada para terminal

```
================================================================================
                    AUDITORIA DE OPERAÇÕES - ÚLTIMAS 24 HORAS
================================================================================
Data/Hora: 2026-03-07T12:37:50.675375Z
Período: 2026-03-06T15:37:49.421000Z até 2026-03-07T15:37:49.421000Z
...
```

### CSV
Três arquivos separados (se houver dados):

**executions_24h.csv**
```
id,timestamp,symbol,direction,action,executed,mode,reason,order_id,...
1,2026-03-07T12:00:00Z,OGUSDT,LONG,CLOSE,1,live,Signal triggered,12345,...
```

**trades_24h.csv** (se houver trades fechadas)
```
trade_id,timestamp_entrada,symbol,direcao,entry_price,exit_price,pnl_usdt,...
1,2026-03-07T10:00:00Z,OGUSDT,LONG,150.23,152.45,45.67,...
```

**signals_24h.csv** (se houver sinais)
```
id,timestamp,symbol,direction,entry_price,stop_loss,confluence_score,...
1,2026-03-07T11:00:00Z,OGUSDT,LONG,150.00,148.50,0.85,...
```

### JSON
Estrutura completa em `reports/audit_24h_report.json`:

```json
{
  "timestamp": "2026-03-07T12:37:50.711250Z",
  "periodo_inicio": "2026-03-06T15:37:49.421000Z",
  "periodo_fim": "2026-03-07T15:37:49.421000Z",
  "metricas": {
    "financial_summary": {...},
    "execution_statistics": {...},
    "risk_metrics": {...},
    "performance_by_symbol": {...}
  },
  "anomalias": [...],
  "recomendacoes": [...],
  "dados_brutos": {
    "total_trades": 10,
    "total_executions": 121,
    "total_signals": 25,
    "total_snapshots": 450
  }
}
```

## 🔍 Como Interpretar os Resultados

### Expectativa Positiva vs. Negativa

```
Expectativa = (Taxa_Acerto × Ganho_Médio) + (Taxa_Erro × Perda_Média)
```

- **✅ POSITIVA**: E > 0 → Ganhos esperados no longo prazo
- **❌ NEGATIVA**: E ≤ 0 → Perdas esperadas, revisar estratégia

**Exemplo:**
```
Taxa Acerto: 45% → Ganho Médio: $100
Taxa Erro: 55% → Perda Média: -$80
E = (0.45 × 100) + (0.55 × -80) = 45 - 44 = +$1 ✅
```

### Tabela de Severidade de Anomalias

| Severidade | Ação |
|------------|------|
| **CRITICAL** | ⛔ Pausar operações imediatamente |
| **HIGH** | ⚠️ Revisar e corrigir hoje |
| **MEDIUM** | ⚠️ Acompanhar próximas 24h |

## 📈 Casos de Uso

### 1. **Verificação Diária**
```bash
# Rodar todo dia 23:59 UTC para revisar operações
python scripts/audit_24h_operations.py > audit_report_$(date +%Y%m%d).txt
```

### 2. **Análise em Excel**
- Baixar `reports/audit_24h/executions_24h.csv`
- Abrir em Excel e criar pivot tables personalizadas
- Filters por symbol, mode (paper/live), executed status

### 3. **Integração com BI**
```bash
# Carregar JSON em ferramentas de análise
curl http://api-bi.local/ingest < reports/audit_24h_report.json
```

### 4. **Automação via Cron/Scheduler**
```bash
# Linux systemd timer
[Unit]
Description=Agent Audit 24h
OnCalendar=daily
OnBootSec=5min

[Install]
WantedBy=timers.target
```

## ⚙️ Configuração e Customização

### Alterar Banco de Dados
```python
# Por padrão: db/crypto_agent.db
audit = AuditOperations24h(db_path="custom/path.db")
```

### Alterar Período de Tempo
Editar a classe `AuditOperations24h`:

```python
# Mudar para 7 dias (ao invés de 24h)
self.hours_24_ago_ms = self.now_ms - (7 * 24 * 60 * 60 * 1000)
```

### Adicionar Métrica Customizada
```python
# Em analyze() method
self.metrics['custom_metric'] = self.analyze_custom()

def analyze_custom(self) -> Dict[str, Any]:
    # Sua lógica aqui
    return {...}
```

## 🐛 Troubleshooting

### Erro: "Nenhuma trade encontrada"
- ✅ Normal se banco vazio ou sem operações nas últimas 24h
- Verificar: `python -c "import sqlite3; con=sqlite3.connect('db/crypto_agent.db'); cur=con.cursor(); cur.execute('SELECT COUNT(*) FROM trade_log'); print(cur.fetchone())"`

### Arquivo JSON corrompido
- Verificar encoding UTF-8
- Validar JSON: `python -m json.tool reports/audit_24h_report.json`

### Permissão negada ao criar reports/
- Criar diretório: `mkdir -p reports/audit_24h`
- Verificar permissões: `ls -l reports/`

## 📚 Referências

- **Banco de Dados**: [data/database.py](../data/database.py) — Schema completo
- **Audit Trail**: [logs/audit_trail.py](../logs/audit_trail.py) — Métodos de análise
- **Database Manager**: [logs/database_manager.py](../logs/database_manager.py) — Query layer

## 📝 Log de Mudanças

### v1.0 (2026-03-07)
- ✅ Implementação inicial
- ✅ 4 seções de análise (financeira, execução, risco, performance)
- ✅ Detecção de anomalias (outliers, execuções bloqueadas, sinais não-executados)
- ✅ Recomendações automatizadas
- ✅ Multi-formato (console, CSV, JSON)

## 🎯 Roadmap

- [ ] Integração com Telegram/Slack para alertas de críticos
- [ ] Exportação para Parquet para big data analysis
- [ ] Dashboard web em tempo real
- [ ] Comparação série temporal (dia a dia)
- [ ] Bucket de análise por horário (00:00-04:00, 04:00-08:00, etc)
- [ ] Integração com modelo de RL para feedback de reward

---

**Autor:** GitHub Copilot
**Data:** 2026-03-07
**Status:** ✅ Produção
