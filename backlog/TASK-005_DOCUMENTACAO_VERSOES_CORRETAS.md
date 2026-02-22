# 📋 REFERÊNCIA DOCUMENTAÇÃO TASK-005 — Versões Corrigidas

**Status:** 🟢 VERSÕES EM PORTUGUÊS 100% LINT COMPLIANCE
**Data:** 22 FEV 2026
**Responsável:** Doc Advocate

---

## 📚 Arquivos Corretos a Usar

### ✅ VERSÕES CORRIGIDAS (Usar ESTAS)

```
backlog/TASK-005_PLANO_SINCRONIZACAO_DOCS.md
  └─ Plano mestre sincronização documentação
  └─ Português puro, max 80 chars, UTF-8
  └─ ✅ Pronto para usar

backlog/TASK-005_CHECKLIST_DIARIO_DOC_ADVOCATE.md
  └─ Checklist diário 08:00 UTC
  └─ Português puro, copy-paste ready
  └─ ✅ Pronto para usar

backlog/TASK-005_SYNC_MATRIX.json
  └─ Matriz dependências (JSON estruturado)
  └─ ✅ Pode usar como está
```

### ❌ VERSÕES ANTIGAS (REMOVER)

```
backlog/TASK-005_DOC_SYNCHRONIZATION_PLAN.md
  └─ Mix português/inglês
  └─ Linhas > 80 chars
  ❌ DELETAR — Usar TASK-005_PLANO_SINCRONIZACAO_DOCS.md

backlog/TASK-005_DOC_ADVOCATE_DAILY_CHECKLIST.md
  └─ Muita tradução incompleta
  └─ Formatação complexa
  ❌ DELETAR — Usar TASK-005_CHECKLIST_DIARIO_DOC_ADVOCATE.md

backlog/TASK-005_DOC_ADVOCATE_IMPLEMENTATION_GUIDE.md
  └─ Muito longo, mix idiomas
  └─ Precisa revisão completa
  ❌ USAR COM CAUTELA — Apenas como referência
```

---

## 🎯 Como Usar Arquivos Corretos

### 1️⃣ Doc Advocate — Lê primeiro

```bash
# Ler plano mestre
cat backlog/TASK-005_PLANO_SINCRONIZACAO_DOCS.md

# Ler checklist diário
cat backlog/TASK-005_CHECKLIST_DIARIO_DOC_ADVOCATE.md

# Estudar matriz dependências
cat backlog/TASK-005_SYNC_MATRIX.json
```

### 2️⃣ Executar Fase 0 (22 FEV 15:00)

Use: `TASK-005_PLANO_SINCRONIZACAO_DOCS.md`, Fase 0

### 3️⃣ Usar Checklist Diário (08:00 UTC)

Use: `TASK-005_CHECKLIST_DIARIO_DOC_ADVOCATE.md`
- Copy-paste template
- Preencher checklist
- Postar em #docs-governance

---

## ✅ Validação Markdown Lint

Todos arquivos corretos já passam:

```bash
# Testar markdown lint locally
markdownlint \
  backlog/TASK-005_PLANO_SINCRONIZACAO_DOCS.md \
  backlog/TASK-005_CHECKLIST_DIARIO_DOC_ADVOCATE.md

# Deve output: (nenhum erro)
```

---

## 🔍 Verificação Compliance

Arquivos corrigidos têm:

- ✅ Português 100% (sem inglês)
- ✅ Max 80 chars por linha
- ✅ UTF-8 encoding válido
- ✅ Sem trailing whitespace
- ✅ Formatação markdown válida
- ✅ Links internos válidos
- ✅ Tabelas formatadas

---

## 📞 Próximas Ações

### 22 FEV 15:00

Doc Advocate:
1. Ler `TASK-005_PLANO_SINCRONIZACAO_DOCS.md`
2. Ler `TASK-005_CHECKLIST_DIARIO_DOC_ADVOCATE.md`
3. Começar FASE 0 conforme plano

### 23 FEV 08:00

Doc Advocate:
1. Usar checklist diário
2. Preencher todos 6 seções
3. Postar em Slack

---

## 💡 Referência Rápida

**Qual arquivo para cada tarefa:**

| Tarefa | Arquivo |
|--------|---------|
| Entender plano mestre | TASK-005_PLANO_* |
| Executar audit 08:00 | TASK-005_CHECKLIST_* |
| Ver dependências | TASK-005_SYNC_MATRIX.json |
| Refs técnicas | Outros docs prompts/ |

---

**STATUS:** ✅ Documentação corrigida
**PRÓXIMO:** Doc Advocate inicia FASE 0 (22 FEV 15:00)
