# M008 Auth/OIDC Final Report

## Summary

M008 is implemented as a backend-only auth milestone. It adds creator user JWT auth behind a
verifier abstraction, persists normalized users, associates rooms with authenticated creators, and
preserves existing anonymous/capability-token room flows.

Final verdict: PASS.

## Files Created

- `backend/app/api/routers/auth.py`
- `backend/app/auth/context.py`
- `backend/app/auth/errors.py`
- `backend/app/auth/jwt.py`
- `backend/app/auth/provider.py`
- `backend/app/models/user.py`
- `backend/app/repositories/interfaces/user.py`
- `backend/app/repositories/postgres/user.py`
- `backend/migrations/versions/002_m008_auth_users.py`
- `backend/tests/api/test_auth_api.py`
- `backend/tests/auth/test_auth_context.py`
- `backend/tests/auth/test_contracts.py`
- `backend/tests/auth/test_jwt_verifier.py`
- `backend/tests/repositories/test_room_owner.py`
- `backend/tests/repositories/test_user.py`
- `docs/architecture/auth.md`
- `docs/reports/M008-auth-oidc.md`
- `task.md`
- `walkthrough.md`

## Files Modified

- `backend/app/api/router.py`
- `backend/app/api/routers/rooms.py`
- `backend/app/api/routers/split.py`
- `backend/app/auth/dependencies.py`
- `backend/app/auth/models.py`
- `backend/app/config.py`
- `backend/app/models/__init__.py`
- `backend/app/models/room.py`
- `backend/app/repositories/interfaces/__init__.py`
- `backend/app/repositories/interfaces/room.py`
- `backend/app/repositories/postgres/__init__.py`
- `backend/app/repositories/postgres/room.py`

## Database Changes

- Added `users` table with UUID primary key, provider, subject, nullable email, timestamps, and
  unique `(provider, subject)`.
- Added nullable `rooms.creator_user_id` foreign key to `users.id`.
- Added `idx_rooms_creator_user`.
- Existing rooms with `creator_user_id = NULL` remain valid.

## Auth Behavior Matrix

| Scenario | Result |
|---|---|
| Valid user JWT calls `GET /api/auth/me` | 200 |
| Participant token calls `GET /api/auth/me` | 403 `NOT_AUTHORIZED` |
| Invalid JWT calls `GET /api/auth/me` | 403 `INVALID_TOKEN` |
| User JWT creates room | Room is linked via `creator_user_id` |
| No JWT creates room | Legacy creator/invite tokens returned |
| Owner JWT calls creator route | 200 |
| Unrelated JWT calls creator route | 403 `NOT_AUTHORIZED` |
| Participant token calls creator route | 403 `NOT_AUTHORIZED` |
| Legacy creator token calls creator route | 200 |
| Cross-room capability token is reused | 403 `INVALID_TOKEN` |

## Tests Added

- JWT verifier tests.
- Request context separation tests.
- Shared contract tests.
- User repository tests.
- Room ownership repository tests.
- API tests for `/api/auth/me`, user room listing, owner JWT authorization, legacy token
  compatibility, cross-room rejection, and token-hash response leakage.

## Raw Validation Output

Commands were run from `D:\ReceiptSplit\backend` using
`D:\ReceiptSplit\backend\.venv\Scripts\python.exe` because `uv` is not on PATH.

- `python -m pytest --collect-only -q`: passed, 371 tests collected.
- `python -m pytest tests\ -q`: passed. Output reached `[100%]` with three skipped tests.
- `python -m pytest tests\auth tests\api -q`: passed. Output reached `[100%]`.
- `python -m pytest tests\repositories\test_user.py tests\repositories\test_room_owner.py -q`: passed, 6 tests.
- `python -m ruff check .`: passed.
- `python -m mypy .`: failed at the known repository baseline, `Found 380 errors in 31 files`.
- `python -m mypy --cache-dir D:\ReceiptSplit\.mypy_cache_m008_final --follow-imports=silent <M008 files>`: passed, no issues in 19 source/test files.

## Mypy Baseline Status

Full mypy is still not clean repo-wide. The refreshed baseline is 380 errors in 31 files, matching
the pre-M008 known strict-mode issue class: untyped legacy tests, protocol/base repository typing
gaps, and existing service test typing errors.

M008-introduced mypy errors: 0, proven with focused M008 mypy over auth, DB, API, migration, and
new M008 tests using a writable cache directory.

## Git Diff Summary

`git diff --stat ce35066..HEAD` before the final report commit showed 29 files changed with 1568
insertions and 54 deletions.

## Commit Hashes

- `6ca5e2c` - `chore(auth): define M008 shared auth contracts`
- `f6cb8d9` - `feat(auth): add authenticated user context and JWT verifier`
- `1a24f41` - `merge: integrate M008 auth core`
- `191d217` - `feat(db): associate rooms with authenticated creators`
- `2533fd2` - `merge: integrate M008 auth database ownership`
- `e3f7778` - `feat(api): expose auth endpoints and ownership checks`
- `fc4f42d` - `docs(auth): add M008 auth architecture report`

## Remaining Risks

- Production OIDC/JWKS verification is still deferred. The current non-dev provider path fails
  closed.
- Full mypy remains blocked by pre-existing repository-wide strict-mode errors.
- JWT revocation, account linking, and frontend login UX are not part of M008.

## Acceptance Checklist

- [x] Creator user JWT auth exists behind abstraction.
- [x] Participant capability tokens still work.
- [x] Legacy creator capability token still works.
- [x] Rooms can be associated with authenticated creators.
- [x] Owner JWT authorization is enforced.
- [x] Unrelated users are rejected.
- [x] Participant tokens cannot access user-only endpoints.
- [x] Token hashes are never leaked.
- [x] `/api/auth/me` exists and is tested.
- [x] Auth tests pass.
- [x] Full test suite passes.
- [x] Ruff passes.
- [x] M008-introduced mypy errors are 0.
- [x] `docs/reports/M008-auth-oidc.md` exists.
- [x] `docs/architecture/auth.md` exists.
- [x] Atomic commits exist.
- [x] No M009/M010/M011 work started.
