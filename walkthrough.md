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
8. Split preview stays in a friendly not-ready state until preview data is valid.
9. Creators preview and lock/unlock the split where backend state allows it.

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

## M010.1 Preview Readiness Cleanup

M010.1 adds a frontend-only readiness gate before split preview calls.

- Item-wise rooms do not call preview until every item quantity is claimed.
- Equal rooms can preview once participants and positive item totals exist.
- Incomplete rooms show `Split preview is not ready yet.` instead of normal-flow API errors.
- Creator Lock remains disabled until a valid preview exists.
- Realtime refetches recompute readiness before calling preview.

Manual smoke screenshots for this run are blocked because Docker/Postgres startup and npm audit
network escalation were rejected by the environment quota. The blocked evidence note is in
`docs/reports/screenshots/M010/M010.1-screenshots-blocked.md`.

## M011 OCR MVP Walkthrough

M011 adds a backend OCR draft flow:

1. Creator uploads a PNG/JPEG receipt image to `POST /api/rooms/{room_id}/receipts/upload`.
2. Backend validates size, content type, magic bytes, and dimensions.
3. Backend strips metadata and saves normalized private image bytes.
4. Backend creates an OCR job and runs the configured provider.
5. `MockOcrProvider` is available for tests; `TesseractOcrProvider` is the free local provider.
6. Raw OCR text is parsed into an editable draft.
7. Creator can fetch and patch the draft.
8. Creator confirms the draft into normal room items and adjustments.
9. Confirmation emits normal room events so existing realtime clients can refresh.

Important M011 endpoints:

- `POST /api/rooms/{room_id}/receipts/upload`
- `GET /api/rooms/{room_id}/ocr-jobs/{job_id}`
- `GET /api/rooms/{room_id}/parsed-receipts/{parsed_receipt_id}`
- `PATCH /api/rooms/{room_id}/parsed-receipts/{parsed_receipt_id}`
- `POST /api/rooms/{room_id}/parsed-receipts/{parsed_receipt_id}/confirm`

Focused validation:

```powershell
cd D:\ReceiptSplit\backend
.\.venv\Scripts\python.exe -m pytest tests\ocr -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy app\ocr app\api\routers\ocr.py app\api\schemas\ocr.py app\models\receipt_image.py app\models\ocr_job.py app\models\ocr_result.py app\models\parsed_receipt.py
```

## M011.1 Local Browser Smoke

Local database setup:

```powershell
docker compose -f docker-compose.dev.yml up -d
cd D:\ReceiptSplit\backend
$env:RECEIPTSPLIT_DATABASE_URL="postgresql+asyncpg://receiptsplit:receiptsplit@127.0.0.1:54329/receiptsplit_dev"
$env:RECEIPTSPLIT_CORS_ORIGINS="http://127.0.0.1:3000,http://localhost:3000"
$env:RECEIPTSPLIT_OCR_PROVIDER="mock"
$env:RECEIPTSPLIT_OCR_STORAGE_BACKEND="local"
$env:RECEIPTSPLIT_OCR_LOCAL_STORAGE_DIR=".local/ocr"
$env:RECEIPTSPLIT_OCR_STORE_RAW_TEXT="false"
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd D:\ReceiptSplit\frontend
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Smoke evidence:

- Sample receipt: `docs/reports/screenshots/M011.1/sample-receipt.jpg`.
- Screenshots: `create-page.png`, `creator-room-upload-card.png`, `ocr-draft-review.png`,
  `ocr-confirmed-items.png`, `participant-claim-after-ocr.png`, and
  `split-preview-after-ocr.png` in `docs/reports/screenshots/M011.1/`.
- Smoke room: `41667706-00bc-4029-a823-4219ed3b87ad`.
- Result: OCR draft edited and confirmed into room items, participant joined separately, both
  OCR-created items were claimed, and split preview returned `44600` paise.
- Caveat: creator lock/unlock was not exercised; the scripted creator pass still saw Lock disabled
  after preview.
