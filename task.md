# ReceiptSplit Current Task

Read `docs/ACTIVE_CONTEXT.md` first, then `docs/MILESTONE_INDEX.md`, then current `git status` and
`git diff`.

Archived milestone reports are evidence under `docs/archive/milestones/`. Do not load them by
default.

## Current Status

- Last full pass: M011.1 OCR Frontend Review UI, commit `2985a40`.
- Current active milestone: M012 UPI Settlement MVP.
- M012 state: CONDITIONAL PASS only.
- M012 product code exists in the working tree, DB/API validation passes, and browser screenshot
  evidence is captured, but audit evidence is not complete.
- Do not start M013, gateway work, payment verification, wallet, escrow, refunds, or deployment.

## M012 Delivered So Far

- Backend settlement domain, status transitions, service, schemas, routes, and models.
- Migration `backend/migrations/versions/004_m012_settlement_mvp.py`.
- Server-side `SettlementLinkBuilder` for UPI URI and QR payload strings.
- Creator settlement setup/dashboard and participant payment flow.
- Settlement architecture doc: `docs/architecture/settlement.md`.
- Conditional closeout evidence: `docs/archive/milestones/M012-upi-settlement.md`.

## M012 Validation State

Passed in the latest closeout run:

- settlement link builder unit test
- DB-backed settlement API tests
- full backend pytest with longer timeout
- full backend Ruff
- focused M012 mypy
- frontend lint
- frontend typecheck
- full frontend tests
- frontend build
- `git diff --check`
- browser smoke through payer-confirmed and disputed with demo VPA `receiptsplit.test@upi`

Blocked or pending:

- `npm.cmd audit --json` approval decision and registry access

Screenshot evidence note:

- `docs/reports/screenshots/M012/M012-screenshots-blocked.md`

Commit blocker:

- `git add` escalation is currently blocked by the approval-system usage limit, not by a current
  `.git/index.lock`.

## Product Boundary

ReceiptSplit coordinates settlement only. It does not process funds, verify transfers, integrate a
payment gateway, hold funds, pool balances, escrow money, refund payments, or auto-confirm payment.

Use `marked paid`, `payer confirmed`, and `disputed`. Do not use `verified paid`.

Money stays as integer paise except at display and UPI URI formatting boundaries.
