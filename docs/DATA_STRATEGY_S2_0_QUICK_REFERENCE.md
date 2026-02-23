# 🚪 QA Gates S2-0 — Quick Reference Card

**Issue:** #60 (Data Strategy)  
**Role:** Audit (#8)  
**Status:** 🟡 PLANEJANDO → 🟢 PRONTO PARA VALIDAÇÃO

---

## 🎯 2 Gates — Bem-Definidos e Mensuráveis

### Gate 1: Dados & Integridade (🟢 Simples)
**Owner:** Data Engineer (#11)  
**Duração:** 5 min validação + 15-20 min setup  
**Automação:** ✅ 100%

| Critério | Validação | Go/No-Go |
|----------|-----------|----------|
| 60 símbolos | `SELECT COUNT(DISTINCT symbol) FROM klines = 60` | ✅ Automático |
| 0 gaps | `klines_cache_manager.py validate-gaps` | ✅ Automático |
| 0 duplicatas | `klines_cache_manager.py validate-duplicates` | ✅ Automático |
| Preços válidos | `klines_cache_manager.py validate-prices` | ✅ Automático |
| Cache < 100ms | `time klines_cache_manager.py query-symbol` | ✅ Automático |
| 1 ano dados | `SELECT MAX(ts) - MIN(ts) ≥ 360 dias` | ✅ Automático |
| ~650 KB SQLite | `ls -lh db/klines_cache.db` | ✅ Automático |

**Pass Condition:** TODOS 7 critérios = ✅

---

### Gate 2: Qualidade & Testes (🟠 Moderado)
**Owner:** QA Lead (#8)  
**Duração:** 10-15 min  
**Automação:** ✅ 80% + ❌ 20% (manual review)

| Critério | Validação | Go/No-Go |
|----------|-----------|----------|
| 5 testes PASS | `pytest tests/data/test_klines_*.py -v | grep passed` | ✅ Automático |
| 80% coverage | `pytest --cov=data --cov-report=term` | ✅ Automático |
| 0 regressão | `pytest tests/ -v | grep FAIL` = None | ✅ Automático |
| 100% docstrings | Code review [`data/scripts/*.py`]() | ❌ Manual |
| README.md OK | [`data/README.md`]() ≥ 300 palavras | ❌ Manual |
| pylint ≥ 8.0 | `pylint data/scripts/klines_cache_manager.py` | ✅ Automático |

**Pass Condition:** TODOS 6 critérios = ✅

---

## 📋 Documentação Checklist (6 itens)

| D# | Item | Status |
|----|------|--------|
| D1 | Docstrings (100% PT) | ☐ |
| D2 | README.md (data/) | ☐ |
| D3 | CRITERIOS S2-0 | ✅ |
| D4 | DECISIONS S2-0 | ☐ |
| D5 | [SYNC] entry | ✅ |
| D6 | STATUS_ENTREGAS | ✅ |

**Pass Condition:** 6/6 = ✅

---

## 👥 Responsáveis (RACI)

| Papel | Gate 1 | Gate 2 | Doc | Final |
|------|--------|--------|-----|-------|
| Data Eng (#11) | **R** | — | **A** | — |
| QA Lead (#8) | — | **R** | **R** | — |
| Architect (#6) | C | C | — | — |
| Dr. Risk (#4) | I | — | — | — |
| Guardian (#5) | — | I | — | — |
| **Angel (#1)** | — | — | — | **A** |

**Legend:** R=Responsável | A=Accountable | C=Consulted | I=Informed

---

## 🚦 Fluxo de Aprovação (em 5 passos)

```
┌─────────────────────────────────────────┐
│ S2-0 Pronto para Validação              │
└──────────────┬──────────────────────────┘
               │
        ┌──────▼──────┐
        │ Gate 1      │
        │ Data Eng #11│
        │ 5 min       │
        └──────┬──────┘
               │
         ✅ PASS? ──NO──→ [Escalate → Dr. Risk]
               │
               │ YES
        ┌──────▼──────┐
        │ Gate 2      │
        │ QA Lead #8  │
        │ 15 min      │
        └──────┬──────┘
               │
         ✅ PASS? ──NO──→ [Escalate → Guardian]
               │
               │ YES
        ┌──────▼──────┐
        │ Docs        │
        │ QA Lead #8  │
        │ 10 min      │
        └──────┬──────┘
               │
         ✅ 6/6? ──NO──→ [Fix + Re-check]
               │
               │ YES
        ┌──────▼──────────┐
        │ Sign-Off Final  │
        │ Angel #1        │
        │ 5 min           │
        └──────┬──────────┘
               │
        ┌──────▼──────────────┐
        │ 🟢 S2-0 VALIDADO    │
        │ ↓                   │
        │ 🔵 S2-3 DESBLOQUEADO│
        └─────────────────────┘
```

**Total duração:** ~60 minutos (setup + validações + review)

---

## ✅ Definição de "Pronto" (Ready for S2-3)

Checklist antes de liberar S2-3:

- [ ] Gate 1 ✅ (Data Engineer assinado)
- [ ] Gate 2 ✅ (QA Lead assinado)
- [ ] Documentação ✅ (6/6 itens)
- [ ] Sem riscos abertos (escalations resolvidas)
- [ ] Angel ✅ (aprovação final)

**Quando TODOS checkboxes estão ✅:** 🟢 GO → Desbloqueia S2-3

---

## 📁 Documentos de Referência

| Documento | Propósito |
|-----------|----------|
| [DATA_STRATEGY_QA_GATES_S2_0.md](DATA_STRATEGY_QA_GATES_S2_0.md) | Referência COMPLETA (500+ linhas) |
| [CRITERIOS_DE_ACEITE_MVP.md#s2-0](CRITERIOS_DE_ACEITE_MVP.md#s2-0) | Critérios de aceite oficiais |
| [DATA_STRATEGY_S2_0_AUDIT_SUMMARY.md](DATA_STRATEGY_S2_0_AUDIT_SUMMARY.md) | Sumário executivo |
| [prompts/board_16_members_data.json](../prompts/board_16_members_data.json) | Matriz JSON (gates_s2_0) |

---

## 🔗 Próximo Passo

**Quando:** Sprint 2 (24-72h)  
**Responsável:** Data Engineer (#11)  
**Ação:** Executar Gate 1 + completar docs D1, D2, D4

---

*Quick Reference Card v1.0 — Audit (#8) — 22 FEV 2026*
