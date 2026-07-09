# ReceiptSplit Current Task

Read `docs/ACTIVE_CONTEXT.md` first, then `docs/MILESTONE_INDEX.md`, then current `git status` and
`git diff`.

Archived milestone reports are evidence under `docs/archive/milestones/`. Do not load them by
default.

## Current Status

- Last full pass: M014.1 Real-World UX Bug Bash & Payment Flow Repair, commit `2e14478`.
- Current active milestone: M015 Dark Mode + Pilot Readiness QA.
- M015 is a conditional pass until audit approval, Docker/Testcontainers backend proof, and
  real-device UPI checks are completed.
- Do not add payment verification, gateway code, wallet behavior, escrow, refunds, deployment, or
  new product scope.

## M015 Delivered In This Working Tree

- Added CSS-variable-backed light/dark tokens and made dark mode the primary tested UI.
- Added accessible theme toggle with localStorage persistence and first-load system preference.
- Polished create, join, creator room, participant room, OCR, item claiming, removal, safety, and
  settlement/payment card surfaces for dark mode.
- Kept QR payment fallbacks readable inside light QR containers.
- Preserved `claimed_paid` as pending/amber and `payer_confirmed` as success/green.
- Added M015 tests for theme toggle, dark-mode shell usability, QR fallback visibility,
  payer-confirmed action hiding, and unsafe-copy absence.
- Added pilot docs under `docs/pilot/`.
- Captured mocked local browser screenshots under `docs/reports/screenshots/M015/`.

## Validation State

Passing:

- `cd frontend && npm.cmd run lint`
- `cd frontend && npm.cmd run typecheck`
- `cd frontend && npm.cmd test` -> 12 files, 56 tests passed
- `cd frontend && npm.cmd run build`
- `cd backend && .\.venv\Scripts\python.exe -m ruff check .`
- mocked local browser UI smoke through dark create/join/creator/participant/payment/settled/mobile
  states

Recorded:

- unsafe payment copy search matched only tests/docs forbidden examples

Pending:

- `cd frontend && npm.cmd audit --json` -> blocked by approval reviewer due dependency metadata
  egress to npm
- `cd backend && .\.venv\Scripts\python.exe -m pytest tests\ -q` -> blocked by
  Docker/Testcontainers named-pipe access
- real Android/iPhone UPI behavior
- M015 closeout commit

## Product Boundary

ReceiptSplit coordinates settlement only. It does not process funds, verify transfers, integrate a
payment gateway, hold funds, pool balances, escrow money, refund payments, or auto-confirm payment.

Use `marked paid`, `payer confirmed`, and `disputed`. Do not use `verified paid`.

Money stays as integer paise except at display and UPI URI formatting boundaries.
