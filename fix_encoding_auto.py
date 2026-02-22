#!/usr/bin/env python3
"""
Script para corrigir automaticamente encoding de commits
Usa git filter-branch e git filter-repo approach
"""

import subprocess
import json
import sys
import os

# Mapeamento de commits para corrigir
COMMITS_TO_FIX = {
    '81aa257': '[PHASE2] Script recuperacao dados conta real',
    '6e04cd4': '[GOLIVE] Canary Deployment Phase 1 iniciado',
    '9b5166c': '[BOARD] Votacao Final GO-LIVE aprovada unanime',
    'b715f9a': '[DOCS] Integration Summary Board 16 membros',
    '0dcee01': '[INFRA] Board Orchestrator 16 membros setup',
    '1f2b75d': '[BOARD] Reuniao 16 membros Go-Live Auth',
    '09d2ecf': '[CLOSE] Reuniao Board 21 FEV encerrada',
    '813e5fd': '[VALIDATE] TASK-003 Alpha SMC Validation OK',
    'fd1a7f8': '[PLAN] TASK-004 Preparacao go-live canary',
    'a229fab': '[TEST] TASK-002 QA Testing 40/40 testes ok',
    '7849056': '[FEAT] TASK-001 Heuristicas implementadas',
}

def run_cmd(cmd):
    """Execute command and return result"""
    print(f"→ Executando: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"✗ Erro: {result.stderr}")
        return False
    if result.stdout:
        print(f"✓ {result.stdout[:100]}")
    return True

def main():
    print("="*80)
    print("SCRIPT DE CORRECAO AUTOMATICA DE ENCODING")
    print("="*80)

    # Criar script de rebase
    rebase_script = """#!/bin/bash
set -e

# Função para executar rebase e amend de cada commit
fix_commit() {
    local hash=$1
    local message=$2

    echo "Corrigindo commit $hash..."

    # Começar rebase a partir do commit anterior
    git rebase -i $hash^ --onto HEAD

    # Amend da mensagem
    git commit --amend --no-edit -m "$message"

    # Continuar rebase
    git rebase --continue 2>/dev/null || true
}

echo "Iniciando correções de encoding..."

# Função alternativa: filter-branch approach
git filter-branch -f --msg-filter 'python -c "
import sys
msg = sys.stdin.read()
# Aplicar conversões
{conversions}
sys.stdout.write(msg)
"' -- --all 2>&1 | tee filter-branch.log || true

echo "Rebase completo!"
"""

    # Gerar conversões Python
    conversions = ""
    for short_hash, fixed_msg in COMMITS_TO_FIX.items():
        conversions += f"if '{short_hash}' in msg:\n    msg = '{fixed_msg}'\n"

    rebase_script = rebase_script.format(conversions=conversions)

    # Salvar script
    with open('fix_encoding.sh', 'w') as f:
        f.write(rebase_script)

    print("\nScript de rebase criado: fix_encoding.sh")
    print("="*80)

    # Usar abordagem mais simples: cherry-pick com nova mensagem
    print("\nAbordagem: Git cherry-pick com branches temporários")
    print("="*80)

    print("\nPasso 1: Criar backup branch")
    run_cmd("git branch backup-before-fix")

    print("\nPasso 2: Identificar ponto antes dos problemas")
    # Começamos do commit mais antigo problemático
    run_cmd("git log --oneline | head -20")

if __name__ == '__main__':
    main()
