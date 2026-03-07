# Git Hooks Installation Guide

## Overview

Este repositório usa Git Hooks para garantir conformidade com políticas de documentação e código. Os hooks são armazenados em `.githooks/` (versionado) mas executados de `.git/hooks/` (local).

---

## ✅ Instalação Rápida

### 1. **Configurar Git para usar `.githooks/` como hooks path**

```bash
git config core.hooksPath .githooks
```

**Nota:** Isso configura localmente em `.git/config`. Não é necessário reverter.

### 2. **Tornar hooks executáveis** (Linux/macOS)

```bash
chmod +x .githooks/*
```

**Windows:** Git Bash ou WSL2 — será automático ao fazer clone.

### 3. **Verificar Instalação**

```bash
git config core.hooksPath
# Output: .githooks
```

---

## 📋 Hooks Disponíveis

| Hook | Descrição | Dispara Quando |
|------|-----------|---|
| **pre-commit** | Valida Markdown lint + Python docstrings | `git commit` |
| **pre-push** | Verifica [SYNC] tags em mudanças | `git push` |

---

## 🔧 Pre-Commit Hook

**Localização:** `.githooks/pre-commit`  
**Linguagem:** Bash  
**Dispara:** Antes de `git commit`

### Validações:

1. **Markdownlint** — Verifica todos os `.md` staged
   - Usa configuração em `.markdownlint.json`
   - Max line length: 80 chars (customizável por tipo)
   - Detecta tabelas, code blocks, URLs

2. **Python Docstrings** — Verifica módulos críticos
   - `agent/*`, `execution/*`, `risk/*`, `backtest/*`
   - Requer docstring no início do arquivo

### Comportamento:

- ✅ **PASSA:** Commit procede normalmente
- ❌ **FALHA:** Mostra erros, commit bloqueado
- ⏭️ **SKIP:** Use `git commit --no-verify` para contornar

### Exemplo:

```bash
$ git add docs/SYNCHRONIZATION.md
$ git commit -m "[SYNC] Atualizacao"

🔍 PRE-COMMIT: Validando documentação...
  ├─ Executando markdownlint...
  ✅ Markdownlint: OK (docs/SYNCHRONIZATION.md)
  ├─ Executando docstring checker...
  ✅ Docstring check: OK
  ├─ Verificando .gitignore...
  ✅ .gitignore: OK

[main abc1234] [SYNC] Atualizacao
```

---

## 🔐 Pre-Push Hook

**Localização:** `.githooks/pre-push`  
**Linguagem:** Bash  
**Dispara:** Antes de `git push`

### Validações:

1. **[SYNC] Tag Obrigatória**
   - Commits que modificam arquivos em `docs/*` DEVEM ter `[SYNC]` tag
   - Exemplo: `[SYNC] Atualizacao de DATABASE_ARCHITECTURE.md`

2. **Commits Válidos**
   - Última mensagem de commit é checar se contém [SYNC]

### Comportamento:

- ✅ **[SYNC] tag presente:** Push prossegue
- ❌ **[SYNC] tag ausente em docs/:** Push bloqueado
- ⏭️ **SKIP:** Use `git push --no-verify` para contornar

### Exemplo:

```bash
$ git push origin main

🔍 PRE-PUSH: Verificando conformidade [SYNC] tag...
✅ PRE-PUSH VALIDAÇÃO COMPLETA ([SYNC] tags OK)
To https://github.com/jadergreiner/crypto-futures-agent.git
   abc1234..def5678  main -> main
```

---

## 🛠️ Scripts de Suporte

Três scripts Python estão disponíveis para corrigir erros detect pelo pre-commit:

### `fix_markdown_lint.py`

Corrige erros básicos:
- MD040: Language in code blocks
- MD024: Duplicate headings
- MD031: Blanks around fences

```bash
python scripts/fix_markdown_lint.py docs/SYNCHRONIZATION.md
```

### `fix_markdown_advanced.py`

Corrige erros complexos:
- MD013: Line length (quebra inteligente)
- MD060: Table formatting

```bash
python scripts/fix_markdown_advanced.py docs/SYNCHRONIZATION.md
```

### `fix_markdown_final.py`

Corrige erros finais:
- MD032: Blanks around lists
- MD036: Emphasis as heading

```bash
python scripts/fix_markdown_final.py docs/SYNCHRONIZATION.md
```

Cada script cria backup (`.bak`, `.bak2`, `.bak3`).

---

## 🚫 Contornar Hooks (Quando Necessário)

**Pre-commit:**
```bash
git commit --no-verify -m "Mensagem"
```

**Pre-push:**
```bash
git push --no-verify
```

**Nota:** Use apenas em emergências. Os hooks existem para garantir qualidade!

---

## 🔍 Troubleshooting

### ❌ "Permission denied" ao commitar

**Solução:**
```bash
chmod +x .githooks/pre-commit
chmod +x .githooks/pre-push
```

### ❌ "markdownlint: command not found"

**Solução:**
```bash
npm install -g markdownlint-cli
# ou
npm install markdownlint-cli --save-dev
```

### ❌ Hooks não executando

**Verificar configuração:**
```bash
git config core.hooksPath
# Deve retornar: .githooks
```

**Se vazio, configurar:**
```bash
git config core.hooksPath .githooks
```

### ❌ Windows: Hooks não funcionam

**Causa:** Linha endings CRLF vs LF

**Solução:**
```bash
# Converter para LF
dos2unix .githooks/pre-commit
dos2unix .githooks/pre-push

# Ou usar WSL2/Git Bash
bash .githooks/pre-commit
```

---

## 📊 Status dos Hooks

**Versão:** 1.0  
**Última atualização:** 2026-03-07  
**Estado:** ✅ Operacional  

Hooks foram testados e validados em:
- Commits com mudanças em docs/
- Pushes com [SYNC] tags
- Conflitos de merge

---

## 📚 Arquivos Relacionados

- [.markdownlint.json](.markdownlint.json) — Configuração lint
- [scripts/fix_markdown_*.py](scripts/) — Scripts de correção
- [.githooks/pre-commit](.githooks/pre-commit) — Hook principal
- [.githooks/pre-push](.githooks/pre-push) — Hook de push

---

## ✅ Próximas Etapas

1. **Instalar hooks:** `git config core.hooksPath .githooks`
2. **Testar:** Fazer commit com erro lint propositalmente
3. **Usar scripts:** Corrigir com `python scripts/fix_markdown_*.py`
4. **Commit novamente:** Deve passar agora
5. **Push:** Validar [SYNC] tag obrigatória

---

**Última revisão:** 2026-03-07  
**Responsável:** Database Architecture + Docs Sync Team
