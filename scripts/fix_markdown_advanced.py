#!/usr/bin/env python3
"""
Corretor avançado para MD013 (line length) e MD060 (table formatting).

Estratégia:
1. MD013: Quebra linhas longas mantendo semântica
   - Ignora URLs (exceto permitido por markdownlint)
   - Ignora linhas dentro de código
   - Quebra descrições em pontos lógicos
   
2. MD060: Reformata tabelas com espaçamento correto

Uso:
  python fix_markdown_advanced.py docs/SYNCHRONIZATION.md
"""

import re
import sys
from pathlib import Path


def is_url_or_exception(line):
    """Verifica se linha deve ser excluída do limite de 80 chars."""
    # URLs
    if 'http://' in line or 'https://' in line:
        return True
    # Linhas muito técnicas (caminhos, etc)
    if line.strip().startswith('##') and len(line) < 200:
        return False
    # Linhas de documentação muito longa podem ser mantidas em certos contextos
    if '```' in line:
        return True
    return False


def break_long_line(line, max_len=80):
    """
    Quebra linha longa mantendo semântica.
    
    Estratégia:
    1. Se tem parênteses em listas, quebra antes deles
    2. Se tem "e", "ou", quebra antes
    3. Se tem "-", quebra antes
    4. Se tem vírgula, quebra depois
    """
    if len(line) <= max_len or is_url_or_exception(line):
        return [line]

    # Se é uma lista/item, pode quebrar melhor
    if line.strip().startswith(('-', '*', '+')):
        # Item de lista
        indent = len(line) - len(line.lstrip())
        prefix = line[:indent]
        content = line[indent:].lstrip('-*+ ')

        # Se é uma lista com descrição em parênteses
        match = re.search(r'^(.*?)\s+\((.+)\)$', content)
        if match:
            name, desc = match.groups()
            # Quebrar após o parêntese de abertura se necessário
            if len(prefix + '- ' + name + ' (') <= max_len:
                return [
                    prefix + '- ' + name + ' (',
                    prefix + '  ' + desc + ')'
                ]

        # Se muy largo, tentar quebrar em "," ou "and"
        if ',' in content:
            parts = content.split(',')
            lines = []
            current_line = prefix + '- ' + parts[0]
            for part in parts[1:]:
                part = part.strip()
                if len(current_line) + len(part) + 2 <= max_len:
                    current_line += ', ' + part
                else:
                    lines.append(current_line + ',')
                    current_line = prefix + '  ' + part
            if current_line:
                lines.append(current_line)
            return lines if len(lines) > 1 else [line]

    # Para parágrafos normais, quebra em pontos lógicos
    if len(line) > max_len and not line.strip().startswith('#'):
        # Procurar pontos de quebra: " e ", " ou ", ", "
        breakpoints = []
        for sep in [' e ', ' ou ', ', ']:
            idx = 0
            while True:
                idx = line.find(sep, idx)
                if idx == -1:
                    break
                # Ajustar para quebrar DEPOIS do separador
                breakpoints.append(idx + len(sep))
                idx += 1

        # Encontrar o melhor ponto de quebra (estar perto do max_len)
        if breakpoints:
            best_bp = max([bp for bp in breakpoints if bp <= max_len],
                          default=None)
            if best_bp:
                part1 = line[:best_bp].rstrip()
                part2 = line[best_bp:].lstrip()
                if part2:
                    # Recursivamente quebrar parte 2 se ainda muito longa
                    return [part1] + break_long_line(part2, max_len)

    return [line]


def fix_table_formatting(content):
    """
    Reformata tabelas Markdown para MD060 conformidade.
    Garante espaço após pipes.
    """
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Detectar linhas de tabela (têm pipes)
        if '|' in line and not line.strip().startswith('```'):
            # Reformatar
            cells = line.split('|')

            # Limpar e reformatar cada célula
            formatted_cells = [cell.strip() for cell in cells]

            # Reconstruir com espaçamento correto
            formatted_line = ' | '.join(formatted_cells)

            # Assegurar que começa e termina com |
            if not formatted_line.startswith('|'):
                formatted_line = '| ' + formatted_line
            if not formatted_line.endswith('|'):
                formatted_line = formatted_line + ' |'

            fixed_lines.append(formatted_line)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def fix_line_lengths(content, max_len=80):
    """Quebra todas as linhas longas inteligentemente."""
    lines = content.split('\n')
    fixed_lines = []
    in_code_block = False

    for line in lines:
        # Rastrear blocos de código
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            fixed_lines.append(line)
            continue

        # Não quebrar dentro de blocos de código
        if in_code_block:
            fixed_lines.append(line)
            continue

        # Quebrar linhas longas
        if len(line) > max_len:
            broken = break_long_line(line, max_len)
            fixed_lines.extend(broken)
        else:
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
    print("[*] Corrigindo MD060 (table formatting)...")
    fixed = fix_table_formatting(original)

    print("[*] Corrigindo MD013 (line length)...")
    fixed = fix_line_lengths(fixed)

    # Criar backup
    backup_path = filepath.with_suffix('.md.bak2')
    backup_path.write_text(original, encoding='utf-8')
    print(f"[✓] Backup salvo em: {backup_path}")

    # Salvar arquivo corrigido
    filepath.write_text(fixed, encoding='utf-8')
    print(f"[✓] Arquivo corrigido salvo em: {filepath}")

    # Estatísticas
    original_lines = original.count('\n')
    fixed_lines = fixed.count('\n')
    print(f"\n[Estatísticas]")
    print(f"  Linhas originais: {original_lines}")
    print(f"  Linhas após correção: {fixed_lines}")
    print(f"  Diferença: {fixed_lines - original_lines:+d} linhas")

    # Contar linhas ainda > 80
    long_lines = sum(
        1 for line in fixed.split('\n')
        if len(line) > 80 and not is_url_or_exception(line)
    )
    print(f"  Linhas ainda > 80 chars (excluindo URLs): {long_lines}")

    print("\n[✓] Próximo passo: rodar 'markdownlint docs/SYNCHRONIZATION.md' " \
          "para validar")


if __name__ == '__main__':
    main()
