# ❌ ISSUE DETECTADA: Commits Fora de Padrão

**Data:** 22 FEV 2026 | 04:45 BRT  
**Status:** ⚠️ **CORREÇÃO EM QA**  
**Severidade:** 🟠 **ALTO** (violação de policy)

---

## Problema Identificado

Os commits Phase 5 foram criados com **encoding UTF-8 corrompido**, violando a política estrita de ASCII puro da project:

### Commits Afetados

| Hash | Mensagem Atual | Problema |
|------|----------------|----------|
| `b759615` | `[SYNC] Registro de resolução de desafio agile infrastructure – DOC Advocate audit update` | UTF-8 com acentos (ã, ç),  tavessões UTF-8 (–) |
| `2cbc04d` | `[SYNC] Atualização de infraestrutura agile – Features, Roadmap, ...` | UTF-8 com acentos (ã, ç) |
| `8d156e7` | `[SYNC] Atualização urgente de documentação – Phase 4 operacionalização` | UTF-8 com acentos (ã, ç) |

### Violações de Policy

Segundo `COMMIT_MESSAGE_POLICY.md` e `copilot-instructions.md`:

```
❌ VIOLADO: "Apenas ASCII (0-127), sem caracteres corrompidos"
❌ VIOLADO: "Apenas português SEM acentuação"
❌ VIOLADO: "Sem caracteres especiais (–, —, ©, etc)"
```

**Regra Correta:**
```
✅ [TAG] Descricao breve em portugues, maximo 72 chars
   └─ Sem acentuação: "resolucao" em vez de "resolução"
   └─ Sem travessões: "-" em vez de "–"
   └─ ASCII puro: 0-127 apenas
```

---

## Mensagens Correctas (ASCII Puro)

| Hash | Mensagem Correta (Proposta) |
|------|---------------------------|
| `b759615` | `[SYNC] Phase 5 governance validation plan and testing framework` |
| `2cbc04d` | `[SYNC] Audit infrastructure and governance documentation` |
| `8d156e7` | `[SYNC] Phase 4 operationalization and feature delivery` |

---

## Plano de Correção

### Opção A: Rebase Interativo (Rewrite History)

```bash
git rebase -i ada3057  # Rebase last 3 commits
# Editar cada mensagem para ASCII puro
# git push --force-with-lease origin main
```

**Prós:** Histórico limpo
**Contras:** Força push, reescrita de histórico (coordenação necessária)

### Opção B: Novo Commit de Correção

```bash
git commit --allow-empty -m "[SYNC] Correction of previous commit messages - ASCII policy"
git push origin main
```

**Prós:** Não reescreve histórico
**Contras:** Registra "mistake" no histórico

### Opção C: Aceitar com Carryforward

Documentar o issue e prometer correção em próxima oportunidade.

---

##  Recomendação

**Usar Opção A (Rebase) COM COORDENAÇÃO:**

1. ✅ Informar board que histórico será reescrito nos últimos 3 commits
2. ✅ Executar rebase local interativo (corrigir mensagens)
3. ✅ Force push com `--force-with-lease` (seguro)
4. ✅ Todos pullarem novo histórico
5. ✅ Documentar correção em `CHANGELOG.md`

---

## Impacto

- 📊 **Funcionalidade:** ZERO (apenas mensagens de commit)
- 🔐 **Segurança:** ZERO
- 📝 **Governance:** ALTO (violação de policy)
- 👥 **Equipe:** Rebase pode afetar branches locais (se houver)

---

## Próximos Passos

**Ação Imediata:**
1. ⏸️ Pausar novos commits até correção
2. 📞 Comunicar com board sobre rebase
3. ✏️ Executar rebase interativo
4. 📤 Force push após confirmação
5. 📦 Documentar lição aprendida

**Prevenção Futura:**
- ✅ Git hook pré-commit para validar encoding ASCII
- ✅ CI/CD check para mensagens de commit
- ✅ Treinamento de equipe em COMMIT_MESSAGE_POLICY

---

**Issue Criado:** 22 FEV 2026 | 04:45 BRT  
**Responsável:** PM (Project Manager)  
**Status:** 🟡 **AWAITING BOARD COORDINATION**

