# OCR Architecture

## Purpose

M011 adds OCR as a draft generator for ReceiptSplit. OCR output is never treated as final bill
state. A creator uploads a receipt image, the backend validates and normalizes it, a provider
extracts text, a parser builds an editable draft, and the creator confirms that draft into normal
room items and adjustments.

## Free-first Provider Model

The OCR provider boundary is `OcrProvider.extract_text(image)`. The current implementations are:

- `MockOcrProvider` for deterministic tests and development fixtures.
- `TesseractOcrProvider` for free local OCR through a configurable Tesseract binary.
- An optional browser `PaddleOCR.js` adapter for free client-side inference. It is disabled by
  default and sends only a bounded, untrusted candidate to the existing authenticated upload.

Tesseract is the production-oriented local fallback because it is free and does not require paid
API credentials. It requests TSV output and preserves ordered word geometry/confidence in the
provider result while keeping the existing parser-compatible text stream. If the binary is missing
or times out, the provider maps that failure to safe domain errors instead of crashing the API.

Future providers such as `EasyOcrProvider`, `PaddleOcrProvider`, `GoogleVisionProvider`, or a
custom ML parser should implement the same provider protocol. API routes, parsed draft review, and
confirmation do not depend on Tesseract-specific details.

## Pipeline

The M011 synchronous MVP pipeline is:

1. `POST /api/rooms/{room_id}/receipts/upload`
2. Validate file size, MIME, magic bytes, and image dimensions.
3. Strip image metadata and store normalized private image bytes.
4. Create `receipt_images` and `ocr_jobs` rows.
5. If the browser flag is enabled and local OCR succeeds, validate its bounded candidate and use
   its text; otherwise run `OcrProvider.extract_text()`.
6. Store `ocr_results` with raw text only when explicitly enabled and redacted text for display.
7. Parse text with `IndianRestaurantReceiptParser`.
8. Store `parsed_receipts` in `draft` status.
9. Creator reviews and optionally patches the draft.
10. Creator confirms the draft into normal `line_items` and `split_adjustments`.

There is no public image URL and no local filesystem path is exposed in API responses.

## Validation And Preprocessing

`ReceiptImageValidator` accepts PNG and JPEG based on MIME and magic bytes. It enforces size and
dimension limits from config and rejects corrupt or mismatched images.

`BasicReceiptPreprocessor` is dependency-free for M011. It strips PNG ancillary chunks and JPEG APP
segments, preserving image pixels. Pillow/OpenCV grayscale, thresholding, denoising, and deskew are
deferred until the dependency and quality tradeoffs are worth it.

## Parser

`IndianRestaurantReceiptParser` is conservative and India-restaurant-focused. It detects item lines,
quantity x unit price forms, rupee/Rs/INR-prefixed amounts, quantity x amount lines, subtotal, CGST,
SGST, IGST, service charge, discount, rounding, and grand total. When a quantity x amount line does
not identify whether the amount is a unit or line total, it preserves the inferred line total and
sets `quantity_total_inferred` so the draft remains review-required. Money is always integer paise.
Ambiguous or inconsistent output sets warnings and `needs_review`.

## Privacy

OCR text can contain sensitive data. M011 redacts card-like numbers, phone numbers, email addresses,
and UPI-like IDs before display. Raw text storage is controlled by `OCR_STORE_RAW_TEXT`; even when
stored, raw text is not returned by default.

## Authorization

All OCR routes are creator-only through `require_room_owner_or_creator`, so both owner JWTs and
legacy creator capability tokens work. Participant tokens, wrong-room tokens, unrelated JWTs, and
missing credentials are rejected by the existing M008 authorization dependency.

## Event Integration

OCR draft creation/update emits OCR-specific room events. Confirmation emits existing room event
types for created items and adjustments, plus `room.updated`, so M009 clients can refresh through
the existing event transport.

## Configuration

- `RECEIPTSPLIT_OCR_PROVIDER=tesseract | mock`
- `RECEIPTSPLIT_TESSERACT_CMD=tesseract`
- `RECEIPTSPLIT_TESSERACT_LANGUAGE=` (optional installed language pack, for example `eng`)
- `RECEIPTSPLIT_TESSERACT_PSM=6`
- `RECEIPTSPLIT_OCR_TIMEOUT_SECONDS=30`
- `RECEIPTSPLIT_OCR_MAX_IMAGE_BYTES=5242880`
- `RECEIPTSPLIT_OCR_MAX_WIDTH=5000`
- `RECEIPTSPLIT_OCR_MAX_HEIGHT=5000`
- `RECEIPTSPLIT_OCR_STORAGE_BACKEND=local`
- `RECEIPTSPLIT_OCR_LOCAL_STORAGE_DIR=.local/ocr`
- `RECEIPTSPLIT_OCR_STORE_RAW_TEXT=false` (enable only for a deliberate local debugging policy)

The frontend browser path is opt-in with `NEXT_PUBLIC_RECEIPTSPLIT_BROWSER_OCR=false`. It uses the
pinned PaddleOCR.js package in a Web Worker with single-thread WASM settings. A local candidate
never bypasses creator authorization, server image validation, backend parsing, draft review, or
explicit confirmation. The image still follows the existing private upload/storage path.

For local browser smoke, use `RECEIPTSPLIT_OCR_PROVIDER=mock`. The mock provider now has a
deterministic synthetic receipt fixture by default, so local OCR review can be exercised without
Tesseract or paid OCR credentials.

## Local Development Database

Local browser smoke uses `docker-compose.dev.yml` with Postgres 15 on host port `54329`:

```powershell
docker compose -f docker-compose.dev.yml up -d
cd backend
$env:RECEIPTSPLIT_DATABASE_URL="postgresql+asyncpg://receiptsplit:receiptsplit@127.0.0.1:54329/receiptsplit_dev"
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Alembic derives a sync `postgresql+psycopg2://...` URL from the async URL, so `psycopg2-binary` is
a runtime dependency. Revision `001` creates `pgcrypto` before table creation because the schema
uses `gen_random_uuid()`.

## Deferred

Backend PaddleOCR workers, worker-backed async OCR, EasyOCR, Google Vision, camera capture, crop
detection, multi-page receipts, handwritten receipt support, and paid OCR defaults are
intentionally deferred. Browser PaddleOCR.js is implemented as an opt-in candidate path, but its
receipt accuracy and warm/cold latency are not yet benchmark evidence.
