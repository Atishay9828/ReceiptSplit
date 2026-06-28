# M008 Auth/OIDC Walkthrough

## What Changed

M008 adds account-level creator identity without removing the existing no-login room model.

1. User JWTs are parsed and verified behind `JwtVerifier`.
2. Verified `(provider, subject, email)` claims are upserted into `users`.
3. JWT-created rooms are linked with `rooms.creator_user_id`.
4. Creator routes accept either the owner JWT or the same-room legacy creator token.
5. Participant tokens remain valid for participant routes but are rejected from user-only and
   creator-only routes.

## Important Endpoints

- `GET /api/auth/me`
- `GET /api/users/me/rooms`
- `POST /api/rooms`
- `PATCH /api/rooms/{room_id}`
- `POST /api/rooms/{room_id}/split/lock`
- `POST /api/rooms/{room_id}/split/unlock`

## Validation Commands

Run from `backend`:

```powershell
D:\ReceiptSplit\backend\.venv\Scripts\python.exe -m pytest --collect-only -q
D:\ReceiptSplit\backend\.venv\Scripts\python.exe -m pytest tests\ -q
D:\ReceiptSplit\backend\.venv\Scripts\python.exe -m pytest tests\auth tests\api -q
D:\ReceiptSplit\backend\.venv\Scripts\python.exe -m ruff check .
D:\ReceiptSplit\backend\.venv\Scripts\python.exe -m mypy --cache-dir D:\ReceiptSplit\.mypy_cache_m008_final --follow-imports=silent app\auth\context.py app\auth\jwt.py app\auth\provider.py app\auth\errors.py app\auth\dependencies.py app\models\user.py app\models\room.py app\repositories\interfaces\user.py app\repositories\interfaces\room.py app\repositories\postgres\user.py app\repositories\postgres\room.py app\api\router.py app\api\routers\auth.py app\api\routers\rooms.py app\api\routers\split.py migrations\versions\002_m008_auth_users.py tests\api\test_auth_api.py tests\repositories\test_user.py tests\repositories\test_room_owner.py
```

Full mypy is intentionally not listed as passing because the repo has a pre-existing strict-mode
baseline.
