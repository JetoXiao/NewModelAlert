FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUTF8=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN pip install --upgrade pip && pip install .

RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

USER appuser

CMD ["model-alert", "run"]

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD ["python", "-m", "model_alert.healthcheck"]
