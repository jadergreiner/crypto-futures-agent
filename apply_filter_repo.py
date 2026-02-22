#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import sys

def run_cmd(cmd):
    """Execute command"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def main():
    os.chdir(r'c:\repo\crypto-futures-agent')

    print("="*70)
    print("Git Filter Repo - Correcao de Encoding")
    print("="*70)

    print("\n1. Criando script de conversao...")

    # Criar mensagem converter em arquivo separado
    script_content = r'''import sys
msg = sys.stdin.read()

# Replace corrupted UTF-8 sequences
msg = msg.replace('recuperaÃ§Ã£o', 'recuperacao')
msg = msg.replace('Recuperaçao', 'Recuperacao')
msg = msg.replace('VotaÃ§Ã£o', 'Votacao')
msg = msg.replace('Votação', 'Votacao')
msg = msg.replace('UNANIME', 'UNANIME')
msg = msg.replace('UNÃ‚NIME', 'UNANIME')
msg = msg.replace('inicializaÃ§Ã£o', 'inicializacao')
msg = msg.replace('inicialização', 'inicializacao')
msg = msg.replace('ReuniaÃ£o', 'Reuniao')
msg = msg.replace('Reunião', 'Reuniao')
msg = msg.replace('PrepareÃ§Ã£o', 'Preparacao')
msg = msg.replace('Preparação', 'Preparacao')
msg = msg.replace('HeurÃsticas', 'Heuristicas')
msg = msg.replace('HeurÃ­sticas', 'Heuristicas')
msg = msg.replace('Heurísticas', 'Heuristicas')

# Remove em-dash and other non-ASCII
msg = msg.replace('â€"', '-')
msg = msg.replace('â€"', '--')
msg = msg.replace('âœ…', '')
msg = msg.replace('Ô£à', '')
msg = msg.replace('â€', '')
msg = msg.replace('Ô', '')

# Generic cleanup: remove non-ASCII
result = ""
for c in msg:
    if ord(c) < 128:
        result += c
    elif c == ' ':
        result += ' '

msg = result.strip()
msg = " ".join(msg.split())  # Clean multiple spaces

print(msg, end='')
'''

    with open('.git_filter_callback.py', 'w', encoding='utf-8') as f:
        f.write(script_content)

    print("  Created: .git_filter_callback.py")

    print("\n2. Running git-filter-repo...")

    success, out, err = run_cmd(
        'git filter-repo --message-callback "python .git_filter_callback.py" -f'
    )

    print(f"\nResult:")
    if success:
        print(f"  Success!")
        print(out[:300] if out else "(no output)")
    else:
        print(f"  Error: {err[:500]}")
        return False

    print("\n3. Verificando resultado...")
    success, out, _ = run_cmd("git log --oneline -12")
    print("\nFirst 12 commits:")
    print(out)

    print("\n" + "="*70)
    print("Para fazer push com force:")
    print("  git push origin main --force-with-lease")
    print("="*70)

    return True

if __name__ == '__main__':
    if not main():
        sys.exit(1)
