# Framework de Validação de Integridade e Sincronização de Docs

**Status:** Operacional (2026-03-07)
**Versão:** 1.0
**Responsável:** Database Architecture Board + Documentation Sync Team

---

## Visão Geral

Este framework implementa **2 triggers automáticos** que garantem:

1. **Validação de Integridade:** Sempre que uma tarefa de backlog é
   solicitada, valida o estado do database
2. **Sincronização de Docs:** Sempre que uma tarefa é entregue, atualiza
   documentação e valida consistência

## Trigger 1: Validação de Integridade (Pre-Backlog)

### Finalidade

Validar saúde do database antes de aceitar nova tarefa, prevenindo que
tarefas sejam assignadas em condições de desincronização crítica.

### Como Usar

```bash
cd /path/to/crypto-futures-agent
python scripts/hooks/validate_integrity_on_backlog_task.py \
  --backlog-item "US-001" \
  --affected-modules "position_monitor.py,order_executor.py" \
  --output-json reports/integrity_check_US-001.json
```

### Parâmetros

- `--backlog-item`: ID da tarefa (ex: `F-12`, `US-001`)
- `--affected-modules`: Módulos afetados (CSV, ex: `position_monitor.py,risk_gate.py`)
- `--output-json`: Arquivo para salvar relatório (opcional)

### Saída Esperada

```
[INFO] ======================================================================
[INFO] VALIDAÇÃO DE INTEGRIDADE - US-001
[INFO] ======================================================================
[INFO] Status: PASS
[INFO] Orfãos: 0
[INFO] Stales: 0
[INFO] PnL Missing: 0
[INFO] ======================================================================
[INFO] Recomendação: ACEITAR: Database em condição operacional saudável.
[INFO] ======================================================================
```

### Critérios de Aprovação

| Métrica | PASS | FAIL |
|---------|------|------|
| Execuções órfãs | 0 | > 0 |
| Trades obsoletas (>30d) | 0 | > 0 |
| PnL faltando | 0 | > 0 |
| Integridade BD | OK | ERRO |

### Recomendações por Cenário

| Cenário | Status | Ação |
|---------|--------|------|
| Nenhum problema | PASS | ✅ Aceitar tarefa |
| < 10 órfãos | WARNING | ⚠️ Aceitar com monitoramento |
| > 1 trade obsoleta | FAIL | 🔴 Bloquear, limpar primeiro |
| > 0 PnL missing | FAIL | 🔴 Bloquear, auditoria obrigatória |

## Trigger 2: Sincronização de Documentação (Post-Delivery)

### Finalidade

Após entregar tarefa, validar que:
1. Documentação foi atualizada
2. Links cruzados ainda são válidos
3. Exemplos de código em docs estão sincronizados
4. Lint Markdown (máx 80 chars) está ok

### Como Usar

```bash
cd /path/to/crypto-futures-agent
python scripts/hooks/sync_docs_on_delivery.py \
  --task-id "F-12" \
  --modified-files "position_monitor.py,order_executor.py" \
  --auto-update \
  --output-json reports/docs_sync_F-12.json
```

### Parâmetros

- `--task-id`: ID da tarefa entregue (ex: `F-12`)
- `--modified-files`: Arquivos modificados (CSV)
- `--auto-update`: Flag para atualizar docs/SYNCHRONIZATION.md
  automaticamente
- `--output-json`: Arquivo para salvar relatório

### Saída Esperada

```
[INFO] ======================================================================
[INFO] SINCRONIZAÇÃO DE DOCS - F-12
[INFO] ======================================================================
[INFO] Status: PASS
[INFO] Docs afetados: 2
[INFO]   Lint: PASS
[INFO]   Links: PASS
[INFO]   Code: PASS
[INFO] ======================================================================
[INFO] Relatório salvo em: reports/docs_sync_F-12.json
```

### Validações Implementadas

#### 1. Lint Markdown (Máx 80 caracteres)

```bash
# Verificar manualmente
cat docs/DATABASE_ARCHITECTURE.md | awk 'length > 80'
```

Exceções permitidas:
- Tabelas Markdown (`|`)
- URLs with `http`
- Blocos de código (indentedblocks)
- Linhas em branco

#### 2. Links Cruzados

Valida todas as referências Markdown:
```markdown
[DATABASE_ARCHITECTURE.md](docs/DATABASE_ARCHITECTURE.md)
```

Se arquivo não existir → FAIL

#### 3. Sincronização de Código

