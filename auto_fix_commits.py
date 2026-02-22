#!/usr/bin/env python3
"""
Automatiza git rebase interativo para corrigir encoding de commits
Usa GIT_SEQUENCE_EDITOR para editar a lista de rebase
"""

import subprocess
import os
import sys
import tempfile

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

def run_cmd(cmd, cwd=None):
    """Execute command"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode == 0, result.stdout, result.stderr

def create_sequence_editor():
    """Cria script que edita lista de rebase para marcar commits como 'edit'"""

    editor_code = f"""#!/usr/bin/env python3
import sys

# Commits que precisam ser editados
commits_to_edit = {list(COMMITS_TO_FIX.keys())}

if len(sys.argv) > 1:
    filename = sys.argv[1]

    with open(filename, 'r') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # Se a linha start com um dos commits problemáticos, marque como 'edit'
        for commit_hash in commits_to_edit:
            if line.startswith(f'pick {{commit_hash}}'):
                line = line.replace('pick', 'edit', 1)
                print(f"Marcando {{commit_hash}} como 'edit'", file=sys.stderr)
                break

        new_lines.append(line)

    with open(filename, 'w') as f:
        f.writelines(new_lines)
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(editor_code)
        return f.name

def amend_commit(new_message):
    """Amend commit atual com nova mensagem"""
    cmd = f'git commit --amend -m "{new_message}"'
    success, out, err = run_cmd(cmd)
    return success

def main():
    print("="*80)
    print("CORRECAO AUTOMATICA DE ENCODING DE COMMITS")
    print("="*80)

    os.chdir(r'c:\repo\crypto-futures-agent')

    # Criar backup
    print("\n1. Criando backup branch...")
    success, out, err = run_cmd("git branch fix-encoding-backup")
    if success or "already exists" in err:
        print("✓ Backup criado/existente")
    else:
        print(f"✗ Erro ao criar backup: {err}")
        sys.exit(1)

    # Começar rebase a partir do commit mais antigo problemático
    # O mais antigo é 7849056, vamos rebasar desde um antes dele
    print("\n2. Iniciando rebase interativo...")

    # Vamos fazer isso commit por commit para mais controle
    print("\n3. Corrigindo commits um a um...\n")

    for short_hash, new_msg in COMMITS_TO_FIX.items():
        print(f"\nProcessando {short_hash}...")

        # Rebase interativo começando do commit anterior
        cmd = f'git rebase -i {short_hash}^'

        # Para cada commit, vamos fazer um approach diferente:
        # Vamos usar git 's' (squash) ou melhor: fazer cherry-pick com nova msg

        success, out, err = run_cmd(cmd + ' --abort')  # Cancel any pending rebase

        # Verificar encoding da mensagem atual
        cmd_check = f'git log -1 --format=%s {short_hash}'
        _, current_msg, _ = run_cmd(cmd_check)
        current_msg = current_msg.strip()

        print(f"  Current: {current_msg}")
        print(f"  New:     {new_msg}")
        print(f"  Chars: {len(new_msg)}")

        # Validar se nova mensagem está em ASCII
        try:
            new_msg.encode('ascii')
            print(f"  ✓ Valido em ASCII")
        except UnicodeEncodeError:
            print(f"  ✗ Contem caracteres nao-ASCII!")
            continue

if __name__ == '__main__':
    main()
