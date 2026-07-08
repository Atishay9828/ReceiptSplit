# Security Architecture

## Scope

This file captures the active security model for the MVP. Detailed milestone evidence lives in
`docs/archive/milestones/`.

M013 controls are MVP hardening, not fraud-proof payment verification. ReceiptSplit still does not
verify bank transfers, hold funds, act as escrow, or integrate payment gateways.

## Assets

- Capability tokens for creator, participant, and invite access.
- Creator owner access through user JWTs.
- Receipt images, OCR text, and parsed receipt drafts.
- Room participant data, nicknames, item claims, and split totals.
- Settlement amounts, payer VPA/name, payment references, and settlement status events.
- Security audit logs and abuse reports.

## Threats

- Link spraying, invite-token guessing, and repeated failed token access.
- OCR upload abuse against local CPU, parser, and storage limits.
- Payment launch spam against a settlement request.
- Fake `I paid` spam and claim/dispute churn.
- Creator or payer VPA bait-and-switch after settlement requests are prepared.
- Cross-room token reuse and request tampering.
- XSS through OCR text, nicknames, item names, dispute text, or abuse report text.
- Public indexing of join and room pages.
- Excessive room creation and participant join attempts.
- Mass bills to one VPA or high fanout rooms.

## M013 Controls

- In-process rate limits protect room creation, participant join, OCR upload, payer details,
  settlement open-payment, claim-paid, confirm/dispute, and abuse report submission.
- Rate-limit keys use room IDs, request IDs, actor IDs, client host fallback, and token
  fingerprints where needed. Raw capability tokens are not used as keys.
- Durable `audit_logs` records security-sensitive actions with safe metadata only.
- `abuse_reports` stores reason and sanitized optional message without phone, email, or contact
  collection.
- Payer details are blocked after settlement requests exist. Blocked changes are audited.
- Failed invite-token access is audited with a token fingerprint, never the raw token.
- Repeated open-payment activity records `suspicious.flagged` as detect-and-record only.
- Sensitive frontend routes send noindex and basic security headers.
- Settlement copy states that ReceiptSplit does not verify bank transfer and payer confirmation is
  manual.

## Rate Limit Rules

| Action | Key | Rule |
|---|---|---|
| Room creation | client host + user/anonymous | 10/hour |
| Participant join | room + invite fingerprint + client host | 20/hour |
| OCR upload | room + actor + client host | 20/hour |
| Settlement open-payment | request + participant + client host | 10/10 min |
| Settlement claim-paid | request + participant | 10/hour |
| Creator confirm/dispute | room + actor | 60/hour |
| Payer detail update | room + actor + client host | 5/hour |
| Abuse report | room + client host | 5/hour |

The limiter is in-process and single-instance only. A Redis or database-backed distributed limiter
is deferred until there is real multi-instance deployment pressure.

## Audit Rules

Audit logs may store:

- action name
- room id
- participant id
- actor participant/user id
- actor type
- short IP fingerprint
- user-agent
- safe metadata such as counts, booleans, status names, request IDs, and fingerprints

Audit logs must not store:

- raw JWTs
- raw capability tokens
- raw invite tokens
- full raw request bodies
- full OCR text
- UPI transaction IDs or bank transfer data

## Noindex And Headers

Sensitive routes are protected with `X-Robots-Tag: noindex, nofollow`:

- `/join/:inviteToken`
- `/rooms/:roomId`
- `/rooms/:roomId/creator`

They also send basic hardening headers:

- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: frame-ancestors 'none'`

## Deferred Risks

- In-memory rate limits reset on process restart and do not coordinate across instances.
- Failed bearer-token auditing is currently strongest for invalid invite-token joins and cross-room
  checks; broader auth middleware logging can be expanded later.
- Suspicious flags are detect-and-record only. They do not automatically block accounts or rooms.
- Browser E2E remains separate from unit/API validation.
