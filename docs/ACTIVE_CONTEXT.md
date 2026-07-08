# ReceiptSplit Active Context

## How To Use This File

Read this first. It is the current project state, not a full milestone history.
Historical milestone reports live in `docs/archive/milestones/` and should only be opened when
investigating that milestone.

Do not load all markdown files by default. Archived reports are evidence, not active working
context.

## Future Agent Reading Order

1. `docs/ACTIVE_CONTEXT.md`
2. `docs/MILESTONE_INDEX.md`
3. `task.md`
4. current git diff/status
5. archived milestone reports only when needed

## Product Boundary

- ReceiptSplit is a UPI-native, receipt-first settlement coordinator for India.
- It is not a wallet, escrow service, payment intermediary, payment gateway, or verification system.
- Do not add fund holding, fund pooling, refunds, auto-confirmation, webhook verification, or
  `verified paid` claims unless a future milestone explicitly changes scope.
- Money is integer paise in storage, API payloads, services, and tests.
- Rupee strings are allowed only at display and UPI URI boundaries.

## Architecture Snapshot

- Backend: FastAPI modular monolith with SQLAlchemy async and Postgres.
- Frontend: Next.js App Router, TypeScript, Tailwind, mobile-first room flows.
- Realtime: durable `room_events` is the source of truth; SSE is an optimization for refetch.
- Auth: owner JWT plus legacy room-scoped creator and participant capability tokens.
- OCR: provider-based pipeline with mock and Tesseract providers; OCR creates editable drafts.
- Settlement: server-generated UPI links/QR payloads, manual participant and payer status changes.

## Current Milestone Status

- Last full pass before M013: M012 UPI Settlement MVP, commits `8c39279` and `05456c0`.
- Current active milestone: M013 Security Hardening & Abuse Controls.
- M013 state: FULL PASS after validation and local DB smoke; closeout commit pending.
- M013 adds lightweight rate limits, durable security audit logs, abuse reports, payer detail
  change blocking after settlement prepare, suspicious activity audit flags, and noindex/security
  headers for sensitive room routes.

See `docs/MILESTONE_INDEX.md` for compact milestone history and evidence paths.

## Current Immediate Task

Create the M013 closeout commit, then keep the working tree clean.

## M012 Current Implementation

Backend:

- settlement domain and status transitions
- migration `backend/migrations/versions/004_m012_settlement_mvp.py`
- `settlement_requests` and `settlement_status_events` models
- `SettlementService`
- `SettlementLinkBuilder`
- settlement API schemas and routes

Frontend:

- creator settlement setup and dashboard
- participant pay-your-share card
- open-payment, claim-paid, confirm, and dispute actions
- server-generated UPI URI/QR payload usage

Docs:

- active architecture: `docs/architecture/settlement.md`
- archived closeout evidence: `docs/archive/milestones/M012-upi-settlement.md`
- screenshot evidence note: `docs/reports/screenshots/M012/M012-screenshots-blocked.md`

## M012 Blockers

- None carried into M013 per user confirmation on 2026-07-08.

## Validation Baselines

- M011.1 backend pytest passed with local Docker/Postgres and three skipped tests.
- M011.1 frontend lint, typecheck, tests, and build passed.
- M012 DB-backed API tests passed: `.\.venv\Scripts\python.exe -m pytest tests\api\test_settlement.py -q`.
- Full backend pytest passed when rerun with a longer timeout after isolated API/non-API passes.
- Backend Ruff passed.
- Focused M012 mypy passed for 12 settlement-touched backend files.
- Frontend lint, typecheck, tests, and build passed.
- `git diff --check` passed with only CRLF normalization warnings.
- Browser smoke passed through payer-confirmed and disputed states with screenshots under
  `docs/reports/screenshots/M012/`.
- Full backend mypy remains known-red at about 382/383 errors in 30/31 files depending checkpoint.
- `npm audit` remains unverified in this run because registry metadata submission was rejected by
  the approval reviewer.
- Browser E2E harness is deferred.

M013 focused checks passing so far:

- `.\.venv\Scripts\python.exe -m pytest tests\api\test_m013_security.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\api\test_settlement.py tests\api\test_rooms.py tests\api\test_participants.py -q`
- `npm.cmd test -- settlement-ui.test.tsx api.test.ts security-headers.test.ts`
- Full backend pytest passed: `.\.venv\Scripts\python.exe -m pytest tests\ -q`
- Backend Ruff passed: `.\.venv\Scripts\python.exe -m ruff check .`
- Focused M013 mypy passed for changed backend/API/security/test files.
- Frontend lint, typecheck, tests, and build passed.
- `npm.cmd audit --json` returned 2 moderate advisories, 0 high, 0 critical:
  `GHSA-qx2v-qp2m-jg93` via Next/PostCSS. No `npm audit fix --force` was run.
- Local Postgres smoke passed through create room, join, lock, settlement prepare, open payment,
  claim paid, payer confirm, and abuse report.

## Non-Negotiables For Future Agents

- No scope creep into gateway, wallet, escrow, refunds, cashback, deployment, or native app work.
- No payment verification, bank confirmation, webhook confirmation, or `verified paid` wording.
- No floats for money.
- Do not trust frontend-submitted amount, VPA, payee name, or settlement reference.
- Durable DB state is source of truth.
- SSE/refetch is an optimization over durable `room_events`.
- Do not leak raw tokens in logs, responses, screenshots, or docs.
- Preserve screenshot notes, validation artifacts, migrations, tests, and source evidence.

## Useful Commands

Local Postgres:

```powershell
docker compose -f docker-compose.dev.yml up -d
```

Backend:

```powershell
cd D:\ReceiptSplit\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m pytest tests\ -q
.\.venv\Scripts\python.exe -m ruff check .
```

Frontend:

```powershell
cd D:\ReceiptSplit\frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Focused M012 checks:

```powershell
cd D:\ReceiptSplit\backend
.\.venv\Scripts\python.exe -m pytest tests\unit\test_settlement_link_builder.py -q
.\.venv\Scripts\python.exe -m pytest tests\api\test_settlement.py -q

cd D:\ReceiptSplit\frontend
npm.cmd test -- settlement-ui.test.tsx api.test.ts
```

## Key Evidence Paths

- Milestone index: `docs/MILESTONE_INDEX.md`
- Archived milestone reports: `docs/archive/milestones/`
- M011.1 screenshots: `docs/reports/screenshots/M011.1/`
- M012 screenshot evidence note: `docs/reports/screenshots/M012/M012-screenshots-blocked.md`
- Frontend architecture: `docs/architecture/frontend.md`
- OCR architecture: `docs/architecture/ocr.md`
- Settlement architecture: `docs/architecture/settlement.md`
- Security architecture: `docs/architecture/security.md`
