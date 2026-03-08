# Script PowerShell para corrigir encoding de commits de forma batch
# Usa git filter-branch com Python para fazer conversões

$WorkDir = "c:\repo\crypto-futures-agent"
Set-Location $WorkDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CORRECAO DE ENCODING - BATCH PROCESSING" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Primeiro, criar o script Python que será usado pelo filter-branch
$pythonScript = @'
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
    # Verificar se este commit está na mensagem (nao vai estar, mas fazemos parse)
    pass

# Aplicar conversoes de acentos genéricas se não encontrou
conversions_accents = {
    "Ã§": "c",   # ç corrupted
    "Ã£": "a",   # ã corrupted
    "Ã¡": "a",   # á corrupted
    "Ã©": "e",   # é corrupted
    "Ãº": "u",   # u corrupted
    "Ã": "",     # A mal codificado
    "â€"": "-",  # em dash
    "â€": "",    # corruption marker
    "âœ…": "",   # checkmark
    "Ô": "",     # corruption
    "ç": "c",    # ç normal
    "Â": "",     # corruption
    "ü": "u",
    "ö": "o",
    "á": "a",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
}

for old_char, new_char in conversions_accents.items():
    msg = msg.replace(old_char, new_char)

# Se a mensagem ainda tem caracteres > 127, remover
msg = ''.join(c if ord(c) < 128 else '' for c in msg)

# Limpar espaços multiplos
msg = ' '.join(msg.split())

with open("filter_log.txt", "a") as f:
    f.write(f"Fixed:    {msg[:60]}\n\n")

print(msg)
'@

# Salvar script Python temporário
$pythonScript | Out-File -FilePath "fix_msg.py" -Encoding UTF8

Write-Host "`n1. Criado script de conversão: fix_msg.py"

Write-Host "`n2. AVISO: Esta operação reescreverá o histórico de commits!"
Write-Host "   Se algo der errado, use: git reset --hard fix-encoding-backup"
Read-Host "   Pressione ENTER para continuar..."

# Backup adicional
Write-Host "`n3. Criando commits conhecidos como reference..."
git log --oneline -12 | Tee-Object -FilePath "commits_before_fix.txt"

Write-Host "`n4. Iniciando filter-branch..."
Write-Host "   Analisando cada commit e convertendo encoding..."

# Usar filter-branch com o script Python
git filter-branch -f --msg-filter "python fix_msg.py" -- --all 2>&1 | Tee-Object -FilePath "filter_output.log"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Filter-branch concluído com sucesso!" -ForegroundColor Green
} else {
    Write-Host "`n✗ Filter-branch retornou erro code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "`n   Tentando recuperar..."
    git reset --hard fix-encoding-backup
}

Write-Host "`n5. Verificando resultado..."
git log --oneline -12

Write-Host "`n6. Validando mensagens em ASCII..."
$nonAscii = 0
$commits = git log --format=%H HEAD~15...HEAD 2>$null
foreach ($commit in @($commits -split "`n")) {
    if ($commit) {
        $msg = git log -1 --format=%s $commit 2>$null
        $hasNonAscii = $msg | Select-String -Pattern '[^\x00-\x7F]' -Quiet
        if ($hasNonAscii) {
            Write-Host "  ✗ Commit $commit ainda tem não-ASCII" -ForegroundColor Yellow
            $nonAscii++
        }
    }
}

if ($nonAscii -eq 0) {
    Write-Host "  ✓ Todos os commits agora em ASCII puro!" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Encontrados $nonAscii commits ainda com problemas" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PROXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host "- Se OK: git push origin main --force-with-lease" -ForegroundColor White
Write-Host "- Se erro: git reset --hard fix-encoding-backup" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
