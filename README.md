# Crypto Futures Agent

## Visao Geral

Este repositorio foi simplificado para foco no **Modelo 2.0**.
O objetivo atual e reduzir complexidade operacional e evoluir um fluxo por
camadas:

1. Scanner de Oportunidades
2. Rastreador de Tese
3. Ponte de Sinal

O legado do Modelo 1.0 foi movido para:

- `archive/root_modelo1_20260308/`
- `docs_archive_20260307_pre_modelo2/`

## Estrutura Essencial da Raiz

Arquivos operacionais mantidos na raiz:

- `main.py`
- `menu.py`
- `iniciar.bat`
- `setup.bat`
- `status.py`
- `status_realtime.py`
- `posicoes.py`
- `diagnostico_sinais.py`
- `resumo_ciclo.py`
- `requirements.txt`
- `requirements-test.txt`
- `.env.example`

## Documentacao Ativa (Modelo 2.0)

Toda a documentacao oficial ativa esta em `docs/`:

- `docs/REGRAS_DE_NEGOCIO.md`
- `docs/ADRS.md`
- `docs/ARQUITETURA_ALVO.md`
- `docs/MODELAGEM_DE_DADOS.md`
- `docs/DIAGRAMAS.md`
- `docs/BACKLOG.md`

## Setup Rapido (Windows)

```bat
setup.bat
```

O script cria ambiente virtual, instala dependencias e verifica configuracao.

## Execucao

Menu interativo:

```bat
iniciar.bat
```

Interface de linha de comando:

```bash
python main.py --help
python main.py --mode paper
python main.py --mode live
python main.py --setup
python main.py --train
```

Pipeline diario M2 (stages RL de entrada):

```bash
python scripts/model2/daily_pipeline.py --timeframe H4 --symbol BTCUSDT
```

Ordem relevante no runtime:

1. `persist_training_episodes`
2. `train_entry_agents`
3. `entry_rl_filter`
4. `order_layer`

Status:

```bash
python status.py
python status_realtime.py
python posicoes.py
```

## Rastreamento de Experimentos (MLflow)

O pipeline de retreino PPO integra MLflow para rastreabilidade de runs:

```bash
mlflow ui   # Interface local em http://localhost:5000
```

Parametros, metricas e artefatos de cada run sao registrados automaticamente
em `agent/trainer.py` e `agent/convergence_monitor.py`.
O artefato `ppo_model.zip` e versionado via MLflow e nao e rastreado pelo git.

## Lint de Documentacao

Validacao manual:

```bash
markdownlint docs/*.md
pytest -q tests/test_docs_model2_sync.py
```

O repositorio usa:

- Hook local em `.githooks/pre-commit`
- Workflow CI em `.github/workflows/docs-validate.yml`

## Politica de Arquivamento

Novos materiais legados nao devem voltar para a raiz.

Regra:

1. Ativo do Modelo 2.0 fica em `docs/` ou nos modulos de codigo.
2. Material historico vai para `archive/`.
3. Artefatos temporarios nao devem ser versionados.

## Aviso

Trading de futuros envolve alto risco.
Este projeto e experimental e requer uso responsavel.

## Sugestoes de Prompts (Copilot)

Use estes prompts para validar rapidamente as instrucoes do workspace:

1. Mapeie a proxima tarefa seguindo BACKLOG, PRD, ARQUITETURA,
 MODELAGEM DE DADOS, ADRs, REGRAS DE NEGOCIO e DIAGRAMAS e
 proponha um plano de execucao.
2. Implemente a task X com mudanca minima, rode pytest -q tests/ e
 atualize docs/SYNCHRONIZATION.md se necessario.
3. Revise esta alteracao com foco em risco operacional e regressao de
 comportamento.
4. Atualize docs/BACKLOG.md e sincronize docs/PRD.md, quando houver
 impacto real, e docs/SYNCHRONIZATION.md.

## Sugestoes de Customizacoes

1. /create-instruction model2-live applyTo core/model2/**
 Objetivo: reforcar regras de execucao live, protecao e reconciliacao.
2. /create-instruction docs-sync applyTo docs/**
 Objetivo: reforcar checklist de sincronizacao e padrao MD013.
3. /create-skill m2-incident-response
 Objetivo: padronizar resposta a incidentes operacionais com evidencias.
4. /create-prompt preflight-live-check
 Objetivo: validar ambiente e risco antes de qualquer rodada em live.
