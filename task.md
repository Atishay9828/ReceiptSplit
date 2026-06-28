# M008 Auth/OIDC Task

## Status

PASS.

## Scope Completed

- Shared auth contracts.
- JWT verifier abstraction with development verifier and fail-closed unsupported-provider behavior.
- User persistence through `users`.
- Room ownership through `rooms.creator_user_id`.
- Owner JWT support for creator routes.
- Legacy creator and participant capability-token compatibility.
- Auth architecture and milestone report docs.

## Validation

- 371 tests collected.
- Full pytest passed with three skipped tests.
- `tests/auth tests/api` passed.
- Ruff passed.
- Full mypy remains at the known 380-error baseline.
- Focused M008 mypy passed with 0 introduced errors.

## Deferred

- Production OIDC/JWKS verifier.
- Frontend login/account UX.
- JWT revocation/account lifecycle policy.
