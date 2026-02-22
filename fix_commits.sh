#!/bin/bash
# Script bash para corrigir encoding de commits

set -e  # Exit on error

cd /c/repo/crypto-futures-agent

echo "=========================================="
echo "CORRECAO DE COMMITS - Via Bash Script"
echo "=========================================="
echo ""

# Declarar arrays associativos com os commits e mensagens
declare -A COMMITS
COMMITS[7849056]="[FEAT] TASK-001 Heuristicas implementadas"
COMMITS[a229fab]="[TEST] TASK-002 QA Testing 40/40 testes ok"
COMMITS[fd1a7f8]="[PLAN] TASK-004 Preparacao go-live canary"
COMMITS[813e5fd]="[VALIDATE] TASK-003 Alpha SMC Validation OK"
COMMITS[09d2ecf]="[CLOSE] Reuniao Board 21 FEV encerrada"
COMMITS[1f2b75d]="[BOARD] Reuniao 16 membros Go-Live Auth"
COMMITS[0dcee01]="[INFRA] Board Orchestrator 16 membros setup"
COMMITS[b715f9a]="[DOCS] Integration Summary Board 16 membros"
COMMITS[9b5166c]="[BOARD] Votacao Final GO-LIVE aprovada unanime"
COMMITS[6e04cd4]="[GOLIVE] Canary Deployment Phase 1 iniciado"
COMMITS[81aa257]="[PHASE2] Script recuperacao dados conta real"

# Criar editor script
cat > /tmp/git_rebase_editor.sh << 'EDITOR_END'
#!/bin/bash

EDIT_COMMITS="7849056 a229fab fd1a7f8 813e5fd 09d2ecf 1f2b75d 0dcee01 b715f9a 9b5166c 6e04cd4 81aa257"

# Arquivo passado como primeiro argumento
if [ -n "$1" ]; then
    # Se é arquivo de rebase interativo
    if grep -q "^pick " "$1"; then
        # Fazer backup
        cp "$1" "$1.bak"

        # Marcar como edit para cada commit
        for commit in $EDIT_COMMITS; do
            sed -i "s/^pick $commit/edit $commit/" "$1"
        done
    fi
fi
EDITOR_END

chmod +x /tmp/git_rebase_editor.sh

echo "1. Editor script criado: /tmp/git_rebase_editor.sh"
echo ""

echo "2. Iniciando rebase interativo..."
echo "   (Isto pode ficar aguardando input)"
echo ""

# Usar GIT_SEQUENCE_EDITOR
export GIT_SEQUENCE_EDITOR="/tmp/git_rebase_editor.sh"

# Função para processar cada commit
process_commits() {
    local count=0
    local total=11

    # Array ordenado de commits
    local commits_array=(7849056 a229fab fd1a7f8 813e5fd 09d2ecf 1f2b75d 0dcee01 b715f9a 9b5166c 6e04cd4 81aa257)
    local messages_array=(
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

    # Iniciar rebase
    git rebase -i 7849056^ << EOF_REBASE
# Isto não funciona, pois git rebase -i é fundamentalmente interativa
EOF_REBASE
}

# Tentar iniciar rebase mas provavelmente vai ficar aguardando
echo "3. Executando rebase..."
git rebase -i 7849056^ || true

echo ""
echo "=========================================="
echo "Script parou aqui. Para continuar:"
echo "=========================================="
echo ""
echo "No repositório aberto, para CADA commit em 'edit' mode:"
echo ""
echo "git commit --amend -m \"[nova mensagem]\""
echo "git rebase --continue"
echo ""
echo "Mensagens para usar:"
for commit in "${!COMMITS[@]}"; do
    echo "  $commit -> ${COMMITS[$commit]}"
done

# Cleanup
rm -f /tmp/git_rebase_editor.sh /tmp/git_rebase_editor.sh.bak
