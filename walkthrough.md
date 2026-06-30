# M010 Frontend MVP Walkthrough

## What Changed

M010 adds the first mobile-first frontend for ReceiptSplit's manual receipt-first flow.

1. Creators create a room from `/create`.
2. The frontend stores the creator capability token in localStorage.
3. Creators add manual receipt items and optional adjustments.
4. Creators share `/join/[inviteToken]`, which encodes the backend room id and invite token.
5. Participants join with nickname only and store a participant capability token locally.
6. Participants claim/unclaim item quantities from `/rooms/[roomId]`.
7. Creator and participant rooms refresh through M009 replay/SSE event sync.
8. Creators preview and lock/unlock the split where backend state allows it.

## Important Endpoints

- `POST /api/rooms`
- `GET /api/rooms/{room_id}/summary`
- `PATCH /api/rooms/{room_id}`
- `POST /api/rooms/{room_id}/join`
- `POST /api/rooms/{room_id}/items`
- `PATCH /api/rooms/{room_id}/items/{item_id}`
- `DELETE /api/rooms/{room_id}/items/{item_id}`
- `POST /api/rooms/{room_id}/items/{item_id}/claim`
- `DELETE /api/rooms/{room_id}/items/{item_id}/claim`
- `GET /api/rooms/{room_id}/split/preview`
- `POST /api/rooms/{room_id}/split/lock`
- `POST /api/rooms/{room_id}/split/unlock`
- `GET /api/rooms/{room_id}/events`
- `GET /api/rooms/{room_id}/events/stream`

## Validation Commands

Backend commands use `.venv` in this shell because `uv` is unavailable:

```powershell
D:\ReceiptSplit\backend\.venv\Scripts\python.exe -m pytest tests\ -q
D:\ReceiptSplit\backend\.venv\Scripts\python.exe -m ruff check .
```

Frontend commands:

```powershell
cd D:\ReceiptSplit\frontend
npm.cmd install
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

Full backend mypy remains blocked by the pre-existing strict-mode baseline.
