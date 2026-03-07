#!/usr/bin/env python3
"""
Corretor automático de erros lint Markdown básicos.

Corrige:
- MD040: Adiciona linguagem a blocos de código
- MD031: Adiciona linhas em branco ao redor de blocos
- MD024: Renomeia headings duplicados

Uso:
  python fix_markdown_lint.py docs/SYNCHRONIZATION.md
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def fix_code_block_language(content):
    """
    Adiciona linguagem a blocos de código sem especificação.
    Detecta contexto para sugerir linguagem apropriada.
    """
    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detectar bloco ``` sem linguagem
        if line.strip() == '```':
            # Procurar contexto anterior para detectar tipo
            context = ''
            for j in range(max(0, i - 5), i):
                context += lines[j].lower() + ' '

            # Inteligência: determinar linguagem baseado em contexto
            if 'sql' in context or 'database' in context or 'query' in context:
                suggested = 'sql'
            elif 'python' in context or 'script' in context or '.py' in context:
                suggested = 'python'
            elif 'bash' in context or 'command' in context or '$' in context \
                    or 'terminal' in context or 'shell' in context:
                suggested = 'bash'
            elif 'json' in context:
                suggested = 'json'
            elif 'yaml' in context or 'yml' in context:
                suggested = 'yaml'
            elif 'markdown' in context or '.md' in context:
                suggested = 'markdown'
            else:
                # Default: tentar detectar pelo conteúdo do bloco
                suggested = detect_language_from_content(lines, i)

            # Adicionar linguagem
            fixed_lines.append(f'```{suggested}')
            i += 1

            # Processar conteúdo do bloco até encontrar fechamento
            while i < len(lines) and lines[i].strip() != '```':
                fixed_lines.append(lines[i])
                i += 1

            # Adicionar fechamento
            if i < len(lines):
                fixed_lines.append('```')
                i += 1
        else:
            fixed_lines.append(line)
            i += 1

    return '\n'.join(fixed_lines)


def detect_language_from_content(lines, start_idx):
    """Detecta linguagem pelo conteúdo do bloco de código."""
    content = ''
    for i in range(start_idx + 1, min(start_idx + 20, len(lines))):
        if lines[i].strip() == '```':
            break
        content += lines[i] + '\n'

    # Heurísticas
    if 'import ' in content or 'def ' in content or 'class ' in content:
        return 'python'
    elif 'SELECT' in content.upper() or 'INSERT' in content.upper():
        return 'sql'
    elif '{' in content and '"' in content:
        return 'json'
    elif '--' in content or '#!/bin/bash' in content:
        return 'bash'
    else:
        return 'txt'


def fix_blank_around_fences(content):
    """Adiciona linhas em branco ao redor de blocos de código."""
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        # Adicionar linha em branco ANTES de ```
        if line.strip().startswith('```') and i > 0:
            prev_line = fixed_lines[-1] if fixed_lines else ''
            if prev_line.strip():  # Se a linha anterior não é vazia
                fixed_lines.append('')

        fixed_lines.append(line)

        # Adicionar linha em branco DEPOIS de ```
        if line.strip().startswith('```') and line.strip().endswith('```'):
            # Bloco de uma linha (raro)
            if i + 1 < len(lines) and lines[i + 1].strip():
                fixed_lines.append('')

    return '\n'.join(fixed_lines)


def fix_duplicate_headings(content):
    """Renomeia headings duplicados adicionando sufixo."""
    lines = content.split('\n')
    heading_counts = defaultdict(int)
    fixed_lines = []

    for line in lines:
        if line.startswith('#'):
            # Extrair nível e texto
            match = re.match(r'^(#+)\s+(.+)$', line)
            if match:
                level = match.group(1)
                text = match.group(2).strip()

                # Contar ocorrências
                heading_counts[text] += 1
                count = heading_counts[text]

                # Se é duplicado, adicionar sufixo
                if count > 1:
                    # Evitar sufixos muito óbvios; usar "(n)" discreto
                    new_text = f"{text} (#{count})"
                    line = f"{level} {new_text}"

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Arquivo não encontrado: {filepath}")
        sys.exit(1)

    print(f"[*] Lendo {filepath}...")
    original = filepath.read_text(encoding='utf-8')

    # Aplicar correções em sequência
    print("[*] Corrigindo MD040 (language in code blocks)...")
    fixed = fix_code_block_language(original)

    print("[*] Corrigindo MD031 (blanks around fences)...")
    fixed = fix_blank_around_fences(fixed)

    print("[*] Corrigindo MD024 (duplicate headings)...")
    fixed = fix_duplicate_headings(fixed)

    # Salvar backup
    backup_path = filepath.with_suffix('.md.bak')
    backup_path.write_text(original, encoding='utf-8')
    print(f"[✓] Backup salvo em: {backup_path}")

    # Salvar arquivo corrigido
    filepath.write_text(fixed, encoding='utf-8')
    print(f"[✓] Arquivo corrigido salvo em: {filepath}")

    # Statisticas
    original_lines = original.count('\n')
    fixed_lines = fixed.count('\n')
    print(f"\n[Estatísticas]")
    print(f"  Linhas originais: {original_lines}")
    print(f"  Linhas após correção: {fixed_lines}")
    print(f"  Diferença: {fixed_lines - original_lines} linhas")

    print("\n[✓] Próximo passo: rodar 'markdownlint docs/SYNCHRONIZATION.md' " \
          "para validar")


if __name__ == '__main__':
    main()
