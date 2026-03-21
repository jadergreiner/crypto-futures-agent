# Project Guidelines

Instrucoes para agentes no repositorio `crypto-futures-agent`.

## Code Style

- Idioma padrao: Portugues (pt-BR) em codigo, comentarios, logs e docs.
- Excecoes: nomes de API, bibliotecas e termos tecnicos consolidados.
- Mudancas devem ser pequenas, focadas e compativeis com o estilo existente.
- Manter UTF-8 valido em arquivos texto.
- Para markdown em `docs/`, respeitar limite de 80 colunas.

## Architecture

- Linguagem principal: Python.
- Arquitetura operacional vigente: Modelo 2.0 model-driven.
- A decisao de trade nasce no modelo com acoes permitidas:
  `OPEN_LONG`, `OPEN_SHORT`, `HOLD`, `REDUCE`, `CLOSE`.
- Safety Envelope e guard-rails sao inviolaveis em qualquer modo:
  - `risk/risk_gate.py`
  - `risk/circuit_breaker.py`
  - `scripts/model2/go_live_preflight.py`
- Modos de operacao:
  - `backtest` (validacao offline)
  - `shadow` (decisao sem ordem real)
  - `live` (decisao com ordem real e guard-rails ativos)
- Referencias de arquitetura e dados:
  - `docs/ARQUITETURA_ALVO.md`
  - `docs/MODELAGEM_DE_DADOS.md`
  - `docs/REGRAS_DE_NEGOCIO.md`

## Garantias Operacionais

- Nunca desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Em duvida operacional, bloquear operacao em vez de assumir risco.
- Decisao e execucao devem ser idempotentes por `decision_id`.
- Antes de operar em live, executar `scripts/model2/go_live_preflight.py`.

## Build and Test

- Setup (Windows): `setup.bat`.
- Setup alternativo: `make setup`.
- Modo paper: `python main.py --mode paper` ou `make paper`.
- Modo live: `make live` (inclui preflight) ou `python main.py --mode live`.
- Inicializacao de dados: `python main.py --setup` ou `make db`.
- Treino RL: `python main.py --train` ou `make train`.
- Pipeline diario M2: `python scripts/model2/daily_pipeline.py`.
- Cadeia operacional M2:
  - `python scripts/model2/scan.py --timeframe H4`
  - `python scripts/model2/track.py --symbol BTCUSDT --timeframe H4`
  - `python scripts/model2/validate.py --symbol BTCUSDT --timeframe H4`
  - `python scripts/model2/resolve.py --symbol BTCUSDT --timeframe H4`
  - `python scripts/model2/bridge.py --symbol BTCUSDT --timeframe H4`
  - `python scripts/model2/order_layer.py --symbol BTCUSDT --timeframe H4`
- Migracoes do banco M2: `python scripts/model2/migrate.py up`.
- Checagem pre-live: `python scripts/model2/go_live_preflight.py`.
- Testes: `pytest -q tests/`.
- Teste de sincronizacao de docs: `pytest -q tests/test_docs_model2_sync.py`.
- Lint de docs: `markdownlint docs/*.md`.
- Tipagem (arquivos alterados): `mypy --strict`.

## Conventions

- Commits: `[TAG] Descricao breve em portugues` (ASCII, max 72 chars).
- Tags aceitas: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`.
- Alterou docs: registrar sincronizacao em `docs/SYNCHRONIZATION.md`.
- Alterou `config/symbols.py`: sincronizar `README.md`,
  `playbooks/__init__.py` e `docs/SYNCHRONIZATION.md`.

## Task Source of Truth

Ao pedir "proxima tarefa", prioridade ou planejamento:

1. Ler `docs/BACKLOG.md`.
2. Ler `docs/PRD.md`.
3. Complementar com `docs/ARQUITETURA_ALVO.md` quando necessario.
4. Se necessario, cruzar com GitHub Issues abertas.

## Common Pitfalls

- Pre-commit bloqueia docs fora do padrao de markdown (principalmente MD013).
- Evitar versionar artefatos temporarios e backups de banco.
- Nao alterar arquitetura global para resolver problema local.
- Nao deixar mudanca de codigo sem atualizacao dos docs dependentes.

## Agent Customizations

- Instrucoes por escopo: ver `.github/instructions/`.
- Prompts operacionais: ver `.github/prompts/`.
- Skills de workflow: ver `.github/skills/`.
- CI de referencia: `.github/workflows/docs-validate.yml` e
  `.github/workflows/model2-smoke.yml`.

## Referencias (Link, nao duplicar)

- Visao geral: `README.md`.
- Arquitetura alvo: `docs/ARQUITETURA_ALVO.md`.
- Regras de negocio: `docs/REGRAS_DE_NEGOCIO.md`.
- Modelagem de dados: `docs/MODELAGEM_DE_DADOS.md`.
- Decisoes de arquitetura: `docs/ADRS.md`.
- Roadmap e prioridades: `docs/BACKLOG.md`.
- Trilhas de sincronizacao: `docs/SYNCHRONIZATION.md`.
- Operacao do M2: `docs/RUNBOOK_M2_OPERACAO.md`.
