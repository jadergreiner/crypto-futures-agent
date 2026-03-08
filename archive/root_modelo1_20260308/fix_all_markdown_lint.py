#!/usr/bin/env python3
"""
Lint fixer para markdown — valida e corrige erros comuns
Erros tratados:
  - MD040: Fenced code blocks without language
  - MD009: Trailing whitespace
  - MD034: Bare URLs (URLs sem markdown links)
"""

import os
import re
from pathlib import Path

def fix_markdown_file(filepath):
    """Fix lint issues in a single markdown file"""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    issues_fixed = []

    # 1. Fix fenced code blocks without language (MD040)
    # Pattern: ``` followed by newline (no language specified)
    def fix_code_blocks(text):
        count = 0
        # Find all ``` blocks
        lines = text.split('\n')
        fixed_lines = []
        in_block = False
        block_start = -1

        for i, line in enumerate(lines):
            if line.strip().startswith('```'):
                if not in_block:
                    # Opening fence
                    if len(line.strip()) == 3:  # Just "```" with no language
                        # Try to infer language from context
                        if i > 0:
                            # Look at previous line for clues
                            prev = lines[i-1].lower()
                            if 'python' in prev or '.py' in prev:
                                line = '```python'
                                count += 1
                            elif 'json' in prev:
                                line = '```json'
                                count += 1
                            elif 'yaml' in prev or '.yml' in prev:
                                line = '```yaml'
                                count += 1
                            elif 'bash' in prev or 'shell' in prev or '$' in prev:
                                line = '```bash'
                                count += 1
                            elif 'sql' in prev or 'SELECT' in prev:
                                line = '```sql'
                                count += 1
                            elif 'markdown' in prev or '.md' in prev:
                                line = '```markdown'
                                count += 1
                            else:
                                # Default to text
                                line = '```text'
                                count += 1
                    in_block = True
                    block_start = i
                else:
                    # Closing fence
                    in_block = False

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), count

    content, code_count = fix_code_blocks(content)
    if code_count > 0:
        issues_fixed.append(f'MD040: {code_count} code blocks fixed')

    # 2. Fix trailing whitespace (MD009)
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)

    # 3. Fix bare URLs (MD034) — wrap in brackets if not already
    def fix_bare_urls(text):
        count = 0
        # Pattern: http(s):// followed by non-whitespace but NOT already in []()
        # This is tricky, so we'll be conservative
        lines = text.split('\n')
        fixed_lines = []

        for line in lines:
            # Skip if already in code block or link
            if line.strip().startswith('```') or line.strip().startswith('>'):
                fixed_lines.append(line)
                continue

            # Find bare URLs (http:// or https:// not in [] or ())
            # Simple check: if URL is not preceded by ] or (
            pattern = r'(?<![]\)])(https?://[^\s)]+)'
            def wrapin_link(match):
                url = match.group(1)
                # Remove trailing punctuation (., ,, etc) if any
                trailing = ''
                while url and url[-1] in '.,;:':
                    trailing = url[-1] + trailing
                    url = url[:-1]
                return f'[{url}]({url}){trailing}'

            new_line = re.sub(pattern, wrapin_link, line)
            if new_line != line:
                count += 1
            fixed_lines.append(new_line)

        return '\n'.join(fixed_lines), count

    content, url_count = fix_bare_urls(content)
    if url_count > 0:
        issues_fixed.append(f'MD034: {url_count} bare URLs wrapped')

    # Write back if changed
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return issues_fixed

    return []

# Main: scan all markdown files
def main():
    print('MARKDOWN LINT FIX — Full Project Scan\n')
    print('='*70)

    md_files = list(Path('.').rglob('*.md'))
    print(f'Found {len(md_files)} markdown files\n')

    total_fixed = 0
    files_with_fixes = 0

    for md_file in sorted(md_files):
        try:
            issues = fix_markdown_file(str(md_file))
            if issues:
                files_with_fixes += 1
                print(f'✅ {str(md_file):60s}')
                for issue in issues:
                    print(f'   • {issue}')
                    total_fixed += 1
        except Exception as e:
            print(f'⚠️  {str(md_file):60s} ERROR: {e}')

    print('\n' + '='*70)
    print(f'\nFiles fixed: {files_with_fixes}')
    print(f'Total issues fixed: {total_fixed}')
    print(f'✅ MARKDOWN LINT FIX COMPLETE')

if __name__ == '__main__':
    main()
