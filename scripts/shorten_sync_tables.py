from pathlib import Path

FILE = Path('docs/SYNCHRONIZATION.md')

def shorten_table_line(line: str) -> str:
    # Skip separator lines
    if set(line.strip()) <= set('| -:'):
        return line
    parts = line.strip('\n').split('|')
    # ensure at least 4 elements: ['', col1, col2, col3, '']
    if len(parts) < 4:
        return line
    col1 = parts[1].strip()
    col2 = parts[2].strip()
    # Reduce second column to filename only to shorten the line
    try:
        from pathlib import Path as _P
        col2 = _P(col2).name
    except Exception:
        pass
    # Short placeholder for third column
    new_col3 = 'Ver commits/PR'
    new_line = f'| {col1} | {col2} | {new_col3} |\n'
    return new_line

def main():
    text = FILE.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    new_lines = []
    for line in lines:
        if line.startswith('|') and len(line) > 80:
            new_lines.append(shorten_table_line(line))
        else:
            new_lines.append(line)
    FILE.write_text(''.join(new_lines), encoding='utf-8')

if __name__ == '__main__':
    main()
