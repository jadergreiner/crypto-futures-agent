# Project Guidelines

## Idioma

- Usar pt-BR em codigo, comentarios, logs e docs.
- Excecoes: nomes de API, bibliotecas e termos tecnicos.

## Invariantes de Seguranca

- Nunca desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Em duvida operacional, bloquear operacao (fail-safe).
- Preservar idempotencia por `decision_id` em decisao e execucao.
- Antes de qualquer live, rodar `scripts/model2/go_live_preflight.py`.

## Build e Teste

- Setup rapido: `setup.bat`.
- Gate pre-commit:

```bash
pytest -q tests/
mypy --strict        # modulos alterados
markdownlint docs/*.md   # se alterou docs
```

## Convencoes de Commit e Sync

- Formato: `[TAG] Descricao` (ASCII, max 72 chars).
- Tags: `[FEAT]` `[FIX]` `[SYNC]` `[DOCS]` `[TEST]`.
- Se alterar docs, atualizar `docs/SYNCHRONIZATION.md`.
- Se alterar `config/symbols.py`, sincronizar `README.md` e
  `playbooks/__init__.py`.

## Fontes de Verdade (Link, nao embed)

- Prioridades: `docs/BACKLOG.md` e `docs/PRD.md`.
- Arquitetura/schema: `docs/ARQUITETURA_ALVO.md`.
- Regras operacionais: `docs/REGRAS_DE_NEGOCIO.md`.
- Decisoes arquiteturais vigentes: `docs/ADRS.md`.
- Contexto completo de componentes/comandos: `CLAUDE.md`.

## Armadilhas Frequentes

- `docs/*.md` tem limite de 80 colunas (MD013).
- Nao versionar backups temporarios de banco.
- Nao alterar arquitetura global para corrigir problema local.
- Mudanca de codigo sem atualizar docs dependentes invalida o commit.
