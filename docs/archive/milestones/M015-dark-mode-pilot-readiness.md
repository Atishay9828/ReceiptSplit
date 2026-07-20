# M015 Dark Mode + Pilot Readiness QA

## Status

CONDITIONAL PASS.

M015 delivered the dark theme system, theme toggle, dark-mode UI polish, pilot checklists, and
local browser screenshot evidence. Full pass is blocked by environment/policy items outside the
changed frontend scope:

- `npm.cmd audit --json` was blocked by the approval reviewer because it sends dependency metadata
  to npm.
- Full backend pytest was blocked by Docker/Testcontainers named-pipe access:
  `CreateFile`, `The system cannot find the file specified.`
- Real Android/iPhone UPI behavior is not verified in this environment.

## Implementation

Frontend:

- Added CSS-variable-backed light/dark tokens in `frontend/app/globals.css`.
- Added a global accessible theme toggle with localStorage persistence and first-load system
  preference handling.
- Kept dark mode calm and readable: deep green-black background, slate surfaces, mint primary,
  amber pending, cyan info, coral dispute/error, and green payer-confirmed status.
- Kept QR codes inside a light `bg-qr` container in dark mode.
- Updated shared buttons, inputs, selects, error states, OCR upload card, create page, join page,
  and room/payment UI styling through tokens.

Product boundary:

- No wallet, escrow, gateway, webhook, payment verification, bank verification, refund handling, or
  fund custody was added.
- Payment copy remains manual: marked paid, payer confirmed, disputed.

Pilot readiness:

- Added real-device QA checklist.
- Added UPI intent behavior checklist.
- Added demo flow.
- Added known issues.

## Validation

Passing:

- `cd D:\ReceiptSplit\frontend && npm.cmd run lint`
- `cd D:\ReceiptSplit\frontend && npm.cmd run typecheck`
- `cd D:\ReceiptSplit\frontend && npm.cmd test` -> 12 files, 56 tests passed
- `cd D:\ReceiptSplit\frontend && npm.cmd run build`
- `cd D:\ReceiptSplit\backend && .\.venv\Scripts\python.exe -m ruff check .`

Blocked:

- `cd D:\ReceiptSplit\frontend && npm.cmd audit --json`
  - sandbox run failed before advisory data was returned
  - escalation was rejected because dependency metadata egress to npm was not approved
- `cd D:\ReceiptSplit\backend && .\.venv\Scripts\python.exe -m pytest tests\ -q`
  - Docker/Testcontainers could not reach the Docker named pipe

Unsafe copy search:

- User-facing source had no unsafe payment copy.
- Matches were limited to tests and documentation describing forbidden terms.

Browser evidence:

- Local production Next server.
- Playwright using system Microsoft Edge.
- API responses mocked with fake demo data only.
- Fake VPA: `receiptsplit.test@upi`.
- True DB-backed end-to-end smoke was not possible without Docker/Postgres.

Screenshots:

```text
docs/reports/screenshots/M015/dark-create-page.png
docs/reports/screenshots/M015/dark-join-page.png
docs/reports/screenshots/M015/dark-creator-room-draft.png
docs/reports/screenshots/M015/dark-creator-items-quantity.png
docs/reports/screenshots/M015/dark-participant-claim-flow.png
docs/reports/screenshots/M015/dark-payment-card-qr-visible.png
docs/reports/screenshots/M015/dark-payer-confirmed-no-pay-actions.png
docs/reports/screenshots/M015/dark-settled-room.png
docs/reports/screenshots/M015/dark-remove-participant.png
docs/reports/screenshots/M015/dark-mobile-participant-payment.png
docs/reports/screenshots/M015/light-mode-still-readable.png
docs/reports/screenshots/M015/theme-toggle.png
```

## Deferred Risks

- Real Android UPI chooser behavior.
- iPhone Safari UPI behavior.
- npm audit advisory refresh.
- DB-backed browser smoke.
- Real pilot feedback on contrast, density, and restaurant/night usage.
