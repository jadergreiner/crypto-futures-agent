#!/usr/bin/env python3
"""
Validador de Markdown Lint — verifica se todos os erros foram corrigidos
Valida:
  - MD040: Fenced code blocks com language
  - MD009: Trailing whitespace
  - Linha máxima: 80 caracteres
"""

import os
import re
from pathlib import Path

def validate_markdown_file(filepath):
    """Validate lint compliance for a single markdown file"""

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    errors = []

    # 1. Check MD040: Fenced code blocks must have language
    in_block = False
    for i, line in enumerate(lines, 1):
        if line.strip() == '```':
            if not in_block:
                # Opening fence — should have language
                errors.append(f'MD040: Line {i}: Fenced code block without language')
            in_block = not in_block
        elif line.strip().startswith('```'):
            # This is OK — has language
            pass

    # 2. Check MD009: Trailing whitespace
    for i, line in enumerate(lines, 1):
        if line.rstrip('\n') != line.rstrip('\n').rstrip():
            errors.append(f'MD009: Line {i}: Trailing whitespace')

    # 3. Check line length: max 80 chars
    for i, line in enumerate(lines, 1):
        if len(line.rstrip()) > 80:
            errors.append(f'LINE_LENGTH: Line {i}: {len(line.rstrip())} chars (max 80)')

    return errors

# Main: validate all markdown files
def main():
    print('\nMARKDOWN LINT VALIDATOR — Verificação Pós-Correção\n')
    print('='*70)

    md_files = list(Path('.').rglob('*.md'))
    print(f'Validando {len(md_files)} arquivos markdown...\n')

    total_errors = 0
    files_with_errors = 0
    files_ok = 0

    for md_file in sorted(md_files):
        try:
            errors = validate_markdown_file(str(md_file))
            if errors:
                files_with_errors += 1
                for error in errors[:3]:  # Show first 3 errors
                    print(f'❌ {str(md_file):60s}')
                    print(f'   → {error}')
                if len(errors) > 3:
                    print(f'   → ... e {len(errors)-3} mais erros')
                total_errors += len(errors)
            else:
                files_ok += 1
        except Exception as e:
            files_with_errors += 1
            print(f'⚠️  {str(md_file):60s} ERROR: {e}')
            total_errors += 1

    print('\n' + '='*70)
    print(f'\n✅ Arquivos OK: {files_ok}/{len(md_files)}')
    print(f'❌ Arquivos com erro: {files_with_errors}/{len(md_files)}')
    print(f'Total de erros encontrados: {total_errors}')

    if total_errors == 0:
        print('\n🎉 LINT VALIDATION PASSED — Sem erros!')
    else:
        print(f'\n⚠️  Ainda há {total_errors} erros a corrigir')

    print('='*70)

if __name__ == '__main__':
    main()
