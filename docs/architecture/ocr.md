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

Tesseract is the production-oriented default because it is local, free, and does not require paid
API credentials. If the binary is missing or times out, the provider maps that failure to safe
domain errors instead of crashing the API.

Future providers such as `EasyOcrProvider`, `PaddleOcrProvider`, `GoogleVisionProvider`, or a
custom ML parser should implement the same provider protocol. API routes, parsed draft review, and
confirmation do not depend on Tesseract-specific details.

## Pipeline

The M011 synchronous MVP pipeline is:

1. `POST /api/rooms/{room_id}/receipts/upload`
2. Validate file size, MIME, magic bytes, and image dimensions.
3. Strip image metadata and store normalized private image bytes.
4. Create `receipt_images` and `ocr_jobs` rows.
5. Run `OcrProvider.extract_text()`.
6. Store `ocr_results` with raw text according to config and redacted text for display.
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
quantity x unit price forms, subtotal, CGST, SGST, IGST, service charge, discount, rounding, and
grand total. Money is always integer paise. Ambiguous or inconsistent output sets warnings and
`needs_review`.

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

- `OCR_PROVIDER=tesseract | mock`
- `TESSERACT_CMD=tesseract`
- `OCR_TIMEOUT_SECONDS=30`
- `OCR_MAX_IMAGE_BYTES=5242880`
- `OCR_MAX_WIDTH=5000`
- `OCR_MAX_HEIGHT=5000`
- `OCR_STORAGE_BACKEND=local`
- `OCR_LOCAL_STORAGE_DIR=.local/ocr`
- `OCR_STORE_RAW_TEXT=true`

The settings are exposed with the existing `RECEIPTSPLIT_` prefix.

## Deferred

Worker-backed async OCR, EasyOCR, PaddleOCR, Google Vision, camera capture, crop detection,
multi-page receipts, handwritten receipt support, and paid OCR defaults are intentionally deferred.
