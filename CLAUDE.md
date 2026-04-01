# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Idioma

Todo código, comentários, logs e documentação devem ser escritos em **português**.
Exceções: nomes de APIs, bibliotecas, identificadores de propriedade e termos
técnicos sem tradução consagrada (ex.: `trailing stop`, `candlestick`).

## Comandos

```bash
# Setup
setup.bat                                        # Windows: cria venv, instala deps
make setup                                       # Linux/CI: equivalente ao setup.bat

# Execução
iniciar.bat                                      # Menu interativo (loop M2 model-driven)
python main.py --mode paper                      # Modo paper trading
python main.py --mode live                       # Modo live trading
python main.py --setup                           # Inicia DB + coleta dados históricos
python main.py --train                           # Treina modelo RL

# Pipeline Modelo 2.0
python scripts/model2/daily_pipeline.py --timeframe M5 --symbol BTCUSDT
python scripts/model2/bootstrap_algousdt_data.py --symbol ALGOUSDT --timeframes D1,H4,H1,M5 --start-date 2025-04-01 --end-date 2026-03-31
python scripts/model2/live_cycle.py --execution-mode shadow --live-symbol BTCUSDT
python scripts/model2/scan.py                   # Escaneia oportunidades
python scripts/model2/track.py                  # Rastreia teses
python scripts/model2/validate.py               # Valida teses
python scripts/model2/resolve.py                # Resolve/invalida teses
python scripts/model2/migrate.py up             # Executa migrações do DB
python scripts/model2/go_live_preflight.py      # Checagens pré-live (obrigatório antes de live)

# Monitoramento e diagnóstico
python status.py                                 # Status de posições e ciclo
python status_realtime.py                        # Monitoramento em tempo real
python posicoes.py                               # Breakdown de posições
python diagnostico_sinais.py                     # Diagnóstico de sinais
mlflow ui                                        # Dashboard MLflow (http://localhost:5000)

# Testes
pip install -r requirements-test.txt
pytest -q tests/                                 # Suite completa
pytest -q tests/test_model2_scanner.py           # Arquivo específico
pytest -q tests/ -k "scanner"                    # Por keyword

# Type checking
mypy --strict core/model2/scanner.py            # Módulo específico
# Nota: mypy exclui checkpoints/ automaticamente (ver mypy.ini)

# Lint de documentação
markdownlint docs/*.md
# Atenção: docs/*.md tem limite de 80 colunas (MD013)

# Docker (Linux/CI)
make docker-build                                # Constrói imagem
make docker-paper                                # Container em paper trading
```

## Formato de Commits

Padrão obrigatório: `[TAG] Descricao breve em portugues`

- Tags: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`
- Apenas ASCII (0–127), máximo 72 caracteres
- Qualquer commit que altere docs deve atualizar `docs/SYNCHRONIZATION.md`
  com a tag `[SYNC]`

## Arquitetura — Modelo 2.0

O sistema é um pipeline model-driven de decisão em camadas para negociação de
futuros cripto na Binance:

```
Binance API → Cache OHLCV → Scanner → Rastreador/Validador → Ponte de Sinal
                                                                    ↓
                                                        Camada de Ordem (admissão)
                                                                    ↓
                                                      Executor Live → Reconciliação
```

**Fluxo model-driven (ciclo de vida runtime via `iniciar.bat`):**

```
daily_pipeline.py → live_cycle.py → persist_training_episodes.py → healthcheck
     ↓                  ↓                     ↓
  scan/track/       model_state →         episódios →
  validate/resolve  policy inference →    treino RL por símbolo
                    safety envelope →
                    execução + reconciliação
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
Idempotência garantida por `decision_id`.

**Camada 5 — Execução Live** (`core/model2/live_exchange.py`, `core/model2/live_execution.py`, `core/model2/live_service.py`)
Envia ordens MARKET, arma proteções STOP_MARKET + TAKE_PROFIT_MARKET, reconcilia
fills e detecta saídas externas. O risk gate é validado aqui antes de qualquer ordem.

**Componentes model-driven transversais:**
- `core/model2/model_state_builder.py` — consolida OHLCV, técnicos, posição e risco
- `core/model2/model_inference_service.py` — inferência do policy model (OPEN_LONG | OPEN_SHORT | HOLD | REDUCE | CLOSE)
- `core/model2/promotion_gate.py` — validação de promoção shadow → live

**Utilitários transversais:**
- `core/model2/time_utils.py` — conversão canônica de timestamps para BRT; usar sempre que formatar datas/horas
- `core/model2/observability.py` — snapshots RED (signal flow, thesis lifecycle, audit)
- `core/model2/repository.py` — camada de acesso ao DB; preferir sobre SQL direto

## Bancos de Dados

- `db/crypto_agent.db` — Operacional (OHLCV legado, indicadores, dados macro)
- `db/modelo2.db` — DB canônico M2 com tabelas:
  - `opportunities`, `opportunity_events` — ciclo de vida das teses
  - `technical_signals`, `signal_executions`, `signal_execution_events` — ciclo de execução