Extrai blocos Python em docs e valida sintaxe:
```python
# Exemplo em docs/ é verificado com compile()
```

### Mapa de Impacto Automático

Scripts detectam automaticamente quais docs são impactados:

```python
{
  'monitoring/position_monitor.py': [
    'DATABASE_ARCHITECTURE.md',
    'DATA_FLOW_DIAGRAM.md',
    'REFERENTIAL_INTEGRITY.md',
    'DIAGRAMAS.md'
  ],
  'execution/order_executor.py': [
    'DATABASE_ARCHITECTURE.md',
    'DATA_FLOW_DIAGRAM.md',
    'MODELAGEM_DE_DADOS.md'
  ],
  'risk/risk_gate.py': [
    'C4_MODEL.md',
    'USER_MANUAL.md',
    'REGRAS_DE_NEGOCIO.md'
  ],
  'agent/': ['DIAGRAMAS.md', 'REGRAS_DE_NEGOCIO.md'],
  'backtest/': ['MODELAGEM_DE_DADOS.md', 'DATA_FLOW_DIAGRAM.md']
}
```

## Validação de Integridade Manual

### Script SQL Reutilizável

```bash
sqlite3 db/crypto_futures.db < reports/db_integrity_check.sql
```

Executa 7 verificações:
1. Contagem de registros
2. Execuções órfãs
3. Posições obsoletas (> 30d)
4. Trades sem PnL
5. Integridade estrutural
6. Tamanho e performance
7. Resumo de saúde

### Saída Exemplo

```
═══════════════════════════════════════════
VALIDAÇÃO DE INTEGRIDADE DO DATABASE
2026-03-07 14:30:25
═══════════════════════════════════════════

1. CONTAGEM DE REGISTROS POR TABELA
tabela                 registros  ultimo_registro
─────────────────────────────────────────────────────
trade_log                      7  2026-02-21 14:30
execution_log                128  2026-03-07 13:45
position_snapshots         13756  2026-03-07 13:45
trade_signals                 11  2026-02-21 12:00

2. CRÍTICO - EXECUÇÕES ÓRFÃS
execucoes_orfas  status
─────────────────────────
0                ✓ OK

3. ALERTA - POSIÇÕES ABERTAS POR > 30 DIAS
obsoletas  status
─────────────────
7          ⚠️ REVISÃO
```

## Workflow de Integração com Backlog

### Fluxo Completo

```
1. Nova tarefa solicitada (issue criada)
   ↓
2. Cria branch git-feature/TASK-ID
   ↓
3. ANTES de aceitar:
   python scripts/hooks/validate_integrity_on_backlog_task.py \
     --backlog-item "TASK-ID" \
     --affected-modules "..."

   Se FAIL → Abrir issue de bloqueador
   Se PASS → Prosseguir
   ↓
4. Executar tarefa, fazer commits
   ↓
5. Criar Pull Request
   ↓
6. Code Review + merge
   ↓
7. APÓS merge ao main:
   python scripts/hooks/sync_docs_on_delivery.py \
     --task-id "TASK-ID" \
     --modified-files "..." \
     --auto-update

   Se FAIL → Abrir issue de doc sync
   Se PASS → Atualizar BACKLOG.md status
```

### Exemplo Prático

#### Cenário: Tarefa F-12 (Implementar risk_gate melhorado)

```bash
# Passo 1: Validar antes de aceitar
python scripts/hooks/validate_integrity_on_backlog_task.py \
  --backlog-item "F-12" \
  --affected-modules "risk_gate.py,risk_manager.py" \
  --output-json reports/integrity_F-12_pre.json

# Output: PASS (3 warnings sobre orfãos, mas aceitável)

# Passo 2: Implementar tarefa (commits, PRs, etc)
git commit -m "[FEAT] Implement dynamic risk gate thresholds"

# Passo 3: Após merge
python scripts/hooks/sync_docs_on_delivery.py \
  --task-id "F-12" \
  --modified-files "risk_gate.py,risk_manager.py" \
  --auto-update \
  --output-json reports/docs_sync_F-12.json

# Output: PASS
# files: risk_gate.py → C4_MODEL.md, USER_MANUAL.md
# Validações: Lint OK, Links OK, Code OK
# docs/SYNCHRONIZATION.md atualizado com [SYNC] tag
```

## Documentação de Arquitetura Criada

Todos os documentos abaixo seguem lint (máx 80 caracteres):

### Documentação Principal

