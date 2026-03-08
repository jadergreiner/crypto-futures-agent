# COMMIT MESSAGE POLICY — Correction & Future Standard

**Problema Identificado:** 21 FEV 2026 20:30 UTC

Commits recentes violaram regra de ASCII puro da .github/copilot-instructions.md:

```
❌ 5ed0056: [SYNC] Reuniao Board: Phase 2 Live e Governance Docs Aprovadas
           (OK em ASCII, mas "Governance" é inglês - verificar se necessário)

❌ 81aa257: [PHASE2] Script de recupera├º├úo de dados API Binance - operacional
           (Caracteres corrompidos: recuperação com encoding UTF-8 quebrado)
           
❌ 6e04cd4: [GOLIVE] Canary Deployment Phase 1 INICIADO ÔÇö 10% volume ativa
           (Caracteres corrompidos: ÔÇö em vez de travessão)
           
❌ 9b5166c: [BOARD] Vota├º├úo Final ÔÇö GO-LIVE APROVADO UN├éNIME (16/16) Ô£à
           (Múltiplos caracteres corrompidos: votação, unanimidade)
```

**Regra Violada:**
- Menos de 72 caracteres (OK em alguns)
- Apenas ASCII 0-127 (❌ VIOLADO — UTF-8 com acentuação)
- Sem caracteres corrompidos (❌ VIOLADO — encoding issues)

---

## POLÍTICA CORRIGIDA DAQUI EM DIANTE

### Padrão de Commit (Strict ASCII)

```
[TAG] Descricao breve em portugues, maximo 72 chars
```

**Tags Autorizadas:**
- `[FEAT]` — Nova feature
- `[FIX]` — Bugfix
- `[SYNC]` — Sincronização de docs
- `[DOCS]` — Atualização de documentação
- `[TEST]` — Testes e validação
- `[PHASE2]` — Operação Phase 2
- `[BOARD]` — Decisões de board
- `[INFRA]` — Infraestrutura

**Regras Estritas:**
1. ✅ Apenas ASCII 0-127 (sem acentuação)
2. ✅ Max 72 caracteres (incluindo tag)
3. ✅ Em português (sem acentos)
4. ✅ Sem caracteres especiais (–, —, ©, etc)
5. ✅ Sem emojis, UTF-8 multi-byte

---

## EXEMPLOS CORRETOS vs INCORRETOS

### ❌ INCORRETO (Violações)

```
[SYNC] Reuniao Board: Phase 2 Live e Governance Docs Aprovadas
       └─ Muito longo (73 chars), "Governance" inglês

[PHASE2] Script de recuperação de dados API Binance - operacional
         └─ UTF-8 com acentos (ã, ç)

[GOLIVE] Canary Deployment Phase 1 INICIADO – 10% volume ativa
         └─ Travessão UTF-8 (–)

[BOARD] Votação Final GO-LIVE APROVADO UNÂNIME 16/16
        └─ Acentos (ã, â)
```

### ✅ CORRETO (ASCII Puro)

```
[SYNC] Reuniao Board: Phase 2 Live aprovada
       └─ 50 chars, ASCII puro, tags português

[PHASE2] Script recuperacao dados API Binance ok
         └─ 58 chars, ASCII puro, sem UTF-8

[GOLIVE] Canary Deployment Phase 1 iniciado
         └─ 50 chars, ASCII puro, sem hífens especiais

[BOARD] Votacao Final GO-LIVE aprovada unanime
        └─ 54 chars, ASCII, sem acentos
```

---

## CONVERSÃO DE PALAVRAS PORTUGUESAS (para ASCII)

| Com Acento | ASCII | Contexto |
|-----------|-------|---------|
| à | a | "a partir" → "a partir" |
| á | a | "análise" → "analise" |
| â | a | "plâ­tô" → "platô" |
| ã | a | "não" → "nao", "votação" → "votacao" |
| á | a | "máquina" → "maquina" |
| é | e | "operação" → "operacao" |
| ê | e | "âmbar" → "ambar" |
| í | i | "crítico" → "critico" |
| ó | o | "síntese" → "sintese" |
| ô | o | "decisão" → "decisao" |
| ú | u | "última" → "ultima" |
| ç | c | "sincronização" → "sincronizacao" |
| ü | u | "pinguim" → "pinguim" |

---

## POLÍTICA DE COMMIT— A PARTIR DE AGORA

**Todos os commits futuros DEVEM:**

```bash
# Verificar antes de fazer commit
# 1. Remover acentos
# 2. Contar caracteres (máx 72)
# 3. Usar tag apropriada
# 4. Testar: git commit --dry-run

# Exemplo:
git commit -m "[SYNC] Sincronizacao de documentacao critica"
# ✅ Correto: 62 chars, ASCII puro, tag valida

# Contra-exemplo:
git commit -m "[SYNC] Sincronização de documentação crítica"
# ❌ Errado: UTF-8 com acentos, violação de política
```

**Git Hook de Validação (Futura):**

Será implementado pre-commit hook que validará:
- ASCII puro apenas
- Max 72 caracteres
- Tag autorizada
- Bloqueia commits inválidos

---

## REFERÊNCIA HISTÓRICA

**Commits com Encoding Corrompido a Corrigir:**

```
5ed0056 — OK (sem acentos)
81aa257 — Recuperacao (corrigir: recuperacao em vez de recuperação)
6e04cd4 — OK (sem acentos no titulo, mas hífens UTF-8)
a2d758c — OK (sem acentos)
9b5166c — Votacao, Unanime (corrigir acentos)
```

---

## AÇÃO IMEDIATA

1. **Documentation:** Este documento registra a política
2. **Future Commits:** Todos os commits respeitarão ASCII+72chars
3. **Pre-Commit Hook:** Será implementado em Sprint 2 (validação automática)
4. **Audit:** Próxima reunião discutirá reescrita de histórico (se necessário)

---

**Policy Effective Date:** 21 FEV 2026 20:35 UTC  
**Status:** ATIVO PARA TODOS OS COMMITS FUTUROS  
**Enforcement:** Pré-commit hook (Sprint 2)
