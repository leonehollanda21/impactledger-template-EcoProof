# ══════════════════════════════════════════════
#  EcoProof API — Dockerfile
#  Base: python:3.11-slim
#  Porta: 8000
# ══════════════════════════════════════════════

FROM python:3.11-slim

# Metadados
LABEL maintainer="EcoProof Team <api@ecoproof.io>"
LABEL description="EcoProof API — Plataforma Web3 de ações ambientais"

# Variáveis de ambiente Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema (necessário para psycopg2-binary, bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python primeiro (cache de layer)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copia o código da aplicação
COPY . .

# Cria diretório para credenciais Google (montado via volume em produção)
RUN mkdir -p /app/credentials

# Usuário não-root para segurança
RUN useradd -m -u 1000 ecoproof && chown -R ecoproof:ecoproof /app
USER ecoproof

# Expõe a porta da API
EXPOSE 8000

# Healthcheck interno do Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização
# --workers 1 para desenvolvimento; em prod use: --workers 4
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
