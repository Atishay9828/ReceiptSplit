# M013 Security Hardening & Abuse Controls

## Scope

M013 hardens room access, capability-token flows, OCR upload, settlement actions, UPI payment
launch, claim-paid/payer-confirmed/disputed flows, shareable participant links, and public room
pages.

## Non-Goals

No wallet, escrow, payment gateway, payment aggregator, refunds, KYC, bank account linking, SMS or
email scraping, UPI transaction polling, automatic settlement, ML fraud detection, contact upload,
admin dashboard, deployment, or payment verification was added.

## Threat Model Summary

Active threat model: `docs/architecture/security.md`.

Main assets:

- capability tokens
- creator owner access
- receipt images and OCR text
- participant data
- settlement amounts
- payer VPA/name
- settlement status events
- audit logs

Main threats:

- link spraying and token guessing
- OCR upload abuse
- payment launch spam
- fake `I paid` spam
- VPA bait-and-switch
- cross-room token reuse
- public indexing of sensitive pages
- claim/dispute churn

## Rate Limit Rules

| Action | Rule |
|---|---|
| room creation | 10/hour per client host and user/anonymous |
| participant join | 20/hour per room, invite fingerprint, and client host |
| OCR upload | 20/hour per room, actor, and client host |
| settlement open-payment | 10/10 min per request, participant, and client host |
| settlement claim-paid | 10/hour per request and participant |
| creator confirm/dispute | 60/hour per room and actor |
| payer detail update | 5/hour per room, actor, and client host |
| abuse report | 5/hour per room and client host |

The limiter is in-process and not distributed-safe. Redis or another shared limiter is deferred.

## Audit Events Added

- `room.created`
- `participant.joined`
- `token.access_failed`
- `receipt.uploaded`
- `ocr.confirmed`
- `settlement.payer_details_set`
- `settlement.payer_details_change_blocked`
- `settlement.requests_prepared`
- `settlement.payment_opened`
- `settlement.claimed_paid`
- `settlement.payer_confirmed`
- `settlement.disputed`
- `abuse.reported`
- `suspicious.flagged`

Audit metadata stores IDs, counts, booleans, status names, and fingerprints. It does not store raw
JWTs, raw capability tokens, invite tokens, full OCR text, full request bodies, or bank/payment
verification data.

## VPA Change Rule

Payer details can be set before settlement requests are prepared. After settlement requests exist,
payer detail changes are blocked by default and audited. This applies to both:

- `PUT /api/rooms/{room_id}/settlement/payer`
- legacy `PATCH /api/rooms/{room_id}` payer field updates

Blocked attempts return:

```json
{
  "error": {
    "code": "SETTLEMENT_NOT_READY",
    "message": "Payer details cannot be changed after settlement requests are prepared."
  }
}
```

## Abuse Report API/UI

Backend:

```http
POST /api/rooms/{room_id}/abuse-reports
```

Payload:

```json
{
  "reason": "spam|fraud_suspected|wrong_payee|harassment|other",
  "message": "optional short text"
}
```

Rules:

- requires valid creator, participant, or owner room access
- message is capped and sanitized
- rate limited
- no phone/email/contact collection
- reports are not exposed to participants
- creates `abuse.reported` audit row

Frontend:

- small Safety panel in creator and participant room flows
- reason dropdown
- optional message
- success and safe failure states

## Security Headers / Noindex

Sensitive frontend routes receive:

- `X-Robots-Tag: noindex, nofollow`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: frame-ancestors 'none'`

Routes:

- `/join/:inviteToken`
- `/rooms/:roomId`
- `/rooms/:roomId/creator`

## Tests / Validation

Passing:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\api\test_m013_security.py -q
.\.venv\Scripts\python.exe -m pytest tests\api\test_settlement.py tests\api\test_rooms.py tests\api\test_participants.py -q
.\.venv\Scripts\python.exe -m pytest tests\ -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy app\api\routers\abuse.py app\api\routers\ocr.py app\api\routers\participants.py app\api\routers\rooms.py app\api\routers\settlement.py app\api\schemas\abuse.py app\models\abuse_report.py app\models\audit_log.py app\security app\services\abuse_service.py app\services\audit_service.py app\services\settlement_service.py tests\api\test_m013_security.py

cd frontend
npm.cmd test -- settlement-ui.test.tsx api.test.ts security-headers.test.ts
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
npm.cmd audit --json
```

`npm.cmd audit --json` returned 2 moderate advisories, 0 high, 0 critical. The advisory is
`GHSA-qx2v-qp2m-jg93` through Next/PostCSS, and npm's suggested fix path is an unsafe Next
downgrade. No `npm audit fix --force` was run.

## Smoke Result

Local Postgres smoke passed after:

```powershell
docker compose -f docker-compose.dev.yml up -d
cd backend
$env:RECEIPTSPLIT_DATABASE_URL='postgresql+asyncpg://receiptsplit:receiptsplit@localhost:54329/receiptsplit_dev'
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Smoke flow passed through:

1. create room
2. open claiming
3. join participant
4. add item
5. lock split
6. save payer details with demo VPA `receiptsplit.test@upi`
7. prepare settlement
8. open payment and verify safety disclaimer/copy VPA
9. mark claimed paid
10. payer confirm
11. submit participant abuse report

## Screenshots

No M013 screenshots were captured. The smoke used API assertions and frontend header/UI tests rather
than browser screenshots, avoiding capability links, JWTs, and private data in artifacts.

## Deferred Risks

- Rate limiter is in-process and resets on process restart.
- Distributed rate limiting is deferred.
- Suspicious flags are detect-and-record only.
- Broad bearer-token failure auditing beyond failed invite joins/cross-room checks can be expanded.
- Browser E2E harness remains separate from this implementation.
- Full backend mypy baseline is known red unless focused M013 scope passes.
  Focused M013 mypy passed.

## Verdict

FULL PASS. M013 meets the hardening acceptance criteria with the distributed limiter, broader auth
failure telemetry, suspicious-flag enforcement, and browser E2E harness deferred.
