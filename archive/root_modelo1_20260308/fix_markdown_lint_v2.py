#!/usr/bin/env python3
"""Aggressively fix markdown lint — force all lines to 80 char max"""

import os
import re

def force_line_width(filepath, max_len=80):
    """Force all lines to max_len by breaking at word boundaries"""

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    changed = 0

    for line in lines:
        original_line = line.rstrip('\n')

        # Code blocks, empty lines, URL lines — keep as-is
        if (original_line.startswith('```') or
            original_line.startswith('    ') or
            not original_line.strip() or
            original_line.startswith('http')):
            fixed_lines.append(line)
            continue

        # Table rows — convert to multiple lines if needed
        if '|' in original_line and len(original_line) > max_len:
            # Break table rows at pipes
            cells = original_line.split('|')
            if len(cells) > 2:
                # Rebuild as wrapped lines
                first_part = '|'.join(cells[:2]) + '|'
                if len(first_part) <= max_len:
                    fixed_lines.append(first_part + '\n')
                    remaining = '|' + '|'.join(cells[2:])
                    if remaining.endswith('|'):
                        remaining = remaining[:-1]
                    fixed_lines.append(remaining + '|\n')
                    changed += 1
                    continue

        # Regular text lines
        if len(original_line) <= max_len:
            fixed_lines.append(line)
            continue

        # Line is too long — need to break it
        indent_match = re.match(r'^(\s*)', original_line)
        indent = indent_match.group(1) if indent_match else ''
        text = original_line[len(indent):]

        # Find natural break points (prioritize: double-space, space+dash, space)
        words = text.split()
        current_line = indent
        lines_to_add = []

        for word in words:
            test_line = current_line + (' ' if current_line != indent else '') + word

            if len(test_line) <= max_len:
                current_line = test_line
            else:
                if current_line != indent:
                    lines_to_add.append(current_line + '\n')
                current_line = indent + '  ' + word  # New line with extra indent

        if current_line.strip():
            lines_to_add.append(current_line + '\n')

        if len(lines_to_add) > 1:
            fixed_lines.extend(lines_to_add)
            changed += 1
        else:
            fixed_lines.append(line)

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    return changed


md_files = [
    'README.md',
    'CHANGELOG.md',
    'DELIVERY_SUMMARY_F12_SPRINT_20FEV.md',
    'docs/agente_autonomo/AGENTE_AUTONOMO_TRACKER_UPDATED_20FEV.md',
]

print('MARKDOWN LINT FIX v2 — Aggressive line breaking\n')
print('='*70)

total_fixed = 0
for filepath in md_files:
    if not os.path.exists(filepath):
        print(f'⚠️  SKIPPED: {filepath}')
        continue

    fixed = force_line_width(filepath, max_len=80)
    status = '✅ FIXED' if fixed > 0 else '✅ OK'
    print(f'{status:8s} {filepath:50s} ({fixed} line breaks)')
    total_fixed += fixed

print('\n' + '='*70)
print(f'\nTotal lines fixed: {total_fixed}')
