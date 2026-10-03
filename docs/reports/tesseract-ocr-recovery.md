# ReceiptSplit Tesseract OCR recovery

## Current release status

**The local release gate passed, and backend commit `0045e0c117a67b55023ceff868755d4f84a431dd` is live on Render.** Blueprint deployment `dep-db0hqclg1s2s73e5c9hg` completed successfully. `/health` reports that exact commit, `tesseract`, and OCR readiness `true`; unauthenticated `GET /api/groups` returns 403. The tested frontend handoff is local at commit `127c18ec7cd49cfbd244b7737d40f2e612ced08e` and has not yet been published. The live authenticated OCR acceptance remains.

Production preflight on 2026-10-03 confirmed Render service `srv-d9f40kbbc2fs7392qba0` (`receiptsplit-api`) tracks `feat/split-engine` in the `free` plan and Singapore region. The runtime is now **Docker**, using `backend/Dockerfile` with context `backend/`, and auto-deploy is **off**. Blueprint deployment `dep-db0hqclg1s2s73e5c9hg` for commit `0045e0c117a67b55023ceff868755d4f84a431dd` is `live`; the health response includes the exact commit, `tesseract`, and `ocr_ready: true`. Unauthenticated `GET /api/groups` returns 403. The existing Vercel project `receiptsplit-web` tracks `feat/split-engine`; deployment `dpl_6H2tGKs3hC3uUKqsc6iU6ERdC8Ng` for commit `0045e0c117a67b55023ceff868755d4f84a431dd` is `READY`, but does not contain the receipt-review frontend handoff.

Render's authenticated MCP access permits service inspection but does not expose a runtime update operation. The service is managed by Blueprint `exs-d9f3svfavr4c73c403h0`; its existing `render.yaml` was synced to apply Docker with auto-deploy off. No production environment variables or database contents were changed during the sync.

The production Supabase database was not used for local testing. The earlier API delay coincided with Supabase being resumed and is not evidence of an OCR or database defect.

## Frozen local configuration

- Container base: `python:3.12-slim-bookworm`, pinned digest `sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3`.
- OCR engine: Tesseract 5.3.0, English language data 4.1.0, `eng`, PSM 4.
- Image preparation: `receipt-binarize-v1` applies EXIF orientation, alpha flattening, bounded page crop when a clear dark border is detected, 2x upscaling within the image limit, grayscale/autocontrast, threshold 190, and metadata stripping.
- API: one Uvicorn worker, one active Tesseract process, 30-second provider timeout, `OMP_THREAD_LIMIT=1`.
- `RECEIPTSPLIT_OCR_STORE_RAW_TEXT=false`; browser OCR remains disabled.
- Local PostgreSQL ran in Compose with its existing persistent volume. Local migrations completed successfully.
- Final immutable image: `sha256:f0b5b964afc4792a585c306b748989a7ed2a99299565addf8e501a318782212b`, 191,309,084 bytes. It reports Tesseract 5.3.0 and languages `eng` and `osd`.
- A constrained run used the exact image with Docker limited to 0.1 CPU and 512 MiB RAM. All 13 corpus cases completed, peak sampled memory was 93.96 MiB, and the container exited 0 without OOM. This is below Render Free's documented 512 MiB limit ([compute plans](https://render.com/docs/compute-plans)).

## Independent corpus results

Synthetic receipt values were authored before rendering the fixture images; expected JSON is independent of OCR and parser output.

The pinned image's real Tesseract provider and parser passed:

| Corpus | Result |
|---|---|
| Seven clear synthetic receipts, including GST, discount/rounding, quantity × unit price, footer noise, and spacing | 7/7 exact |
| Existing Sample Restaurant photograph | Exact: four items, quantities 1/2/1/2, subtotal ₹750.00, tax ₹37.50, total ₹787.50 |
| Existing Riverside Bistro photograph | Exact: nine items, subtotal ₹135.50, tax ₹13.59, service charge ₹24.39, total ₹173.48 |
| Rotated, low-contrast, blurred, and cropped-total variants | 4/4 exact or visibly marked for review |

The rotated receipt has a bad inferred quantity and the cropped image yields a partial total; both are explicitly flagged for review instead of being accepted as correct. Low-contrast and blurred inputs recover the monetary fields and item totals but still carry a review warning. These tests do not claim support for all receipt layouts or currencies.

The selected PSM 4 configuration follows the measured corpus comparison. A trailing split-decimal repair uses Tesseract TSV geometry only when the final two-digit token is on the same line and within a small bounding-box gap; it fixes the actual Sample Restaurant `787.50` split without joining arbitrary nearby tokens.

## Review and money handling

