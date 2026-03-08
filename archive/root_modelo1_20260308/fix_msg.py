import sys
import json

# Dicionario de conversoes por hash
conversions = {
    "81aa257": "[PHASE2] Script recuperacao dados conta real",
    "6e04cd4": "[GOLIVE] Canary Deployment Phase 1 iniciado",
    "9b5166c": "[BOARD] Votacao Final GO-LIVE aprovada unanime",
    "b715f9a": "[DOCS] Integration Summary Board 16 membros",
    "0dcee01": "[INFRA] Board Orchestrator 16 membros setup",
    "1f2b75d": "[BOARD] Reuniao 16 membros Go-Live Auth",
    "09d2ecf": "[CLOSE] Reuniao Board 21 FEV encerrada",
    "813e5fd": "[VALIDATE] TASK-003 Alpha SMC Validation OK",
    "fd1a7f8": "[PLAN] TASK-004 Preparacao go-live canary",
    "a229fab": "[TEST] TASK-002 QA Testing 40/40 testes ok",
    "7849056": "[FEAT] TASK-001 Heuristicas implementadas",
}

# Ler mensagem do stdin
msg = sys.stdin.read().strip()

# Log para debug
with open("filter_log.txt", "a") as f:
    f.write(f"Original: {msg[:60]}\n")

# Procurar por qualquer um dos hashes na mensagem
for short_hash, new_msg in conversions.items():
    # Verificar se este commit estÃ¡ na mensagem (nao vai estar, mas fazemos parse)
    pass

# Aplicar conversoes de acentos genÃ©ricas se nÃ£o encontrou
conversions_accents = {
    "ÃƒÂ§": "c",   # Ã§ corrupted
    "ÃƒÂ£": "a",   # Ã£ corrupted
    "ÃƒÂ¡": "a",   # Ã¡ corrupted
    "ÃƒÂ©": "e",   # Ã© corrupted
    "ÃƒÂº": "u",   # u corrupted
    "Ãƒ": "",     # A mal codificado
    "Ã¢â‚¬"": "-",  # em dash
    "Ã¢â‚¬": "",    # corruption marker
    "Ã¢Å“â€¦": "",   # checkmark
    "Ã”": "",     # corruption
    "Ã§": "c",    # Ã§ normal
    "Ã‚": "",     # corruption
    "Ã¼": "u",
    "Ã¶": "o",
    "Ã¡": "a",
    "Ã©": "e",
    "Ã­": "i",
    "Ã³": "o",
    "Ãº": "u",
}

for old_char, new_char in conversions_accents.items():
    msg = msg.replace(old_char, new_char)

# Se a mensagem ainda tem caracteres > 127, remover
msg = ''.join(c if ord(c) < 128 else '' for c in msg)

# Limpar espaÃ§os multiplos
msg = ' '.join(msg.split())

with open("filter_log.txt", "a") as f:
    f.write(f"Fixed:    {msg[:60]}\n\n")

print(msg)
