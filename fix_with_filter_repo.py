#!/usr/bin/env python3
"""
Script para corrigir encoding de commit messages usando git-filter-repo
"""

import subprocess
import tempfile
import os
import sys
import shutil
from pathlib import Path

def run_command(cmd, shell=True):
    """Execute command and return success status"""
    print(f"-> {cmd}")
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

# Mapeamento de commits para corrigir
COMMIT_FIXES = {
    'recuperacao': 'recuperacao',  # recuperação corrupted - fix double encoding
    'Votacao': 'Votacao',  # Votação corrupted
    'UNANIME': 'UNANIME',  # UNANIME corrupted
    'inicializacao': 'inicializacao',  # inicialização corrupted
    'Reuniao': 'Reuniao',  # Reunião corrupted
    'Preparacao': 'Preparacao',  # Preparação corrupted
    'Heuristicas': 'Heuristicas',  # Heuristicas corrupted
    # Remove non-ASCII markers
    'em dash': '-',  # Em dash encoded
    'corruption': '',  # Corruption marker
    'checkmark': '',  # Checkmark
}

def fix_message(msg):
    """Convert message to ASCII puro"""
    result = msg

    # Apply all conversions
    for corrupted, correct in COMMIT_FIXES.items():
        result = result.replace(corrupted, correct)

    # Remove any remaining non-ASCII
    result = ''.join(c if ord(c) < 128 else '' for c in result)

    # Clean multiple spaces
    result = ' '.join(result.split())

    return result

def main():
    os.chdir(r'c:\repo\crypto-futures-agent')

    print("="*70)
    print("GIT-FILTER-REPO: CORRECAO DE ENCODING")
    print("="*70)

    print("\n1. Criando callback script...")

    # Criar Python script temporário para callback
    callback_script = '''
import sys

# Dicionario de conversoes
conversions = {
    "recuperaÃ§Ã£o": "recuperacao",
    "Vota├º├úo": "Votacao",
    "UN├éNIME": "UNANIME",
    "inicializa├º├úo": "inicializacao",
    "Reuni├úo": "Reuniao",
    "PreparaÃ§Ã£o": "Preparacao",
    "HeurÃsticas": "Heuristicas",
    "â€"": "-",
    "â€": "",
    "âœ…": "",
    "Ô£à": "",
    "Ô": "",
    "ç": "c",
    "Ã": "",
    "├": "",
}

msg = sys.stdin.read()

# Apply conversions
for old, new in conversions.items():
    msg = msg.replace(old, new)

# Remove non-ASCII
msg = ''.join(c if ord(c) < 128 else '' for c in msg)

# Clean spaces
msg = ' '.join(msg.split())

print(msg, end='')
'''

    # Salvar temporário
    callback_file = "message_filter.py"
    with open(callback_file, 'w') as f:
        f.write(callback_script)

    print(f"  ✓ Criado: {callback_file}")

    print("\n2. Criando backup de segurança...")
    success, _, _ = run_command("git branch fix-encoding-cleanup-backup")
    print("  ✓ Branch backup criado")

    print("\n3. Executando git-filter-repo...")
    print("   Isto pode levar alguns minutos...")

    filter_cmd = (
        f'git filter-repo --message-callback '
        f'"python {callback_file}"'
    )

    success, stdout, stderr = run_command(filter_cmd)

    if success:
        print("\n✓ Filter-repo completado com sucesso!")
        print(f"  Stdout: {stdout[:200] if stdout else '(empty)'}")
    else:
        print(f"\n✗ Erro durante filter-repo:")
        print(f"  {stderr[:500]}")

        print("\n  Revertendo...")
        run_command("git reset --hard fix-encoding-cleanup-backup")
        print("  Revertido para backup")
        return False

    print("\n4. Verificando resultado...")

    # Ver primeiros commits
    success, log_output, _ = run_command("git log --oneline -15")
    if success:
        print("\n  Últimos 15 commits:")
        for line in log_output.split('\n')[:15]:
            if line:
                print(f"    {line}")

    print("\n5. Validando encoding...")

    # Verificar se ainda tem não-ASCII
    success, log_full, _ = run_command("git log --format=%s HEAD~20..HEAD")

    non_ascii_count = 0
    for line in log_full.split('\n'):
        if line:
            has_non_ascii = any(ord(c) > 127 for c in line)
            if has_non_ascii:
                non_ascii_count += 1
                print(f"  ✗ Ainda tem não-ASCII: {line[:50]}")

    if non_ascii_count == 0:
        print("  ✓ Todos os commits em ASCII puro!")
    else:
        print(f"  ⚠ Encontrados {non_ascii_count} commits com problemas restantes")

    print("\n" + "="*70)
    print("PROXIMO PASSO:")
    print("  git push origin main --force-with-lease")
    print("="*70)

    # Cleanup
    try:
        os.remove(callback_file)
    except:
        pass

    return True

if __name__ == '__main__':
    if not main():
        sys.exit(1)
