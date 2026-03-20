#!/usr/bin/env bash
# setup.sh — Equivalente Linux/macOS do setup.bat (R-03 do PRD)
# Uso: bash setup.sh
set -euo pipefail

PYTHON=${PYTHON:-python3}
VENV_DIR="venv"

echo ""
echo "============================================================"
echo "       CRYPTO FUTURES AGENT — SETUP (Linux/macOS)"
echo "============================================================"
echo ""

# ------------------------------------------------------------------
# 1. Verificar Python 3.10+
# ------------------------------------------------------------------
echo "[1/7] Verificando instalacao do Python..."
if ! command -v "$PYTHON" &>/dev/null; then
    echo "[ERRO] Python nao encontrado. Instale Python 3.10+ e tente novamente."
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "[ERRO] Python 3.10+ necessario. Versao encontrada: $PY_VERSION"
    exit 1
fi
echo "[OK] Python $PY_VERSION"

# ------------------------------------------------------------------
# 2. Criar virtualenv
# ------------------------------------------------------------------
echo ""
echo "[2/7] Configurando virtualenv..."
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON" -m venv "$VENV_DIR"
    echo "[OK] Virtualenv criado em $VENV_DIR"
else
    echo "[OK] Virtualenv ja existe em $VENV_DIR"
fi

PYTHON_VENV="$VENV_DIR/bin/python"
PIP_VENV="$VENV_DIR/bin/pip"

# ------------------------------------------------------------------
# 3. Atualizar pip
# ------------------------------------------------------------------
echo ""
echo "[3/7] Atualizando pip..."
"$PIP_VENV" install --upgrade pip --quiet
echo "[OK] pip atualizado"

# ------------------------------------------------------------------
# 4. Instalar dependencias
# ------------------------------------------------------------------
echo ""
echo "[4/7] Instalando dependencias (pode demorar alguns minutos)..."
"$PIP_VENV" install -r requirements.txt
echo "[OK] Dependencias instaladas"

# ------------------------------------------------------------------
# 5. Configurar .env
# ------------------------------------------------------------------
echo ""
echo "[5/7] Verificando configuracao..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "[OK] .env criado a partir de .env.example"
        echo ""
        echo "============================================================"
        echo "  ACAO NECESSARIA: configure seu arquivo .env"
        echo "============================================================"
        echo ""
        echo "  Adicione suas credenciais Binance em .env:"
        echo "    BINANCE_API_KEY=<sua-chave>"
        echo "    BINANCE_API_SECRET=<seu-segredo>"
        echo "    TRADING_MODE=paper"
        echo ""
    else
        echo "[AVISO] .env.example nao encontrado. Crie .env manualmente."
    fi
else
    echo "[OK] .env ja existe"
fi

# ------------------------------------------------------------------
# 6. Criar diretorios
# ------------------------------------------------------------------
echo ""
echo "[6/7] Criando diretorios do projeto..."
mkdir -p db logs models checkpoints results
echo "[OK] Diretorios criados: db, logs, models, checkpoints, results"

# ------------------------------------------------------------------
# 7. Permissoes de segurança (RNF-SE-004)
# ------------------------------------------------------------------
echo ""
echo "[7/7] Configurando permissoes de seguranca..."
chmod 700 db
echo "[OK] Permissoes de db/ configuradas (700)"

echo ""
echo "============================================================"
echo "              SETUP CONCLUIDO COM SUCESSO!"
echo "============================================================"
echo ""
echo "Proximos passos:"
echo ""
echo "  1. Edite .env com suas credenciais Binance"
echo ""
echo "  2. Inicialize o banco e colete dados historicos:"
echo "     source $VENV_DIR/bin/activate && python main.py --setup"
echo "     (ou: make db)"
echo ""
echo "  3. (Opcional) Treine o modelo RL:"
echo "     python main.py --train"
echo "     (ou: make train)"
echo ""
echo "  4. Inicie em modo paper trading:"
echo "     python main.py --mode paper"
echo "     (ou: make paper)"
echo ""
echo "  Use 'make help' para ver todos os comandos disponíveis."
echo "============================================================"
echo ""

# Perguntar se deseja executar setup inicial
read -r -p "Deseja executar o setup inicial agora? (s/n): " RUN_SETUP
if [[ "${RUN_SETUP,,}" == "s" ]]; then
    echo ""
    echo "Executando setup inicial..."
    source "$VENV_DIR/bin/activate"
    python main.py --setup
    echo "[OK] Setup inicial concluido!"
else
    echo ""
    echo "Pulando setup inicial. Execute depois com: python main.py --setup"
fi
