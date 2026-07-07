# ReceiptSplit Flow Walkthrough

This is a compact workflow reference. For current project state, read `docs/ACTIVE_CONTEXT.md`; for
milestone history, read `docs/MILESTONE_INDEX.md`.

## Manual Room Flow

1. Creator creates a room from `/create`.
2. Frontend stores the creator capability token locally.
3. Creator adds receipt items and supported adjustments.
4. Creator opens claiming when ready.
5. Participants join through `/join/[inviteToken]` with nickname only.
6. Participants claim or unclaim item quantities.
7. Creator previews and locks the split when preview readiness passes.
8. Creator can unlock where backend state allows it.

## OCR Review Flow

1. Creator uploads a PNG/JPEG receipt image.
2. Backend validates image type, size, magic bytes, dimensions, and strips metadata.
3. Configured OCR provider returns text.
4. Parser creates an editable receipt draft.
5. Creator reviews and edits draft items or adjustments.
6. Creator confirms the draft into normal room items and adjustments.
7. Existing claim, preview, lock, and settlement rules continue to apply.

M011.1 browser evidence lives under `docs/reports/screenshots/M011.1/`.

## Settlement Flow

M012 adds coordinator-safe settlement after room lock. It remains CONDITIONAL PASS until API tests,
browser smoke, screenshots, and commit are complete.

1. Creator locks the split.
2. Creator saves payer display name and VPA.
3. Creator prepares settlement requests from locked participant totals.
4. Participant opens the server-generated UPI URI/QR payload.
5. Participant manually marks `I paid`.
6. Creator manually chooses `Confirm payment` or `Mark disputed`.

ReceiptSplit does not process, hold, verify, refund, or auto-confirm funds.

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
- `POST /api/rooms/{room_id}/receipts/upload`
- `GET /api/rooms/{room_id}/ocr-jobs/{job_id}`
- `GET /api/rooms/{room_id}/parsed-receipts/{parsed_receipt_id}`
- `PATCH /api/rooms/{room_id}/parsed-receipts/{parsed_receipt_id}`
- `POST /api/rooms/{room_id}/parsed-receipts/{parsed_receipt_id}/confirm`
- `GET /api/rooms/{room_id}/settlement`
- `PUT /api/rooms/{room_id}/settlement/payer`
- `POST /api/rooms/{room_id}/settlement/prepare`
- `POST /api/rooms/{room_id}/settlement/requests/{request_id}/open-payment`
- `POST /api/rooms/{room_id}/settlement/requests/{request_id}/claim-paid`
- `POST /api/rooms/{room_id}/settlement/requests/{request_id}/confirm`
- `POST /api/rooms/{room_id}/settlement/requests/{request_id}/dispute`
- `GET /api/rooms/{room_id}/events`
- `GET /api/rooms/{room_id}/events/stream`

## Validation Commands

Backend commands use `.venv` in this shell when `uv` is unavailable:

```powershell
cd D:\ReceiptSplit\backend
.\.venv\Scripts\python.exe -m pytest tests\ -q
.\.venv\Scripts\python.exe -m ruff check .
```

Frontend commands:

```powershell
cd D:\ReceiptSplit\frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

Focused M012 commands:

```powershell
cd D:\ReceiptSplit\backend
.\.venv\Scripts\python.exe -m pytest tests\unit\test_settlement_link_builder.py -q
.\.venv\Scripts\python.exe -m pytest tests\api\test_settlement.py -q

cd D:\ReceiptSplit\frontend
npm.cmd test -- settlement-ui.test.tsx api.test.ts
```

Known blockers:

- full backend mypy is still at the known strict baseline
- M012 API test/browser smoke need local Docker/Postgres access
- M012 screenshots are pending; see `docs/reports/screenshots/M012/M012-screenshots-blocked.md`
