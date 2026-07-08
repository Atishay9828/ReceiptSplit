> Historical milestone evidence.
> Do not load this file into default working context unless investigating this milestone.
> For current project state, read `docs/ACTIVE_CONTEXT.md` and `docs/MILESTONE_INDEX.md`.

# M012 UPI Settlement MVP

## Verdict

CONDITIONAL PASS.

The implemented code covers coordinator-safe UPI settlement APIs, frontend room flows, server-side
UPI URI generation, manual status transitions, durable status events, DB-backed API tests, and
browser evidence through payer-confirmed and disputed states. This is not a full pass because the
npm audit result remains blocked by public-registry metadata submission policy.

## Scope

Delivered:

- Creator/payer payout setup.
- Idempotent settlement request preparation from locked `participant_totals`.
- Server-generated UPI URI and QR payload.
- Participant `open payment` and `I paid` actions.
- Creator/payer `Confirm payment` and `Mark disputed` actions.
- Statuses: `due`, `payment_opened`, `claimed_paid`, `payer_confirmed`, `disputed`.
- Durable settlement status history and room events.
- Frontend creator settlement dashboard and participant payment card.

Non-goals preserved:

- No wallet.
- No escrow.
- No payment gateway.
- No webhooks.
- No bank-transfer verification.
- No auto-confirmation.
- No refunds or fund handling.

## Product Boundary

ReceiptSplit tells participants what to pay and helps open a UPI app. It does not process or verify
payments.

Safe language used:

- `marked paid`
- `waiting for payer confirmation`
- `payer confirmed`
- `disputed by payer`

Unsafe language avoided:

- `verified paid`
- `payment successful`
- `bank verified`
- `transfer verified`

## Data Model Changes

Migration:

- `backend/migrations/versions/004_m012_settlement_mvp.py`

Tables added:

- `settlement_requests`
- `settlement_status_events`

Existing fields used:

- `rooms.payer_vpa`
- `rooms.payer_name`
- `split_sessions`
- `participant_totals`
- `room_events`

Indexes:

- `idx_settlement_requests_room`
- `idx_settlement_requests_room_participant`
- `idx_settlement_requests_room_status`
- `uq_settlement_requests_room_participant_session`
- `idx_settlement_status_events_room_request_created`

Money storage:

- Integer paise in DB, API, service logic, and tests.
- Rupee decimal string only at UPI URI/display boundary.

## Backend

Services and domain:

- `backend/app/domain/settlement.py`
- `backend/app/services/settlement_service.py`

API endpoints:

- `GET /api/rooms/{room_id}/settlement`
- `PUT /api/rooms/{room_id}/settlement/payer`
- `POST /api/rooms/{room_id}/settlement/prepare`
- `POST /api/rooms/{room_id}/settlement/requests/{request_id}/open-payment`
- `POST /api/rooms/{room_id}/settlement/requests/{request_id}/claim-paid`
- `POST /api/rooms/{room_id}/settlement/requests/{request_id}/confirm`
- `POST /api/rooms/{room_id}/settlement/requests/{request_id}/dispute`

Auth rules:

- Creator/owner only: configure payer, prepare, confirm, dispute.
- Participant only: open own request, claim own request.
- Existing room-scoped auth dependencies reject cross-room capability tokens.

Status transitions:

| From | Allowed to |
|---|---|
| `due` | `payment_opened`, `claimed_paid`, `disputed` |
| `payment_opened` | `claimed_paid`, `disputed` |
| `claimed_paid` | `payer_confirmed`, `disputed` |
| `disputed` | `payment_opened`, `claimed_paid`, `payer_confirmed` |
| `payer_confirmed` | terminal |

Events:

- `settlement.payer_configured`
- `settlement.requests_prepared`
- `settlement.payment_opened`
- `settlement.claimed_paid`
- `settlement.payer_confirmed`
- `settlement.disputed`

## Frontend

Files changed:

- `frontend/types/api.ts`
- `frontend/lib/api.ts`
- `frontend/components/room-client.tsx`

Creator UI:

- Payout details form after lock.
- Prepare settlement button.
- Per-participant settlement dashboard.
- Confirm payment and Mark disputed controls.

Participant UI:

