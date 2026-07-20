# ReceiptSplit

> UPI-native, receipt-first bill splitting for India.
> Split restaurant bills by item. Pay via UPI. No app install required.

## Repository Structure

```text
ReceiptSplit/
├── backend/          FastAPI backend (Python 3.12)
├── frontend/         Next.js frontend for room, OCR review, and settlement UI
├── docs/             Active context, architecture notes, and archived reports
├── task.md           Short current-task pointer
└── README.md
```

## Run Locally

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- Docker Desktop with the Docker engine running

The commands below are for Windows PowerShell and start PostgreSQL, the FastAPI backend, and the
Next.js website.

### First-time setup

Run these commands from the repository root:

```powershell
# Start PostgreSQL on 127.0.0.1:54329
docker compose -f docker-compose.dev.yml up -d

# Install backend dependencies and create backend/.env
Set-Location backend
uv sync --extra dev
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run alembic upgrade head
Set-Location ..

# Install frontend dependencies and create frontend/.env.local
Set-Location frontend
npm.cmd install
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
Set-Location ..
```

### Start the app

Keep the following two terminals open.

Terminal 1 - backend:

```powershell
Set-Location backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If `uv` is unavailable after the environment has already been created, use:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 - website:

```powershell
Set-Location frontend
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Open the website at <http://127.0.0.1:3000>. The backend API runs at
<http://127.0.0.1:8000>, its health check is <http://127.0.0.1:8000/health>, and interactive API
documentation is available at <http://127.0.0.1:8000/docs>.

After pulling backend changes that include new migrations, run this before starting the backend:

```powershell
Set-Location backend
uv run alembic upgrade head
```

### Stop the app

Press `Ctrl+C` in both development-server terminals. Stop the local database from the repository
root when it is no longer needed:

```powershell
docker compose -f docker-compose.dev.yml down
```

See `backend/README.md` for backend configuration and test commands.

## Deploy from GitHub

The production setup uses two Vercel projects and one managed PostgreSQL database:

- Website: <https://receiptsplit-web.vercel.app> (project root: `frontend`)
- API health: <https://receiptsplit-api.vercel.app/health> (project root: `backend`)
- Database: Supabase Postgres in Singapore, close to the API region

Vercel automatically creates preview deployments for branches and redeploys production when the
configured production branch is updated. Do not commit deployment secrets or local `.env` files.

Configure these API environment variables in Vercel:

```text
RECEIPTSPLIT_ENV=production
RECEIPTSPLIT_DATABASE_URL=<managed-postgres-session-pooler-url>
RECEIPTSPLIT_DATABASE_POOL_SIZE=1
RECEIPTSPLIT_DATABASE_MAX_OVERFLOW=0
RECEIPTSPLIT_DATABASE_POOL_RECYCLE_SECONDS=120
RECEIPTSPLIT_CORS_ORIGINS=https://receiptsplit-web.vercel.app
RECEIPTSPLIT_AUTH_OIDC_PROVIDER=disabled
RECEIPTSPLIT_OCR_PROVIDER=mock
RECEIPTSPLIT_OCR_STORE_RAW_TEXT=false
RECEIPTSPLIT_LOG_LEVEL=INFO
```

Configure the website project after the API URL is known:

```text
NEXT_PUBLIC_API_BASE_URL=https://receiptsplit-api.vercel.app
```

Run every committed Alembic migration against the managed database before deploying backend code
that depends on it. The current public MVP deliberately rejects account JWTs until a production
OIDC verifier is configured; room and participant capability tokens continue to work. OCR uses the
mock provider because Vercel's local filesystem is ephemeral.

The initial production builds are live. Git-triggered redeployment requires both Vercel projects
to be linked to `Atishay9828/ReceiptSplit` with `feat/split-engine` as the production branch.

## Architecture

- Backend: FastAPI modular monolith.
- Database: PostgreSQL 15 locally; Supabase remains the production-oriented target.
- Auth: owner JWT for creators, legacy creator capability tokens, and participant capability tokens.
- Realtime: durable `room_events` with fetch-based SSE refetch.
- OCR: free-first `OcrProvider` abstraction with mock and Tesseract providers.
- Settlement: coordinator-safe UPI URI/QR generation and manual payer confirmation.

## Product Boundary

ReceiptSplit coordinates settlement; it does not process funds.

M012 generates server-controlled UPI payment links/QR payloads, records participant `marked paid`
claims, and lets the payer manually confirm or dispute. It does not implement wallet, escrow,
payment gateway, webhooks, bank verification, refunds, or auto-confirmation.

## Development Phases

| Phase | Status | Description |
|---|---|---|
| 1 | Implemented | Foundation: manual items, rooms, claims, equal and item-wise split |
| 2 | Implemented | Creator auth and receipt image upload |
| 3 | Implemented | OCR and receipt parsing |
| 4 | Conditional | UPI settlement coordination |
| 5 | Planned | Security hardening |
| 6 | Planned | Pilot readiness |

## Current Context

- `docs/ACTIVE_CONTEXT.md`
- `docs/MILESTONE_INDEX.md`
- `task.md`
- `docs/architecture/frontend.md`
- `docs/architecture/settlement.md`

Historical milestone reports are archived under `docs/archive/milestones/`. Do not use them as the
default working context unless investigating a specific milestone.
