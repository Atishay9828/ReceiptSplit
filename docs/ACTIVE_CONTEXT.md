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

- Last full pass: M014.1 Real-World UX Bug Bash & Payment Flow Repair, commit `2e14478`.
- Current active milestone: M016 Persistent Rooms, Friends, Multi-Bill Ledger & Mixed Item Splits.
- M015 state: CONDITIONAL PASS pending audit approval, Docker/Testcontainers backend proof, and
  real-device UPI checks.
- M015 adds a persisted light/dark theme system, dark-mode UI polish across create/join/room/payment
  screens, pilot QA docs, and mocked local browser screenshot evidence.
- M015.1 state: CONDITIONAL PASS. It repairs creator display identity, discount/percentage
  adjustment math, step-based creator views, settled completion UX, and the dark navy/cyan/violet
  theme identity. Remaining condition: `npm audit --json` reports 2 moderate Next/PostCSS
  advisories; real-device UPI behavior is still external QA.
- M014.1 repaired quantity claiming, payment status visibility, settlement state-machine, room
  settled transitions, and participant removal.

See `docs/MILESTONE_INDEX.md` for compact milestone history and evidence paths.

## Current Immediate Task

M016 is ready for closeout. Google sign-in and the signed-in production dashboard have now passed
live smoke testing. The remaining open release conditions belong to M015/M015.1: the known
Next/PostCSS audit advisory and real-device UPI checks.

- Settlement requests support partial payments: a participant chooses any positive amount up to
  the remaining balance, the payer confirms or disputes that single pending claim, and confirmed
  amounts accumulate without closing the bill early.
- Group and bill dashboards report original, cleared, and pending paise from cumulative confirmed
  amounts. The room settles only after every remaining balance reaches zero.
## M016 Current Implementation

- A persistent room is a long-lived friend group; each receipt is a separate bill under that room.
- Room dashboards aggregate all bill totals plus money pending and payer-confirmed as cleared.
- Locked non-payer shares count as pending even before someone opens the UPI action.
- Item-wise bills can mix individually claimed items with items split equally among everyone.
- Participant controls use explicit `Add to my share` / `Remove` actions and quantity wording;
  the ambiguous `Claim 1/2` labels are gone.
- Account profiles support unique usernames, direct friend connections, and multiple groups.
- Partial-payment regression coverage proves overclaim rejection, one pending claim at a time,
  incremental payer confirmation, final settlement, and group-level cleared/pending totals.
- Existing PostgreSQL schema upgraded from `007_persistent_rooms` to
  `008_partial_settlements`; a fresh temporary PostgreSQL database also migrated from `001`
  through `008` successfully.
- Full backend pytest passed with three expected skips and one Starlette deprecation warning;
  backend Ruff and focused strict mypy passed.
- Frontend lint, typecheck, 19 files / 79 tests, and production build passed.
- Google Identity Services is wired end to end through server-side ID-token verification. The
  production OAuth client is configured for `https://receiptsplit-web.vercel.app`, the external
  consent screen is published, and a real Google account completed sign-in on the live dashboard.
- Architecture details: `docs/architecture/persistent-rooms.md`.

M016 validation in this working tree:

- Backend Ruff passed.
- Focused strict mypy passed for the new community, auth, and mixed-split scope.
- PostgreSQL integration tests passed for accounts, usernames, friends, persistent rooms,
  multi-bill membership, pending/cleared totals, authorization, and settlement privacy.
- Frontend lint and typecheck passed; 19 files / 79 tests passed; production build passed.
- Browser smoke passed for the live dashboard Google button plus a production mixed-item bill:
  a ₹600 equally shared pizza and ₹120 individually claimed drink produced ₹420/₹300 participant
  totals with no numbered claim labels.
- The same production smoke verified a manual partial settlement: ₹125.50 moved to cleared while
  ₹174.50 remained pending for a later payment. The bill stayed open in `settling`.
- A production-smoke UX gap was fixed afterward: payer-only rooms now ask the creator to invite
  another person instead of calling preview and showing a misleading retry error.
- Authenticated dashboard regressions cover Google credential exchange, the persisted account
  session, friends added by username, room creation with selected friends, multi-bill rendering,
  and original/pending/cleared ledger totals.
- Signed-in production smoke passed for `@atishay9828`: a friend was added by username, `Goa Demo
  Trip` was created with two members, and a second `Weekend Demo Room` remained separate with a
  different member set.
