# ReceiptSplit Current Task

Read `docs/ACTIVE_CONTEXT.md`, then `docs/MILESTONE_INDEX.md`, then current git status/diff.
Archived milestone reports remain evidence under `docs/archive/milestones/`.

## Active Milestone

M016 Persistent Rooms, Friends, Multi-Bill Ledger & Mixed Item Splits.

Implemented in the current working tree:

- mixed item-wise allocation: each line can be individually claimed or split equally;
- explicit share actions with the old `Claim 1/2` wording removed;
- account profiles with usernames and Google ID-token authentication;
- friends added by exact username;
- multiple persistent rooms with different friend membership;
- multiple bills per room, each retaining its own lifecycle;
- room-level all-bills, pending, and payer-confirmed cleared totals;
- JWT-linked room membership and participant-scoped settlement privacy;
- database migration, API schemas, frontend dashboard, tests, and deployment configuration.

## Remaining Closeout

- Review the final diff, commit, and push the branch.
- Configure a real Google OAuth web client ID in Vercel as
  `NEXT_PUBLIC_GOOGLE_CLIENT_ID` and in Render as
  `RECEIPTSPLIT_AUTH_OIDC_AUDIENCE`.
- Verify the deployed site. Do not call Google login live until that credential is confirmed.

## Product Boundary

ReceiptSplit coordinates settlement only. It does not process funds, verify transfers, integrate a
payment gateway, hold funds, pool balances, escrow money, refund payments, or auto-confirm payment.
Use `marked paid`, `payer confirmed`, and `disputed`; never `verified paid`.
