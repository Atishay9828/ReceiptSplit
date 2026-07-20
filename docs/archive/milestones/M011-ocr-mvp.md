> Historical milestone evidence.
> Do not load this file into default working context unless investigating this milestone.
> For current project state, read `docs/ACTIVE_CONTEXT.md` and `docs/MILESTONE_INDEX.md`.

# M011 OCR MVP Report

## Goal

Build a free-first modular OCR MVP that turns receipt images into editable drafts. OCR saves typing;
the creator remains responsible for review and confirmation.

## Scope

Implemented backend OCR domain modules, image validation, metadata stripping, local private storage,
mock and Tesseract providers, conservative parser fixtures, OCR persistence tables, creator-only API
routes, draft update, and confirm-to-room-items flow.

## Non-goals

No Google Vision default, paid OCR provider, UPI settlement, payment verification, wallet, escrow,
deployment, analytics, contact import, POS integration, native mobile app, or camera capture work
was started.

## Provider Architecture

Provider-specific code is isolated behind `OcrProvider`. `MockOcrProvider` is deterministic and used
by tests. `TesseractOcrProvider` uses a configurable local binary and maps missing-binary, timeout,
and provider failures to safe domain errors.

## Free-first OCR Decision

Tesseract is the free local provider for M011. It is not coupled to upload, parser, review, or
confirmation code. Future EasyOCR, PaddleOCR, Google Vision, or custom ML providers should plug in
without route or draft-flow rewrites.

## Image Validation

`ReceiptImageValidator` enforces file size, MIME, magic bytes, dimensions, supported formats, and
corrupt-image rejection. PNG/JPEG are supported without adding a new binary dependency.

## Preprocessing

`BasicReceiptPreprocessor` strips PNG ancillary chunks and JPEG APP segments, then stores normalized
bytes. More advanced OCR image processing is deferred.

## OCR Job Lifecycle

M011 stores `pending`, `processing`, `succeeded`, and `failed` job states in `ocr_jobs`. Upload
creates the job and processes synchronously with timeout-controlled provider execution. A worker is
deferred, but the job model is ready for one.

## Parser Design

The parser handles Indian restaurant receipt patterns: item lines, quantity x unit price, subtotal,
CGST, SGST, IGST, service charge, discount, rounding, and grand total. It ignores common footer
noise and emits warnings such as `missing_total`, `items_sum_mismatch`, `tax_detected`,
`discount_detected`, `low_confidence_line`, and `ambiguous_line`.

## Review/Correction Model

Parsed drafts are stored in `parsed_receipts` with editable JSON items/adjustments and `draft` or
`confirmed` status. `PATCH /api/rooms/{room_id}/parsed-receipts/{parsed_receipt_id}` updates the
draft before confirmation.

## Authorization Model

OCR APIs use `require_room_owner_or_creator`. Owner JWTs and legacy creator capability tokens are
accepted. Participant tokens, wrong-room tokens, unrelated user JWTs, malformed tokens, and missing
tokens are rejected by existing M008 auth dependencies.

## Storage Model

M011 stores normalized images through `ReceiptImageStorage`. The implemented backend is local
filesystem storage under `OCR_LOCAL_STORAGE_DIR`. API responses return opaque image ids, not
filesystem paths or public URLs.

## Privacy/Redaction

Raw OCR text is not returned by default. Display text is redacted for card-like numbers, phone
numbers, email addresses, and UPI-like IDs. Raw storage is controlled by `OCR_STORE_RAW_TEXT`.

## Event Integration

Draft creation/update emits `ocr.draft_created` and `ocr.draft_updated`. Confirmation emits
`item.created`, `adjustment.created`, and `room.updated` through the existing M009 event publisher.

## Frontend OCR UI

Deferred. The frontend tree already contains separate uncommitted M010.1 preview-readiness work, so
M011 avoids mixing OCR UI changes into that dirty surface.

## Tests

Added OCR unit coverage for:

- Mock provider fixture output.
- Tesseract missing binary and timeout error mapping.
- PNG validation, size rejection, corrupt image rejection, metadata stripping.
- Redaction of sensitive OCR text.
- Parser fixtures for simple restaurant, CGST/SGST, discount/rounding, quantity x price, noisy
  footer, and bad spacing.
- Parser mismatch and integer-paise money behavior.

## Validation Output

Commands used `D:\ReceiptSplit\backend\.venv\Scripts\python.exe` because `uv` is not installed in
this shell.

- `python -m pytest tests\ocr -q -o cache_dir=D:\ReceiptSplit\tmp\pytest-cache-ocr`: passed, 17 tests.
- `python -m ruff check .`: passed.
- Focused M011 mypy:
  `python -m mypy app\ocr app\api\routers\ocr.py app\api\schemas\ocr.py app\models\receipt_image.py app\models\ocr_job.py app\models\ocr_result.py app\models\parsed_receipt.py --cache-dir D:\ReceiptSplit\tmp\mypy-cache-m011`: passed, no issues in 16 source files.

