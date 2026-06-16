# ReceiptSplit Backend

FastAPI backend for ReceiptSplit. Python 3.12, SQLAlchemy 2 async, PostgreSQL.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 15+ (or Supabase project)

## Setup

```bash
# Install dependencies (creates .venv automatically)
uv sync --extra dev

# Copy environment template
cp .env.example .env
# Edit .env with your database URL and Supabase keys

# Run migrations
uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --reload --port 8000
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `RECEIPTSPLIT_DATABASE_URL` | Yes | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `RECEIPTSPLIT_SUPABASE_URL` | Yes | Supabase project URL |
| `RECEIPTSPLIT_SUPABASE_SERVICE_KEY` | Yes | Supabase service role key (for Realtime publishing) |
| `RECEIPTSPLIT_ENV` | No | `development` / `production` (default: `development`) |
| `RECEIPTSPLIT_CORS_ORIGINS` | No | Comma-separated allowed origins |

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
