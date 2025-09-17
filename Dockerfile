# syntax=docker/dockerfile:1

# 1) Base image
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    API_KEY=dev-key-change-me \
    APP_VERSION=0.1.0

# 2) Workdir
WORKDIR /app

# 3) System deps (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# 4) Python deps (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5) App source
COPY api/ api/
COPY src/ src/
COPY models/ models/
COPY monitoring/ monitoring/
COPY artifacts/ artifacts/
COPY data/ data/
COPY README.md README.md
# Optional project configs if present
COPY pyproject.toml* ./
COPY pytest.ini* ./
COPY .ruff.toml* ./
COPY .pre-commit-config.yaml* ./

# 6) Ensure report/log dirs exist and are writable
RUN mkdir -p /app/monitoring/reports && \
    mkdir -p /app/monitoring && \
    touch /app/monitoring/metrics.csv

# 7) Non-root user
RUN useradd -ms /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# 8) Start FastAPI via uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
