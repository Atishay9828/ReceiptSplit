# Auth Architecture

## Purpose

M008 added account-level creator identity while preserving legacy room capabilities. M016 added
Google sign-in and account-backed room membership. Invite joins require an authenticated user,
while existing creator capability sessions remain supported. The backend supports two bearer types:

- User JWTs identify an account-level creator through normalized OIDC claims.
- Room capability tokens authorize room-scoped creator and participant actions.

These credentials are not interchangeable. A participant capability token cannot satisfy a
user-only endpoint, and a user JWT cannot bypass room ownership checks.

## Context Model

`AuthenticatedUser` is the normalized user identity:

- `id`: internal user UUID from the `users` table.
- `provider`: OIDC provider key, currently `dev` for local verification.
- `subject`: provider subject.
- `email`: optional provider email claim.

`ParticipantAuthContext` is the existing room capability identity:

- `participant_id`: `room_participants.id`.
- `room_id`: room bound to the token.
- `role`: `creator` or `participant`.

`RequestAuthContext` keeps the two identities separate with optional `user` and
`participant` fields.

## JWT/OIDC Design

JWT handling is behind the `JwtVerifier` protocol. The current implementation includes a
development verifier for unsigned JWT-shaped local tokens and a Google OIDC verifier for production
ID tokens.

The request flow is:

1. Parse `Authorization: Bearer <token>`.
2. Classify capability tokens separately from JWT-shaped tokens.
3. Verify JWT claims through `JwtVerifier`.
4. Upsert `(provider, subject, email)` into `users`.
5. Return `RequestAuthContext(user=AuthenticatedUser(...))`.

No raw JWTs are stored.

## Capability Token Compatibility

Capability token behavior remains unchanged:

- Raw creator, participant, and invite tokens remain available for compatibility.
- Public invite joins require a user JWT and persist `room_participants.user_id`; the frontend
  continues with the account JWT after joining.
- Only SHA-256 token hashes are stored.
- Same-room creator capability tokens still authorize creator routes.
- Same-room participant capability tokens still authorize participant routes.
- Cross-room capability token reuse is rejected.

## Database Model

M008 adds:

- `users(id, provider, subject, email, created_at, updated_at)`.
- Unique `(provider, subject)`.
- Nullable `rooms.creator_user_id` foreign key to `users.id`.

Legacy rooms keep `creator_user_id = NULL` and remain valid.

## Authorization Matrix

| Scenario | Result |
|---|---|
| Valid user JWT calls `GET /api/auth/me` | 200 |
| Participant token calls `GET /api/auth/me` | 403 `NOT_AUTHORIZED` |
| Invalid JWT calls `GET /api/auth/me` | 403 `INVALID_TOKEN` |
| User JWT creates room | Room is linked through `creator_user_id` |
| No JWT creates room | Legacy creator/invite tokens returned, no user owner |
| No JWT joins an invite | 403 `NOT_AUTHORIZED` |
| User JWT joins an invite | Participant is linked through `user_id` |
| Owner JWT calls creator route | 200 |
| Unrelated JWT calls creator route | 403 `NOT_AUTHORIZED` |
| Participant token calls creator route | 403 `NOT_AUTHORIZED` |
| Legacy creator token calls creator route | 200 |
| Cross-room capability token is reused | 403 `INVALID_TOKEN` |

## Security Decisions

- Keep account auth and capability auth separate in code and tests.
- Store capability token hashes only.
- Do not log raw bearer tokens.
- Persist only normalized user claims, not JWTs.
- Keep room ownership checks in dependencies, not route bodies.
- Fail closed for unsupported JWT providers.

## Deferred Work

- JWKS caching and key-rotation policy.
- Account recovery, provider linking, and explicit account deletion.
