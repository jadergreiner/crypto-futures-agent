#!/usr/bin/env python3
"""
Executar rebase interativo com amends automáticos
"""

import subprocess
import os
import sys
import time

os.chdir(r'c:\repo\crypto-futures-agent')

# Configurar editor automático
os.environ['GIT_SEQUENCE_EDITOR'] = 'python automated_rebase_editor.py'

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
print("AUTOMATED REBASE - Correcao de 11 Commits")
print("="*70)

print("\n1. Editor automático configurado: automated_rebase_editor.py")
print("2. Iniciando git rebase -i 7849056^")
print("\n   Processando 11 commits...")

try:
    # Usar Popen para ter controle fino
    proc = subprocess.Popen(
        ['git', 'rebase', '-i', '7849056^'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # O editor automático vai marcar como 'edit'
    # e o git vai parar em cada 'edit' aguardando input

    # Para cada commit em edit mode
    commit_list = [
        '7849056', 'a229fab', 'fd1a7f8', '813e5fd', '09d2ecf',
        '1f2b75d', '0dcee01', 'b715f9a', '9b5166c', '6e04cd4', '81aa257'
    ]

    for i, commit_hash in enumerate(commit_list, 1):
        new_msg = FIXES[commit_hash]

        print(f"\n   [{i:2}/11] {commit_hash}")
        print(f"           {new_msg}")

        # Amend message
        amend_cmd = f'git commit --amend -m "{new_msg}"\n'
        print(f"           Executando: git commit --amend -m ...")

        try:
            proc.stdin.write(amend_cmd)
            proc.stdin.flush()
        except:
            pass

        time.sleep(0.5)

        # Continue rebase
        continue_cmd = 'git rebase --continue\n'
        print(f"           Executando: git rebase --continue")

        try:
            proc.stdin.write(continue_cmd)
            proc.stdin.flush()
        except:
            pass

        time.sleep(0.3)

    # Fechar stdin e aguardar processo
    proc.stdin.close()
    output, _ = proc.communicate(timeout=30)

    if proc.returncode == 0:
        print("\n   ✓ Rebase completado com sucesso!")
    else:
        print(f"\n   ⚠ Rebase retornou código: {proc.returncode}")
        print("\n   Output:")
        print(output[-500:] if len(output) > 500 else output)

except subprocess.TimeoutExpired:
    print("\n   ✗ Timeout - rebase demorou mais que o esperado")
    proc.kill()
except Exception as e:
    print(f"\n   ✗ Erro: {e}")
    try:
        subprocess.run('git rebase --abort', shell=True, capture_output=True)
    except:
        pass
    sys.exit(1)

print("\n" + "="*70)
print("3. Verificando resultado...")

# Ver log
result = subprocess.run('git log --oneline -15', shell=True, capture_output=True, text=True)
print("\n   Últimos 15 commits:")
for line in result.stdout.split('\n')[:15]:
    if line.strip():
        # Indicar se tem non-ASCII
        has_non_ascii = any(ord(c) > 127 for c in line)
        marker = "⚠" if has_non_ascii else " "
        print(f"   {marker} {line}")

print("\n" + "="*70)
print("4. Próximo passo:")
print("   git push origin main --force-with-lease")
print("="*70)
