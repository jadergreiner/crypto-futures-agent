import sys
msg = sys.stdin.read()

# Replace corrupted UTF-8 sequences
msg = msg.replace('recuperaÃ§Ã£o', 'recuperacao')
msg = msg.replace('Recuperaçao', 'Recuperacao') 
msg = msg.replace('VotaÃ§Ã£o', 'Votacao')
msg = msg.replace('Votação', 'Votacao')
msg = msg.replace('UNANIME', 'UNANIME')
msg = msg.replace('UNÃ‚NIME', 'UNANIME')
msg = msg.replace('inicializaÃ§Ã£o', 'inicializacao')
msg = msg.replace('inicialização', 'inicializacao')
msg = msg.replace('ReuniaÃ£o', 'Reuniao')  
msg = msg.replace('Reunião', 'Reuniao')
msg = msg.replace('PrepareÃ§Ã£o', 'Preparacao')
msg = msg.replace('Preparação', 'Preparacao')
msg = msg.replace('HeurÃsticas', 'Heuristicas')
msg = msg.replace('HeurÃ­sticas', 'Heuristicas')
msg = msg.replace('Heurísticas', 'Heuristicas')

# Remove em-dash and other non-ASCII
msg = msg.replace('â€"', '-')
msg = msg.replace('â€"', '--')
msg = msg.replace('âœ…', '')
msg = msg.replace('Ô£à', '')
msg = msg.replace('â€', '')
msg = msg.replace('Ô', '')

# Generic cleanup: remove non-ASCII
result = ""
for c in msg:
    if ord(c) < 128:
        result += c
    elif c == ' ':
        result += ' '

msg = result.strip()
msg = " ".join(msg.split())  # Clean multiple spaces

print(msg, end='')
