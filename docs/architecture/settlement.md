# Settlement Architecture

## Boundary

M012 implements settlement coordination only.

ReceiptSplit does not process funds, hold money, pool balances, settle transfers, refund money,
verify bank transfers, integrate a payment gateway, read UPI app responses, or call payment
provider webhooks.

ReceiptSplit:

- Calculates what each participant owes from the locked split session.
- Stores payer UPI details controlled by the creator/payer.
- Creates server-controlled settlement requests from locked participant totals.
- Generates UPI URI and QR payload strings on the server.
- Lets participants manually mark `I paid`.
- Lets the payer manually confirm or dispute.
- Records durable status history and room events.

Do not use `verified paid` copy. The safe terms are `marked paid`, `payer confirmed`, and
`disputed`.

## Data Model

Payer setup uses existing `rooms.payer_vpa` and `rooms.payer_name`.

M012 adds:

- `settlement_requests`
- `settlement_status_events`

`settlement_requests` stores:

- `room_id`
- `split_session_id`
- `participant_id`
- `amount_paise`
- `currency`
- `payee_vpa`
- `payee_name`
- `payment_reference`
- `status`
- timestamps for opened, claimed paid, payer confirmed, and disputed
- `version`

The unique request identity is `(room_id, participant_id, split_session_id)`. This keeps prepare
idempotent for a locked split session and avoids duplicate participant requests.

Money is stored and transported as integer paise. Rupee decimal strings are produced only at the UPI
URI formatting boundary and frontend display boundary.

## Statuses

| Status | Meaning |
|---|---|
| `due` | Participant owes the payer. |
| `payment_opened` | Participant opened the server-generated UPI link. |
| `claimed_paid` | Participant manually marked `I paid`. |
| `payer_confirmed` | Payer manually confirmed payment. |
| `disputed` | Payer manually disputed the participant claim. |

## Transitions

| From | To |
|---|---|
| `due` | `payment_opened`, `claimed_paid`, `disputed` |
| `payment_opened` | `claimed_paid`, `disputed` |
| `claimed_paid` | `payer_confirmed`, `disputed` |
| `disputed` | `payment_opened`, `claimed_paid`, `payer_confirmed` |
| `payer_confirmed` | terminal |

Participants can only open or claim their own request. Participants cannot confirm or dispute.
Creators and room owners can configure payer details, prepare settlement requests, confirm, and
dispute. Cross-room capability tokens are rejected by the existing room auth dependencies before the
settlement service runs.

## UPI Link Generation

`SettlementLinkBuilder` builds:

```text
upi://pay?pa=<payee_vpa>&pn=<payee_name>&am=<rupees.decimal>&cu=INR&tn=<note>&tr=<reference>
```

The server chooses:

- amount
- payee VPA
- payee display name
- payment reference
- UPI URI
- QR payload

The frontend can only request actions such as open payment, claim paid, confirm, or dispute. It does
not submit trusted amount, VPA, or reference values.

## Events

Settlement writes durable room events inside the request transaction:

- `settlement.payer_configured`
- `settlement.requests_prepared`
- `settlement.payment_opened`
- `settlement.claimed_paid`
- `settlement.payer_confirmed`
- `settlement.disputed`

`settlement_status_events` records the status-history audit trail. Room events drive existing
SSE/refetch behavior; status events preserve settlement history. No raw tokens, UPI app response
payloads, bank data, or gateway identifiers are stored.

## M013 Security Hardening

Settlement mutation endpoints now have lightweight in-process rate limits. The limiter is
MVP-appropriate and not distributed-safe; Redis or another shared limiter is deferred.

Security-sensitive settlement actions write durable `audit_logs` rows:

- `settlement.payer_details_set`
- `settlement.payer_details_change_blocked`
- `settlement.requests_prepared`
- `settlement.payment_opened`
- `settlement.claimed_paid`
- `settlement.payer_confirmed`
- `settlement.disputed`
- `suspicious.flagged`

Payer details can be set before settlement requests are prepared. Once settlement requests exist,
payer details changes are blocked by default through both the settlement payer endpoint and the
legacy room PATCH path. The blocked attempt is audited with a VPA fingerprint, not the raw attempted
VPA.

Repeated open-payment activity records a `suspicious.flagged` audit entry. M013 does not auto-block
based on suspicious flags; enforcement remains limited to explicit rate limits.
