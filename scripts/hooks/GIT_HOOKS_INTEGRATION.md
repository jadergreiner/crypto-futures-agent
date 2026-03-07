# Integração de Triggers com Git Hooks

**Status:** Disponível para integração
**Versão:** 1.0
**Responsável:** DevOps e Database Architecture Team

---

## Visão Geral

Este documento descreve como integrar os triggers de validação de
integridade e sincronização de docs com **Git Hooks**, permitindo
automação completa do workflow.

## Git Hooks Disponíveis

### 1. prepare-commit-msg (Pre-commit: validar branches)

**Objetivo:** Validar que branches seguem padrão ao criar commit

**Arquivo:** `.git/hooks/prepare-commit-msg`

```bash
#!/bin/bash
# Valida nomenclatura do branch

BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Padrão obrigatório: feature/TASK-NNN, hotfix/etc, release/v*
if [[ ! $BRANCH =~ ^(feature|hotfix|release|docs|chore)/ ]]; then
  echo "❌ Branch inválido: $BRANCH"
  echo "Use: feature/TASK-NNN, hotfix/..., release/v..."
  exit 1
fi

echo "✓ Branch validado: $BRANCH"
```

### 2. post-checkout (ao mudar de branch: validação automática)

**Objetivo:** Ao fazer checkout, validar saúde do database

**Arquivo:** `.git/hooks/post-checkout`

```bash
#!/bin/bash
# Executa validação de integridade ao fazer checkout

echo "Validando integridade do database..."

python scripts/hooks/validate_integrity_on_backlog_task.py \
  --affected-modules "monitoring/position_monitor.py" \
  --output-json /tmp/integrity_check.json

# Se FAIL, avisar usuário
if [ $? -ne 0 ]; then
  echo "⚠️ AVISO: Database em estado questionável"
  echo "Veja /tmp/integrity_check.json para detalhes"
  echo "Execute limpeza antes de prosseguir"
fi
```

### 3. pre-push (validação antes de push)

**Objetivo:** Antes de fazer push, validar que não há commits de debug

**Arquivo:** `.git/hooks/pre-push`

```bash
#!/bin/bash
# Valida commits antes de push para origin

protected_branch='main'
current_branch=$(git symbolic-ref --short HEAD)

if [[ "$current_branch" == "$protected_branch" ]]; then
  echo "❌ Não é permitido fazer push diretamente para $protected_branch"
  echo "Use: Pull Request e Code Review"
  exit 1
fi

echo "✓ Branch permitido para push: $current_branch"
```

### 4. post-merge (após merge ao main: sincronizar docs)

**Objetivo:** Após merge de PR, atualizar docs automaticamente

**Arquivo:** `.git/hooks/post-merge`

```bash
#!/bin/bash
# Executado após merge ao main

# Detectar TASK-ID partir do branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
TASK_ID=$(echo $BRANCH | grep -oE 'TASK-[0-9]+|F-[0-9]+|US-[0-9]+')

if [ -z "$TASK_ID" ]; then
  echo "⚠️ Não conseguiu detectar TASK-ID do branch"
  exit 0
fi

# Obter lista de arquivos modificados neste merge
MODIFIED_FILES=$(git log -1 --name-only --pretty=format: | tr '\n' ',')

echo "Sincronizando documentação para $TASK_ID..."

python scripts/hooks/sync_docs_on_delivery.py \
  --task-id "$TASK_ID" \
  --modified-files "$MODIFIED_FILES" \
  --auto-update \
  --output-json "reports/docs_sync_${TASK_ID}.json"

if [ $? -eq 0 ]; then
  echo "✓ Docs sincronizadas para $TASK_ID"
else
  echo "⚠️ Verifique sincronização de docs"
fi
```

## Instalação dos Hooks

### Passo 1: Criar diretório hooks

```bash
mkdir -p .git/hooks
chmod +x .git/hooks/*
```

### Passo 2: Copiar scripts

```bash
# Clone dos exemplos abaixo
cp < exemplo prepare-commit-msg .git/hooks/
cp < exemplo post-checkout .git/hooks/
cp < exemplo pre-push .git/hooks/
cp < exemplo post-merge .git/hooks/
```

### Passo 3: Dar permissão de execução

```bash
chmod +x .git/hooks/prepare-commit-msg
chmod +x .git/hooks/post-checkout
chmod +x .git/hooks/pre-push
chmod +x .git/hooks/post-merge
```

### Passo 4: Testar

```bash
git checkout -b feature/TEST-001

# Deve executar post-checkout e validar integridade
# Deve avisar se database problemático
```

## Integração com GitHub Actions (CI/CD)

### Workflow Exemplo: Validar PR

**Arquivo:** `.github/workflows/database-integrity.yml`

