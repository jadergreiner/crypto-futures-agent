# ✅ Checklist Diário Doc Advocate — TASK-005

**Responsável:** Doc Advocate
**Data Início:** 22 FEV 2026
**Status:** 🟢 PRONTO PARA USO

---

## 🎯 Propósito

Doc Advocate usa este checklist **diariamente** (08:00 UTC) para:

1. Verificar sincronização código ↔ docs
2. Validar compliance mensagem commit
3. Verificar markdown lint (80 chars, UTF-8)
4. Validar cross-references
5. Documentar audit trail

**Frequência:** Diária @ 08:00 UTC (após standup)
**Tempo:** 30 minutos
**Relatório:** #docs-governance Slack

---

## 📋 Template Diário (Copiar-Colar)

```markdown
## Audit Sincronização Documentação — TASK-005

**Data:** [DATA] 2026
**Horário:** 08:00-08:30 UTC
**Doc Advocate:** [NOME]
**Status:** ✅ PASS / 🔴 FAIL

---

### 1️⃣ Sincronização Código → Docs

#### README.md Atualizações
- [ ] Módulo checkpoint_manager.py mencionado?
- [ ] Módulo convergence_monitor.py mencionado?
- [ ] Módulo rollback_handler.py mencionado?
- [ ] Script ppo_training_orchestrator.py mencionado?
- [ ] Exemplo quick-start incluído?
- [ ] Todos links válidos (não quebrados)?

**Ação se FALHAR:** Adicionar seções + COMMIT [SYNC]

#### BEST_PRACTICES.md Atualizações
- [ ] Section "### Gestão Checkpoint" existe?
- [ ] Exemplo código checkpoint matches fonte?
- [ ] Section "### Monitoramento Convergência" documenta?
- [ ] Section "### Estratégia Rollback" documenta?
- [ ] Todos exemplos código válidos?
- [ ] Referências apontam arquivos agent/ corretos?

**Ação se FALHAR:** Atualizar seções + COMMIT [SYNC]

#### Documentação Arquitetura
- [ ] Pasta docs/ reflete estrutura TASK-005?
- [ ] Diagrama pipeline dados atualizado?
- [ ] Pontos integração documentados?

**Ação se FALHAR:** Criar/atualizar docs relevantes

---

### 2️⃣ Validação Mensagem Commit

#### Compliance Tag [SYNC]
- [ ] Todos commits relacionados docs têm [SYNC]?
- [ ] Formato correto: [SYNC] Descrição — arquivos?
- [ ] Zero commits sem [SYNC] em 48h?

**Validação comando:**
```bash
git log --oneline origin/main..feature/task-005-ppo-training \
  | grep -v "\[SYNC\]\|\[FEAT\]\|\[FIX\]" | wc -l
# Deve retornar: 0
```

#### Comprimento e Formato
- [ ] Todas mensagens ≤ 72 caracteres?
- [ ] Nenhuma mensagem vaga (ex: "Updated")
- [ ] Todas mensagens começam com [TAG]?

**Exemplos maus (FALHAM audit):**
- ❌ "Updated documentation"
- ❌ "[SYNC] Mensagem muito longa que exceeds 72 chars limite"
- ❌ "Fix typo in README"

#### Validação ASCII Only
- [ ] Todas mensagens commit contêm APENAS ASCII?
- [ ] Nenhum caractere Unicode (ç, ã, é, ó)?

**Validação comando:**
```bash
git log --oneline \
  origin/main..feature/task-005-ppo-training | \
  while read line; do
    if echo "$line" | grep -qP '[^\x00-\x7F]'; then
      echo "NAO-ASCII: $line"
    fi
  done
# Deve retornar: (vazio)
```

---

### 3️⃣ Conformidade Markdown Lint

#### Encoding
- [ ] README.md encoding UTF-8?
- [ ] BEST_PRACTICES.md UTF-8?
- [ ] Todos .md em docs/ UTF-8?
- [ ] Todos .md em backlog/ UTF-8?

**Validação comando:**
```bash
file -i README.md BEST_PRACTICES.md \
  docs/*.md backlog/*.md | \
  grep -v "UTF-8|us-ascii"
# Deve retornar: (vazio)
```

#### Comprimento Linhas (Max 80 chars)
- [ ] README.md: 0 linhas > 80 chars?
- [ ] BEST_PRACTICES.md: 0 linhas > 80?
- [ ] SYNCHRONIZATION.md: 0 linhas > 80?
- [ ] SPRINT_BACKLOG: 0 linhas > 80?
- [ ] TASKS_TRACKER: 0 linhas > 80?

**Validação comando:**
```bash
for file in README.md BEST_PRACTICES.md \
  docs/SYNCHRONIZATION.md backlog/*.md; do
  LONG=$(awk 'length > 80' "$file" | wc -l)
  [ "$LONG" -gt 0 ] && \
    echo "$file: $LONG linhas > 80"
done
# Deve retornar: (vazio)
```

#### Trailing Whitespace
- [ ] README.md: sem espaços trailing?
- [ ] BEST_PRACTICES.md: sem espaços?
- [ ] SYNCHRONIZATION.md: sem espaços?

**Validação comando:**
```bash
grep ' $' README.md BEST_PRACTICES.md \
  docs/SYNCHRONIZATION.md | wc -l
# Deve retornar: 0
```

#### Regras Markdown Personalizadas
- [ ] Headings formatados (# H1, ## H2)?
- [ ] Blocos código com linguagem?
- [ ] Listas indentadas?
- [ ] Tabelas formatadas corretamente?

---

### 4️⃣ Validação Cross-References

#### Verificação Links Quebrados
- [ ] Todos links internos em README válidos?
- [ ] Arquivos referenciados existem?
- [ ] Referências linha número corretas?

**Validação comando:**
```bash
grep -o "\[.*\]([^)]*\.py)" README.md \
  BEST_PRACTICES.md | \
  while read link; do
    file=$(echo "$link" | sed 's/.*(\([^)]*\)).*/\1/')
    if ! [ -f "$file" ]; then
      echo "QUEBRADO: $link"
    fi
  done
