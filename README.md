# ReceiptSplit

> **UPI-native, receipt-first bill splitting for India.**
> Split restaurant bills by item. Pay via UPI. No app install required.

---

## Repository Structure

```
ReceiptSplit/
├── backend/          FastAPI backend (Python 3.12)
├── frontend/         Next.js frontend (Phase 10 — not yet implemented)
├── CHANGELOG.md      Milestone changelog
└── README.md
```

## Development Setup

See [`backend/README.md`](backend/README.md) for full setup instructions.

**Quick start (local Postgres + backend):**
```powershell
docker compose -f docker-compose.dev.yml up -d
cd backend
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Quick start (frontend):**
```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Architecture

- **Backend:** FastAPI (Python 3.12), modular monolith
- **Database:** PostgreSQL 15 for local development; Supabase remains the production-oriented target
- **Auth:** Capability tokens for participants; Supabase Auth for creators (Phase 2)
- **Realtime:** Supabase Realtime broadcast channels
- **OCR:** Free-first `OcrProvider` abstraction with mock and Tesseract providers

## Development Phases

| Phase | Status | Description |
|---|---|---|
| 1 | 🚧 In Progress | Foundation — manual items, rooms, claims, equal + item-wise split |
| 2 | ⬜ Planned | Creator auth + receipt image upload |
| 3 | ⬜ Planned | OCR + receipt parsing |
| 4 | ⬜ Planned | UPI settlement |
| 5 | ⬜ Planned | Security hardening |
| 6 | ⬜ Planned | Pilot readiness |

## Design Documents

- [Product Decisions Document](docs/product_decisions.md)
- [Implementation Plan](docs/implementation_plan.md)
- [Phase 1 Design](docs/phase1_design.md)
- [Phase 1 Design Amendments v1](docs/phase1_design_amendments_v1.md)
