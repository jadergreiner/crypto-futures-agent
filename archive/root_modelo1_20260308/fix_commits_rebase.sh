#!/bin/bash
# Script para corrigir encoding de commits usando rebase interativo automatizado
# Usa GIT_SEQUENCE_EDITOR para automatizar a seleção de commits para 'edit'

set -e

cd "/c/repo/crypto-futures-agent" || exit 1

echo "======================================"
echo "FIX COMMIT ENCODING - AUTOMATED REBASE"
echo "======================================"

# Arrays de commits e mensagens corrigidas
declare -A COMMITS_FIXES=(
    ['7849056']='[FEAT] TASK-001 Heuristicas implementadas'
    ['a229fab']='[TEST] TASK-002 QA Testing 40/40 testes ok'
    ['fd1a7f8']='[PLAN] TASK-004 Preparacao go-live canary'
    ['813e5fd']='[VALIDATE] TASK-003 Alpha SMC Validation OK'
    ['09d2ecf']='[CLOSE] Reuniao Board 21 FEV encerrada'
    ['1f2b75d']='[BOARD] Reuniao 16 membros Go-Live Auth'
    ['0dcee01']='[INFRA] Board Orchestrator 16 membros setup'
    ['b715f9a']='[DOCS] Integration Summary Board 16 membros'
    ['9b5166c']='[BOARD] Votacao Final GO-LIVE aprovada unanime'
    ['6e04cd4']='[GOLIVE] Canary Deployment Phase 1 iniciado'
    ['81aa257']='[PHASE2] Script recuperacao dados conta real'
)

# Criar script editor para automatizar rebase
cat > /tmp/git_rebase_editor.py << 'EDITOR_SCRIPT'
#!/usr/bin/env python3
import sys
import os

# Commits para fazer edit
COMMIT_HASHES = {
    '7849056', 'a229fab', 'fd1a7f8', '813e5fd', '09d2ecf',
    '1f2b75d', '0dcee01', 'b715f9a', '9b5166c', '6e04cd4', '81aa257'
}

if len(sys.argv) > 1:
    filename = sys.argv[1]
    with open(filename, 'r') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # Trocar 'pick' por 'edit' para commits que precisam corrigir
        parts = line.split()
        if parts and parts[0] in ('pick', 'p'):
            commit_hash = parts[1] if len(parts) > 1 else ''
            if commit_hash in COMMIT_HASHES:
                line = line.replace('pick', 'edit', 1)
                print(f"EDIT: {commit_hash}", file=sys.stderr)

        new_lines.append(line)

    with open(filename, 'w') as f:
        f.writelines(new_lines)
EDITOR_SCRIPT

chmod +x /tmp/git_rebase_editor.py

echo ""
echo "1. Começando rebase interativo desde o commit mais antigo..."
echo "   Rebasando desde: 7849056^"
echo ""

# Usar GIT_SEQUENCE_EDITOR para automatizar
export GIT_SEQUENCE_EDITOR="python3 /tmp/git_rebase_editor.py"

# Vamos fazer de forma mais segura: começar rebase, deixar interativo
# para que o usuário veja cada commit sendo editado

git rebase -i 7849056^ --quiet 2>&1 | head -20 &

# Aguardar um pouco para o git iniciar
sleep 2

# Agora para cada commit em 'edit' mode:
# Vamos fazer amend e continuar
echo ""
echo "2. Corrigindo commits..."
echo ""

# Dicionário de mensagens
declare -A FIXES_MAP
FIXES_MAP['7849056']='[FEAT] TASK-001 Heuristicas implementadas'
FIXES_MAP['a229fab']='[TEST] TASK-002 QA Testing 40/40 testes ok'
FIXES_MAP['fd1a7f8']='[PLAN] TASK-004 Preparacao go-live canary'
FIXES_MAP['813e5fd']='[VALIDATE] TASK-003 Alpha SMC Validation OK'
FIXES_MAP['09d2ecf']='[CLOSE] Reuniao Board 21 FEV encerrada'
FIXES_MAP['1f2b75d']='[BOARD] Reuniao 16 membros Go-Live Auth'
FIXES_MAP['0dcee01']='[INFRA] Board Orchestrator 16 membros setup'
FIXES_MAP['b715f9a']='[DOCS] Integration Summary Board 16 membros'
FIXES_MAP['9b5166c']='[BOARD] Votacao Final GO-LIVE aprovada unanime'
FIXES_MAP['6e04cd4']='[GOLIVE] Canary Deployment Phase 1 iniciado'
FIXES_MAP['81aa257']='[PHASE2] Script recuperacao dados conta real'

# Para cada commit, fazer amend e rebase --continue
for hash in "${!FIXES_MAP[@]}"; do
    msg="${FIXES_MAP[$hash]}"
    echo "  - Preparando: $hash"
    # Isto seria executado dentro do rebase interativo
    # Mas bash + git rebase -i interativa é complicada
done

echo ""
echo "======================================"
echo "Script parado aqui por limitações de automation"
echo "Execute os comandos abaixo manualmente:"
echo "======================================"
echo ""

cat << 'INSTRUCTIONS'
# Para fazer a correção manualmente:
HASHES=("7849056" "a229fab" "fd1a7f8" "813e5fd" "09d2ecf" "1f2b75d" "0dcee01" "b715f9a" "9b5166c" "6e04cd4" "81aa257")
MESSAGES=(
    "[FEAT] TASK-001 Heuristicas implementadas"
    "[TEST] TASK-002 QA Testing 40/40 testes ok"
    "[PLAN] TASK-004 Preparacao go-live canary"
    "[VALIDATE] TASK-003 Alpha SMC Validation OK"
    "[CLOSE] Reuniao Board 21 FEV encerrada"
    "[BOARD] Reuniao 16 membros Go-Live Auth"
    "[INFRA] Board Orchestrator 16 membros setup"
    "[DOCS] Integration Summary Board 16 membros"
    "[BOARD] Votacao Final GO-LIVE aprovada unanime"
    "[GOLIVE] Canary Deployment Phase 1 iniciado"
    "[PHASE2] Script recuperacao dados conta real"
)

# Ou use git-filter-repo se disponível:
pip3 install git-filter-repo
git filter-repo --message-callback '
    import sys
    msg = sys.stdin.read()
    # Fazer conversões aqui
    sys.stdout.write(msg)
'
INSTRUCTIONS

echo ""
echo "✓ Script pronto, continue manualmente ou instale git-filter-repo"
