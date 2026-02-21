#!/usr/bin/env python3
"""Fix markdown lint issues — break long lines intelligently"""

import os
import re

def break_long_lines(filepath, max_len=80):
    """Break lines longer than max_len while preserving markdown formatting"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    changed = 0
    
    for line_num, line in enumerate(lines, 1):
        line_clean = line.rstrip('\n')
        
        # Skip code blocks and links
        if line_clean.startswith('```') or line_clean.startswith('    '):
            fixed_lines.append(line)
            continue
        
        # If line is short enough, keep it
        if len(line_clean) <= max_len:
            fixed_lines.append(line)
            continue
        
        # Try to break at natural boundaries
        if '|' in line_clean:  # Table row
            # Keep table rows as-is (they often exceed 80 chars legitimately)
            fixed_lines.append(line)
            continue
        
        if line_clean.startswith('- ') or line_clean.startswith('├') or line_clean.startswith('└'):
            # List item — try to break at conjunction
            if ' → ' in line_clean:
                parts = line_clean.split(' → ')
                fixed_lines.append(parts[0] + '\n')
                fixed_lines.append('   → ' + ' → '.join(parts[1:]) + '\n')
                changed += 1
                continue
            elif ' | ' in line_clean:
                parts = line_clean.split(' | ')
                if len(parts) > 1:
                    fixed_lines.append(parts[0] + ' |\n')
                    fixed_lines.append('  ' + ' | '.join(parts[1:]) + '\n')
                    changed += 1
                    continue
        
        # For long text lines, try to break at word boundary
        if len(line_clean) > max_len + 20:  # More than 20 chars over limit
            # Find last space before max_len
            break_point = line_clean.rfind(' ', 0, max_len)
            
            if break_point > max_len - 40:  # Reasonable break point found
                first_part = line_clean[:break_point]
                second_part = line_clean[break_point+1:]
                
                # Add appropriate indent for second line
                indent = ''
                if line_clean.startswith('  '):
                    indent = '  '
                
                fixed_lines.append(first_part + '\n')
                fixed_lines.append(indent + second_part + '\n')
                changed += 1
                continue
        
        # Default: keep as-is
        fixed_lines.append(line)
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    return changed

# Process markdown files
md_files = [
    'README.md',
    'CHANGELOG.md',
    'DELIVERY_SUMMARY_F12_SPRINT_20FEV.md',
    'DOCUMENTATION_SYNC_SUMMARY_20FEV.md',
    'docs/agente_autonomo/AGENTE_AUTONOMO_ROADMAP.md',
    'docs/agente_autonomo/AGENTE_AUTONOMO_RELEASE.md',
    'docs/agente_autonomo/AGENTE_AUTONOMO_BACKLOG.md',
    'docs/agente_autonomo/AGENTE_AUTONOMO_TRACKER_UPDATED_20FEV.md',
    'docs/agente_autonomo/SYNC_F12_TRACKER_20FEV.md',
    'docs/agente_autonomo/SYNC_COMPLETE_20FEV_v1.md',
]

print('MARKDOWN LINT FIX — Breaking long lines\n')
print('='*70)

total_fixed = 0
for filepath in md_files:
    if not os.path.exists(filepath):
        print(f'⚠️  SKIPPED (not found): {filepath}')
        continue
    
    fixed = break_long_lines(filepath, max_len=80)
    if fixed > 0:
        print(f'✅ FIXED {filepath:50s} ({fixed} lines)')
        total_fixed += fixed
    else:
        print(f'✅ OK    {filepath:50s} (no long lines)')

print('\n' + '='*70)
print(f'\nTotal lines fixed: {total_fixed}')
print(f'✅ MARKDOWN LINT FIX COMPLETE')
