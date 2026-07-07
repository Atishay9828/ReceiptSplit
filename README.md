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

## Development Setup

See `backend/README.md` for backend setup details.

Local backend:

```powershell
docker compose -f docker-compose.dev.yml up -d
cd backend
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Local frontend:

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

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
