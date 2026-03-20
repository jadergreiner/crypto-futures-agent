# Makefile — crypto-futures-agent
# Equivalente Linux/cloud do setup.bat (R-03 do PRD)
# Uso: make setup | make paper | make live | make test | make docker-build

PYTHON      ?= python3
VENV_DIR    ?= venv
VENV_BIN    := $(VENV_DIR)/bin
PIP         := $(VENV_BIN)/pip
PYTHON_VENV := $(VENV_BIN)/python
ENV_FILE    := .env

.DEFAULT_GOAL := help

.PHONY: help setup venv deps env db train paper live test lint docker-build \
        docker-paper preflight clean

# ── Ajuda ─────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "crypto-futures-agent — Makefile"
	@echo "================================"
	@echo ""
	@echo "  make setup        Cria venv, instala deps e copia .env"
	@echo "  make db           Inicializa banco e coleta dados historicos"
	@echo "  make train        Treina modelo PPO/LSTM"
	@echo "  make paper        Inicia agente em modo paper trading"
	@echo "  make live         Inicia agente em modo live (cuidado!)"
	@echo "  make preflight    Executa checklist pre-live"
	@echo "  make test         Roda suite de testes (pytest)"
	@echo "  make lint         Executa markdownlint nos docs"
	@echo "  make docker-build Constroi imagem Docker"
	@echo "  make docker-paper Sobe container em paper trading"
	@echo "  make clean        Remove venv e arquivos temporarios"
	@echo ""

# ── Setup completo ─────────────────────────────────────────────────────
setup: venv deps env
	@mkdir -p db logs models checkpoints results
	@echo ""
	@echo "✓ Setup concluido!"
	@echo ""
	@echo "Proximos passos:"
	@echo "  1. Edite $(ENV_FILE) com suas credenciais Binance"
	@echo "  2. Execute: make db"
	@echo "  3. Execute: make paper"
	@echo ""

# ── Virtualenv ─────────────────────────────────────────────────────────
venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "[1/3] Criando virtualenv..."; \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "✓ Virtualenv criado em $(VENV_DIR)"; \
	else \
		echo "✓ Virtualenv ja existe em $(VENV_DIR)"; \
	fi

# ── Dependencias ───────────────────────────────────────────────────────
deps: venv
	@echo "[2/3] Instalando dependencias..."
	@$(PIP) install --upgrade pip --quiet
	@$(PIP) install -r requirements.txt
	@echo "✓ Dependencias instaladas"

# ── Arquivo .env ───────────────────────────────────────────────────────
env:
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "[3/3] Criando $(ENV_FILE) a partir de .env.example..."; \
		cp .env.example $(ENV_FILE); \
		echo ""; \
		echo "⚠️  ACAO NECESSARIA: configure $(ENV_FILE) com suas credenciais Binance"; \
		echo ""; \
	else \
		echo "✓ $(ENV_FILE) ja existe"; \
	fi

# ── Banco de dados ─────────────────────────────────────────────────────
db: venv
	@echo "Inicializando banco e coletando dados historicos..."
	@$(PYTHON_VENV) main.py --setup

# ── Treinamento ────────────────────────────────────────────────────────
train: venv
	@echo "Treinando modelo PPO/LSTM..."
	@$(PYTHON_VENV) main.py --train

# ── Paper trading ──────────────────────────────────────────────────────
paper: venv
	@echo "Iniciando agente em modo paper trading..."
	@$(PYTHON_VENV) main.py --mode paper

# ── Live trading ───────────────────────────────────────────────────────
live: preflight
	@echo "Iniciando agente em modo live..."
	@$(PYTHON_VENV) main.py --mode live

# ── Preflight ──────────────────────────────────────────────────────────
preflight: venv
	@echo "Executando checklist pre-live..."
	@$(PYTHON_VENV) scripts/model2/go_live_preflight.py

# ── Testes ─────────────────────────────────────────────────────────────
test: venv
	@echo "Rodando suite de testes..."
	@$(PYTHON_VENV) -m pytest -q tests/

# ── Lint ───────────────────────────────────────────────────────────────
lint:
	@echo "Executando markdownlint..."
	@if command -v markdownlint >/dev/null 2>&1; then \
		markdownlint docs/*.md; \
	else \
		echo "markdownlint nao encontrado. Instale com: npm install -g markdownlint-cli"; \
	fi

# ── Docker ─────────────────────────────────────────────────────────────
docker-build:
	@echo "Construindo imagem Docker..."
	@docker build -t crypto-futures-agent:latest .

docker-paper:
	@echo "Subindo container em modo paper trading..."
	@docker run --rm \
		--env-file $(ENV_FILE) \
		-v "$(PWD)/db:/app/db" \
		-v "$(PWD)/logs:/app/logs" \
		-v "$(PWD)/checkpoints:/app/checkpoints" \
		crypto-futures-agent:latest \
		--mode paper

# ── Limpeza ────────────────────────────────────────────────────────────
clean:
	@echo "Removendo venv e cache..."
	@rm -rf $(VENV_DIR) __pycache__ .pytest_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Limpeza concluida"