# Deve retornar: (vazio)
```

#### Validação Formato
- [ ] Links formato correto: [texto](caminho)?
- [ ] Refs linha: #L10 (não #line10)?
- [ ] Caminhos arquivo: / (não \)?

**Exemplos válidos:**
- ✅ [checkpoint manager](agent/checkpoint_manager.py)
- ✅ [Ver exemplo](BEST_PRACTICES.md#L150)
- ✅ [Link](docs/folder/file.md)

**Exemplos inválidos:**
- ❌ [texto](C:\repo\file.md)
- ❌ [texto](file.md#150)
- ❌ [texto](#L10-L15)

#### Matriz Cross-Reference
- [ ] Toda ref docs em README existe?
- [ ] Todos módulos TASK-005 em BEST_PRACTICES?
- [ ] Todas updates TASK-005 logadas em SYNC?

---

### 5️⃣ Audit Trail & Logging

#### Entries SYNCHRONIZATION.md
- [ ] SYNCHRONIZATION.md atualizado progresso?
- [ ] Cada entry tem: DATA | HORA | EVENTO | OWNER?
- [ ] Não mais velho que 2 horas?

**Exemplo entry:**
```
| 23 FEV | 10:00 | checkpoint_manager.py created | SWE Sr | README atualizado |
```

#### Entry CHANGELOG.md
- [ ] CHANGELOG.md tem section TASK-005?
- [ ] Lista 4 módulos novos?
- [ ] Inclui métricas (Sharpe, tempo)?
- [ ] Data correta?

#### Audit Trail Commits
- [ ] Todos commits [SYNC] logados em SYNC?
- [ ] Timestamps match git log?
- [ ] Owners documentados mudanças?

**Validação comando:**
```bash
git log origin/main..feature/task-005 \
  --oneline | grep "\[SYNC\]" | wc -l
# Cross-check com entries SYNCHRONIZATION.md
```

---

### 6️⃣ Risk & Blocker Check

#### Problemas Encontrados?
- [ ] Erros encoding detectados?
- [ ] Links quebrados em docs?
- [ ] Tags [SYNC] faltando?
- [ ] Violações line length?
- [ ] Trailing whitespace?

#### Blockers para Merge
- [ ] Violações [SYNC] tag? (FAIL = bloqueador)
- [ ] Violações encoding? (FAIL = bloqueador)
- [ ] Links quebrados README? (FAIL = bloqueador)
- [ ] Docs críticas faltando? (FAIL = bloqueador)

**SE qualquer bloqueador:** Status = 🔴 FAIL e NÃO sign-off

---

## 📊 Resultado Audit

### Status Geral

**Data:** [DATA]
**Resultado:** ✅ PASS / 🔴 FAIL
**Contagem Blockers:** 0 / _
**Contagem Warnings:** _ / _

### Sign-Off

- [ ] Doc Advocate revisou todas seções?
- [ ] Todos blockers resolvidos (se teve)?
- [ ] Pronto para merge? **SIM / NÃO**

**Nome Doc Advocate:** _________________
**Assinatura/Aprovação:** ✅ / 🔴
**Horário Conclusão:** _________ UTC

---

## 📝 Notas & Ações

Ações tomadas hoje:
1. [Descrever fixes feitas]
2. [Blockers escalados SWE Sr?]
3. [Próximos passos amanhã?]

---

## 🔗 Referências

- 📋 Plano Sincronização: [TASK-005_PLANO_SINCRONIZACAO_DOCS.md]
- 📊 Matriz Sincronização: [TASK-005_SYNC_MATRIX.json]
- 📚 SYNCHRONIZATION: [docs/SYNCHRONIZATION.md]
- 🎯 SPRINT BACKLOG: [backlog/SPRINT_BACKLOG_21FEV]
- 🔄 TRACKER: [backlog/TASKS_TRACKER_REALTIME.md]

---

## ✅ Completar Audit

Após completar audit, **postar resumo Slack:**

```
📚 AUDIT PASS — TASK-005
✅ README sincronizado (4 módulos)
✅ BEST_PRACTICES updated (3 sections)
✅ 100% compliance tag [SYNC]
✅ Lint markdown: 0 errors
✅ Cross-refs: 100% válido
✅ Pronto para merge

Próximo: Training dia N, monitoring contínuo
```

---

**Template Versão:** 1.0
**Última Atualização:** 22 FEV 2026
**Status:** 🟢 PRONTO PARA USO DIÁRIO
