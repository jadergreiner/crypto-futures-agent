# Instruções para o GitHub Copilot

Orientações para mudanças no repositório `crypto-futures-agent`.

## Princípios Essenciais

- **Segurança operacional**: Nunca remover controles de risco existentes.
- **Previsibilidade**: Mudanças pequenas, focadas, compatíveis com estilo.
- **Rastreabilidade**: Todas as decisões críticas devem ser auditáveis.
- **Português**: Código, docs, logs em português (termos técnicos propriedade excetuados).

## Stack

- **Linguagem**: Python
- **Módulos críticos**: `agent/` (RL), `execution/` (ordens), `data/` (Binance),
  `risk/` (controles), `backtest/` (F-12), `tests/`
- **Modo compatibilidade**: `paper` e `live` preservados

## Status: F-12 PHASE 3 (22/02/2026)

**Backtest Engine**: ✅ 100% funcional (9/9 testes passando)
**Risk Gates**: ⚠️ 2/6 passados → Decisão CTO necessária (ref: PHASE_3_EXECUTIVE_DECISION_REPORT.md)

**Root Cause**: Ações aleatórias (modelo não treinado)
**Próximo**: Decision #2 (train PPO 5-7d, Option B recomendado)

## Regras Críticas

### 1. Português Obrigatório

- Diálogos, comentários, logs, docs: **SEMPRE português**
- Exceção: APIs, bibliotecas, termos propriedade

### 2. Commits ASCII, Max 72 Chars

- Padrão: `[TAG] Descrição breve em português`
- Tags: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`
- Apenas ASCII (0-127), sem caracteres corrompidos

### 3. Markdown Lint: Max 80 Chars

- Usar `markdownlint *.md docs/*.md`
- Sem linhas > 80 caracteres, UTF-8 válido
- Títulos descritivos, blocos com linguagem (` ```python `)

## Regras de Domínio (Trading/Risk)

**Invioláveis:**
- Nunca desabilitar validações de risco (sizing, alavancagem, stop, liquidação).
- Alterações em reward/risk devem: manter segurança por padrão + fallback
  conservador + auditoria.
- Em dúvida: bloquear operação, não asumir risco.

## Sincronização Obrigatória

Toda mudança em código → sincronizar documentação. Checklist mínimo:

- [ ] Código funcional + testes passam (`pytest -q`)
- [ ] Docs dependentes atualizadas (ref: `docs/SYNCHRONIZATION.md`)
- [ ] Commit message com tag (`[SYNC]`, `[FEAT]`, etc.)

**Dependências principais:**
- `config/symbols.py` → `README.md`, `playbooks/__init__.py`, `docs/SYNCHRONIZATION.md`
- `docs/*` → sempre registrar em `docs/SYNCHRONIZATION.md`
- `README.md` versão → `CHANGELOG.md`, `docs/ROADMAP.md`

## O Que Evitar

- Não criar features "nice-to-have" sem solicitação.
- Não alterar arquitetura para resolver problema local.
- Não deixar documentação desatualizada.

## Detalhes: Referência em BEST_PRACTICES.md

Para mais contexto:
- **Padrões**: Log, estilo código, testes → `BEST_PRACTICES.md`
- **Sincronização**: Matriz de dependências, histórico → `docs/SYNCHRONIZATION.md`
- **Decisões**: Phase 3 gates, opções PPO → `PHASE_3_EXECUTIVE_DECISION_REPORT.md`
