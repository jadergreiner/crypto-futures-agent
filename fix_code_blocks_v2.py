#!/usr/bin/env python3
"""
Markdown Code Block Fixer v2 — Corrige espacos e langs faltando
Estratégia: 
  1. Encontra ``` puro (sem language)
  2. Adiciona language basado em contexto
  3. Trata casos especiais (YAML, JSON configs)
"""

import re
from pathlib import Path

def detect_language_context(lines, block_start):
    """Detecta language basado no contexto antes do bloco"""
    # Look back até 5 linhas
    for i in range(max(0, block_start-5), block_start):
        line_lower = lines[i].lower()
        if 'python' in line_lower or '.py' in line_lower:
            return 'python'
        elif 'json' in line_lower or '"' in line_lower:
            return 'json'
        elif 'yaml' in line_lower or '.yml' in line_lower or 'yml:' in line_lower:
            return 'yaml'
        elif 'bash' in line_lower or 'shell' in line_lower or '$ ' in line_lower or '# ' in line_lower:
            return 'bash'
        elif 'sql' in line_lower:
            return 'sql'
        elif 'html' in line_lower:
            return 'html'
        elif 'javascript' in line_lower or '.js' in line_lower or 'node' in line_lower:
            return 'javascript'
        elif 'typescript' in line_lower or '.ts' in line_lower:
            return 'typescript'
    
    # Olha para frente — tipo de conteúdo
    if block_start + 1 < len(lines):
        first_content = lines[block_start + 1].strip()
        if first_content.startswith('{') or first_content.startswith('['):
            return 'json'
        elif first_content.startswith('import ') or first_content.startswith('def ') or first_content.startswith('class '):
            return 'python'
        elif first_content.startswith('SELECT ') or first_content.startswith('INSERT '):
            return 'sql'
        elif first_content.startswith('<!DOCTYPE') or first_content.startswith('<'):
            return 'html'
        elif first_content.startswith('$') or first_content.startswith('#'):
            return 'bash'
    
    # Default
    return 'text'

def fix_code_blocks_better(filepath):
    """Fix code blocks com heurística melhorada"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Procura por ``` puro (sem language)
        if line.strip() == '```':
            # Esta é uma abertura de bloco
            lang = detect_language_context(lines, i)
            fixed_lines.append('```' + lang)
        else:
            fixed_lines.append(line)
        
        i += 1
    
    new_content = '\n'.join(fixed_lines)
    
    if new_content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    return False

# Main
def main():
    print('MARKDOWN CODE BLOCK FIXER v2 — Detecção de Linguagem\n')
    print('='*70)
    
    # Exclude venv and .pytest_cache
    md_files = [
        f for f in Path('.').rglob('*.md')
        if 'venv' not in str(f) and '.pytest_cache' not in str(f)
    ]
    
    print(f'Processando {len(md_files)} arquivos (excluindo venv)\n')
    
    fixed_count = 0
    for md_file in sorted(md_files):
        try:
            if fix_code_blocks_better(str(md_file)):
                fixed_count += 1
                print(f'✅ {str(md_file)}')
        except Exception as e:
            print(f'⚠️  {str(md_file)}: {e}')
    
    print('\n' + '='*70)
    print(f'Arquivos corrigidos: {fixed_count}')
    print('✅ CODE BLOCK FIX COMPLETE')

if __name__ == '__main__':
    main()
