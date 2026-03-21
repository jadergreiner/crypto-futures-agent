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
  Referencia completa: `docs/ARQUITETURA_ALVO.md`.
- A decisao de trade nasce no modelo, com acoes:
  - `OPEN_LONG`, `OPEN_SHORT`, `HOLD`, `REDUCE`, `CLOSE`.
- Guard-rails obrigatorios e inviolaveis:
  - `risk/risk_gate.py`
  - `risk/circuit_breaker.py`
  - `scripts/model2/go_live_preflight.py`
- Camadas operacionais vigentes:
  1. Coleta de estado — OHLCV multi-timeframe, features tecnicas,
     estado de posicao e restricoes operacionais.
  2. Policy Model — inferencia do modelo RL; saida: acao +
     confianca + parametros de execucao.
  3. Safety Envelope — `risk/risk_gate.py`,
     `risk/circuit_breaker.py`,
     `scripts/model2/go_live_preflight.py`.
  4. Execucao e reconciliacao — `core/model2/live_service.py`,
     `core/model2/live_exchange.py`,
     `core/model2/live_execution.py`.
  5. Persistencia e aprendizado — `db/modelo2.db`, episodios
     para retreino governado.
- Banco canonico M2: `db/modelo2.db`
  - Tabelas: `model_decisions`, `signal_executions`,
    `signal_execution_events`, `learning_episodes`,
    `training_runs`.
  - Migracoes versionadas em `scripts/model2/migrations/*.sql`.
- Modos de operacao: `backtest` (validacao offline),
  `shadow` (decisao sem ordem real),
  `live` (decisao com ordem real e guard-rails ativos).

## Build and Test

- Setup (Windows): `setup.bat`.
- Setup alternativo: `make setup`.
- Modo paper: `python main.py --mode paper` ou `make paper`.
- Modo live: `python main.py --mode live` ou `make live`.
- Inicializacao de dados: `python main.py --setup` ou `make db`.
- Treino RL: `python main.py --train` ou `make train`.
- Pipeline diario M2: `python scripts/model2/daily_pipeline.py`.
- Migracoes do banco M2: `python scripts/model2/migrate.py up`.
- Checagem pre-live: `python scripts/model2/go_live_preflight.py`.
- Testes: `pytest -q tests/`.
- Teste de sincronizacao de docs: `pytest -q tests/test_docs_model2_sync.py`.
- Lint de docs: `markdownlint docs/*.md`.
- Tipagem (arquivos alterados): `mypy --strict`.

## Conventions

- Regras de risco sao inviolaveis.
- Nunca desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Em duvida operacional, bloquear operacao em vez de assumir risco.
- Decisao e execucao devem ser idempotentes por `decision_id`.
- Commits: `[TAG] Descricao breve em portugues` (ASCII, max 72 chars).
- Tags aceitas: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`.
- Alterou docs: registrar sincronizacao em `docs/SYNCHRONIZATION.md`.
- Alterou `config/symbols.py`: sincronizar `README.md`,
  `playbooks/__init__.py` e `docs/SYNCHRONIZATION.md`.

## Task Source of Truth

Ao pedir "proxima tarefa", prioridade ou planejamento:

1. Ler `docs/BACKLOG.md`.
2. Conferir `docs/TRACKER.md` (se existir no workspace atual).
3. Complementar com `docs/ROADMAP.md`.
4. Se necessario, cruzar com GitHub Issues abertas.

## Common Pitfalls

- Pre-commit bloqueia docs fora do padrao de markdown (principalmente MD013).
- Evitar versionar artefatos temporarios e backups de banco.
- Nao alterar arquitetura global para resolver problema local.
- Nao deixar mudanca de codigo sem atualizacao dos docs dependentes.

## Referencias (Link, nao duplicar)

- Visao geral: `README.md`.
- Arquitetura alvo: `docs/ARQUITETURA_ALVO.md`.
- Regras de negocio: `docs/REGRAS_DE_NEGOCIO.md`.
- Modelagem de dados: `docs/MODELAGEM_DE_DADOS.md`.
- Decisoes de arquitetura: `docs/ADRS.md`.
- Roadmap e prioridades: `docs/BACKLOG.md`.
- Trilhas de sincronizacao: `docs/SYNCHRONIZATION.md`.
- Operacao do M2: `docs/RUNBOOK_M2_OPERACAO.md`.
