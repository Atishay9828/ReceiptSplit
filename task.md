# ReceiptSplit Current Task

Read `docs/ACTIVE_CONTEXT.md` first, then `docs/MILESTONE_INDEX.md`, then current `git status` and
`git diff`.

Archived milestone reports are evidence under `docs/archive/milestones/`. Do not load them by
default.

## Current Status

- Last full pass: M014 Frontend Experience & Pilot Polish; closeout commit pending.
- Previous full pass: M013 Security Hardening & Abuse Controls, commits `44fede4` and `49b3c21`.
- Current active milestone: M014 Frontend Experience & Pilot Polish.
- Do not add payment verification, gateway code, wallet behavior, escrow, refunds, deployment, or
  new product scope.

## M014 Delivered In This Working Tree

- Polished create and join pages for fast first impression.
- Added participant "You owe" summary, clearer claim cards, and safe payment action card.
- Added creator next-step card, cleaner item/OCR area, and settlement dashboard wording.
- Made `claimed_paid` pending/amber and `payer_confirmed` success/green.
- Kept abuse reporting visible but low-friction.
- Added loading/error/empty-state polish and reduced-motion CSS guard.
- Fixed Tailwind v4 CSS import/design tokens so production styles render.
- Added focused M014 frontend tests.
- Fixed backend CORS `PUT` preflight for settlement payer-detail save and added regression test.
- Captured production screenshots under `docs/reports/screenshots/M014/`.

## Validation State

Passing:

- `cd frontend && npm.cmd run lint`
- `cd frontend && npm.cmd run typecheck`
- `cd frontend && npm.cmd test` -> 11 files, 51 tests passed
- `cd frontend && npm.cmd run build`
- `cd backend && .\.venv\Scripts\python.exe -m pytest tests\ -q`
- `cd backend && .\.venv\Scripts\python.exe -m ruff check .`
- production browser smoke through create, join, claim, lock, payer details, settlement prepare,
  payment open/copy fallback, marked paid, payer confirmed, and abuse report

Recorded:

- `cd frontend && npm.cmd audit --json` -> 2 moderate, 0 high, 0 critical; no force fix because the
  suggested path downgrades Next.

Pending:

- M014 closeout commit.

## Product Boundary

ReceiptSplit coordinates settlement only. It does not process funds, verify transfers, integrate a
payment gateway, hold funds, pool balances, escrow money, refund payments, or auto-confirm payment.

Use `marked paid`, `payer confirmed`, and `disputed`. Do not use `verified paid`.

Money stays as integer paise except at display and UPI URI formatting boundaries.
