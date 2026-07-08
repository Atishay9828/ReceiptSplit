# M014 Frontend Experience & Pilot Polish

Status: FULL PASS pending closeout commit

## Scope

M014 made the existing ReceiptSplit flow feel more polished, understandable, and mobile-first
without adding new product scope. The focus was participant clarity, creator control, payment trust
copy, status semantics, responsive layout, accessible actions, and evidence screenshots.

## Non-Goals

- No wallet, escrow, payment gateway, payment webhooks, refunds, or payment verification.
- No new settlement behavior.
- No groups, trips, history, analytics, admin, auth redesign, Supabase migration, or new OCR
  provider.
- No heavy animation/UI dependency stack.

## Frontend Design Direction

- Warm neutral background, white surfaces, soft borders, clear green primary action.
- Large participant totals and simple next-action copy.
- Tone-aware badges for payment status.
- Mobile-first single-column room layout with 44px+ actions.
- CSS/Tailwind transitions only; no new animation dependency.
- Reduced-motion guard in global CSS.

## Key Screens Changed

- `/create`: stronger headline, trust strip, `Create split room` CTA.
- `/join/[inviteToken]`: nickname-first join flow, no-account-needed copy.
- Participant room: `You owe` card, item claim cards, payment action card, safety notice.
- Creator room: lifecycle strip, next-step card, cleaner item/OCR area, settlement dashboard.
- OCR review: clearer "OCR can make mistakes" review copy.
- Abuse report: visible but calm report entry and success/error states.

## Component Changes

- Button/input polish for focus and touch feedback.
- `ParticipantTotalCard`
- `ParticipantClaimList`
- `CreatorNextActionCard`
- tone-aware `SettlementStatusBadge`
- shared local `SafetyNotice` and `EmptyState`

Tailwind v4 styling was fixed by switching `globals.css` to `@import "tailwindcss";` and defining
app design tokens with CSS `@theme`.

## Product Safety Copy

Payment UI includes:

- "ReceiptSplit does not verify bank transfers."
- "Check the recipient and amount in your UPI app before paying."
- "Payer confirmation is manual."

The UI uses `marked paid`, `payer confirmed`, and `disputed`. It does not use `verified paid` or
`payment successful`.

## Backend Compatibility Fix

Browser smoke found `PUT /settlement/payer` was blocked by CORS preflight. M014 adds `PUT` to
FastAPI CORS `allow_methods` and a regression test:

- `backend/tests/api/test_cors.py`

This does not change settlement behavior or backend schema.

## Tests

Frontend tests added:

- create page CTA/trust copy
- join page nickname flow
- participant amount summary
- participant claim actions/states
- payment card details and safety copy
- claimed-paid pending badge tone
- creator next-action card
- creator settlement dashboard actions
- abuse report form

Backend test added:

- CORS preflight allows settlement payer `PUT`

## Smoke Result

Production browser smoke passed with demo data only:

1. Open create page.
2. Create a room.
3. Add manual item.
4. Open claiming.
5. Join as participant.
6. Claim item.
7. Verify participant `You owe` summary.
8. Verify creator split preview.
9. Lock room.
10. Save payer details with fake VPA `receiptsplit.test@upi`.
11. Prepare settlement.
12. Verify participant payment card.
13. Open UPI action and QR/copy fallback.
14. Mark `I paid`.
15. Creator confirms payment.
16. Participant sees payer-confirmed copy.
17. Open abuse report form.
18. Submit abuse report.
19. Verify mobile participant/payment layouts.

## Screenshots

Stored under `docs/reports/screenshots/M014/`:

- `create-page-polished.png`
- `join-page-polished.png`
- `participant-claim-flow.png`
- `participant-payment-card.png`
- `creator-room-dashboard.png`
- `creator-settlement-dashboard.png`
- `mobile-participant-room.png`
- `mobile-payment-flow.png`
- `abuse-report-ui.png`
- `error-empty-states.png`

Screenshots use fake/demo data only. No real receipts, real UPI IDs, raw OCR text, JWTs,
capability tokens, or invite tokens are intentionally captured.

## Validation

Passing:

- `cd frontend && npm.cmd run lint`
- `cd frontend && npm.cmd run typecheck`
- `cd frontend && npm.cmd test` -> 11 files, 51 tests passed
- `cd frontend && npm.cmd run build`
- `cd backend && .\.venv\Scripts\python.exe -m pytest tests\ -q`
- `cd backend && .\.venv\Scripts\python.exe -m ruff check .`

Recorded:

- `cd frontend && npm.cmd audit --json` -> 2 moderate, 0 high, 0 critical.
- Advisory: `GHSA-qx2v-qp2m-jg93` via Next/PostCSS.
- No `npm audit fix --force`; suggested path is an unsafe Next downgrade.

## Deferred Risks

- Browser smoke is temporary Playwright/Edge automation, not a committed E2E harness.
- Visual polish remains subjective and should be rechecked on real phones.
- Rate limiting remains in-process from M013.
- `npm audit` moderate advisories remain until the upstream Next/PostCSS path is safe.

## Verdict

FULL PASS.

Reason: participant/creator/payment flows are clearer, mobile screenshots are captured, safety copy
and status semantics are correct, production smoke passed, frontend validation passed, backend CORS
regression proof passed, and no unsafe payment-product scope was added.
