# Receipt OCR Research and Free-First Implementation Plan

**Research date:** 2026-08-09
**Scope:** printed paper receipts, especially restaurant/retail receipts photographed on a phone; free or self-hosted options only.
**Security boundary:** OCR is an untrusted suggestion inside a money workflow. It must never create a bill, lock a split, or imply payment verification without creator review and the existing domain checks.

## Executive verdict

Use a two-tier PaddleOCR-based design, while retaining the existing Tesseract provider as a fallback:

1. **Public zero-cost website path:** run the official `PaddleOCR.js` browser SDK in a Web Worker, using a small/mobile PP-OCR model. OCR inference happens on the user device, so the public Render service does not need to host a heavy model. The current implementation still sends the validated image through the existing authenticated upload/storage path; the browser result is only a bounded, untrusted candidate for backend parsing, review, and audit-safe persistence.
2. **Local/self-hosted accuracy path:** add a `PaddleOcrProvider` behind the existing provider protocol. Use a pinned PaddleOCR release and a small CPU model first; run it in a separate worker/container when the local benchmark proves the dependency and latency are acceptable. Preserve boxes and confidence, not just a flattened string.
3. **Fallback path:** keep `TesseractOcrProvider` for offline/local development and as a low-dependency fallback. It now emits TSV-derived word boxes/confidence while preserving the parser-compatible text stream; continue benchmarking receipt-specific preprocessing and parser logic. Do not treat Tesseract as the final quality bar without corpus evidence.
4. **Do not pay for or depend on cloud OCR:** AWS Textract, Google Document AI, Azure Document Intelligence, and Mindee are useful references for what a mature receipt pipeline returns, but their hosted processing, quotas, billing, and external data transfer violate the current free-only boundary.
5. **Do not build a custom OCR model yet:** first benchmark the open engines on a consented, India-relevant receipt set. If the failure is mostly extraction/line grouping, improve the parser before training OCR. Custom recognition or detection is the last resort for a proven language/layout gap.

This is a recommendation, not a measured accuracy claim. The final engine must be selected from a reproducible local benchmark; vendor-reported benchmark numbers are not evidence for ReceiptSplit’s receipt mix.

## Fresh local smoke evidence (not a benchmark)

On 2026-08-09, `rapidocr` 3.9.2 with ONNX Runtime 1.28.0 was run locally against the existing
`docs/reports/screenshots/M011.1/sample-receipt.jpg` (727,620 bytes, 1024x1024). The PP-OCRv6
small ONNX models returned 21 text tokens. Manual comparison with the image found all visible text
groups represented, including rupee-prefixed amounts. The minimum token score was 0.934 and the
mean was 0.98352. Three same-process runs took 2.788s, 2.122s, and 2.402s.

This is useful feasibility evidence for a local RapidOCR/Paddle-derived path, not an accuracy claim:
it is one receipt, one device, one model configuration, and no ground-truth corpus. It does not
justify enabling RapidOCR on the public Render service or replacing the planned benchmark.

## What receipt OCR actually requires

“Read all text” and “turn a receipt into split items” are different problems:

```text
image capture
  -> image validation and privacy normalization
  -> orientation / crop / perspective / contrast handling
  -> text detection (where are the words?)
  -> text recognition (what does each word say?)
  -> layout reconstruction (which words share a line/column?)
  -> receipt semantics (merchant, items, taxes, discounts, total)
  -> arithmetic reconciliation in paise
  -> editable draft with provenance and warnings
  -> explicit creator confirmation
  -> normal ReceiptSplit items and adjustments
```

A plain OCR string is insufficient for receipts because item descriptions and prices are usually separate columns, quantities may be printed as `2 x 120.00`, and totals can be visually emphasized or repeated. The system should retain an ordered list of text tokens/lines with bounding boxes and confidence, then derive the editable draft from that representation.

Receipt-specific difficult cases include:

- narrow thermal paper, faint or broken ink, dot-matrix characters, glare, shadows, blur, and JPEG artifacts;
- perspective distortion, curled paper, rotation, cropped edges, and receipts photographed against a busy background;
- item names wrapping to another line, abbreviated SKU text, prices aligned at the far right, and quantity/unit-price variants;
- headers and footers containing merchant/address/GSTIN/phone/payment text that should not become items;
- several taxes or charges (`CGST`, `SGST`, `IGST`, service charge, delivery/packaging fee), discounts, coupons, and rounding;
- mixed scripts and languages. Current PaddleOCR model families do not all support the same Indic languages, so language coverage must be selected and tested rather than assumed.