## Backend Validation Output

- `uv run pytest tests/ -q`: blocked because `uv` is not installed.
- Fallback `python -m pytest tests/ -q`: blocked by Docker/Testcontainers named-pipe access:
  `pywintypes.error: (5, 'CreateFile', 'Access is denied.')`.
- `python -m pytest --collect-only -q`: passed collection, 354 tests collected.
- `python -m ruff check .`: passed.
- `python -m mypy .`: known baseline failure, 382 errors in 30 files.

## Mypy Baseline Status

Full backend mypy remains blocked by the pre-existing strict baseline. M011-introduced mypy errors
are 0 based on focused mypy over new OCR source, API, schema, and model files.

## M011.1 Local Browser Smoke

Current local closeout no longer classifies the previous browser failure as Docker being off.
Docker Desktop was reachable from this agent shell, and `docker ps` plus `docker info` worked.
The actual blocker was local app database setup: the dev backend needed a running Postgres
container, a valid `RECEIPTSPLIT_DATABASE_URL`, a sync Alembic driver, and fresh migrations.

Local setup added:

- `docker-compose.dev.yml` runs `postgres:15-alpine` on host port `54329`.
- `backend/.env.example` now points to
  `postgresql+asyncpg://receiptsplit:receiptsplit@127.0.0.1:54329/receiptsplit_dev`.
- Alembic revision `001` creates `pgcrypto` before using `gen_random_uuid()`.
- `psycopg2-binary` is now a backend dependency because Alembic uses the derived sync
  `postgresql+psycopg2://...` URL.
- `frontend/.env.example` sets `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.

Commands and results:

- `docker compose -f docker-compose.dev.yml up -d`: passed; `receiptsplit-postgres-dev`
  became healthy.
- `uv run alembic upgrade head`: `uv` was not installed in this shell; fallback
  `.venv\Scripts\python.exe -m alembic upgrade head` passed.
- Backend ran at `http://127.0.0.1:8000`; `GET /health` returned `{"status":"ok"}`.
- `GET /openapi.json` contained OCR upload, OCR job, parsed receipt, patch, and confirm routes.
- Frontend was already running at `http://127.0.0.1:3000`; starting a duplicate dev server
  returned `EADDRINUSE`, and `/create` returned HTTP 200 from the existing server.

## M011.1 Final Browser Smoke - OCR + Lock/Unlock

Final acceptance smoke ran against:

- Docker Desktop Linux engine: reachable after launching Docker Desktop.
- `receiptsplit-postgres-dev`: healthy on `127.0.0.1:54329`.
- `RECEIPTSPLIT_DATABASE_URL=postgresql+asyncpg://receiptsplit:receiptsplit@127.0.0.1:54329/receiptsplit_dev`.
- `RECEIPTSPLIT_OCR_PROVIDER=mock`.
- Backend: `http://127.0.0.1:8000`; `GET /health` returned `{"status":"ok"}`.
- Frontend: clean Next dev server on `http://localhost:3000`; `/create` returned HTTP 200.

Browser smoke result:

- Created final smoke room `086e25eb-951f-44ae-98a8-98095510752f`.
- Uploaded `docs/reports/screenshots/M011.1/sample-receipt.jpg`.
- Mock OCR produced a draft, creator edited `Paneer Tikka` to `Final Smoke Paneer Tikka` and changed
  the amount to `245.00`.
- Confirming the draft created normal room items: `Final Smoke Paneer Tikka` and `Masala Dosa`.
- A separate participant context joined as `AJ Lock Smoke`.
- Participant-authenticated claim calls assigned both OCR-created items.
- Split preview returned `44600` paise and the UI showed creator total `0.00` and participant
  total `446.00`.
- No auto-share and no auto-lock happened; the room remained `active`.
- Creator summary reflected both participant claims through the live sync path without reload.
- Creator Lock became enabled after preview was available.
- Creator Lock transitioned the room to `settling`.
- Locked mutation controls were hidden or disabled: scan receipt, add adjustment, and item edit
  controls were not available while locked.
- Creator Unlock transitioned the room back to `active`.
- Unlock restored mutation controls: scan receipt, add adjustment, and two item edit controls were
  available again.
- Final summary after unlock: status `active`, 2 items, 2 assignments, 2 participants.

Screenshots:

