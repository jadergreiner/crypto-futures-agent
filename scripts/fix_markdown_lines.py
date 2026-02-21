#!/usr/bin/env python3
"""
Script inteligente para corrigir linhas > 80 caracteres em Markdown.
Mantém semântica: quebra linhas em pontos lógicos (vírgulas, -, etc).
"""

import re
from pathlib import Path
import sys

class MarkdownFixer:
    """Corrige linhas > 80 chars em MD mantendo estrutura."""

    MAX_LINE_LEN = 80

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.content = self.filepath.read_text(encoding='utf-8')
        self.fixed = False

    def fix_line_length(self) -> bool:
        """Corrige linhas longas."""
        lines = self.content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines, 1):
            if len(line) > self.MAX_LINE_LEN:
                # Não quebrar linhas em blocos de código
                if line.strip().startswith('```') or line.strip().startswith('    '):
                    fixed_lines.append(line)
                    continue

                # Quebrar links inline
                if '[' in line and '](' in line:
                    fixed = self._break_link_line(line)
                    fixed_lines.extend(fixed)
                    self.fixed = True
                # Quebrar listas
                elif line.strip().startswith(('-', '*', '•')) and len(line) > self.MAX_LINE_LEN:
                    fixed = self._break_list_item(line)
                    fixed_lines.extend(fixed)
                    self.fixed = True
                # Quebrar parágrafos normais
                elif not line.startswith('#') and '|' not in line:  # Não quebrar headers ou tabelas
                    fixed = self._break_paragraph(line)
                    fixed_lines.extend(fixed)
                    self.fixed = True
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        self.content = '\n'.join(fixed_lines)
        return self.fixed

    def _break_link_line(self, line: str) -> list:
        """Quebra linhas com links longos."""
        # Detectar padrão: texto [link](url)
        pattern = r'(\*\*.*?\*\*|\w+).*?\[(.*?)\]\((.*?)\)'

        if re.search(pattern, line):
            # Quebra antes do link
            indent = len(line) - len(line.lstrip())
            parts = re.split(r'\s+(?=\[)', line)

            result = []
            current = ""

            for part in parts:
                if len(current) + len(part) + 1 > self.MAX_LINE_LEN:
                    if current:
                        result.append(current)
                    current = ' ' * indent + part
                else:
                    current = (current + ' ' + part).lstrip() if current else part

            if current:
                result.append(current)

            return result if result else [line]

        return [line]

    def _break_list_item(self, line: str) -> list:
        """Quebra itens de lista longa."""
        indent = len(line) - len(line.lstrip())
        marker = line.lstrip()[0]  # '-', '*', '•'
        content = line.lstrip()[1:].lstrip()

        # Quebra por vírgula ou 'e'
        if ',' in content:
            parts = content.split(',')
            result = []
            current_item = f"{' ' * indent}{marker} {parts[0].strip()}"

            for part in parts[1:]:
                test = current_item + ", " + part.strip()
                if len(test) > self.MAX_LINE_LEN:
                    result.append(current_item + ",")
                    current_item = f"{' ' * (indent + 2)}{part.strip()}"
                else:
                    current_item = test

            result.append(current_item)
            return result

        # Quebra por palavras
        words = content.split()
        result = []
        current = f"{' ' * indent}{marker} "

        for word in words:
            if len(current + word) > self.MAX_LINE_LEN:
                result.append(current.rstrip())
                current = f"{' ' * (indent + 2)}{word} "
            else:
                current += word + " "

        result.append(current.rstrip())
        return result

    def _break_paragraph(self, line: str) -> list:
        """Quebra parágrafos normais."""
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        words = content.split()
        result = []
        current = ' ' * indent

        for word in words:
            if len(current + ' ' + word) > self.MAX_LINE_LEN:
                if current.strip():
                    result.append(current.rstrip())
                    current = ' ' * indent
            current += word + ' '

        if current.strip():
            result.append(current.rstrip())

        return result if result else [line]

    def save(self) -> bool:
        """Salva arquivo modificado."""
        if self.fixed:
            self.filepath.write_text(self.content, encoding='utf-8')
            print(f"✅ Corrigido: {self.filepath.name}")
            return True
        return False


def main():
    """Processa múltiplos arquivos."""
    files = [
        'README.md',
        'CHANGELOG.md',
        'projects/SUMMARY.md',
    ]

    docs_dir = Path('docs')
    if docs_dir.exists():
        files.extend([f.name for f in docs_dir.glob('*.md')])

    fixed_count = 0

    for filepath in files:
        p = Path(filepath)
        if p.exists():
            fixer = MarkdownFixer(str(p))
            if fixer.fix_line_length():
                if fixer.save():
                    fixed_count += 1

    print(f"\n✅ Total de arquivos corrigidos: {fixed_count}")
    return fixed_count > 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