```yaml
name: Database Integrity Check

on:
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      # Instalar dependências
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -q -r requirements.txt

      # Validar integridade
      - name: Validate Database Integrity
        run: |
          python scripts/hooks/validate_integrity_on_backlog_task.py \
            --backlog-item "${{ github.event.number }}" \
            --affected-modules "monitoring/position_monitor.py" \
            --output-json /tmp/integrity_${PR}.json

      # Comentar resultado no PR
      - name: Comment integrity check on PR
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const result = JSON.parse(
              fs.readFileSync('/tmp/integrity_${{ github.event.number }}.json')
            );
            const comment = `
            ## Database Integrity Check
            - Status: **${result.status}**
            - Orphaned: ${result.integrity_checks.orphaned_executions.count}
            - Stale: ${result.integrity_checks.stale_positions.count}
            - Missing PnL: ${result.integrity_checks.missing_pnl.count}
            - Recomendação: ${result.recommendation}
            `;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Workflow Exemplo: Sincronizar docs após merge

**Arquivo:** `.github/workflows/docs-sync-on-merge.yml`

```yaml
name: Sync Docs on Merge

on:
  push:
    branches: [ main ]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -q -r requirements.txt

      # Detectar TASK-ID do último commit
      - name: Extract Task ID
        id: task
        run: |
          TASK_ID=$(git log -1 --pretty=%B | \
            grep -oE 'TASK-[0-9]+|F-[0-9]+|US-[0-9]+' | head -1)
          echo "task_id=$TASK_ID" >> $GITHUB_OUTPUT

      # Detectar arquivos modificados
      - name: Get modified files
        id: files
        run: |
          FILES=$(git diff --name-only HEAD~1..HEAD | tr '\n' ',')
          echo "files=$FILES" >> $GITHUB_OUTPUT

      # Sincronizar docs
      - name: Sync Documentation
        if: steps.task.outputs.task_id != ''
        run: |
          python scripts/hooks/sync_docs_on_delivery.py \
            --task-id "${{ steps.task.outputs.task_id }}" \
            --modified-files "${{ steps.files.outputs.files }}" \
            --auto-update \
            --output-json reports/docs_sync.json

      # Fazer commit de docs atualizadas
      - name: Commit docs updates
        if: success()
        run: |
          git config --local user.email "ci@example.com"
          git config --local user.name "CI Bot"
          git add docs/SYNCHRONIZATION.md
          git commit -m "[SYNC] Docs atualializadas para \
            ${{ steps.task.outputs.task_id }}" || true
          git push origin main
```

## Monitoramento Contínuo (Cron)

### Validação Diária (00:00 UTC)

**Arquivo:** `.github/workflows/daily-integrity-check.yml`

```yaml
name: Daily Database Integrity Check

on:
  schedule:
    - cron: '0 0 * * *'  # 00:00 UTC diariamente

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -q -r requirements.txt

      - name: Run SQL integrity check
        run: |
          sqlite3 db/crypto_futures.db \
            < reports/db_integrity_check.sql > /tmp/daily_check.txt

      - name: Parse results
        run: |
          # Se encontrar problemas, abrir issue
          if grep -q "CRÍTICO" /tmp/daily_check.txt; then
            echo "CRITICAL_ISSUES=true" >> $GITHUB_ENV
          fi

      - name: Create issue if problems found
        if: env.CRITICAL_ISSUES == 'true'
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '🔴 Database Integrity Alert',
              body: 'Daily check encontrou problemas. Veja check de hoje.',
              labels: ['database', 'urgent']
            });
```

## Fluxo Completo Automatizado

```
1. Developer cria feature branch
   ↓
   post-checkout hook:
   └─ Valida integridade (PASS = verde, FAIL = aviso)

2. Developer faz commits
   ↓
   prepare-commit-msg hook:
   └─ Valida nome do branch

3. Developer faz push
   ↓
   pre-push hook:
   └─ Previne push direto para main

4. Developer cria Pull Request
   ↓
   GitHub Actions (database-integrity.yml):
   ├─ Valida integridade
   ├─ Comenta no PR com resultado
   └─ Bloqueia merge se FAIL crítico

5. Code Review & Merge ao main
   ↓
   post-merge hook (local) + GitHub Actions (docs-sync.yml):
   ├─ Detecta TASK-ID
   ├─ Sincroniza docs
   ├─ Atualiza SYNCHRONIZATION.md
   └─ Faz commit automático

6. Daily (00:00 UTC)
   ↓
   GitHub Actions (daily-integrity.yml):
   ├─ Valida database
   ├─ Se problema: abre issue
   └─ Dashboard atualizado
```

## Troubleshooting

### Hook não executa

```bash
# Verificar permissões
ls -la .git/hooks/

# Dar permissão
chmod +x .git/hooks/*

# Testar manualmente
.git/hooks/post-checkout
```

### Erro de Python

```bash
# Verificar caminho do Python
which python3
which python

# Atualizar shebang nos hooks
#!/usr/bin/env python3
```

### Ignorar hook temporariamente

```bash
# Fazer commit sem trigger hook
git commit --no-verify

# Fazer push sem validação
git push --no-verify
```

---

**Última atualização:** 2026-03-07
**Status:** Pronto para integração
**Próximas Steps:** Setup em CI/CD pipeline
