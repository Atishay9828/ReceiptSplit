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

- Last full pass: M011.1 OCR Frontend Review UI, commit `2985a40`.
- Current active milestone: M012 UPI Settlement MVP.
- M012 state: CONDITIONAL PASS only.
- M012 implementation exists, DB-backed API tests now pass, and all requested browser screenshot
  evidence is captured.
- M012 closeout commit: `8c39279`.
- M012 remains CONDITIONAL PASS because `npm.cmd audit --json` is unverified: the sandboxed retry
  failed at the npm registry endpoint, and the escalated retry was rejected because it would send
  dependency metadata to the public npm registry.

See `docs/MILESTONE_INDEX.md` for compact milestone history and evidence paths.

## Current Immediate Task

Close out the remaining M012 gates only when policy/user approval allows registry metadata
submission:

1. rerun `npm.cmd audit --json`
2. update M012 from CONDITIONAL PASS to FULL PASS only if audit evidence is captured

Do not start M013 or payment-gateway work while M012 is conditional.

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

- `npm.cmd audit --json` remains unverified. The sandboxed retry failed at the npm registry
  endpoint, and the escalated retry was rejected because it sends dependency metadata to the public
  npm registry.
- Prior Git index-lock issues are not present in this closeout run.

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
