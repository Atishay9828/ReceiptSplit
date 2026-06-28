# M008 Auth/OIDC Report

## Goal

Add creator user JWT authentication behind an abstraction while preserving existing room
capability-token behavior.

## Scope

- Shared auth contracts.
- Development JWT verifier and request auth context.
- User persistence and room ownership.
- `/api/auth/me` and `/api/users/me/rooms`.
- Owner JWT support for creator routes.
- Regression tests and architecture docs.

## Non-goals

- M009/M010/M011.
- Frontend, realtime, OCR, UPI, settlement, wallets, escrow, or deployment.
- Production OIDC/JWKS rollout.

## Architecture

ReceiptSplit now separates account identity from room capability identity. User JWTs resolve to
`AuthenticatedUser`; legacy capability tokens resolve to `ParticipantAuthContext`.
Creator-only dependencies accept either the room owner JWT or a same-room legacy creator token.

## Auth Context Model

- `AuthenticatedUser`: internal user id, provider, subject, optional email.
- `ParticipantAuthContext`: participant id, room id, role.
- `RequestAuthContext`: optional user and optional participant identities.

## JWT/OIDC Design

`JwtVerifier` is the trust boundary. Development uses `DevJwtVerifier`; unsupported providers fail
closed. Verified claims are upserted into the `users` table by provider and subject.

## Capability Token Compatibility

Legacy creator and participant tokens remain supported. Raw capability tokens are never stored,
and token hashes are not exposed in API responses.

## Database Changes

- Added `users` table.
- Added nullable `rooms.creator_user_id` foreign key.
- Added user repository methods for create, find, and upsert.
- Added room repository methods for owner attachment and listing.

## API Changes

- Added `GET /api/auth/me`.
- Added `GET /api/users/me/rooms`.
- Updated `POST /api/rooms` to attach an owner when a user JWT is present.
- Updated room PATCH and split lock/unlock to accept owner JWT or legacy creator token.

## Authorization Matrix

| Case | Expected |
|---|---|
| Valid user JWT on `/api/auth/me` | 200 |
| Participant token on `/api/auth/me` | 403 |
| Invalid JWT on `/api/auth/me` | 403 |
| JWT-created room | `creator_user_id` set |
| Anonymous room | legacy tokens, no owner |
| Owner JWT on creator route | 200 |
| Unrelated JWT on creator route | 403 |
| Participant token on creator route | 403 |
| Legacy creator token on creator route | 200 |
| Cross-room capability token | 403 |

## Security Decisions

- No raw JWT storage.
- No raw token logging.
- Capability token hashes only.
- Dependency-level owner checks.
- Unsupported JWT providers fail closed.

## Testing

Added auth-core, repository, and API regression coverage for JWT verification, request context
separation, user upsert, room ownership, owner authorization, legacy token compatibility, cross-room
rejection, and token-hash response leakage.

## Validation Output

Final validation output is recorded in the final report section after all lanes are integrated.

## Mypy Baseline Status

Full mypy has a known pre-existing strict-mode baseline. M008 source files are validated with
focused mypy runs using writable cache directories.

## Deferred Work

- Production OIDC/JWKS verifier.
- JWKS cache and rotation policy.
- Account lifecycle UX.

## Files Changed

Final file lists are captured in the final report.

## Git Commits

Final commit hashes are captured in the final report.

## Acceptance Checklist

- [x] Creator user JWT auth exists behind abstraction.
- [x] Participant capability tokens still work.
- [x] Legacy creator capability token still works.
- [x] Rooms can be associated with authenticated creators.
- [x] Owner JWT authorization is enforced.
- [x] Unrelated users are rejected.
- [x] Participant tokens cannot access user-only endpoints.
- [x] Token hashes are not leaked.
- [x] `/api/auth/me` exists and is tested.
- [ ] Final validation completed.