- `Goa Demo Trip` retained two bills at once. `Dinner Day 1` remained open with ₹300 pending while
  `Cab Day 2` independently previewed an ₹800 equal split as ₹400/₹400.
- The smoke test exposed and repaired a dashboard summary gap: active bills now report their
  current receipt total before a locked split session exists, instead of appearing as ₹0.
- The production auth verifier was corrected from disabled to Google OIDC before the signed-in
  smoke. Render then deployed the exact production commit successfully.
- Full backend pytest passed after the compatibility fix, with three expected skips and one
  Starlette deprecation warning.
- The final privacy regression also passed against PostgreSQL after Docker Desktop was restored;
  friend and group responses do not expose Google email addresses.
- Render is live at migration `008_partial_settlements`, including the persistent group/friend
  tables and cumulative settlement fields. A legacy database ownership mismatch was repaired by
  transferring the ReceiptSplit schema objects to the application role before redeploying.
- The production branch is deployed through Render and Vercel. M016 has signed-in browser proof
  for Google auth, usernames, friends, multiple persistent rooms, multiple bills in one room,
  mixed equal/individual items, and a pending settlement that remains open for later clearing.
- Render deployed API commit `7f6ff5e`; the final live dashboard showed `Goa Demo Trip` at ₹1,520
  across its ₹720 and ₹800 bills, with ₹300 pending and ₹0 payer-confirmed as cleared.

## M014.1 Current Implementation

Frontend:

- Quantity selection in `CreatorClaimSection` and `ParticipantClaimList`
- Participant settlement panel shows QR codes and payment states
- Creator settlement panel allows safe payment confirmation
- Automatic transition to `settled` state when all payments confirmed
- Full participant removal UI

Backend:

- `removeParticipant` API with claim cleanup and event broadcast
- Room `settled` auto-transition on payment confirmation

Docs:

- active architecture: `docs/architecture/frontend.md`
- archived closeout evidence: `docs/archive/milestones/M014-frontend-experience-polish.md`

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

M014.1 closeout checks:

- `npm.cmd run lint` -> passed
- `npm.cmd run typecheck` -> passed
- `npm.cmd test` -> 11 files, 51 tests passed
- `npm.cmd run build` -> passed
- `npm.cmd audit --json` -> 2 moderate, 0 high, 0 critical; no force fix
- `.\.venv\Scripts\python.exe -m pytest tests\ -q` -> full backend suite passed with 3 skipped
- `.\.venv\Scripts\python.exe -m ruff check .` -> passed
- Production browser smoke passed through create, join, claim, quantity change, lock, save payer details, prepare settlement, open payment, claim paid, payer confirm, and room transition to settled.

M015 closeout checks:

- `npm.cmd run lint` -> passed
- `npm.cmd run typecheck` -> passed
- `npm.cmd test` -> 12 files, 56 tests passed
- `npm.cmd run build` -> passed
- `npm.cmd audit --json` -> blocked by approval reviewer because audit sends dependency metadata
  to npm
- `.\.venv\Scripts\python.exe -m pytest tests\ -q` -> blocked by Docker/Testcontainers named-pipe
  access
- `.\.venv\Scripts\python.exe -m ruff check .` -> passed
- Unsafe payment copy search matched only tests/docs forbidden examples
- Mocked browser UI smoke with system Edge captured screenshots under `docs/reports/screenshots/M015/`

M015.1 focused checks:

- Backend split calculator tests cover subtractive discounts and percentage tax/discount math.
- Full backend pytest passed after unrestricted rerun, with three skipped tests and one Starlette
  deprecation warning.
- Backend Ruff passed.
- Frontend lint, typecheck, tests, and build passed.
- Frontend tests cover creator chip fallback, percentage adjustment UI, step headers, and settled
  completion copy.
- `npm audit --json` -> 2 moderate, 0 high, 0 critical for Next/PostCSS; no forced downgrade.
- Mocked local production browser smoke captured 14 dark-mode screenshots under
  `docs/reports/screenshots/M015.1/`.
- User-facing forbidden payment-claim copy scan found no unsafe verification claims.

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
- M015 pilot docs: `docs/pilot/`
- OCR architecture: `docs/architecture/ocr.md`
- Settlement architecture: `docs/architecture/settlement.md`
- Security architecture: `docs/architecture/security.md`
