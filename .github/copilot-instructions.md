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
- Arquitetura operacional: Modelo 2.0 em 5 camadas.
- Scanner: `core/model2/scanner.py` e `scripts/model2/scan.py`.
- Rastreador/validador: `core/model2/validator.py` e
  `core/model2/resolver.py`.
- Ponte de sinal: `core/model2/signal_bridge.py` e
  `core/model2/signal_adapter.py`.
- Camada de ordem: `core/model2/order_layer.py`.
- Execucao live: `core/model2/live_execution.py`,
  `core/model2/live_service.py` e `core/model2/live_exchange.py`.
- Bancos: `db/crypto_agent.db` (legado) e `db/modelo2.db` (canonico M2).

## Build and Test

- Setup (Windows): `setup.bat`.
- Setup alternativo: `make setup`.
- Modo paper: `python main.py --mode paper` ou `make paper`.
- Modo live: `python main.py --mode live` ou `make live`.
- Inicializacao de dados: `python main.py --setup` ou `make db`.
- Treino RL: `python main.py --train` ou `make train`.
- Testes: `pytest -q tests/`.
- Teste de sincronizacao de docs: `pytest -q tests/test_docs_model2_sync.py`.
- Lint de docs: `markdownlint docs/*.md`.
- Tipagem (arquivos alterados): `mypy --strict`.

## Conventions

- Regras de risco sao inviolaveis.
- Nunca desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Em duvida operacional, bloquear operacao em vez de assumir risco.
- Commits: `[TAG] Descricao breve em portugues` (ASCII, max 72 chars).
- Tags aceitas: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`.
- Alterou docs: registrar sincronizacao em `docs/SYNCHRONIZATION.md`.
- Alterou `config/symbols.py`: sincronizar `README.md`,
  `playbooks/__init__.py` e `docs/SYNCHRONIZATION.md`.

## Task Source of Truth

Ao pedir "proxima tarefa", prioridade ou planejamento:

1. Ler `docs/BACKLOG.md`.
2. Conferir `docs/TRACKER.md`.
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
