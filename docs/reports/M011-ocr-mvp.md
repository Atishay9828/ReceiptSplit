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

## Deferred Work

- Worker-backed OCR processing.
- OCR frontend review UI.
- Pillow/OpenCV grayscale, denoise, threshold, and deskew preprocessing.
- EasyOCR/PaddleOCR/Google Vision providers.
- Production object storage such as Supabase Storage.
- Raw OCR retention policy automation.
- Browser E2E coverage for OCR review.

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
- `docs/reports/M011-ocr-mvp.md`

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
- [x] `docs/reports/M011-ocr-mvp.md` exists.
- [x] `docs/architecture/ocr.md` exists.
- [x] No paid OCR default, payment, deployment, or settlement work started.
- [ ] Full backend suite passes: blocked by Docker/Testcontainers access in this environment.
- [ ] Frontend OCR UI: deferred due dirty M010.1 frontend tree.

## Verdict

CONDITIONAL PASS for backend OCR MVP. The implementation meets the backend architecture and focused
validation gates, but the full backend test-suite gate is blocked by environment-level Docker access.
