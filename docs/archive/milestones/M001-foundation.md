> Historical milestone evidence.
> Do not load this file into default working context unless investigating this milestone.
> For current project state, read `docs/ACTIVE_CONTEXT.md` and `docs/MILESTONE_INDEX.md`.

# Milestone M001 — Foundation

## Goal

Establish a clean, reproducible project skeleton that all future milestones build upon. This includes the Git repository, Python toolchain, linter configuration, dependency management, project layout, and baseline application entry point.

---

## Scope

**Included:**
- Git repository initialisation
- `.gitignore` and `.gitattributes` (LF line endings enforced)
- Python packaging via `uv` + `pyproject.toml`
- `ruff` linter and formatter configured
- `pytest` test runner with markers, asyncio, coverage plug-ins
- FastAPI application skeleton (`app/main.py`, `app/config.py`, `app/database.py`)
- Alembic migration framework wired to async SQLAlchemy engine
- `CHANGELOG.md` and `README.md`
- `.env.example` with all required environment variables documented

**Excluded:**
- Any database schema (M002)
- Any domain logic (M003+)
- Any API endpoints
- Any frontend

---

## Files Created

| File | Purpose |
|------|---------|
| `.gitignore` | Ignore `.venv`, `__pycache__`, `.env`, pytest/ruff caches |
| `.gitattributes` | Enforce LF line endings on all text files |
| `CHANGELOG.md` | Human-readable change history |
| `README.md` | Project overview and setup instructions |
| `backend/pyproject.toml` | Project metadata, dependencies, tool configuration |
| `backend/.env.example` | All required environment variables with documentation |
| `backend/alembic.ini` | Alembic configuration pointing at `migrations/` |
| `backend/migrations/env.py` | Async Alembic env wired to `app.database` engine |
| `backend/migrations/script.py.mako` | Migration file template |
| `backend/migrations/README` | Alembic boilerplate readme |
| `backend/app/__init__.py` | Package marker |
| `backend/app/config.py` | Pydantic `Settings` class — reads `.env`, validates all config |
| `backend/app/database.py` | Async SQLAlchemy engine lifecycle, `get_db` dependency |
| `backend/app/main.py` | FastAPI app factory, lifespan, CORS, root health endpoint |
| `backend/tests/__init__.py` | Test package marker |
| `backend/tests/conftest.py` | Shared pytest fixtures |

## Files Modified

None — this is the initial commit.

---

## Architecture Decisions

### `uv` for dependency management
`uv` was chosen over `pip`/`poetry` for its deterministic lockfile (`uv.lock`) and significantly faster installs. All subsequent milestones run via `uv run pytest`, `uv run alembic`, etc.

### `pyproject.toml`-only configuration
All tool config (`ruff`, `pytest`, `mypy`) lives in `pyproject.toml`. No separate `setup.cfg`, `.flake8`, or `pytest.ini` files.

### Async-first database layer
`app/database.py` uses `asyncpg` driver and `AsyncSession` from `sqlalchemy.ext.asyncio`. This was chosen from day one to avoid a painful async migration later. All repository layer code (M005) will use async sessions natively.

### `ruff` over `flake8 + isort + black`
Single tool for formatting, import sorting, and linting. Configured with aggressive rules including `B` (flake8-bugbear), `SIM` (simplify), `TC` (type-checking), `C4` (comprehensions), `UP` (pyupgrade).

### `pytest` markers
`unit`, `integration`, `e2e` markers defined in `pyproject.toml`. All split engine tests are tagged `@pytest.mark.unit` and run without any I/O.

---

## Implementation Details

```
pyproject.toml
  ↓ defines
FastAPI (app/main.py)
  ↓ uses
Settings (app/config.py)   ←  .env / environment variables
AsyncEngine (app/database.py) ← asyncpg / PostgreSQL
Alembic (alembic.ini + migrations/env.py)
```

**Key configuration values documented in `.env.example`:**
- `DATABASE_URL` — asyncpg connection string
- `SECRET_KEY` — 32+ byte HMAC key for token signing
- `ENVIRONMENT` — `development` | `production`
- `CORS_ORIGINS` — comma-separated list of allowed frontend origins

---

## Bugs Found During Development

None.

---

## Testing

| Test File | Count | Status |
|-----------|-------|--------|
| (no tests in M001) | 0 | — |

---

## Git History

| Commit | Message |
|--------|---------|
| `5d49d42` | `chore(repo): initialize repository with project structure and tooling` |
| `c46b18e` | `chore(repo): add .gitattributes for consistent LF line endings` |

---

## Risks / Known Limitations

- No database migration yet — the app will crash on startup without a valid `DATABASE_URL` and a migrated schema.
- No authentication middleware — the app is fully open in this milestone.
- CORS origins are hard-coded to `["*"]` in development mode; must be restricted for production.

---

## Next Milestone

**M002 — Database Schema**
- Objective: Define the full Phase 1 PostgreSQL schema (12 tables) as a single Alembic migration.
- Dependencies: M001 complete.
- Blockers: None.

---

## Updated Progress

```
[x] Repository setup        ← M001
[ ] Database schema
[ ] Domain foundations
[ ] Split engine
[ ] Repository layer
[ ] Services
[ ] API layer
[ ] Frontend
[ ] Realtime
[ ] Deployment
```

---

## Acceptance Checklist

| Requirement | Status |
|-------------|--------|
| Git repository initialised | ✅ |
| `.gitignore` and `.gitattributes` present | ✅ |
| `uv` lockfile committed | ✅ |
| `pyproject.toml` with `ruff`, `pytest`, dependency config | ✅ |
| FastAPI app boots without error | ✅ |
| Alembic wired to async engine | ✅ |
| `.env.example` documents all config | ✅ |
| `CHANGELOG.md` and `README.md` present | ✅ |
