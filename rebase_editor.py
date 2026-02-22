#!/usr/bin/env python3
"""Editor automático para git rebase -i"""

import sys

# Commits que precisam 'edit'
EDIT_COMMITS = {
    '7849056', 'a229fab', 'fd1a7f8', '813e5fd', '09d2ecf',
    '1f2b75d', '0dcee01', 'b715f9a', '9b5166c', '6e04cd4', '81aa257'
}

# Mensagens corrigidas para cada commit
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

if len(sys.argv) > 1:
    filename = sys.argv[1]

    with open(filename, 'r') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        parts = line.split()

        # Se é uma linha de comando (pick, reword, edit, etc)
        if len(parts) >= 2:
            cmd = parts[0]
            commit = parts[1]

            # Se é um pick ou p de um commit que precisa edit
            if cmd in ('pick', 'p') and commit in EDIT_COMMITS:
                # Trocar para edit
                line = line.replace(cmd, 'edit', 1)

        new_lines.append(line)

    with open(filename, 'w') as f:
        f.writelines(new_lines)

    sys.exit(0)
