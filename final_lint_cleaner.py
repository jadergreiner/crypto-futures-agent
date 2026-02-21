#!/usr/bin/env python3
"""
Markdown Final Lint Cleaner — Remove trailing whitespace + quebra linhas longas
"""

import re
from pathlib import Path

def fix_trailing_whitespace(content):
    """Remove trailing whitespace de cada linha"""
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    return '\n'.join(lines)

def break_long_line(line, max_width=80):
    """Quebra linhas que excedem max_width em pontos lógicos"""
    if len(line) <= max_width:
        return [line]
    
    # Skip lines that shouldn't be broken
    if line.strip().startswith('```') or line.strip().startswith('http'):
        return [line]
    
    # Para markdown links [texto](url), não quebra
    if re.match(r'^\[.+\]\(.+\)$', line.strip()):
        return [line]
    
    # Try to break at word boundaries
    words = line.split(' ')
    lines = []
    current = ''
    
    for word in words:
        test = current + (' ' if current else '') + word
        if len(test) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    
    if current:
        lines.append(current)
    
    return lines if len(lines) > 1 else [line]

def fix_markdown_complete(filepath):
    """Limpa lint completo: trailing + long lines + MD040 já feito"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. Remove trailing whitespace
    content = fix_trailing_whitespace(content)
    
    # 2. Break long lines (exceto certos tipos)
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if len(line) > 80:
            # Não quebra URLs, código dentro de ``` ou markdown especial
            if line.strip().startswith('```') or line.strip().startswith('>'):
                fixed_lines.append(line)
            elif '```' in line and '```' in line:  # inline code
                fixed_lines.append(line)
            else:
                # Try to break
                broken = break_long_line(line)
                fixed_lines.extend(broken)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

# Main
def main():
    print('MARKDOWN FINAL LINT CLEANER\n')
    print('='*70)
    
    # Project files only
    md_files = [
        f for f in Path('.').rglob('*.md')
        if 'venv' not in str(f) and '.pytest_cache' not in str(f)
    ]
    
    print(f'Processando {len(md_files)} arquivos\n')
    
    fixed_count = 0
    for md_file in sorted(md_files):
        try:
            if fix_markdown_complete(str(md_file)):
                fixed_count += 1
                print(f'✅ {str(md_file)}')
        except Exception as e:
            print(f'⚠️  {str(md_file)}: {e}')
    
    print('\n' + '='*70)
    print(f'Arquivos processados: {fixed_count}')
    print('✅ LINT CLEANING COMPLETE')

if __name__ == '__main__':
    main()
