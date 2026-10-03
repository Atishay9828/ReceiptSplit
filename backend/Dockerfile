FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_THREAD_LIMIT=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr=5.3.0-2 tesseract-ocr-eng=1:4.1.0-2 \
    && rm -rf /var/lib/apt/lists/* \
    && tesseract --list-langs | grep -Fx eng

RUN pip install --no-cache-dir uv==0.11.21

COPY pyproject.toml uv.lock README.md ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

RUN uv sync --frozen --no-dev --link-mode=copy --compile-bytecode

EXPOSE 8000

CMD ["sh", "-c", "uv run --no-dev alembic upgrade head && exec uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
