#!/usr/bin/env python3
"""
Abordagem alternativa: fazer reset e cherry-pick cada commit com nova mensagem
"""

import subprocess
import os
import sys

os.chdir(r'c:\repo\crypto-futures-agent')

def run(cmd):
    """Executar comando"""
    print(f"→ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return True, result.stdout.strip()
    else:
        print(f"  ✗ Erro: {result.stderr.strip()[:100]}")
        return False, result.stderr.strip()

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
print("CHERRY-PICK APPROACH: Recriar commits com nova mensagem")
print("="*70)

print("\n1. Mapeando commits...")

# Ordem correta de commits (do mais antigo para o mais novo)
commit_order = [
    '7849056', 'a229fab', 'fd1a7f8', '813e5fd', '09d2ecf',
    '1f2b75d', '0dcee01', 'b715f9a', '9b5166c', '6e04cd4', '81aa257'
]

# Conseguir o commit anterior ao primeiro
first_commit = commit_order[0]
success, parent, _ = run(f'git rev-parse {first_commit}^')

if not success:
    print("✗ Não consegui encontrar o parent do primeiro commit")
    sys.exit(1)

print(f"\n2. Fazendo reset para o parent: {parent[:12]}")
success, _, _ = run(f'git reset --hard {parent}')

if not success:
    print("✗ Reset falhou")
    sys.exit(1)

print(f"\n3. Cherry-picking 11 commits com novas mensagens...")

for i, commit_hash in enumerate(commit_order, 1):
    new_msg = FIXES[commit_hash]

    print(f"\n   [{i:2}/11] {commit_hash} -> {new_msg}")

    # Cherry-pick without commit first
    success, _, _ = run(f'git cherry-pick {commit_hash} --no-commit')

    if not success:
        print(f"      ✗ Cherry-pick falhou")
        # Try to recover
        run('git cherry-pick --abort')
        sys.exit(1)

    # Commit com nova mensagem
    success, _, _ = run(f'git commit -m "{new_msg}"')

    if not success:
        print(f"      ✗ Commit falhou")
        run('git cherry-pick --abort')
        sys.exit(1)

    print(f"      ✓ OK")

print("\n" + "="*70)
print("4. Verificando resultado...")

success, log_out, _ = run('git log --oneline -15')

print("\n   Últimos 15 commits:")
for line in log_out.split('\n')[:15]:
    if line.strip():
        marker = " "
        if any(ord(c) > 127 for c in line):
            marker = "⚠"
        print(f"   {marker} {line}")

print("\n" + "="*70)
print("5. Validando encoding...")

success, log_all, _ = run('git log --format=%s HEAD~20..HEAD')

non_ascii = sum(1 for line in log_all.split('\n') if line and any(ord(c) > 127 for c in line))

if non_ascii == 0:
    print(f"   ✓ Todos os commits em ASCII puro!")
else:
    print(f"   ⚠ Encontrados {non_ascii} commits ainda com problemas")

print("\n" + "="*70)
print("6. Próximo passo:")
print("   git push origin main --force-with-lease")
print("="*70)
