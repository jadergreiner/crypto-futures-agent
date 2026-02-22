# 📋 CORRECAO DE COMMITS — Plano de Acao

**Data:** 22 FEV 2026 | 05:00 BRT  
**Status:** 🟡 **EM QA - REQUER ACAO DO PM**  
**Prioridade:** 🟠 **ALTO**

---

## RESUMO DO PROBLEMA

Durante Phase 5, 3 commits foram criados com **violação de ASCII policy**:

### Commits Corrompidos

```
b759615: [SYNC] Registro de resolu├º├úo de desafio agile infrastructure...
         ^ Caracteres corrompidos (ã → ├º, ç → ├º, – → ÔÇö)

2cbc04d: [SYNC] Atualiza├º├úo de infraestrutura agile...
         ^ Idem

8d156e7: [SYNC] Atualiza├º├úo urgente de documenta├º├úo...
         ^ Idem
```

**Root Cause:** Mensagens foram criadas com UTF-8, mas sistema esperava ASCII puro (0-127).

**Violação:** Contradiz `COMMIT_MESSAGE_POLICY.md` e `copilot-instructions.md`

---

## PLANO DE CORRECAO (3 OPCOES)

### ✅ OPCAO RECOMENDADA: Rebase Interativo Local

**Passos:**

1. **Criar Backup Branch:**
   ```bash
   git branch backup_phase5_before_rebase
   ```

2. **Fazer Rebase Interativo:**
   ```bash
   git rebase -i ada3057  # Rebase últimos 3 commits
   ```
   
   Na sessão interativa:
   ```
   pick b759615 [SYNC] Registro...
   pick 2cbc04d [SYNC] Atualiza├º├úo...
   pick 8d156e7 [SYNC] Atualiza├º├úo...
   ```
   
   Mudar para `reword`:
   ```
   reword b759615
   reword 2cbc04d
   reword 8d156e7
   ```

3. **Corrigir Mensagens (ASCII Puro):**
   
   **Para b759615:**
   ```
   Remover: [SYNC] Registro de resolu├º├úo de desafio agile infrastructure ÔÇö DOC Advocate audit update
   
   Adicionar: [SYNC] Phase 5 governance validation and test planning
   ```
   
   **Para 2cbc04d:**
   ```
   Remover: [SYNC] Atualiza├º├úo de infraestrutura agile ÔÇö Features, Roadmap...
   
   Adicionar: [SYNC] Audit infrastructure and governance documentation
   ```
   
   **Para 8d156e7:**
   ```
   Remover: [SYNC] Atualiza├º├úo urgente de documenta├º├úo ÔÇö Phase 4 operacionaliza├º├úo
   
   Adicionar: [SYNC] Phase 4 operationalization and audit closure
   ```

4. **Force Push Com Segurança:**
   ```bash
   git push --force-with-lease origin main
   ```
   
   `--force-with-lease` é mais seguro que `--force` pois detecta outros pushes

5. **Board Communication:**
   - Informar: "Reescrita de histórico dos últimos 3 commits para corrigir encoding"
   - Avisar: Que façam `git pull --rebase` para sincronizar

---

### ⏸️ OPCAO B: Novo Commit de Correção (Sin Rewrite)

Se rebase for muito arriscado:

```bash
git commit --allow-empty -m "[SYNC] Correction of commit message encoding issues"
git push origin main
```

**Vantagem:** Não reescreve histórico  
**Desvantagem:** Registra "mistake" permanentemente

---

## ARQUIVOS DE SUPORTE CRIADOS

| Arquivo | Proposito | Status |
|---------|-----------|--------|
| `management/ISSUE_COMMIT_ENCODING_22FEV.md` | Documentacao completa do issue | ✅ Criado |
| `management/CORRECAO_COMMITS_MANUAL.md` | Instruções passo-a-passo | ✅ (this file) |

---

## PROXIMOS PASSOS

**Imediato (Agora):**
- [ ] PM ler este documento
- [ ] PM decidir OPCAO (rebase vs novo commit)
- [ ] PM comunicar com 1-2 board members críticos

**Se OPCAO A (Rebase):**
- [ ] Criar branch de backup
- [ ] Executar rebase interativo
- [ ] Verfificar commits localmente
- [ ] Force push com `--force-with-lease`
- [ ] Comunicar com board
- [ ] Todos fazem `git pull --rebase`

**Se OPCAO B (Novo Commit):**
- [ ] Criar commit de correção
- [ ] Push normal
- [ ] Documentar issue em `CHANGELOG.md`

---

## TIMELINE RECOMENDADA

```
22 FEV 05:00-05:30: PM decide OPCAO
22 FEV 05:30-06:00: Executar correção (qual foi escolhida)
22 FEV 06:00: Comunicar com board em standup
22 FEV 06:00: SPRINT 2 kickoff (com commits limpos)
```

---

## VERIFICACAO FINAL

Após correção, verificar que mensagens estão ASCII:

```bash
git log --oneline -3
# Deve mostrar mensagens sem caracteres corrompidos
# Ex: [SYNC] Phase 5 governance validation plan and testing
```

---

**Documento:** Plano de Acao - Correcao de Commits  
**Criado:** 22 FEV 2026 | 05:00 BRT  
**Responsável:** PM (Project Manager)  
**Status:** 🟡 **Pendente Decisão PM**

