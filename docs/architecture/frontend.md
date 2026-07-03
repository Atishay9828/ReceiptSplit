# Frontend Architecture

## Purpose

M010 adds a mobile-first Next.js frontend for the manual receipt-first ReceiptSplit flow. It
supports anonymous creator capability sessions and accountless participant sessions. OCR, payment,
settlement verification, wallet, escrow, deployment, and production auth UI remain deferred.

## App Structure

The frontend lives in `frontend/` and uses:

- Next.js App Router.
- TypeScript.
- Tailwind CSS.
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
- `/join/[inviteToken]` decodes a frontend invite parameter containing `{room_id}:{invite_token}`.
- `/rooms/[roomId]` is the participant room.
- `/rooms/[roomId]/creator` is the creator room.

The backend join contract requires `room_id` in the path and `invite_token` in the body, so the
frontend invite URL encodes both values into the dynamic route parameter.

## API Client

`frontend/lib/api.ts` centralizes:

- `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000`.
- `Authorization: Bearer <token>` support.
- JSON request/response handling.
- Backend error parsing for `{ error: { code, message } }`.
- Helpers for room creation/update, summary fetch, joining, item mutations, adjustments, claims,
  split preview, lock, and unlock.

The frontend sends money only as integer paise fields.

## Token Storage

`frontend/lib/storage.ts` stores minimal local sessions:

- `receiptsplit:creator:{room_id}`.
- `receiptsplit:participant:{room_id}`.

Stored values are room id, role, raw capability token, invite token for creators, participant id and
nickname for participants, and last seen event sequence. Token hashes are never stored or displayed.

## Creator Flow

The creator creates a room from `/create`, optionally setting payer metadata. Because backend rooms
start in `draft` and claims require `active`, the creator room exposes an explicit `Open claiming`
action. The creator can add, edit, and delete manual receipt items, add supported adjustments, view
participants, share an invite link/QR/WhatsApp link, preview the split, lock the split, and unlock
if supported by backend state.

## Participant Flow

Participants join with nickname only through `/join/[inviteToken]`; no login is required. Their
participant capability token is stored locally. The participant room shows participants, items,
claim state, the participant total, split preview, and locked-state messaging. Claim conflicts are
shown as visible errors and trigger a room refresh.

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

For M010, events trigger refetches rather than optimistic event-payload application.

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

Adjustment discounts are represented as negative paise in the adjustment form after parsing the
absolute rupee amount.

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
- There is no OCR, camera upload, UPI settlement, payment verification, wallet, escrow, native app,
  analytics, or deployment work in M010.