- `docs/reports/screenshots/M011.1/create-page.png`
- `docs/reports/screenshots/M011.1/creator-room-upload-card.png`
- `docs/reports/screenshots/M011.1/ocr-draft-review.png`
- `docs/reports/screenshots/M011.1/ocr-confirmed-items.png`
- `docs/reports/screenshots/M011.1/participant-claim-after-ocr.png`
- `docs/reports/screenshots/M011.1/split-preview-after-ocr.png`
- `docs/reports/screenshots/M011.1/lock-enabled-after-ocr-preview.png`
- `docs/reports/screenshots/M011.1/locked-after-ocr.png`
- `docs/reports/screenshots/M011.1/unlocked-after-ocr.png`
- `docs/reports/screenshots/M011.1/unlock-controls-restored-after-ocr.png`

Current validation:

- `uv run pytest tests/ -q`: `uv` was not installed in this shell; escalated fallback
  `.venv\Scripts\python.exe -m pytest tests/ -q` passed, with three skipped tests.
- `.venv\Scripts\python.exe -m ruff check .`: passed.
- Focused mypy for OCR backend scope passed:
  `Success: no issues found in 21 source files`.
- `.venv\Scripts\python.exe -m mypy .`: still fails on the known strict baseline, now
  reported as `382 errors in 30 files (checked 172 source files)`.
- Frontend `npm.cmd run lint`: passed.
- Frontend `npm.cmd run typecheck`: passed.
- Frontend `npm.cmd test`: passed, 8 files and 34 tests.
- Frontend `npm.cmd run build`: passed on Next.js 16.2.9.
- `npm.cmd audit --json`: two moderate advisories through Next/PostCSS
  (`GHSA-qx2v-qp2m-jg93`); npm reports a semver-major downgrade-style fix, so no force fix was run.

## Deferred Work

- Worker-backed OCR processing.
- Pillow/OpenCV grayscale, denoise, threshold, and deskew preprocessing.
- EasyOCR/PaddleOCR/Google Vision providers.
- Production object storage such as Supabase Storage.
- Raw OCR retention policy automation.
- Browser E2E coverage should be promoted from local smoke script to a committed test harness.

## Files Changed

Primary M011 files:

- `backend/app/ocr/**`
- `backend/app/api/routers/ocr.py`
- `backend/app/api/schemas/ocr.py`
- `backend/app/models/receipt_image.py`
- `backend/app/models/ocr_job.py`
- `backend/app/models/ocr_result.py`
- `backend/app/models/parsed_receipt.py`
- `backend/migrations/versions/003_m011_ocr_mvp.py`
- `backend/tests/ocr/**`
- `backend/tests/fixtures/receipts/**`
- `docs/architecture/ocr.md`
- `docs/archive/milestones/M011-ocr-mvp.md`

## Git Commits

M011 commit hashes are reported in the final Codex closeout. The tree also contains pre-existing
uncommitted M010.1 frontend/docs changes that are intentionally not part of M011.

## Acceptance Checklist

- [x] OCR is free-first by default.
- [x] OCR is modular/provider-based.
- [x] `MockOcrProvider` exists for tests.
- [x] `TesseractOcrProvider` exists with configurable binary and timeout.
- [x] Image validation exists.
- [x] Metadata stripping exists.
- [x] Preprocessing pipeline exists.
- [x] Raw/redacted OCR result storage exists.
- [x] Parser creates editable receipt draft.
- [x] Correction/update flow exists.
- [x] Confirm flow creates room items/adjustments.
- [x] OCR routes are creator-only.
- [x] Parser fixtures pass.
- [x] Ruff passes.
- [x] M011-introduced mypy errors are 0.
- [x] `docs/archive/milestones/M011-ocr-mvp.md` exists.
- [x] `docs/architecture/ocr.md` exists.
- [x] Local dev Postgres compose path exists.
- [x] Local M011.1 OCR browser smoke evidence exists.
- [x] No paid OCR default, payment, deployment, or settlement work started.
- [x] Full backend suite passes with local Docker/Testcontainers access.
- [x] Frontend OCR review UI is present and smoke-tested.
- [x] Creator lock/unlock is exercised after OCR-created claims.
- [x] Locked and unlocked mutation-control behavior is smoke-tested.
- [ ] Full backend mypy passes: blocked by pre-existing strict baseline.
- [ ] `npm audit --json` is clean: blocked by moderate Next/PostCSS advisory chain.

## Verdict

FULL PASS for M011.1 OCR Frontend Review UI acceptance. The local Postgres path, migrations,
backend, frontend, OCR upload/review/edit/confirm, item creation, participant join, participant
claim state, split preview, creator lock, creator unlock, and locked/unlocked mutation controls
are proven.

Deferred repo-level risks remain outside M011.1 acceptance: full backend mypy is still blocked by
the pre-existing strict baseline, and npm audit still reports the moderate Next/PostCSS advisory
chain.
