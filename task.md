# ReceiptSplit Current Task

Read `docs/ACTIVE_CONTEXT.md` first, then `docs/MILESTONE_INDEX.md`, then current `git status` and
`git diff`.

Archived milestone reports are evidence under `docs/archive/milestones/`. Do not load them by
default.

## Current Status

- Last full pass: M012 UPI Settlement MVP, commits `8c39279` and `05456c0`.
- Current active milestone: M013 Security Hardening & Abuse Controls.
- M013 state: FULL PASS after validation and local DB smoke; closeout commit pending.
- Do not add payment verification, gateway code, wallet behavior, escrow, refunds, deployment, or
  M014 scope.

## M013 Delivered In This Working Tree

- `audit_logs` and `abuse_reports` models plus migration.
- Lightweight in-process rate limits for sensitive room, join, OCR, settlement, payer-detail, and
  abuse-report actions.
- Durable audit rows for settlement/security-sensitive actions.
- Payer detail changes blocked after settlement requests exist through both settlement payer and
  legacy room PATCH paths.
- Failed invite-token join logging with token fingerprints only.
- Minimal abuse report API and room UI.
- Repeated open-payment suspicious activity audit flag.
- Noindex/security headers for join and room pages.
- Settlement copy states that ReceiptSplit does not verify bank transfer and payer confirmation is
  manual.

## Validation State

Passing so far:

- `cd backend && .\.venv\Scripts\python.exe -m pytest tests\api\test_m013_security.py -q`
- `cd backend && .\.venv\Scripts\python.exe -m pytest tests\api\test_settlement.py tests\api\test_rooms.py tests\api\test_participants.py -q`
- `cd frontend && npm.cmd test -- settlement-ui.test.tsx api.test.ts security-headers.test.ts`

Passing:

- `cd backend && .\.venv\Scripts\python.exe -m pytest tests\ -q`
- `cd backend && .\.venv\Scripts\python.exe -m ruff check .`
- focused M013 mypy over changed backend/API/security/test files
- `cd frontend && npm.cmd run lint`
- `cd frontend && npm.cmd run typecheck`
- `cd frontend && npm.cmd test`
- `cd frontend && npm.cmd run build`
- `cd frontend && npm.cmd audit --json` recorded 2 moderate advisories, 0 high, 0 critical
- local Postgres smoke passed through create, join, lock, settlement, payment-open, claim, confirm,
  and abuse report

Pending:

- M013 closeout commit

## Product Boundary

ReceiptSplit coordinates settlement only. It does not process funds, verify transfers, integrate a
payment gateway, hold funds, pool balances, escrow money, refund payments, or auto-confirm payment.

Use `marked paid`, `payer confirmed`, and `disputed`. Do not use `verified paid`.

Money stays as integer paise except at display and UPI URI formatting boundaries.
