#!/usr/bin/env python3
"""
Script para corrigir commits de forma segura via rebase programático
"""

import subprocess
import sys
import os

os.chdir(r'c:\repo\crypto-futures-agent')

# Mapeamento de commits que precisam corrigir
FIXES = [
    ('7849056', '[FEAT] TASK-001 Heuristicas implementadas'),
    ('a229fab', '[TEST] TASK-002 QA Testing 40/40 testes ok'),
    ('fd1a7f8', '[PLAN] TASK-004 Preparacao go-live canary'),
    ('813e5fd', '[VALIDATE] TASK-003 Alpha SMC Validation OK'),
    ('09d2ecf', '[CLOSE] Reuniao Board 21 FEV encerrada'),
    ('1f2b75d', '[BOARD] Reuniao 16 membros Go-Live Auth'),
    ('0dcee01', '[INFRA] Board Orchestrator 16 membros setup'),
    ('b715f9a', '[DOCS] Integration Summary Board 16 membros'),
    ('9b5166c', '[BOARD] Votacao Final GO-LIVE aprovada unanime'),
    ('6e04cd4', '[GOLIVE] Canary Deployment Phase 1 iniciado'),
    ('81aa257', '[PHASE2] Script recuperacao dados conta real'),
]

def run(cmd):
    """Execute command"""
    print(f"→ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Error: {result.stderr[:200]}")
        return False
    if result.stdout.strip():
        print(f"  ✓ {result.stdout.strip()[:100]}")
    return True

def amend_commit_message(commit_hash, new_message):
    """
    Amend menssagem de um commit específico
    """
    print(f"\n{'='*60}")
    print(f"Corrigindo commit {commit_hash}")
    print(f"{'='*60}")

    # Usar rebase para chegar no commit
    cmd_rebase = f"git rebase -i {commit_hash}^ --autostash"

    # Não vamos usar rebase interativo, vamos usar uma tecnica diferente
    # Usar git commit-tree para recrear o commit com nova mensagem

    # Primeiro, conseguir info do commit
    cmd_tree = f"git rev-parse {commit_hash}^{{tree}}"
    result = subprocess.run(cmd_tree, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Nao consegui pegar tree: {result.stderr}")
        return False

    tree_hash = result.stdout.strip()
    print(f"  tree: {tree_hash}")

    # Conseguir parent
    cmd_parent = f"git rev-parse {commit_hash}^"
    result = subprocess.run(cmd_parent, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Nao consegui pegar parent")
        return False

    parent_hash = result.stdout.strip()
    print(f"  parent: {parent_hash}")

    # Conseguir author info
    cmd_author = f'git log -1 --format="%aN <%aE>" {commit_hash}'
    result = subprocess.run(cmd_author, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Nao consegui pegar author")
        return False

    author = result.stdout.strip()
    print(f"  author: {author}")

    # Conseguir date
    cmd_date = f'git log -1 --format="%aD" {commit_hash}'
    result = subprocess.run(cmd_date, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Nao consegui pegar date")
        return False

    date = result.stdout.strip()
    print(f"  date: {date}")

    # Criar novo commit com git commit-tree
    # Usa: git commit-tree <tree sha> -p <parent sha> -m 'mensagem'
    #      -c <original commit for author/date>

    # Mais simples: usar git reset + amend + rebase
    print(f"\n  Estratégia: Reset + amend + rebase")

    # Checkout na branch de origem
    if not run("git checkout main"):
        print("  ✗ Falha ao checkout main")
        return False

    # Fazer rebase desde o parent do commit
    # Marcar como 'edit' e após amend, continuar

    # Na verdade, vamos usar um approach mais seguro com filter-repo ao invés
    # Mas para agora, vamos fazer cherry-pick de todos os commits após este

    print("  Abordagem: Usar rebase programático via shell script")

    # Para cada commit, fazer:
    # 1. git rebase -i <parent> (vai abrir editor)
    # 2. Marcar commit como 'edit'
    # 3. git commit --amend -m 'nova mensagem'
    # 4. git rebase --continue

    # Vamos usar GIT_EDITOR para automatizar

    return True

def main():
    print("="*70)
    print("CORRECAO DE COMMITS - ABORDAGEM SEGURA")
    print("="*70)

    # Verificar status
    print("\n1. Verificando status...")
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("  ⚠ Working tree nao esta limpo!")
        print(result.stdout)
        print("\n  Execute: git add . && git commit -m '[WIP] temp'")
        return False

    print("  ✓ Working tree limpo")

    # Listar commits que vão ser corrigidos
    print("\n2. Commits que serão corrigidos:")
    for i, (hash_short, msg) in enumerate(FIXES, 1):
        print(f"  {i:2}. {hash_short} → {msg[:50]}")

    print("\n" + "="*70)
    print("AVISO: Isto vai reescrever o histórico!")
    print("  - Backup já existe em: fix-encoding-backup")
    print("  - Se algo der errado: git reset --hard fix-encoding-backup")
    print("="*70)

    response = input("\nContinuar com rebase? (S/n): ").strip().lower()
    if response in ('n', 'no'):
        print("Cancelado.")
        return False

    print("\n3. Iniciando rebase...")

    # TODO: Implementar rebase programático com git filter-branch ou
    #       usando a biblioteca gitpython ao invés de shell commands

    # Por enquanto, listar o que precisa fazer
    print("\nPara fazer a correção manualmente, execute os comandos abaixo:")
    print("\n" + "-"*70)

    for hash_short, new_msg in FIXES:
        print(f"\n# Commit {hash_short}")
        print(f"git rebase -i {hash_short}^")
        print(f"# (Marque 'edit' na linha do {hash_short})")
        print(f"git commit --amend -m \"{new_msg}\"")
        print(f"git rebase --continue")

    print("\n" + "-"*70)
    print("\nOU use git filtro-repo se disponível:")
    print("  pip install git-filter-repo")
    print("  git clone file:///c:/repo/crypto-futures-agent crypto-working")
    print("  cd crypto-working")
    print("  git filter-repo --message-callback 'python -c \"...\"' -f")

if __name__ == '__main__':
    main()