1. **[DATABASE_ARCHITECTURE.md](../docs/DATABASE_ARCHITECTURE.md)**
   - Overview do banco único
   - Schemas detalhados (6 tabelas)
   - Mapa módulo → database
   - Politica de retenção

2. **[REFERENTIAL_INTEGRITY.md](../docs/REFERENTIAL_INTEGRITY.md)**
   - 5 regras críticas
   - Detecção de órfãos/stales/missing PnL
   - Procedimentos de limpeza
   - Auditoria manual

3. **[DATA_FLOW_DIAGRAM.md](../docs/DATA_FLOW_DIAGRAM.md)**
   - Ciclo operacional (7 passos)
   - Fluxos por tabela
   - Ponto crítico: sync de fechamento
   - Exemplo completo

4. **[DIAGRAMAS.md](../docs/DIAGRAMAS.md)**
   - Diagramas C4 (Contexto, Containers, Componentes)
   - Fluxos operacionais
   - Estado de ciclo de vida de trades
   - Sync point crítico

5. **[MODELAGEM_DE_DADOS.md](../docs/MODELAGEM_DE_DADOS.md)**
   - Modelo entidade-relacionamento (ER)
   - 4 entidades principais e atributos
   - Tipos de dados e constraints
   - Padrões de acesso (hot/cold paths)

6. **[REGRAS_DE_NEGOCIO.md](../docs/REGRAS_DE_NEGOCIO.md)**
   - Limites operacionais (leverage, capital)
   - Políticas de execução
   - Critérios de decisão
   - Regras de proteção e validação

### Artefatos

7. **[reports/db_integrity_check.sql](../reports/db_integrity_check.sql)**
   - 7 verificações SQL
   - Relatório formatado
   - Pontos críticos (orphans, stales, PnL)

5. **[scripts/hooks/validate_integrity_on_backlog_task.py](../scripts/hooks/validate_integrity_on_backlog_task.py)**
   - Trigger pre-backlog
   - 4 validações
   - Recomendações inteligentes

6. **[scripts/hooks/sync_docs_on_delivery.py](../scripts/hooks/sync_docs_on_delivery.py)**
   - Trigger post-delivery
   - Lint, links, code sync
   - Auto-update docs/SYNCHRONIZATION.md

### Atualizações

7. **[docs/C4_MODEL.md](../docs/C4_MODEL.md)**
   - Nível 4: Database Layer
   - Tabelas, responsabilidades, módulos

8. **[docs/SYNCHRONIZATION.md](../docs/SYNCHRONIZATION.md)**
   - Seção: Database Consolidation Policy
   - Status histórico databases

## Checklist de Implementação

- [x] DATABASE_ARCHITECTURE.md
- [x] REFERENTIAL_INTEGRITY.md
- [x] DATA_FLOW_DIAGRAM.md
- [x] DIAGRAMAS.md
- [x] MODELAGEM_DE_DADOS.md
- [x] REGRAS_DE_NEGOCIO.md
- [x] db_integrity_check.sql (7 queries, formatado)
- [x] validate_integrity_on_backlog_task.py (350 linhas)
- [x] sync_docs_on_delivery.py (380 linhas, mapa expandido)
- [x] C4_MODEL.md atualizado (com Database Layer)
- [x] SYNCHRONIZATION.md atualizado (com database policy)
- [x] Mapa de impacto modulo→docs expandido (include novos docs)

## Observações Importan

**Ressalvas de Implementação:**

1. ✅ **Português Obrigatório**: Todos os documentos e comentários em
   português
2. ✅ **Lint Markdown**: Máx 80 caracteres por linha
   - Exceções: tabelas, URLs, blocos de código
3. ✅ **Validação Automática**: Triggers validam integridade ANTES de
   aceitar tarefa e APÓS entregar
4. ✅ **Sincronização Docs**: Auto-update de docs/SYNCHRONIZATION.md com
   tag [SYNC]

## Suporte

Para dúvidas:
- Validação: Veja [DATABASE_ARCHITECTURE.md](../docs/DATABASE_ARCHITECTURE.md)
- Integridade: Veja [REFERENTIAL_INTEGRITY.md](../docs/REFERENTIAL_INTEGRITY.md)
- Fluxos: Veja [DATA_FLOW_DIAGRAM.md](../docs/DATA_FLOW_DIAGRAM.md)

---

**Última atualização:** 2026-03-07
**Status:** Testado e operacional
**Próximos Passos:** Integrar triggers em CI/CD (GitHub Actions)
