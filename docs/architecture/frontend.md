# Frontend Architecture

For current project state, read `docs/ACTIVE_CONTEXT.md` and `docs/MILESTONE_INDEX.md` before this
architecture note. Archived milestone reports are under `docs/archive/milestones/`.

## Purpose

M010 adds a mobile-first Next.js frontend for the manual receipt-first ReceiptSplit flow. It
supports legacy creator capability sessions and account-backed participant sessions. M011.1 adds OCR
draft review. M012 adds coordinator-safe UPI settlement coordination. M014 adds pilot polish for the
mobile-first room experience. M015 adds a dark-mode-first theme system and pilot readiness docs.
M015.1 repairs creator identity, adjustment math, step-based room views, settled completion UX, and
the ReceiptSplit theme identity.
Payment verification, wallet, escrow, and payment-gateway behavior remain out of scope.

## App Structure

The frontend lives in `frontend/` and uses:

- Next.js App Router.
- TypeScript.
- Tailwind CSS v4 with app tokens defined in `frontend/app/globals.css`.
- CSS-variable-backed light/dark theme tokens.
- Small shadcn/ui-style primitives under `frontend/components/ui/`.
- Vitest and React Testing Library.

Key directories:

- `frontend/app/`: route entrypoints.
- `frontend/components/`: forms, room UI, and reusable controls.
- `frontend/lib/`: API client, event sync, money conversion, invite encoding, storage helpers.
- `frontend/types/`: backend API DTO types.
- `frontend/tests/`: utility and component tests.

## Routes

- `/` redirects to `/create`.
- `/create` creates a room and stores the creator capability token locally.
- `/join/[inviteToken]` requires Google sign-in, then decodes a frontend invite parameter
  containing `{room_id}:{invite_token}`.
- `/rooms/[roomId]` is the participant room.
- `/rooms/[roomId]/creator` is the creator room.

The backend join contract requires an account JWT, `room_id` in the path, and `invite_token` in
the body, so the frontend invite URL encodes both values into the dynamic route parameter.

## API Client

`frontend/lib/api.ts` centralizes:

- `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000`.
- `Authorization: Bearer <token>` support.
- JSON request/response handling.
- Backend error parsing for `{ error: { code, message } }`.
- Helpers for room creation/update, summary fetch, joining, item mutations, adjustments, claims,
  split preview, lock, unlock, and settlement coordination.

The frontend sends money only as integer paise fields.

## Token Storage

`frontend/lib/storage.ts` stores minimal local sessions:

- `receiptsplit:creator:{room_id}`.
- `receiptsplit:participant:{room_id}`.

Stored values are room id, role, the active bearer credential, invite token for creators,
participant id and nickname for participants, and last seen event sequence. Account-backed
participants use their account JWT for room access. Token hashes are never stored or displayed.

## M014 Experience Layer

M014 keeps the product scope unchanged and improves the experience layer:

- `/create` now explains the flow quickly and uses a direct `Create split room` CTA.
- `/join/[inviteToken]` leads with a create-account/sign-in gate, then asks for the display name
  used on the bill.
- Participant room starts with a large `You owe` summary and a status-specific next action.
- Item claim cards show `Available`, `Claimed by you`, or `Claimed`.
- Creator room has a simple lifecycle strip and a `Next step` card.
- Settlement badges are tone-aware:
  - `payment_opened`: blue/info
  - `claimed_paid`: amber/pending
  - `payer_confirmed`: green/final
  - `disputed`: red/orange
  - `due`: muted
- Payment cards repeat the required safety copy:
  `ReceiptSplit does not verify bank transfers. Check the recipient and amount in your UPI app before paying. Payer confirmation is manual.`
- Abuse reporting is visible in the room footer without requiring phone/email.

The Tailwind v4 pipeline uses `@import "tailwindcss";` and CSS `@theme` tokens. This is required
for production browser styles to render correctly with the installed Tailwind/PostCSS stack.

## M015/M015.1 Theme System

M015 keeps Tailwind v4 but maps app colors to CSS variables in `frontend/app/globals.css`:

- background
- surface
- elevated surface
- border
- primary cyan/blue
- accent violet
- warning amber
- danger coral
- success green
- info cyan/blue
- text primary, secondary, and muted

The `.dark` class is applied to `document.documentElement`. First paint is handled by an inline
layout script before the app content renders. User preference is stored in localStorage under
`receiptsplit:theme`; first visit respects system preference. `frontend/components/theme-toggle.tsx`
exposes the accessible icon button with `aria-label="Toggle theme"`.

Dark mode is the primary tested experience, but light mode remains usable. Existing light-oriented
Tailwind utilities are bridged through dark CSS overrides where a full class rewrite would create
unnecessary churn. QR codes use the dedicated `bg-qr` token so the black/white QR payload remains
readable inside dark payment cards.

M015.1 moves the brand away from green. Green is reserved for success and payer-confirmed states;
primary actions are cyan/blue, creator/accent treatments use violet, and surfaces use graphite,
midnight navy, and slate.

M015.1 status colors:

- `due`: muted
- `payment_opened`: info/cyan
- `claimed_paid`: warning/amber
- `payer_confirmed`: success/green
- `disputed`: danger/coral

`claimed_paid` must not look final.

## Creator Flow

The creator creates a room from `/create`, optionally setting payer metadata. Because backend rooms
start in `draft` and item selection requires `active`, the creator room exposes an explicit
`Start item selection` action. M015.1 renders the creator room as distinct state views:

- Build bill: item/OCR input, adjustments, draft preview, and start-item-selection CTA.
- Choose items: invite link/QR, participants, creator share selection, participant choices,
  preview, and lock CTA.
