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

The free deployment uses three services:

- Website: Vercel, with `frontend` as the project root
- API: Render Free Web Service, defined by the repository-root `render.yaml`
- Database: Supabase Postgres in Singapore

The website is live at <https://receiptsplit-web.vercel.app> and the API is live at
<https://receiptsplit-api.onrender.com>. Vercel tracks the repository's `feat/split-engine`
default branch and automatically creates preview deployments for other branches. Render tracks
backend changes on the same branch and redeploys the API through
`.github/workflows/deploy-render.yml`.

### Deploy the API on Render

1. In Render, choose **New > Blueprint** and connect `Atishay9828/ReceiptSplit`.
2. Render reads `render.yaml`, selects the free plan, and asks for
   `RECEIPTSPLIT_DATABASE_URL`. Paste the Supabase session-pooler URL there; never commit it.
3. Apply the Blueprint. The start command runs Alembic migrations before starting FastAPI.
4. Copy the resulting service URL. This repository currently uses
   `https://receiptsplit-api.onrender.com`.
5. Add the service's private deploy-hook URL as the GitHub Actions repository secret
   `RENDER_DEPLOY_HOOK`. Backend changes pushed to `feat/split-engine` will then redeploy Render.

The Blueprint configures these non-secret API settings:

```text
RECEIPTSPLIT_ENV=production
RECEIPTSPLIT_DATABASE_POOL_SIZE=1
RECEIPTSPLIT_DATABASE_MAX_OVERFLOW=0
RECEIPTSPLIT_DATABASE_POOL_RECYCLE_SECONDS=120
RECEIPTSPLIT_CORS_ORIGINS=https://receiptsplit-web.vercel.app
RECEIPTSPLIT_AUTH_OIDC_PROVIDER=disabled
RECEIPTSPLIT_OCR_PROVIDER=mock
RECEIPTSPLIT_OCR_STORE_RAW_TEXT=false
RECEIPTSPLIT_LOG_LEVEL=INFO
```

### Point Vercel at Render

Set this variable for Production, Preview, and Development in the Vercel website project, then
redeploy the current production commit:

```text
NEXT_PUBLIC_API_BASE_URL=https://<service>.onrender.com
```

For the live deployment, use:

```text
NEXT_PUBLIC_API_BASE_URL=https://receiptsplit-api.onrender.com
```

Verify the API at <https://receiptsplit-api.onrender.com/health>, then open the website and create
a room.
The current public MVP deliberately rejects account JWTs until a production OIDC verifier is
configured; room and participant capability tokens continue to work. OCR uses the mock provider
because free hosting has an ephemeral filesystem.

Render's free service sleeps after 15 minutes without traffic and can take about one minute to wake
on the next request. It provides 750 free instance-hours per workspace per month. Keep a payment
method off the account if automatic billing is not wanted; Render suspends service or builds at the
free limits instead of charging an account without a payment method.

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
