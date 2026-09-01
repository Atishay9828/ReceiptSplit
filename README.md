# ReceiptSplit

**ReceiptSplit** is a receipt-first bill-splitting application for Indian groups. It turns a shared
restaurant receipt into an editable bill, supports equal and mixed item-wise allocation, and
coordinates UPI payment hand-offs. It does **not** process, hold, or verify funds.

[Repository](https://github.com/Atishay9828/ReceiptSplit) · [Live web app](https://receiptsplit-web.vercel.app)

## What it demonstrates

- **Full-stack product architecture:** a Next.js 16 / TypeScript frontend and a FastAPI / Python 3.12
  modular monolith backed by async SQLAlchemy, Alembic migrations, and PostgreSQL.
- **Correct money handling:** all calculation, API, and storage paths use integer paise. The split
  engine has deterministic residual allocation, caps discounts to prevent negative totals, and is
  covered by unit and property-based tests.
- **Persistent, authenticated collaboration:** Google ID tokens are verified server-side; accounts,
  usernames, friend connections, persistent groups, bills, and room membership are stored in
  PostgreSQL. Invite joins require an authenticated account, while legacy room-scoped capability
  tokens remain supported for compatibility.
- **Recoverable realtime state:** room mutations write an ordered `room_events` record in the same
  database transaction. Clients replay missed events and receive SSE notifications
  that trigger a state refetch. The current broker is process-local, so horizontal fan-out is a
  deliberate future scaling step.
- **Human-confirmed OCR:** receipt uploads go through server-side image validation, metadata
  stripping, private storage, provider-based text extraction, conservative parsing, and an editable
  draft before anything becomes a bill item. The providers are deterministic mock and local
  Tesseract; optional browser PaddleOCR.js supplies only an untrusted candidate.
- **Safe UPI coordination:** the server generates UPI URI/QR payloads from locked totals and tracks
  partial-payment claims, payer confirmations, and disputes. ReceiptSplit never claims to verify a
  bank transfer or integrate a payment gateway.

## Architecture

```text
Next.js client
  ├─ Google sign-in and authenticated invite join
  ├─ Room/group dashboard, OCR review, split and settlement UI
  └─ Authorized SSE replay + refetch
             │
             ▼
FastAPI modular monolith
  ├─ Auth, room/group, item, split, OCR, event, and settlement services
  ├─ Durable events appended in the mutation transaction
  └─ Server-owned money, payee, and settlement state
             │
             ▼
Supabase Postgres (production) / PostgreSQL 15 (local)
```

The deployment configuration expects a Supabase PostgreSQL connection string in the secret
`RECEIPTSPLIT_DATABASE_URL`; credentials are never committed. The web frontend is configured for
Vercel and the API Blueprint is in [render.yaml](render.yaml). Production Google sign-in also
requires `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in Vercel and `RECEIPTSPLIT_AUTH_OIDC_AUDIENCE` in Render.

For deeper design decisions, see the [split engine](docs/architecture/split-engine.md),
[authentication](docs/architecture/auth.md), [events](docs/architecture/events.md),
[OCR](docs/architecture/ocr.md), [persistent rooms](docs/architecture/persistent-rooms.md), and
[settlement](docs/architecture/settlement.md) notes.

## Verification surface

The repository currently contains 379 backend test functions across 53 files and 82 frontend test
declarations across 20 files. Coverage includes API contracts, authorization, split invariants and
property tests, OCR parsing/validation, durable-event behavior, settlement state transitions, and
frontend UI/API flows. These counts describe the checked-in test source; they are not a claim about
a fresh CI run.

Backend quality gates are defined in [backend/pyproject.toml](backend/pyproject.toml): Ruff,
strict Mypy settings, pytest, coverage with an 80% threshold, and property/concurrency/security
markers. The frontend uses ESLint, TypeScript, Vitest, and a production Next.js build.

```powershell
# Backend (from backend/)
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app/

# Frontend (from frontend/)
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

## Run locally

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 20+, npm, and Docker
Desktop.

```powershell
# From the repository root: PostgreSQL 15 on 127.0.0.1:54329
docker compose -f docker-compose.dev.yml up -d

# Backend setup
Set-Location backend
uv sync --extra dev
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run alembic upgrade head

# In one terminal: API
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
# In a second terminal: frontend
Set-Location frontend
npm.cmd install
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Open <http://127.0.0.1:3000>. The local API health endpoint is
<http://127.0.0.1:8000/health> and interactive API docs are at <http://127.0.0.1:8000/docs>.

## Scope and limitations

- OCR is a reviewable draft generator, not an accuracy-guaranteed extraction system.
- The realtime broker is single-process; durable Postgres events remain the source of truth.
- UPI links and QR codes initiate a payment hand-off only. Payment statuses are participant and
  payer assertions, not bank confirmation.
- No wallet, escrow, payment gateway, webhook-based transfer verification, refund flow, or native
  mobile app is implemented.

## Repository layout

```text
backend/    FastAPI services, SQLAlchemy models, Alembic migrations, and pytest suite
frontend/   Next.js App Router UI, API client, Vitest/RTL suite
docs/       Architecture, active context, validation notes, and milestone records
render.yaml Render API Blueprint; injects the Supabase Postgres URL at deployment
```