- Pay your share card.
- Open UPI app action.
- QR fallback from server-generated payload.
- Copy UPI ID fallback.
- I paid action.
- Payer confirmed and disputed status states.

Frontend does not submit trusted payable amount, payee VPA, payee name, or payment reference.

## Smoke Result

Browser smoke was completed through the payer-confirmed path on 2026-07-07 and the disputed path on
2026-07-08 using local demo data and the fake VPA `receiptsplit.test@upi`.

Verified:

- fresh room created
- two demo items added
- room opened for claiming
- participant joined and claimed items
- creator preview showed Bob Demo owing `₹160.00`
- creator locked the room
- creator prepared settlement
- participant saw Pay your share card
- participant opened UPI flow and QR fallback rendered from a server payload
- status changed to `payment opened`
- participant marked `I paid`
- status changed to `marked paid`
- creator saw `marked paid`
- creator manually confirmed payment
- participant saw `payer confirmed`
- a second local smoke room reached `disputed`
- creator saw the `disputed` settlement status

Screenshot evidence:

- `docs/reports/screenshots/M012/creator-payer-setup.png`
- `docs/reports/screenshots/M012/settlement-prepared.png`
- `docs/reports/screenshots/M012/participant-pay-card.png`
- `docs/reports/screenshots/M012/payment-opened-upi-link.png`
- `docs/reports/screenshots/M012/participant-claimed-paid.png`
- `docs/reports/screenshots/M012/creator-confirm-payment.png`
- `docs/reports/screenshots/M012/payer-confirmed.png`
- `docs/reports/screenshots/M012/disputed-payment.png`
- `docs/reports/screenshots/M012/M012-screenshots-blocked.md`

## Validation

Passed:

```powershell
cd D:\ReceiptSplit\backend
.\.venv\Scripts\python.exe -m pytest tests\unit\test_settlement_link_builder.py -q
.\.venv\Scripts\python.exe -m ruff check app tests\unit\test_settlement_link_builder.py tests\api\test_settlement.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy app\domain\settlement.py app\services\settlement_service.py app\api\routers\settlement.py app\api\schemas\settlement.py app\models\settlement_request.py app\models\settlement_status_event.py tests\api\test_settlement.py

cd D:\ReceiptSplit\frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test -- settlement-ui.test.tsx api.test.ts
npm.cmd test
npm.cmd run build

cd D:\ReceiptSplit
git diff --check
```

Passed in the latest closeout run:

```powershell
cd D:\ReceiptSplit\backend
.\.venv\Scripts\python.exe -m pytest tests\api\test_settlement.py -q
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

Notes:

- Full backend pytest initially timed out at 5 minutes, then passed when rerun with a 12-minute
  timeout after isolated API and non-API suite passes.
- The dev compose port `54329` is inside the Windows excluded port range `54310-54409`; the local
  browser smoke used a temporary Postgres container on `127.0.0.1:55432`.

Full backend mypy:

```text
Found 383 errors in 31 files (checked 181 source files)
```

This remains the known strict baseline. Focused M012 mypy passed.

npm audit:

```text
sandboxed npm.cmd audit --json failed at the npm registry endpoint; escalated retry was rejected
because it sends dependency metadata to the public npm registry
```

No `npm audit fix --force` was run.

Pending final validation:

- npm audit evidence, if policy/user approval allows registry metadata submission.

## Security / Abuse Checks

Implemented and covered by focused tests or code review:

- Server-generated amount.
- Server-generated VPA/reference.
- Participant cannot confirm.
- Participant cannot dispute.
- Participant cannot open another participant request by service rule.
- No raw token fields in settlement responses.
- No verified-paid language introduced in focused frontend tests.

Verified by DB-backed API tests in the latest run:

- Cross-room participant token rejection on settlement open-payment.
- End-to-end API status transitions for open, claim, confirm, and dispute.
- Settlement response does not expose raw creator or participant tokens.

## Deferred Risks

- Full backend mypy baseline remains known-red.
- npm audit remains unverified because registry metadata submission was rejected.
- Browser E2E harness remains deferred.
- QR fallback uses existing `qrcode` frontend dependency and server-generated payload, but mobile UPI
  handoff still needs manual device/browser smoke.
