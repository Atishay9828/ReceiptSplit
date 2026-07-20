# ReceiptSplit Backend

FastAPI backend for ReceiptSplit. Python 3.12, SQLAlchemy 2 async, PostgreSQL.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker Desktop for the local Postgres compose service, or another PostgreSQL 15+ database

## Setup

```powershell
# Start local Postgres on 127.0.0.1:54329
docker compose -f ..\docker-compose.dev.yml up -d

# Install dependencies (creates .venv automatically)
uv sync --extra dev

# Copy environment template
cp .env.example .env
# The template points to the local compose database and safe dev OCR defaults.

# Run migrations
uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Alembic runs synchronously and derives a `postgresql+psycopg2://...` URL from
`RECEIPTSPLIT_DATABASE_URL`, so `psycopg2-binary` is a normal backend dependency.

## Production

The public API runs on Render at <https://receiptsplit-api.onrender.com>. Its health check is
<https://receiptsplit-api.onrender.com/health>. Render builds from the repository's
`feat/split-engine` branch with `backend` as the root directory; pushes containing backend changes
trigger `.github/workflows/deploy-render.yml`, which calls Render's encrypted deploy hook. See the
root `README.md` and `render.yaml` for the free deployment setup.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `RECEIPTSPLIT_DATABASE_URL` | Yes | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `RECEIPTSPLIT_SUPABASE_URL` | Yes | Supabase project URL |
| `RECEIPTSPLIT_SUPABASE_SERVICE_KEY` | Yes | Supabase service role key (for Realtime publishing) |
| `RECEIPTSPLIT_ENV` | No | `development` / `production` (default: `development`) |
| `RECEIPTSPLIT_CORS_ORIGINS` | No | Comma-separated allowed origins |
| `RECEIPTSPLIT_OCR_PROVIDER` | No | `mock` for local smoke, `tesseract` for local OCR binary |
| `RECEIPTSPLIT_OCR_LOCAL_STORAGE_DIR` | No | Local private receipt image storage path |

## Running Tests

```bash
# All tests
uv run pytest

# Unit tests only (no DB required)
uv run pytest -m unit

# With coverage
uv run pytest --cov=app --cov-report=term-missing

# Property-based tests (more examples)
uv run pytest -m property --hypothesis-seed=0
```

## Code Quality

```bash
# Lint + format check
uv run ruff check .
uv run ruff format --check .

# Type check
uv run mypy app/
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              FastAPI application factory
│   ├── config.py            Pydantic settings
│   ├── database.py          Async SQLAlchemy engine + session factory
│   ├── dependencies.py      Cross-cutting FastAPI dependencies
│   ├── shared/              Value objects, errors, validators
│   ├── auth/                Capability token system
│   ├── rooms/               Bill room lifecycle
│   ├── participants/        Participant management
│   ├── items/               Line items + adjustments
│   ├── claims/              Item claiming
│   ├── splits/              Split engine + lock/unlock
│   └── events/              Realtime event publishing
├── migrations/              Alembic migrations
│   └── versions/
│       └── 001_phase1_schema.py
└── tests/
    ├── unit/
    ├── integration/
    ├── property/
    ├── concurrency/
    └── security/
```
