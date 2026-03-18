# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Idioma

Todo código, comentários, logs e documentação devem ser escritos em **português**.
Exceções: nomes de APIs, bibliotecas, identificadores de propriedade e termos
técnicos sem tradução consagrada (ex.: `trailing stop`, `candlestick`).

## Comandos

```bash
# Setup
setup.bat                                        # Cria venv, instala deps, inicia DB

# Execução
python main.py --mode paper                      # Modo paper trading
python main.py --mode live                       # Modo live trading
python main.py --setup                           # Inicia DB + coleta dados históricos
python main.py --train                           # Treina modelo RL

# Pipeline diário (Modelo 2.0)
python scripts/model2/daily_pipeline.py          # Ciclo completo M2
python scripts/model2/scan.py                   # Escaneia oportunidades
python scripts/model2/track.py                  # Rastreia teses
python scripts/model2/validate.py               # Valida teses
python scripts/model2/resolve.py                # Resolve/invalida teses
python scripts/model2/migrate.py up             # Executa migrações do DB
python scripts/model2/go_live_preflight.py      # Checagens pré-live

# Testes
pip install -r requirements-test.txt
pytest -q tests/
pytest -q tests/test_docs_model2_sync.py

# Lint de documentação
markdownlint docs/*.md
```

## Formato de Commits

Padrão obrigatório: `[TAG] Descricao breve em portugues`

- Tags: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`
- Apenas ASCII (0–127), máximo 72 caracteres
- Qualquer commit que altere docs deve atualizar `docs/SYNCHRONIZATION.md`
  com a tag `[SYNC]`

## Arquitetura — Modelo 2.0 (5 Camadas)

O sistema é um pipeline de decisão em camadas para negociação de futuros cripto
na Binance:

```
Binance API → Cache OHLCV → Scanner → Rastreador/Validador → Ponte de Sinal
                                                                    ↓
                                                        Camada de Ordem (admissão)
                                                                    ↓
                                                      Executor Live → Reconciliação
```

**Camada 1 — Scanner** (`core/model2/scanner.py`, `scripts/model2/scan.py`)
Detecta padrões SMC (Smart Money Concepts) nos dados OHLCV. Cria `opportunities`
no estado `IDENTIFICADA` com zonas de entrada, alvos e níveis de invalidação.

**Camada 2 — Rastreador/Validador** (`core/model2/validator.py`, `core/model2/resolver.py`)
Monitora oportunidades a cada novo candle. Transições de estado:
`IDENTIFICADA → MONITORANDO → VALIDADA | INVALIDADA | EXPIRADA`.

**Camada 3 — Ponte de Sinal** (`core/model2/signal_bridge.py`, `core/model2/signal_adapter.py`)
Converte teses validadas em registros padronizados de `technical_signals`
(estado `CREATED`).

**Camada 4 — Camada de Ordem** (`core/model2/order_layer.py`)
Gate de admissão. Consome `technical_signals` e registra `CONSUMED` ou `CANCELLED`.

**Camada 5 — Execução Live** (`core/model2/live_exchange.py`, `core/model2/live_execution.py`, `core/model2/live_service.py`)
Envia ordens MARKET, arma proteções STOP_MARKET + TAKE_PROFIT_MARKET, reconcilia
fills e detecta saídas externas. O risk gate é validado aqui antes de qualquer ordem.

## Bancos de Dados

- `db/crypto_agent.db` — Operacional (OHLCV legado, indicadores, dados macro)
- `db/modelo2.db` — DB canônico M2 com tabelas:
  - `opportunities`, `opportunity_events` — ciclo de vida das teses
  - `technical_signals`, `signal_executions`, `signal_execution_events` — ciclo de execução

## Componentes RL

- `agent/trainer.py` — Núcleo de treinamento PPO
- `agent/lstm_environment.py` — Wrapper LSTM (seq_len=10, n_features=20)
- `scripts/model2/ensemble_voting_ppo.py` — Votação em ensemble de sinais
- `scripts/model2/optuna_grid_search_ppo.py` — Busca de hiperparâmetros (Optuna)
- `scripts/model2/retrain_ppo_with_optuna_params.py` — Retreino com melhores params
- Checkpoints em `checkpoints/`, modelos treinados em `models/`

## Regras de Risco (Invioláveis)

- Nunca desabilitar validações de risco: sizing, alavancagem, stop loss, liquidação.
- Alterações em lógica de reward ou risco devem preservar padrões seguros, incluir
  fallback conservador e ser auditáveis.
- Em dúvida: bloquear a operação, nunca assumir risco.
- `risk/circuit_breaker.py` e `risk/risk_gate.py` devem permanecer ativos em
  todos os caminhos de execução.

## Configuração Principal

- `.env` (baseado em `.env.example`) — `BINANCE_API_KEY`, `BINANCE_API_SECRET`,
  `TRADING_MODE`, `MODEL2_DB_PATH`, `M2_EXECUTION_MODE`, `M2_MAX_DAILY_ENTRIES`
- `config/symbols.py` — Lista de símbolos (40+ ativos); alterações exigem sincronizar
  `README.md`, `playbooks/__init__.py` e `docs/SYNCHRONIZATION.md`
- `config/ppo_config.py`, `config/risk_params.py`, `config/execution_config.py`

## Fontes de Verdade da Documentação

- **`docs/BACKLOG.md`** — Fonte única de verdade para tarefas, sprints e status
- **`docs/TRACKER.md`** — Tabela visual compacta de sprint
- **`docs/ROADMAP.md`** — Linha do tempo estratégica
- **`docs/REGRAS_DE_NEGOCIO.md`** — Regras de negócio para validação de teses e
  transições de estado
- **`docs/ARQUITETURA_ALVO.md`** — Arquitetura alvo e schema do DB M2
- **`docs/SYNCHRONIZATION.md`** — Trilha de auditoria de sincronização (atualizar
  a cada mudança de doc)

Após qualquer alteração de código: executar `pytest -q`, atualizar docs dependentes
e commitar com a tag correta.

## Git Workflow

- Ao finalizar alterações, sempre fazer commit e push automaticamente sem
  perguntar quais arquivos incluir.
- Usar `git add -A` por padrão — inclui arquivos novos, modificados e deletados.
- Não perguntar se deve incluir arquivos deletados: incluir tudo.
- Commit message deve seguir o padrão `[TAG] Descricao` (ASCII, max 72 chars).

## Testing & Quality

- Sempre rodar `pytest -q` e corrigir falhas antes de fazer commit.
- Sempre rodar `mypy --strict` nos módulos alterados e corrigir erros antes
  de commit.
- Ao editar código, nunca duplicar blocos (ex.: blocos `except`) — verificar
  o resultado da edição antes de prosseguir.
- Se lint ou testes falharem: corrigir na mesma sessão, não deixar para depois.

## Backlog

- Ao receber instrução para adicionar itens ao backlog, inserir diretamente
  em `docs/BACKLOG.md` sem apenas ler o arquivo.
- Não aguardar confirmação adicional para operações de escrita no backlog,
  a menos que haja ambiguidade explícita.
- Após qualquer alteração em `docs/BACKLOG.md`, atualizar `docs/TRACKER.md`
  e registrar em `docs/SYNCHRONIZATION.md`.