- Locked: final preview, unlock option, payer details, and prepare-settlement CTA.
- Settling: settlement dashboard only.
- Settled: completion screen, final totals, payer-confirmed participant list, copy summary, and
  create-another-split CTA.

After locking, M012 shows settlement setup. The creator can save payout details, prepare settlement
requests from locked participant totals, see each participant's status, confirm payment manually, or
mark a payment disputed. The UI says `Confirm payment`, `Mark disputed`, `Settlement dashboard`, and
`Payer confirmation`; it does not say `verified paid`.

## OCR Review Flow

M011.1 adds the creator OCR review UI to the existing creator room. The creator selects a PNG/JPEG
receipt, uploads it to `POST /api/rooms/{room_id}/receipts/upload`, reviews the parsed draft, edits
item names or amounts, saves the draft if needed, and confirms it into normal room items and
adjustments. Confirmation does not auto-share, auto-claim, or auto-lock the room; the existing
participant claim and split-preview flow still controls settlement readiness.

## Participant Flow

Participants must sign in through `/join/[inviteToken]`. First-time Google sign-in creates the
ReceiptSplit account automatically; joining links `room_participants.user_id` to that account.
The participant room uses the account JWT, shows a large participant total first, then participants,
item choices, split preview, payment state, and safety reporting. Selection conflicts are shown as
visible errors and trigger a room refresh.

After settlement requests exist, the participant room shows `Pay your share`, amount due, payer
name, payer UPI ID, payment reference, status, `Open UPI app`, `Copy UPI ID`, QR fallback, and `I
paid`. `claimed_paid` is visually pending, not final. The UPI URI and QR payload come from the backend `open-payment` endpoint. The frontend does
not submit payable amount, payee VPA, payee name, or payment reference for settlement mutations.

## Browser Evidence

M014 production browser smoke used demo data only and fake VPA `receiptsplit.test@upi`. Screenshots
are stored in `docs/reports/screenshots/M014/`:

- create page
- join page
- participant claim flow
- participant payment card
- creator item dashboard
- creator settlement dashboard
- mobile participant room
- mobile payment flow
- abuse report UI
- error/empty state

M015 mocked local browser UI evidence used fake demo data only and fake VPA
`receiptsplit.test@upi`. Screenshots are stored in `docs/reports/screenshots/M015/`. This proves UI
rendering and dark-mode states, not DB-backed end-to-end behavior. Real-device UPI behavior remains
tracked in `docs/pilot/REAL_DEVICE_QA.md` and `docs/pilot/UPI_INTENT_QA.md`.

## Event Sync

`frontend/lib/events.ts` implements M009 sync with fetch-based SSE instead of native `EventSource`.
This is intentional: native `EventSource` cannot send the backend-required `Authorization` header.

The event client:

- Replays durable events after the last seen sequence.
- Streams `/api/rooms/{room_id}/events/stream`.
- Sends bearer auth headers.
- Deduplicates events by `sequence_no`.
- Updates local last sequence.
- Refetches room state after each new event.
- Reconnects after disconnect using the last seen sequence.

Events trigger refetches rather than optimistic event-payload application. M012 settlement events use
the same path, so creator and participant settlement cards update through room refetches after
`settlement.*` events.

## Split Preview Readiness

`frontend/lib/split-readiness.ts` gates preview requests from the room summary before the frontend
calls `GET /api/rooms/{room_id}/split/preview`.

The readiness rules are intentionally conservative:

- Archived and expired rooms are not preview-ready.
- A room needs at least one participant, at least one item, and positive item totals.
- Equal split rooms are preview-ready after those base checks.
- Item-wise rooms are preview-ready only when every item quantity is fully claimed.

Room events still refetch the summary. After each refetch, the room client recomputes readiness and
only calls split preview when readiness is true. If the backend still rejects preview with a
validation or locked/conflict status, the frontend shows an inline retry state and suppresses
duplicate preview retries for the same summary key.

Creator lock controls use the same readiness result plus actual preview data, so Lock remains
disabled until the visible preview is valid.

## Money Conversion

`frontend/lib/money.ts` converts rupee strings to integer paise with validation:

- `120.50` becomes `12050`.
- `100` becomes `10000`.
- More than two decimal places, negative item amounts, and non-numeric values are rejected.

M015.1 adjustment inputs support flat amount and percentage modes. The frontend sends discount,
coupon, and offer amounts as positive magnitudes; the backend owns subtractive semantics.

## Backend Read Model

The existing backend had item/adjustment/assignment mutation endpoints but no current-state read
endpoint for frontend refresh/navigation. M010 adds the backward-compatible read-only endpoint:

- `GET /api/rooms/{room_id}/summary`

It returns room metadata, participants, active items, active adjustments, and current assignments.

## Known Limitations

- Production login UI is not implemented.
- Invite URL encoding is frontend-specific because the backend does not expose a room-id-free invite
  lookup endpoint.
- Realtime is process-local on the backend per M009.
- Creator lock/unlock after OCR-created item claims was exercised in the final M011.1 browser smoke.
- There is no payment verification, wallet, escrow, native app, analytics, or deployment work in
  M012.
- Browser smoke is manual/temporary Playwright automation rather than a committed E2E harness.
- `npm audit` currently reports 2 moderate advisories through Next/PostCSS and no high/critical
  advisories as of M014; no forced downgrade is applied. M015 could not refresh audit data because
  the audit command's network escalation was rejected due dependency metadata egress to npm.
- Full backend pytest for M015 is blocked by Docker/Testcontainers named-pipe access in this
  environment.
