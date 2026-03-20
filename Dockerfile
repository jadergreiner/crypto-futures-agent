# syntax=docker/dockerfile:1
# Imagem de producao para o crypto-futures-agent (Python 3.11-slim)
# Compativel com Ubuntu 22.04 LTS e qualquer host Linux/cloud.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias do sistema (TA-Lib nao e necessaria por padrao; adicionar se usado)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# ── Fase de dependencias ──────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ── Imagem final ──────────────────────────────────────────────────────
FROM deps AS runtime

COPY . .

# Criar diretorios persistidos via volume
RUN mkdir -p db logs results checkpoints models

# Permissoes restritas para o banco (RNF-SE-004)
RUN chmod 700 db

# Usuario nao-root para seguranca
RUN groupadd --gid 1001 agent \
    && useradd --uid 1001 --gid agent --shell /bin/bash --create-home agent \
    && chown -R agent:agent /app

USER agent

# Porta reservada para futuro servidor de status/API (nao exposta por padrao)
EXPOSE 8080

# Health check via modulo de status
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from core.model2.repository import Model2ThesisRepository; print('ok')" || exit 1

# Entrada padrao: pipeline diario modo paper
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "paper"]