## Bootstrap historico ALGOUSDT

- Script canonico: `scripts/model2/bootstrap_algousdt_data.py`
- DB alvo default: `db/modelo2.db`
- Timeframes suportados: `D1`, `H4`, `H1`, `M5`
- Validacoes: timestamps UTC ms, conversao BRT, deteccao de gaps,
  idempotencia via `INSERT OR REPLACE`
- Integracao operacional: `daily_pipeline.py` executa `bootstrap_stage_0`
  para `ALGOUSDT` quando `ohlcv_d1` tiver menos de 240 candles.

## Componentes RL

- `agent/trainer.py` — Núcleo de treinamento PPO (integrado com MLflow)
- `agent/sub_agent_manager.py` — Orquestração de agentes RL por símbolo
- `agent/entry_decision_env.py` — Gym environment para decisões de entrada
- `agent/opportunity_learning.py` — Aprendizado com resultados de oportunidades
- `agent/lstm_environment.py` — Wrapper LSTM (seq_len=10, n_features=20)
- `agent/convergence_monitor.py` — Monitor de convergência do treinamento
- `scripts/model2/ensemble_voting_ppo.py` — Votação em ensemble de sinais
- `scripts/model2/optuna_grid_search_ppo.py` — Busca de hiperparâmetros (Optuna)
- `scripts/model2/retrain_ppo_with_optuna_params.py` — Retreino com melhores params
- `scripts/model2/persist_training_episodes.py` — Persiste episódios para treino
- Checkpoints em `checkpoints/`, modelos treinados em `models/`

## Regras de Risco (Invioláveis)

- Nunca desabilitar validações de risco: sizing, alavancagem, stop loss, liquidação.
- Alterações em lógica de reward ou risco devem preservar padrões seguros, incluir
  fallback conservador e ser auditáveis.
- Em dúvida: bloquear a operação, nunca assumir risco.
- `risk/circuit_breaker.py` e `risk/risk_gate.py` devem permanecer ativos em
  todos os caminhos de execução.
- Preservar idempotência por `decision_id` em decisão e execução.
- Antes de qualquer deploy live, rodar `scripts/model2/go_live_preflight.py`.

## Configuração Principal

- `.env` (baseado em `.env.example`) — variáveis principais:
  - `BINANCE_API_KEY`, `BINANCE_API_SECRET` (ou `BINANCE_PRIVATE_KEY_PATH` para Ed25519)
  - `TRADING_MODE` — `paper` | `live` | `shadow`
  - `M2_EXECUTION_MODE` — `shadow` | `paper` | `live`
  - `M2_MAX_DAILY_ENTRIES`, `M2_MAX_MARGIN_PER_POSITION_USD`, `M2_SHORT_ONLY`
  - `M2_LIVE_SYMBOLS` — lista separada por vírgula (vazio = todos os símbolos)
  - `M2_INJECTION_ENABLED`, `M2_CANARY_DB_PATH`, `M2_CANARY_LEVERAGE`
- `config/symbols.py` — Lista de símbolos (40+ ativos); alterações exigem sincronizar
  `README.md`, `playbooks/__init__.py` e `docs/SYNCHRONIZATION.md`
- `config/ppo_config.py`, `config/risk_params.py`, `config/execution_config.py`

## Fontes de Verdade da Documentação

- **`docs/BACKLOG.md`** — Fonte única de verdade para tarefas, sprints e status
- **`docs/PRD.md`** — Fonte de verdade de escopo, requisitos funcionais (RF-*),
  requisitos não funcionais (RNF-*), KPIs e critérios Go/No-Go para `live`.
  Consultar antes de qualquer decisão de escopo ou implementação de nova funcionalidade.
- **`docs/REGRAS_DE_NEGOCIO.md`** — Regras de negócio para validação de teses e
  transições de estado
- **`docs/ARQUITETURA_ALVO.md`** — Arquitetura alvo e schema do DB M2
- **`docs/ADRS.md`** — Decisões arquiteturais vigentes (ADRs)
- **`docs/MODELAGEM_DE_DADOS.md`** — Modelagem de dados e schema
- **`docs/DIAGRAMAS.md`** — Diagramas de fluxo e componentes
- **`docs/RUNBOOK_M2_OPERACAO.md`** — Runbook operacional para trading live
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
- Após qualquer alteração em `docs/BACKLOG.md`, atualizar `docs/PRD.md`
  quando houver impacto de escopo e registrar em `docs/SYNCHRONIZATION.md`.

## Armadilhas Frequentes

- `docs/*.md` tem limite de 80 colunas (MD013) — quebrar linhas longas.
- Não versionar backups temporários de banco (`db/*.bak`).
- Não alterar arquitetura global para corrigir problema local.
- Mudança de código sem atualizar docs dependentes invalida o commit.

## Bootstrap rápido

- Windows: executar `setup.bat` para criar venv e instalar dependências.
- Instalar deps de teste: `pip install -r requirements-test.txt`.
- Rodar testes: `pytest -q tests/`.
- Executar pipeline local (dev): `python main.py --mode paper`.
