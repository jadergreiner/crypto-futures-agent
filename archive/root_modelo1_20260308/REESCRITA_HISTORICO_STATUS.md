# Reescrita de Histórico de Commits - Relatório de Status

## Situação Atual

**Identificados:** 11 commits com encoding UTF-8 corrompido
- 81aa257: `recupera├º├úo` (deveria ser `recuperacao`)
- 6e04cd4: com caracteres `ÔÇö` (non-ASCII)
- 9b5166c, b715f9a, 0dcee01, 1f2b75d, 09d2ecf, 813e5fd, fd1a7f8, a229fab, 7849056

**Backup criado:** `fix-encoding-backup` branch

**Polícia de Commit estabelecida:** COMMIT_MESSAGE_POLICY.md
- ASCII-only (0-127)
- Max 72 characters
- Tags: [FEAT], [FIX], [SYNC], [DOCS], [TEST], [PHASE2], [BOARD], [INFRA]

## Abordagens Tentadas

### 1. git filter-branch (FALHOU)
- Problema: Arquivo de callback não encontrado durante reescrita
- Erro: "no such file or directory"
- Causa: git cria fork e ambiente temporário, não consegue achar arquivo

### 2. git filter-repo (FALHOU)
- Problema: Callback script com erro de return statement
- Tentado com: standalone function, stdin/stdout, diferentes estruturas
- Causa: Gitfilter-repo tem sintaxe específica não documentada bem

### 3. Rebase interativo automático (COMPLEXO)
- Problema: git rebase -i é fundamentalmente interativa
- Env vars GIT_SEQUENCE_EDITOR não funcionam bem em PowerShell
- Bash/Git-Bash não integra bem com PowerShell commands

## Solução Recomendada

**ABORDAGEM MANUAL COM SUPORTE:**

São 11 commits. Cada um leva ~30 segundos com o método abaixo. Total: ~6 minutos.

### Passos:

1. Abra Git Bash (ou Terminal cmd com git.exe):
   ```
   cd c:\repo\crypto-futures-agent
   git rebase -i 7849056^
   ```

2. NO EDITOR QUE ABRIR (vim ou seu editor padrão):
   - Para cada linha dos 11 commits, mude primeira palavra de 'pick' para 'edit'
   - Salve e feche (ESC, :wq, ENTER se vim)

3. Para cada commit, execute:
   ```
   git commit --amend -m "[TAG] New message in ASCII"
   git rebase --continue
   ```

4. Após todos os 11 commits:
   ```
   git push origin main --force-with-lease
   ```

## Commits com Mensagens Corretas

```
1. 7849056  → [FEAT] TASK-001 Heuristicas implementadas
2. a229fab  → [TEST] TASK-002 QA Testing 40/40 testes ok
3. fd1a7f8  → [PLAN] TASK-004 Preparacao go-live canary
4. 813e5fd  → [VALIDATE] TASK-003 Alpha SMC Validation OK
5. 09d2ecf  → [CLOSE] Reuniao Board 21 FEV encerrada
6. 1f2b75d  → [BOARD] Reuniao 16 membros Go-Live Auth
7. 0dcee01  → [INFRA] Board Orchestrator 16 membros setup
8. b715f9a  → [DOCS] Integration Summary Board 16 membros
9. 9b5166c  → [BOARD] Votacao Final GO-LIVE aprovada unanime
10. 6e04cd4  → [GOLIVE] Canary Deployment Phase 1 iniciado
11. 81aa257  → [PHASE2] Script recuperacao dados conta real
```

## Próximas Tentativas (Se Quiser Automação)

### Opção A: Instalar git-python
```
pip install gitpython
# Usar script Python com GitPython library
```

### Opção B: Usar um serviço CI (GitHub Actions)
- Fazer push da branch
- Usar workflow que executa filter-repo
- Checkout da branch filtrada

### Opção C: Aceitar o Manual
- É rápido (6 minutos)
- Sem riscos de automação falhar
- Você controla cada commit

## Recomendação Final

Vamos com a **Abordagem Manual** (Opção C). É rápido e seguro.

Quer que eu guie você passo-a-passo?

## Files Criados para Suporte

- `CORRECAO_COMMITS_MANUAL.md` - Instruções passo-a-passo
- `callback_message.py` - Script de callback (para futuro)
- `msg_filter.py` - Filtro de mensagem (para futuro)
- `fix_commits.bat` - Batch script helper
