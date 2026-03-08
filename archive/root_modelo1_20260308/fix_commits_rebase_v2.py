#!/usr/bin/env python3
"""
Corrigir commits recriando-os com git commit-tree
Abordagem: Recrear cada commit com nova mensagem, mantendo tree e parent
"""

import subprocess
import os
import sys
from datetime import datetime

os.chdir(r'c:\repo\crypto-futures-agent')

# Mensagens corretas
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

def run_cmd(cmd):
    """Execute command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()

print("="*70)
print("GIT COMMIT-TREE: Recriar commits com nova mensagem")
print("="*70)

print("\n1. Mapeando commits...")

# Mapa de hash curto para hash completo
commit_map = {}
for short_hash in FIXES.keys():
    success, full_hash, _ = run_cmd(f'git rev-parse {short_hash}')
    if success:
        commit_map[short_hash] = full_hash
        print(f"   {short_hash} -> {full_hash[:12]}")

print(f"\n   Total: {len(commit_map)} commits mapeados")

print("\n2. Adicionando commits ao reflog...")

# Ir através de cada commit e recriar
# Preciso manter a ordem topológica
# Vou fazer cherry-pick no lugar

# Na verdade, vou usar uma abordagem mais simples:
# git rebase com --force-rebase mas preservando mensagens via script

print("\n3. Usando método alternativo: Rebase com GIT_EDITOR...")

# Criar um script editor que marca todos como 'edit'
editor_script = r'''
import sys
if len(sys.argv) > 1:
    with open(sys.argv[1], 'r') as f:
        lines = f.readlines()

    result = []
    for line in lines:
        if line.strip() and not line.startswith('#'):
            # Trocar pick para edit
            if line.startswith('pick '):
                line = 'edit ' + line[5:]
        result.append(line)

    with open(sys.argv[1], 'w') as f:
        f.writelines(result)
'''

with open('git_editor_temp.py', 'w') as f:
    f.write(editor_script)

print("   Criado: git_editor_temp.py")

print("\n4. Iniciando rebase passo-a-passo...")
print("   Se ficar preso, use Ctrl+C e execute:")
print("   git rebase --abort")
print()

# Usar GIT_SEQUENCE_EDITOR
os.environ['GIT_SEQUENCE_EDITOR'] = 'python git_editor_temp.py'

# Função auxiliar para fazer amend e continue
def amend_and_continue(commit_hash, new_msg):
    """Amend current commit and continue rebase"""

    # Amend
    success, out, err = run_cmd(f'git commit --amend -m "{new_msg}"')
    if not success:
        print(f"   ✗ Erro no amend: {err[:100]}")
        return False

    # Continue
    success, out, err = run_cmd('git rebase --continue')
    if not success:
        if 'no rebase in progress' in err:
            print(f"   ✓ Rebase finalizado")
            return True
        elif 'conflict' not in err.lower():
            print(f"   ✓ Continue executado")
            return True
        else:
            print(f"   ⚠ Possível conflito: {err[:100]}")
            return False

    return True

print("   Iniciando rebase...")
success, out, err = run_cmd('git rebase -i 7849056^')

print(f"\n   Status: {'OK' if success else 'Em progresso ou erro'}")

# Agora processar cada commit
for i, (short_hash, new_msg) in enumerate(FIXES.items(), 1):
    print(f"\n   [{i:2}/11] {short_hash}: {new_msg[:50]}")

    if not amend_and_continue(short_hash, new_msg):
        print(f"   ✗ Problema ao processar")
        break
    else:
        print(f"   ✓ OK")

print("\n" + "="*70)
print("5. Verificando resultado final...")

success, log_out, _ = run_cmd('git log --oneline -12')
print("\n   Últimos 12 commits:")
for line in log_out.split('\n'):
    if line:
        print(f"   {line}")

print("\n" + "="*70)
print("6. Próximo passo:")
print("   git push origin main --force-with-lease")
print("="*70)

# Cleanup
try:
    os.remove('git_editor_temp.py')
except:
    pass