## Techniques to use

### 1. Capture and validation

- Prefer one receipt per image, rear camera, a visible receipt boundary, even lighting, and a short capture guide in the UI.
- Reject empty, oversized, corrupt, mismatched, or extreme-dimension uploads before decoding or inference.
- Accept only the formats needed by the product, currently JPEG and PNG. Detect the actual file signature; never trust the browser MIME type alone.
- Generate storage names server-side. Never use the original filename or a client path.
- Normalize/strip metadata and avoid public image URLs. If the product does not need image re-download, process in memory and delete the original after the draft is created.

### 2. Preprocessing, but not one destructive filter

Use a small ordered pipeline and keep the original pixels available only where the retention policy allows:

1. decode safely and cap decoded pixel count;
2. orientation correction and border/background crop;
3. perspective correction when a receipt boundary can be detected with high confidence;
4. resize so character height is readable; Tesseract’s documentation notes that it works best around 300 DPI-equivalent input;
5. grayscale/contrast normalization and adaptive thresholding for uneven paper;
6. mild denoising and deskewing;
7. preserve an original-color or lightly normalized variant for faint thermal ink;
8. run a second variant only when confidence or arithmetic reconciliation is poor.

Do not aggressively binarize every receipt. A threshold that helps dark printed text can erase faint thermal text. Treat preprocessing as candidate generation and choose the candidate with the best confidence plus receipt consistency, not just the longest output.

### 3. Detection and recognition

Prefer a two-stage detector/recognizer for photographed receipts. Text detection gives geometry; recognition turns each cropped text region into characters. Geometry is what lets the parser align item descriptions with right-side amounts and reconstruct wrapped lines.

For Tesseract, request TSV or hOCR rather than only stdout. Its official formats include word boxes and confidence; configure page segmentation per receipt shape and compare `--psm 4`, `--psm 6`, and sparse-text modes on the benchmark. Tesseract’s own guidance calls out rescaling, binarization, noise, deskewing, dictionaries, and receipt/price-list segmentation as quality levers.

For PaddleOCR, start with the lightweight mobile/small OCR pipeline rather than PP-StructureV3. PP-StructureV3 is a full document-layout pipeline and is useful for complex multi-column documents, but it brings more models, memory, and latency than a single narrow receipt normally needs. Add it only if receipt layout tests show the plain OCR boxes are not enough.

### 4. Layout reconstruction

Convert OCR boxes into canonical lines:

- normalize coordinates to the source image dimensions;
- sort by vertical center, then left edge;
- group boxes by vertical overlap/baseline tolerance;
- preserve both visual order and raw token order;
- detect right-aligned amount columns using x-position clusters and amount-like strings;
- attach wrapped description lines to the nearest item candidate only when the geometry and semantics agree;
- retain the source token IDs for every parsed field.

Never parse by assuming that whitespace has a stable meaning across vendors. Never silently discard an unrecognized line: keep it in raw/redacted text or an “unclassified lines” review section.

### 5. Receipt semantics and arithmetic

Keep the existing conservative parser direction, but make it layout-aware:

- classify merchant/header, date/time, receipt number, address, tax IDs, payment/footer, item, subtotal, tax/fee, discount, rounding, and grand-total candidates;
- parse Indian money forms and currency symbols into integer paise;
- support quantity/unit-price/line-total patterns and multi-line item names;
- identify tax labels and preserve separate tax components even when the split engine later allocates them together;
- compute candidate totals from items and adjustments;
- compare candidates against the printed subtotal and grand total with an explicit rounding policy;
- emit warnings for missing totals, duplicate total candidates, amount-only lines, low confidence, unknown language, and any mismatch;
- set `needs_review` whenever an amount, item, or reconciliation is uncertain.

The parser must be deterministic and must not use a language model to invent missing numbers. A future local model may help classify an ambiguous line, but it must return a candidate with provenance and pass the same arithmetic/review gates.

## Candidate engines

