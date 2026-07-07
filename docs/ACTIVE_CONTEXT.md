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
- M012 implementation exists, but closeout is blocked and uncommitted.
- Git is expected to remain dirty until M012 product code, validation, screenshots, and commit are
  completed.

See `docs/MILESTONE_INDEX.md` for compact milestone history and evidence paths.

## Current Immediate Task

Close out M012 when environment access is available:

1. resolve Git/index lock and dirty state
2. run DB-backed settlement API tests
3. run backend and frontend validation
4. run browser smoke
5. capture M012 screenshots
6. commit M012
7. confirm clean git status

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
- blocked screenshot note: `docs/reports/screenshots/M012/M012-screenshots-blocked.md`

## M012 Blockers

- DB-backed settlement API integration tests are not completed.
- Full backend pytest timed out in the prior run with DB-backed errors before completion.
- Browser smoke has not run.
- Screenshots have not been captured.
- `npm.cmd audit --json` is blocked by registry access.
- M012 commit has not been created.
- Prior Git staging hit `.git/index.lock` permission denied.

## Validation Baselines

- M011.1 backend pytest passed with local Docker/Postgres and three skipped tests.
- M011.1 frontend lint, typecheck, tests, and build passed.
- M012 focused backend unit tests, Ruff, focused mypy, frontend lint, typecheck, tests, build, and
  `git diff --check` passed in the prior focused run.
- M012 DB-backed API test is blocked by Docker/Testcontainers named-pipe access denied.
- Full backend mypy remains known-red at about 382/383 errors in 30/31 files depending checkpoint.
- `npm audit` has a known moderate Next/PostCSS advisory chain (`GHSA-qx2v-qp2m-jg93`) or registry
  access blocker depending environment.
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
- M012 blocked screenshot note: `docs/reports/screenshots/M012/M012-screenshots-blocked.md`
- Frontend architecture: `docs/architecture/frontend.md`
- OCR architecture: `docs/architecture/ocr.md`
- Settlement architecture: `docs/architecture/settlement.md`
