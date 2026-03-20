from pathlib import Path
p = Path('docs/SYNCHRONIZATION.md')
for i, l in enumerate(p.read_text(encoding='utf-8').splitlines(), start=1):
    if len(l) > 80:
        print(i, len(l), l)
