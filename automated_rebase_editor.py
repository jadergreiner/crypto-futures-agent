#!/usr/bin/env python3
"""
Automaticamente marca 11 commits como 'edit' para rebase interativo
Usado como GIT_SEQUENCE_EDITOR
"""

import sys

EDIT_COMMITS = {
    '7849056', 'a229fab', 'fd1a7f8', '813e5fd',
    '09d2ecf', '1f2b75d', '0dcee01', 'b715f9a',
    '9b5166c', '6e04cd4', '81aa257'
}

if len(sys.argv) > 1:
    filepath = sys.argv[1]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            # Verificar se é linha de comando (pick/reword/etc)
            parts = line.split()

            if len(parts) >= 2 and parts[0] in ('pick', 'p'):
                commit_hash = parts[1]

                # Se é um dos commits que precisam editar
                if commit_hash in EDIT_COMMITS:
                    # Trocar pick para edit
                    newline = line.replace(f'{parts[0]} {commit_hash}', f'edit {commit_hash}', 1)
                    new_lines.append(newline)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