| Engine | Free/local | Receipt-relevant strengths | Costs/risks | Decision |
|---|---:|---|---|---|
| **PaddleOCR 3.x / PP-OCRv5 or v6** | Yes; Apache 2.0 project | Modern text detection + recognition, boxes and confidence, lightweight model tiers, CPU/mobile/server options, broad language ecosystem, official browser SDK | Larger dependency/model footprint than Tesseract; Paddle/Python compatibility can be awkward on Windows; model language coverage differs by family; model assets need separate license review | **Primary accuracy engine.** Benchmark `PP-OCRv6 small`/the currently supported small model locally; use browser `PaddleOCR.js` PP-OCRv5 for the public free path. Test Indic scripts separately. |
| **Tesseract 5** | Yes; Apache 2.0 project | Mature, tiny operational footprint, more than 100 language data files, TSV/hOCR/PDF/ALTO/PAGE output, easy offline fallback | Line-oriented segmentation and dictionaries are weaker for variable receipt columns and photos; needs preprocessing; current provider now defaults to `--psm 6` but exposes language/PSM settings | **Fallback and baseline.** Keep it because it is cheap and robust operationally; benchmark the new TSV/layout output before judging it. |
| **RapidOCR** | Yes; Apache 2.0 engineering project, ONNX Runtime/OpenVINO/MNN/etc. | Derived from Paddle models, fast offline deployment, Python/C++/C#/Java support, CPU-friendly and cross-platform | Default examples focus on Chinese/English; model copyrights/terms are separate; less receipt/layout abstraction than a full Paddle pipeline | **Strong deployment fallback** if Paddle’s runtime is too heavy or Windows/CPU latency fails. Benchmark against Paddle on the same images. |
| **EasyOCR** | Yes; Apache 2.0 | 80+ languages, Devanagari support, boxes/text/confidence, CPU mode, easy prototype | Latest stable release is older than the current Paddle line; PyTorch dependency; less receipt-specific layout/semantic tooling | **Prototype/comparison option**, not the first production choice. |
| **docTR** | Yes; Apache 2.0 | Clean two-stage detection/recognition, JSON export, rotated boxes, PyTorch/TensorFlow options, good developer API | General document OCR rather than receipt-specific; heavier model/runtime than Tesseract; language and CPU behavior need local proof | **Useful research baseline** if Paddle integration is blocked, not the first deployment choice. |
| **Custom OCR** | Potentially yes | Can target ReceiptSplit’s exact scripts, thermal printers, and vendor layouts | Requires privacy-safe labeled images, box/transcription annotation, training/inference infrastructure, model/version maintenance, and new failure modes | **Last resort only.** First customize parsing and preprocessing; fine-tune an open engine before building a new recognizer. |

The license labels above refer to the public project repositories, not automatically every downloaded model, dictionary, runtime, or training dataset. Pin versions and record model/dictionary licenses before shipping.

## What mature receipt products do

Public documentation for commercial document-intelligence products converges on the same architecture:

- **Amazon Textract AnalyzeExpense** returns `SummaryFields` for receipt-level data and `LineItemGroups` for purchased lines, with geometry and confidence.
- **Google Document AI Expense Parser** combines OCR with entity extraction for expense date, supplier, total, currency, and line items; its current pricing page shows a paid processor after any free allowance.
- **Azure Document Intelligence prebuilt-receipt** combines OCR and a receipt model to return normalized merchant, items, taxes, total, and detected text fields.
- **Mindee Receipt** exposes merchant, total, taxes, locale, and line items with description, quantity, unit price, and total price.

The lesson is not to copy a paid vendor. It is that a receipt product needs **OCR + geometry + semantic extraction + normalization + confidence + human correction**, not a raw text dump. ReceiptSplit already has the most important safety decision: OCR produces an editable draft, and only explicit creator confirmation creates normal bill items.

## ReceiptSplit baseline and gaps

The current repository already contains a good security-oriented boundary:

