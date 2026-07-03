# M010 Frontend MVP Task

## Status

M010 PASS.

M010.1 CONDITIONAL PASS for code and automated validation; final manual browser evidence remains
blocked by local Docker/Postgres and npm audit network escalation quota.

## Scope Completed

- Next.js mobile-first frontend scaffold.
- Creator room creation with legacy capability token storage.
- Manual receipt item add/edit/delete flow.
- Invite link, QR, copy, and WhatsApp share flow.
- Participant nickname join flow.
- Participant claim/unclaim flow.
- Split preview and lock/unlock controls.
- M010.1 preview readiness gate before split preview calls.
- Friendly incomplete split preview state.
- Creator Lock disabled until preview is valid.
- Fetch-based SSE event sync using M009 endpoints.
- Minimal backend room summary read endpoint for frontend refresh.
- Frontend architecture and M010 report docs.

## Validation

- Backend pytest passed with Docker access and three skipped tests.
- Backend Ruff passed.
- Full backend mypy remains at the known baseline.
- Frontend lint, typecheck, tests, and build passed.
- M010.1 frontend lint, typecheck, tests, and build passed after preview readiness cleanup.
- M010.1 fresh `npm.cmd audit --json` and manual browser screenshots are blocked until environment
  escalation quota is available.

## Deferred

- OCR/camera/upload.
- UPI settlement and payment verification.
- Wallet, escrow, refunds, cashback.
- Production auth UI.
- Native mobile app.
- Deployment.

## M011 OCR MVP Status

M011 backend OCR MVP is implemented as a free-first modular pipeline.

Completed:

- Modular OCR contracts, mock provider, and Tesseract provider.
- Image validation, magic-byte checks, dimension limits, and metadata stripping.
- Local private receipt image storage abstraction.
- OCR job/result/parsed-draft persistence tables and migration.
- Conservative Indian restaurant receipt parser with fixture coverage.
- Creator-only OCR upload, job, parsed draft, update, and confirm endpoints.
- Confirmation flow creates normal room items/adjustments and emits room events.
- OCR architecture and M011 report docs.

Validation:

- Focused OCR tests pass.
- Backend Ruff passes.
- Focused M011 mypy passes.
- Full backend pytest is blocked by Docker/Testcontainers named-pipe access in this environment.

Deferred:

- Frontend OCR UI.
- Worker-backed OCR processing.
- Advanced Pillow/OpenCV preprocessing.
- EasyOCR, PaddleOCR, Google Vision, and custom ML providers.
