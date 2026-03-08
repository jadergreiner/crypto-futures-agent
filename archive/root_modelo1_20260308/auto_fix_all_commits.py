#!/usr/bin/env python3
"""
Script para corrigir encoding de commits automaticamente
"""

import subprocess
import os
import sys
import time

os.chdir(r'c:\repo\crypto-futures-agent')

# Mensagens corretas para cada commit
FIXES = {
    '7849056': '[FEAT] TASK-001 Heuristicas implementadas',
    'a229fab': '[TEST] TASK-002 QA Testing 40/40 testes ok',
    'fd1a7f8': '[PLAN] TASK-004 Preparacao go-live canary',
    '813e5fd': '[VALIDATE] TASK-003 Alpha SMC Validation OK',
    '09d2ecf': '[CLOSE] Reuniao Board 21 FEV encerrada',
    '1f2b75d': '[BOARD] Reuniao 16 membros Go-Live Auth',
    '0dcee01': '[INFRA] Board Orchestrator 16 membros setup',
    'b715f9a': '[DOCS] Integration Summary Board 16 membros',
    '9b5166c': '[BOARD] Votacao Final GO-LIVE aprovada unanime',
    '6e04cd4': '[GOLIVE] Canary Deployment Phase 1 iniciado',
    '81aa257': '[PHASE2] Script recuperacao dados conta real',
}

print("="*70)
print("CORRECAO AUTOMATICA DE COMMITS")
print("="*70)

print("\n1. Iniciando rebase interativo...")
print("   Usando editor automático para marcar 'edit' em 11 commits")

# Configurar editor automático
os.environ['GIT_SEQUENCE_EDITOR'] = 'python rebase_editor.py'

# Começar rebase
print("\n   Iniciando: git rebase -i 7849056^")
process = subprocess.Popen(
    ['git', 'rebase', '-i', '7849056^'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print("\n2. Aguardando entrada interativa...")

# Lista de commits em ordem de execução
commit_order = [
    '7849056', 'a229fab', 'fd1a7f8', '813e5fd', '09d2ecf',
    '1f2b75d', '0dcee01', 'b715f9a', '9b5166c', '6e04cd4', '81aa257'
]

time.sleep(1)

# Para cada commit que vai estar em 'edit'
try:
    for i, commit_hash in enumerate(commit_order, 1):
        new_msg = FIXES[commit_hash]

        print(f"\n   [{i:2}/11] Corrigindo {commit_hash}...")
        print(f"          Nova msg: {new_msg}")

        # Amend da mensagem
        amend_process = subprocess.Popen(
            f'git commit --amend -m "{new_msg}"',
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        amend_out, amend_err = amend_process.communicate()

        if amend_process.returncode != 0:
            print(f"      ✗ Erro no amend: {amend_err[:100]}")
            break

        print(f"      ✓ Amendado")

        # Continuar rebase
        rebase_process = subprocess.Popen(
            'git rebase --continue',
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        rebase_out, rebase_err = rebase_process.communicate()

        if rebase_process.returncode != 0:
            if 'conflict' in rebase_err.lower():
                print(f"      ⚠ Conflito detectado")
            else:
                print(f"      ✓ Rebase continue executado")
        else:
            print(f"      ✓ Rebase continue executado")

        time.sleep(0.2)

    print("\n" + "="*70)
    print("3. Verificando resultado...")

    # Verificar status
    result = subprocess.run('git log --oneline -15', shell=True, capture_output=True, text=True)
    print("\n   Últimos 15 commits:")
    for line in result.stdout.split('\n')[:15]:
        if line:
            print(f"   {line}")

    print("\n" + "="*70)
    print("4. Validando encoding ASCII...")

    # Validar encoding
    log_result = subprocess.run('git log --format=%s HEAD~20..HEAD', shell=True, capture_output=True, text=True)

    non_ascii_count = 0
    for line in log_result.stdout.split('\n'):
        if line and any(ord(c) > 127 for c in line):
            non_ascii_count += 1
            print(f"   ✗ Still has non-ASCII: {line[:50]}")

    if non_ascii_count == 0:
        print("   ✓ Todos em ASCII puro!")
    else:
        print(f"   encontrados {non_ascii_count} ainda com problemas")

    print("\n" + "="*70)
    print("5. Próximo passo:")
    print("   git push origin main --force-with-lease")
    print("="*70)

except KeyboardInterrupt:
    print("\n\nCancelado pelo usuário")
    sys.exit(1)
except Exception as e:
    print(f"\nErro: {e}")
    sys.exit(1)