- `backend/app/ocr/contracts.py` defines provider, preprocessing, parser, and draft contracts.
- `backend/app/ocr/providers.py` contains deterministic mock and local Tesseract providers.
- `backend/app/ocr/validation.py` checks size, signature, MIME agreement, dimensions, and corruption.
- `backend/app/ocr/preprocessing.py` strips PNG/JPEG metadata without adding a heavy dependency.
- `backend/app/ocr/parser.py` handles restaurant items, quantity x price, GST components, fees, discounts, rounding, and mismatch warnings in integer paise.
- `backend/app/ocr/storage.py` keeps image paths opaque and outside public API responses.
- `frontend/components/receipt-upload.tsx` shows an editable review flow and does not add OCR output directly to the room.
- `docs/architecture/security.md` already treats OCR uploads, text, drafts, and settlement data as sensitive assets.
- `render.yaml` currently deploys `RECEIPTSPLIT_OCR_PROVIDER=mock` and local storage on Render Free. That is deliberate: the public service has no durable local filesystem for receipt images and does not currently install a Tesseract binary.

The main quality gaps are:

1. The internal provider result now retains Tesseract word boxes/confidence. The browser candidate
   handoff also normalizes line geometry, but the database and parser do not yet persist or exploit
   full layout provenance.
2. The preprocessor strips metadata but does not deskew, rectify, crop, normalize illumination, or produce alternate OCR variants.
3. The parser is mostly line/regex-based and cannot reliably use price-column geometry or wrapped lines.
4. The current upload route performs synchronous server-side work. A model with cold-start downloads or CPU-heavy inference should not be placed on the request path without bounded jobs.
5. There is no committed receipt-image benchmark with all-text and money-specific metrics.
6. Raw OCR retention is configurable; production should default to no raw text and a short-lived or no-image retention policy.

## Website integration design

### Public, no-cost path

The first optional client-side adapter is now wired into the existing `ReceiptUpload` component,
behind `NEXT_PUBLIC_RECEIPTSPLIT_BROWSER_OCR=false` by default:

1. Load `@paddleocr/paddleocr-js` only in the client adapter. The current slice creates and disposes a model per scan; session caching is a later latency optimization.
2. Run inference in a Web Worker so the upload screen remains responsive. The UI shows model loading, local reading, cancellation through reset/unmount, and server fallback states.
3. Cap the selected file at 5 MiB, cap browser candidate lines/text/coordinates, and rely on the backend for decoded image limits and signature validation. Do not store the image, OCR text, or model output in localStorage.
4. Return text lines, boxes, confidence, language/model version, and raw text to the backend as a bounded candidate alongside the image. The candidate is not an authority and is never used to bypass the authenticated upload.
5. The backend validates the candidate schema, bounds every string/array/coordinate, reconstructs canonical tokens, parses in integer paise, reconciles totals, redacts sensitive display text, and creates the existing editable draft.
6. Treat every client-derived field—including text, confidence, total, and model name—as untrusted. The creator’s authenticated room authorization and explicit draft confirmation remain mandatory.
7. If browser inference is unavailable, slow, or fails, use the existing manual-entry path or a backend/local provider. Do not silently claim a successful scan.

This path is attractive for the current free deployment because OCR inference is local and the public Render service avoids a persistent model dependency. The current route still stores the normalized image according to the existing retention policy, so this is not yet a zero-upload privacy mode. The tradeoff is device-dependent latency and a larger browser download. Pin the npm package and model assets, preferably serve them from a controlled origin, and review the required COOP/COEP/CSP headers before enabling threaded WASM or WebGPU.

### Local/self-hosted backend path

Add a provider without changing the route, draft, or confirmation contract:

```text
OcrProvider.extract_document(image) ->
    provider, engine_version, language, tokens[], lines[], raw_text,
    confidence, preprocessing_metadata
```

Implementation order:

1. Extend the internal result contract with optional tokens/boxes while preserving `raw_text` for compatibility.
2. Add `PaddleOcrProvider` that preloads a pinned lightweight model once per worker process.
3. Run it through a bounded OCR job executor. Enforce one image/job, a timeout, a maximum decoded pixel count, and a concurrency limit.
4. Use Paddle’s normal OCR pipeline first. Add PP-StructureV3 only if receipt benchmark evidence shows a measurable layout benefit worth the memory/latency.
5. Persist only the provider/model/preprocessing versions, redacted OCR result, parser warnings, and draft provenance by default. Keep raw OCR and image retention opt-in for local debugging only.
6. Keep Tesseract available as a fallback when the model is missing, out of memory, or timed out.

Do not simply switch the current Render variable from `mock` to `tesseract` and call that production OCR. The deployed native service needs the binary, enough cold-start/runtime budget, and a safe storage policy. Render Free services have ephemeral filesystems and can spin down; persistent disks require a paid service. The browser path or a separately controlled self-hosted worker is the honest free deployment choice.