- Items, quantities, and printed line totals remain editable. Tax, service charges, discounts, and signed rounding are separate adjustment rows.
- All calculations use integer paise. Service charges do not become tax. CGST/SGST components are deduplicated against an aggregate tax summary.
- Percentage-only amounts are never treated as rupees. Inconsistent quantity arithmetic and missing totals remain visible for review.
- The draft response carries the calculated total, exact difference, and a fingerprint over reviewed values. A mismatched or missing receipt total requires an explicit current-fingerprint acknowledgment; stale acknowledgments conflict.
- The receipt total remains unchanged and is retained for audit. The split uses reviewed items and signed adjustments. Override audit data contains the expected/calculated amounts, difference, and actor, not receipt text.
- The equal-split adjustment allocator rotates paise remainders across components while conserving each tax/charge amount, preventing all fractional components from unfairly landing on one participant.
- Confirmation locks the room row before the parsed draft, then saves items, adjustments, audit/event rows atomically. Repeated confirmation is safe; events publish after commit.
- A reset now clears the file input and releases the save state after cancellation, allowing the same image to be selected again.

## Local handoff and browser evidence

`backend/scripts/local_handoff_acceptance.py` exercised the final immutable API image against local PostgreSQL. Every case uploaded through Tesseract, fetched and edited the persisted draft, confirmed it, read the bill as a second participant, previewed the split, locked it, and read back the locked session:

- Sample receipt: ₹787.50; equal split ₹393.75 each.
- Riverside Bistro: ₹173.48, tax and service charge kept separate; equal shares ₹86.74 each.
- Discount and positive rounding: ₹240.00 − ₹20.00 + ₹0.50 = ₹220.50.
- Negative rounding: reviewed bill ₹219.50; locked total matches.
- Three participants with a one-paise remainder: ₹787.51 conserved exactly.
- Explicit override: printed ₹787.50 retained; acknowledged reviewed/locked total ₹786.50.
- Second-participant summary matched the creator's confirmed items and adjustments in each case.

The integrated browser automation used the real local frontend, API, PostgreSQL, and Tesseract. On desktop, the photo produced the expected editable draft; Save Draft completed, confirmation added all four items, a second participant joined, the preview showed ₹393.75 per person, and Lock moved the room to its settling state. Reload preserved that state. At 390×844 mobile emulation, the receipt, total, both shares, and post-lock controls remained visible in the responsive layout.

The local Google sign-in screen is not configured, so the second test participant was joined through the development-only local API. No authentication route was bypassed. A temporary attempt to install `@playwright/test` failed because npm registry TLS connections reset; no package or lockfile change was kept. Browser acceptance itself used the available browser Playwright interface against the real local stack rather than mocked uploads.

## Verification

| Check | Result |
|---|---|
| Backend full pytest suite, including PostgreSQL-backed, authorization, override, and concurrency coverage | Passed |
| Backend Ruff and focused mypy over OCR, split, OCR API, and acceptance scripts | Passed; 22 source files checked by mypy |
| Frontend Vitest | 85/85 passed |
| Frontend TypeScript check and ESLint | Passed |
| Frontend production build after the reset/file-input fix | Passed |
| Immutable image Tesseract corpus | 13/13 clear, real-photo, and degraded outcomes accepted |
| Immutable image API → local PostgreSQL → review → confirm → participant read → preview → lock → reload | 7/7 passed |
| Real browser desktop flow through saved draft, confirmation, second participant, split lock, and reload | Passed |
| Real browser 390×844 mobile locked-room check | Passed; both ₹393.75 shares and the locked controls remained visible |
| Render Docker Blueprint paths | Validated: `rootDir: backend`, `dockerfilePath: ./Dockerfile`, `dockerContext: .` |
| Live Docker deployment `0045e0c` and health/readiness check | Passed; deploy `dep-db0hqclg1s2s73e5c9hg` is live |
| Live protected route check | Passed; unauthenticated `GET /api/groups` returned 403 |
| Live authenticated OCR | Not performed |

## Deployment checklist

1. Local release gate is complete: frontend production build passed, and constrained-image Tesseract processing peaked at 93.96 MiB on the 0.1-CPU/512-MiB test container.
2. Render service identity, Docker runtime, free plan, Singapore region, auto-deploy off, exact backend commit, Tesseract readiness, and route protection are verified.
3. Publish the verified frontend handoff and report changes to the existing `feat/split-engine` production branch. Keep Render auto-deploy disabled; the exact-commit workflow is the deployment trigger.
4. Verify that Render reports the requested frontend handoff commit as `live` using the Render integration, `/health` reports that exact commit with Tesseract ready, and protected API paths still reject unauthenticated requests. The GitHub workflow checks the running commit, readiness, and protected-route response without requiring a separate Render API-key secret.
5. Deploy the compatible frontend. With AJ's authorized live session, run one synthetic live receipt through OCR, review, confirmation, preview, lock, reload, and second-participant view. Leave that step pending if sign-in requires AJ's interaction.
6. If live acceptance fails, restore the recorded backend runtime/configuration/commit and compatible frontend; do not reset production data.
