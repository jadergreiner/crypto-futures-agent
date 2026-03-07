#!/usr/bin/env python3
"""
Corretor para MD032 (blanks around lists) e MD036 (emphasis instead of heading).

MD032: Listas devem ser rodeadas por linhas em branco
MD036: Usar heading em vez de ênfase para seções principais
"""

import re
import sys
from pathlib import Path


def fix_blanks_around_lists(content):
    """
    Adiciona linhas em branco ao redor de listas.
    
    Regra: Uma lista deve ter linha em branco antes e depois.
    """
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        # Detectar início de lista (linhas com -, *, ou +)
        is_list_item = bool(
            re.match(r'^\s*[-*+]\s', line)
        )

        # Adicionar linha em branco ANTES de lista se necessário
        if is_list_item and i > 0:
            prev_line = lines[i - 1]
            is_prev_list = bool(
                re.match(r'^\s*[-*+]\s', prev_line)
            )
            is_prev_empty = not prev_line.strip()

            if not is_prev_list and not is_prev_empty and \
                    prev_line.strip() and not prev_line.startswith('#'):
                # Inserir linha em branco (se não foi adicionada antes)
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append('')

        fixed_lines.append(line)

        # Adicionar linha em branco DEPOIS de lista se necessário
        if is_list_item and i + 1 < len(lines):
            next_line = lines[i + 1]
            is_next_list = bool(
                re.match(r'^\s*[-*+]\s', next_line)
            ) or next_line.startswith('  ')  # Sublista indentada
            is_next_empty = not next_line.strip()

            if not is_next_list and not is_next_empty and \
                    next_line.strip() and not next_line.startswith('#'):
                # Marcar para adicionar espaço depois (se não for último)
                if i + 1 == len(lines) - 1:
                    pass  # Não adicionar no último
                else:
                    # Será adicionado antes do próximo item
                    pass

    # Segunda passagem: garantir espaço após listas finais
    final_lines = []
    for i, line in enumerate(fixed_lines):
        final_lines.append(line)

        is_list_item = bool(
            re.match(r'^\s*[-*+]\s', line)
        )

        if is_list_item and i + 1 < len(fixed_lines):
            next_line = fixed_lines[i + 1]
            is_next_list = bool(
                re.match(r'^\s*[-*+]\s', next_line)
            ) or next_line.startswith('  ')
            is_next_empty = not next_line.strip()

            if not is_next_list and not is_next_empty and \
                    next_line.strip() and not next_line.startswith('#'):
                if not (i + 2 < len(fixed_lines) and 
                        not fixed_lines[i + 2].strip()):
                    final_lines.append('')

    return '\n'.join(final_lines)


def fix_emphasis_as_heading(content):
    """
    Detecta ênfase usada como heading (MD036) e converte para heading real.
    
    Exemplo: **## Exemplo** → ### Exemplo
    """
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Detectar padrão de ênfase que parece um heading
        # **### Texto** ou ***Texto*** em contexto de heading
        if line.strip().startswith('**#'):
            # Extrair número de # e texto
            match = re.match(r'^\s*\*+#(#+)\s+(.+?)\*+\s*$', line)
            if match:
                hashes = match.group(1)
                text = match.group(2)
                # Converter para heading real
                indent = len(line) - len(line.lstrip())
                line = ' ' * indent + '###' + hashes + ' ' + text

        # Detectar ***texto*** como heading (rare mas acontece)
        elif line.strip().startswith('***') and \
                line.strip().endswith('***') and \
                '##' not in line:
            # Se a linha tem muitos *, pode ser heading
            match = re.match(
                r'^\s*\*{3,}([^*]+?)\*{3,}\s*$',
                line
            )
            if match and len(match.group(1)) > 5:
                # Pode ser um heading
                text = match.group(1).strip()
                indent = len(line) - len(line.lstrip())
                # Usar como heading nivel 2
                line = ' ' * indent + '## ' + text.upper()

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

    print("[*] Corrigindo MD032 (blanks around lists)...")
    fixed = fix_blanks_around_lists(original)

    print("[*] Corrigindo MD036 (emphasis as heading)...")
    fixed = fix_emphasis_as_heading(fixed)

    # Backup
    backup_path = filepath.with_suffix('.md.bak3')
    backup_path.write_text(original, encoding='utf-8')
    print(f"[✓] Backup salvo em: {backup_path}")

    # Salvar
    filepath.write_text(fixed, encoding='utf-8')
    print(f"[✓] Arquivo corrigido salvo em: {filepath}")

    # Estatísticas
    original_lines = original.count('\n')
    fixed_lines = fixed.count('\n')
    print(f"\n[Estatísticas]")
    print(f"  Linhas originais: {original_lines}")
    print(f"  Linhas após correção: {fixed_lines}")
    print(f"  Diferença: {fixed_lines - original_lines:+d} linhas")

    print("\n[✓] Próximo passo: markdownlint --config .markdownlint.json " \
          "docs/SYNCHRONIZATION.md")


if __name__ == '__main__':
    main()