### API and state changes to plan

The existing `pending -> processing -> succeeded/failed` job model is reusable. Add only what is needed:

- `engine`, `engine_version`, `language`, and `preprocessing_version` on the OCR result/job metadata;
- token/line geometry stored privately or in a bounded JSON structure for review provenance;
- a source reference for each parsed field (`token_ids`, confidence range, and parser rule);
- explicit `client_candidate` versus `server_provider` provenance;
- cancellation and timeout states if OCR becomes asynchronous;
- an idempotency key or content hash so repeated uploads do not create unlimited duplicate jobs;
- retention timestamps and a deletion task for images/raw OCR when they are not needed for the draft;
- safe audit events containing counts, provider/version, warning names, latency buckets, and hashes—not receipt text, image bytes, tokens, payment references, or access tokens.

## Security and money-safety requirements

These are release gates, not optional polish:

### Upload and inference boundary

- Require the existing creator/owner authorization before upload, job read, draft patch, or confirmation.
- Allowlist JPEG/PNG and verify file signatures; do not trust extension or `Content-Type` alone.
- Limit both compressed bytes and decoded pixels. Guard against malformed images, decompression bombs, parser CVEs, and CPU/memory exhaustion.
- Generate opaque storage keys and keep files outside the web root; never return local paths or public URLs.
- Run inference with a non-privileged process, bounded timeout, bounded concurrency, and no network access from the OCR worker unless explicitly required for model initialization.
- Pin OCR packages, model files, runtime images, and dictionaries; review their licenses and supply-chain hashes.
- Escape/redact OCR text before displaying it. Treat merchant names, item names, and footer text as attacker-controlled strings.

### Draft and domain integrity

- Never copy OCR output directly into `line_items`, `adjustments`, split sessions, or settlement requests.
- Keep all money as integer paise. Reject negative/overflow/NaN-like values and enforce existing item/adjustment limits server-side.
- Re-run arithmetic reconciliation on every draft patch and confirmation. Do not trust a browser-computed total or confidence score.
- Keep uncertain drafts in `needs_review`; a high OCR confidence score cannot override a total mismatch.
- Require the creator to review/edit and explicitly confirm. Confirmation must remain idempotent and transactionally create the same normal room records as manual entry.
- OCR must never set a room to locked/settling/settled and must never change `payer confirmed`, `marked paid`, or `disputed` settlement state.

### Privacy and observability

- Default production raw-text storage to false. Prefer browser-local OCR or process-and-delete image bytes when retention is not a user feature.
- Do not put raw OCR, card-like numbers, phone/email/UPI strings, payment references, tokens, or full request bodies into logs/audit rows.
- Audit upload, failure, draft update, confirmation, deletion, and suspicious-rate-limit events with actor/resource IDs, safe counts, provider/version, warning names, and request IDs.
- Add tests for cross-room access, participant-token rejection, malformed client OCR payloads, replayed confirmation, oversized token arrays, malicious item names, and arithmetic mismatch.

## Benchmark and acceptance plan

### Corpus

Start with public receipt datasets only for smoke and comparison:

- **SROIE**: receipt text localization, OCR, and key-information extraction tasks; it has 1,000 whole scanned receipt images.
- **CORD**: photographed Indonesian receipts with OCR boxes/text and post-OCR semantic labels.

Neither dataset proves performance on Indian restaurant or grocery receipts. Create a private, consented evaluation set containing multiple cities/vendors, thermal and laser print, English plus relevant Indian scripts, long receipts, poor photos, discounts, GST components, and handwritten marks if that is in scope. Store hashes/annotations separately from production receipt data and do not commit personal receipts.

### Metrics

Record each engine/model/preprocessing version and measure:

- all-text character error rate and word error rate;
- detected text-line precision/recall and box overlap;
- merchant/date/total/tax normalized exact match;
- line-item precision/recall, quantity accuracy, and amount accuracy;
- arithmetic reconciliation rate and **silent wrong-total rate**;
- manual-review rate, rejected-image rate, and missing-line rate;
- warm and cold latency p50/p95, peak memory, CPU time, model download/cache size, and concurrent behavior on the actual free deployment target.

