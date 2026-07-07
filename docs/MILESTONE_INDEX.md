# ReceiptSplit Milestone Index

## Current Status Summary

- Current active milestone: M012 UPI Settlement MVP.
- Last full pass: M011.1 OCR Frontend Review UI, commit `2985a40`.
- Current blocker: M012 needs DB-backed API tests, full validation, browser smoke, screenshots, and
  commit.
- Default context: read `docs/ACTIVE_CONTEXT.md`, this file, `task.md`, and current git status/diff.

## Milestones

| Milestone | Status | Key Commit(s) | Evidence / Notes |
|---|---|---|---|
| M001 Foundation | PASS | `5d49d42`, historical | `docs/archive/milestones/M001-foundation.md` |
| M002 Database | PASS | historical | `docs/archive/milestones/M002-database.md` |
| M003 Domain | PASS | historical | `docs/archive/milestones/M003-domain.md` |
| M004 Split Engine | PASS | historical | `docs/archive/milestones/M004-split-engine.md` |
| M005 Repository Layer | PASS | `29a3503`, `50780b5` | `docs/archive/milestones/M005-repositories.md` |
| M006 Service Layer | PASS | `afb3b2d`; DB-5 fix `02a8ce3` | `docs/archive/milestones/M006-services.md` |
| M007 API Layer | PASS | `e39d46e` | `docs/archive/milestones/M007-api-layer.md` |
| M007.5 Critical/High Hardening | PASS | `f830c50` | `docs/archive/milestones/M007.5-architecture-hardening.md` |
| M007.6 Medium/Low Hardening | PASS | `ce35066` | `docs/archive/milestones/M007.6-medium-low-hardening.md` |
| M008 Auth/OIDC | PASS | `fc4f42d`, `e51ae6e` | `docs/archive/milestones/M008-auth-oidc.md` |
| M009 Realtime/Event Sync | PASS | `3ed4074` | `docs/archive/milestones/M009-realtime-event-sync.md`; durable `room_events` |
| M010 Frontend MVP | PASS | `2d5a19c` | `docs/archive/milestones/M010-frontend-mvp.md` |
| M010.1 Preview Readiness Cleanup | PASS | `82cc32c` | `docs/archive/milestones/M010.1-preview-readiness-cleanup.md`; screenshot note under `docs/reports/screenshots/M010/` |
| M011 Backend OCR MVP | PASS history, backend implemented | `7216e0f` | `docs/archive/milestones/M011-ocr-mvp.md`; M011.1 upgraded the flow to full browser evidence |
| M011.1 OCR Frontend Review UI | FULL PASS | `e0d6dc4`, `2985a40` | screenshots under `docs/reports/screenshots/M011.1/` |
| M012 UPI Settlement MVP | CONDITIONAL PASS | none yet | `docs/archive/milestones/M012-upi-settlement.md`; needs API tests, browser smoke, screenshots, commit |

## Deferred Baselines

- Full backend mypy baseline remains red at about 382/383 errors in 30/31 files depending
  checkpoint.
- `npm audit` has a known moderate Next/PostCSS advisory chain (`GHSA-qx2v-qp2m-jg93`) or registry
  access blocker depending environment.
- Browser E2E harness remains deferred.
- M012 DB-backed integration tests and browser smoke depend on local Docker/Postgres access.

## Archive Location

Historical milestone reports:

```text
docs/archive/milestones/
```

Archived reports are evidence. Do not load them into default working context unless investigating a
specific milestone.
