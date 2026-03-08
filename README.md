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

Status:

```bash
python status.py
python status_realtime.py
python posicoes.py
```

## Lint de Documentacao

Validacao manual:

```bash
markdownlint docs/*.md
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