For money, an incorrect total or line amount is more severe than a misspelled merchant name. Select the engine with the best risk-weighted result, not the best average OCR score. A candidate that is fast but silently changes ₹1,520 to ₹1,250 fails the gate.

### Proposed quality gate

Do not promote an engine until the benchmark report shows, on the ReceiptSplit corpus:

- no silent arithmetic mismatch reaches confirmation without a visible warning/review state;
- every extracted amount has a source token/line or is manually entered;
- every engine failure is bounded and recoverable to manual entry;
- p95 warm latency and memory fit the chosen browser/server target;
- security tests pass for authorization, upload validation, retention, redaction, and log safety.

Exact numeric accuracy thresholds should be agreed after the first corpus is annotated; publishing a made-up percentage now would be false precision.

## Custom OCR last-resort path

Only start custom training if the benchmark identifies a repeatable failure that open engines cannot address through language selection, preprocessing, or parser rules:

1. Define the failure class: a script, dot-matrix font, vendor layout, or camera condition—not “OCR is sometimes wrong.”
2. Gather permissioned images and annotate text polygons/transcriptions plus receipt entities. Keep training data separate from live room data.
3. First fine-tune an open detector/recognizer or train only the receipt semantic parser. A custom parser is usually cheaper and safer than a new OCR engine.
4. Keep a held-out vendor/time split to detect overfitting to one receipt template.
5. Ship model/version provenance, rollback, latency/memory limits, and a review fallback. Never make the custom model the sole authority for money.

## Decision status

| Decision | Status | Evidence |
|---|---|---|
| Keep provider boundary and editable draft/confirm flow | **Verified in repo** | Existing OCR architecture, API, parser, frontend review UI, and tests |
| Keep Tesseract as local fallback | **Implemented, benchmark pending** | Mature Apache project, local operation, TSV-derived tokens/confidence, cancellation cleanup; receipt quality still needs benchmarking |
| Add PaddleOCR as accuracy candidate | **Recommended, backend provider pending** | Current project/docs expose detection, recognition, boxes, confidence, lightweight model tiers, and Apache project license; local receipt benchmark is still pending |
| Use PaddleOCR.js for public free path | **Implemented, default off** | Pinned `@paddleocr/paddleocr-js@0.4.2` runs PP-OCRv5 in a worker, sends a bounded candidate through the existing creator-authorized upload, and falls back to the server provider; browser latency and receipt accuracy still need measurement |
| Use cloud OCR free tiers | **Rejected for now** | Data leaves the system and current services have paid pricing/quotas; not compatible with the free-only boundary |
| Train custom OCR | **Deferred** | No ReceiptSplit-specific benchmark has proved open engines insufficient |

## Primary sources

- [Tesseract quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), [Tesseract command-line/TSV/hOCR output](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), and [Tesseract repository/license](https://github.com/tesseract-ocr/tesseract)
- [PaddleOCR repository and current release notes](https://github.com/PaddlePaddle/PaddleOCR), [PP-OCRv6 model/language notes](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv6/PP-OCRv6.md), [PP-StructureV3](https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/pipeline_usage/PP-StructureV3.html), and [PaddleOCR.js package](https://www.npmjs.com/package/@paddleocr/paddleocr-js)
- [RapidOCR repository](https://github.com/RapidAI/RapidOCR), [EasyOCR repository](https://github.com/JaidedAI/EasyOCR), and [docTR repository](https://github.com/mindee/doctr)
- [ICDAR/SROIE receipt OCR and information-extraction benchmark](https://arxiv.org/abs/2103.10213) and [CORD post-OCR receipt parsing dataset](https://mlanthology.org/neuripsw/2019/park2019neuripsw-cord/)
- [Amazon Textract AnalyzeExpense](https://docs.aws.amazon.com/textract/latest/dg/analyzing-document-expense.html), [Google Document AI processor list](https://docs.cloud.google.com/document-ai/docs/processors-list), [Google Document AI pricing](https://cloud.google.com/products/document-ai/pricing), [Azure receipt model](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/receipt), and [Mindee Receipt model](https://docs.mindee.com/use-cases/extraction-models/receipt)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html), [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html), and [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [Render Free deployment limitations](https://render.com/docs/free) and [Render persistent disks](https://render.com/docs/disks)
