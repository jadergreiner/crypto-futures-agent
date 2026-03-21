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
2. Ler `docs/PRD.md`.
3. Complementar com `docs/ARQUITETURA_ALVO.md` quando necessario.
4. Se necessario, cruzar com GitHub Issues abertas.

## Common Pitfalls

- Pre-commit bloqueia docs fora do padrao de markdown (principalmente MD013).
- Evitar versionar artefatos temporarios e backups de banco.
- Nao alterar arquitetura global para resolver problema local.
- Nao deixar mudanca de codigo sem atualizacao dos docs dependentes.

## Agent Customizations

### Instructions (aplicadas automaticamente por escopo)

| Arquivo | Escopo (`applyTo`) | Descricao |
| --- | --- | --- |
| `.github/instructions/docs-sync.instructions.md` | `docs/**` | Checklist MD013 e padrao de sincronizacao |
| `.github/instructions/incident-logs.instructions.md` | `logs/**` | Padrao de artefatos JSON para incidentes |
| `.github/instructions/m2-reconciliation.instructions.md` | `core/model2/live_service.py` | Regras de idempotencia por `decision_id` |
| `.github/instructions/model2-live.instructions.md` | `core/model2/**` | Regras extras para o live M2 |
| `.github/instructions/preflight-gates.instructions.md` | `scripts/model2/go_live_preflight.py` | Gates de liberacao live |

### Prompts (invocar explicitamente)

| Arquivo | Descricao |
| --- | --- |
| `.github/prompts/post-task.md` | Revisao pos-task: coerencia, guard-rails, docs, commit |
| `.github/prompts/preflight-live-check.prompt.md` | Validar ambiente e risco antes de ir para live |
| `.github/prompts/m2-go-no-go-report.prompt.md` | Relatorio GO/NO-GO para promocao shadow→live |
| `.github/prompts/m2-sev1-triage.prompt.md` | Triage de incidente SEV-1 em execucao M2 |

### Skills (carregar sob demanda)

| Skill | Descricao |
| --- | --- |
| `backlog-development` | Gerenciar backlog, atualizar status, mover sprints |
| `live-release-readiness` | Workflow GO/NO-GO para promocao para live |
| `m2-incident-response` | Playbook de incidente: evidencias, mitigacao, auditoria |

### Workflows CI/CD

| Arquivo | Gatilho | Descricao |
| --- | --- | --- |
| `.github/workflows/docs-validate.yml` | `push` / `pull_request` | Valida markdownlint e sincronizacao de docs |
| `.github/workflows/model2-smoke.yml` | `push` / `pull_request` | Smoke test do pipeline M2 (dry-run + healthcheck) |

## Referencias (Link, nao duplicar)

- Visao geral: `README.md`.
- Arquitetura alvo: `docs/ARQUITETURA_ALVO.md`.
- Regras de negocio: `docs/REGRAS_DE_NEGOCIO.md`.
- Modelagem de dados: `docs/MODELAGEM_DE_DADOS.md`.
- Decisoes de arquitetura: `docs/ADRS.md`.
- Roadmap e prioridades: `docs/BACKLOG.md`.
- Trilhas de sincronizacao: `docs/SYNCHRONIZATION.md`.
- Operacao do M2: `docs/RUNBOOK_M2_OPERACAO.md`.
