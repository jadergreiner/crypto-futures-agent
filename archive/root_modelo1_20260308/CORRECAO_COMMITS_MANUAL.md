# PROCURE REESCREVER COMMITS - INSTRUÇ ÇÕES MANUAIS

Dado que git-filter-repo está tendo dificuldades e rebase automático é complexo,
aqui estão as instruções passo-a-passo para fazer a correção manualmente.

## Opção 1: Rebase Interativo Simples (RECOMENDADO)

Execute:
```
git rebase -i 7849056^
```

Na janela do editor que abrir, mude 'pick' para 'edit' na linha de cada commit abaixo:

- 7849056 [FEAT] TASK-001 ...             -> mude para 'edit'
- a229fab [TEST] TASK-002 ...             -> mude para 'edit'
- fd1a7f8 [PLAN] TASK-004 ...             -> mude para 'edit'
- 813e5fd [VALIDATE] TASK-003 ...         -> mude para 'edit'
- 09d2ecf [CLOSE] Reuniao Board ...       -> mude para 'edit'
- 1f2b75d [BOARD] REUNIAO 16 MEMBROS ...  -> mude para 'edit'
- 0dcee01 [INFRA] Board Orchestrator ...  -> mude para 'edit'
- b715f9a [DOCS] Integration Summary ...  -> mude para 'edit'
- 9b5166c [BOARD] Votacao Final ...       -> mude para 'edit'
- 6e04cd4 [GOLIVE] Canary ...             -> mude para 'edit'
- 81aa257 [PHASE2] Script ...             -> mude para 'edit'

Depois de mudar, salve e feche o editor.

## Passo 2: Corrigir cada commit

Para CADA commit que está em 'edit', execute:

```
git commit --amend -m "nova mensagem aqui"
git rebase --continue
```

Use as mensagens corretas abaixo:

### Commits e mensagens corretas:

1. 7849056:
   git commit --amend -m "[FEAT] TASK-001 Heuristicas implementadas"
   git rebase --continue

2. a229fab:
   git commit --amend -m "[TEST] TASK-002 QA Testing 40/40 testes ok"
   git rebase --continue

3. fd1a7f8:
   git commit --amend -m "[PLAN] TASK-004 Preparacao go-live canary"
   git rebase --continue

4. 813e5fd:
   git commit --amend -m "[VALIDATE] TASK-003 Alpha SMC Validation OK"
   git rebase --continue

5. 09d2ecf:
   git commit --amend -m "[CLOSE] Reuniao Board 21 FEV encerrada"
   git rebase --continue

6. 1f2b75d:
   git commit --amend -m "[BOARD] Reuniao 16 membros Go-Live Auth"
   git rebase --continue

7. 0dcee01:
   git commit --amend -m "[INFRA] Board Orchestrator 16 membros setup"
   git rebase --continue

8. b715f9a:
   git commit --amend -m "[DOCS] Integration Summary Board 16 membros"
   git rebase --continue

9. 9b5166c:
   git commit --amend -m "[BOARD] Votacao Final GO-LIVE aprovada unanime"
   git rebase --continue

10. 6e04cd4:
    git commit --amend -m "[GOLIVE] Canary Deployment Phase 1 iniciado"
    git rebase --continue

11. 81aa257:
    git commit --amend -m "[PHASE2] Script recuperacao dados conta real"
    git rebase --continue

## Passo 3: Fazer push force

Depois que todos os commits forem corrigidos:

```
git push origin main --force-with-lease
```

## Se algo der errado:

```
git rebase --abort
git reset --hard fix-encoding-backup
```
