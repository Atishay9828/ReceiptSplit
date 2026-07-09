# ReceiptSplit Milestone Index

## Current Status Summary

- Current active milestone: M015 Dark Mode + Pilot Readiness QA.
- Last full pass: M014.1 Real-World UX Bug Bash & Payment Flow Repair, commit `2e14478`.
- Current blocker: M015 audit, full backend pytest, and real-device UPI checks remain pending.
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
| M012 UPI Settlement MVP | FULL PASS | `8c39279`, `05456c0` | DB/API, backend, frontend validation, and browser evidence accepted before M013 per user confirmation on 2026-07-08 |
| M013 Security Hardening & Abuse Controls | FULL PASS | `44fede4` | rate limits, audit logs, abuse reports, noindex/security headers; `docs/architecture/security.md`; `docs/archive/milestones/M013-security-hardening.md` |
| M014 Frontend Experience & Pilot Polish | FULL PASS | `79f2041` | mobile-first polish, participant total/action clarity, creator next-step flow, settlement status colors, Tailwind v4 fix, production browser smoke; `docs/reports/screenshots/M014/`; `docs/archive/milestones/M014-frontend-experience-polish.md` |
| M014.1 Real-World UX Bug Bash & Payment Flow Repair | FULL PASS | `2e14478` | Participant removal, quantity claiming, payment status visibility, settlement auto-transition |
| M015 Dark Mode + Pilot Readiness QA | CONDITIONAL PASS | pending | Dark theme system, persisted toggle, pilot QA docs, mocked local browser screenshots; audit/backend/real-device UPI checks pending |

## Deferred Baselines

- Full backend mypy baseline remains known-red at about 382/383 errors in 30/31 files depending
  checkpoint.
- M013 `npm audit --json` recorded 2 moderate advisories, 0 high, 0 critical. The fix path suggests
  an unsafe Next downgrade, so no forced audit fix was run.
- M014 `npm audit --json` remains 2 moderate advisories, 0 high, 0 critical for
  `GHSA-qx2v-qp2m-jg93` via Next/PostCSS. The suggested fix is an unsafe Next downgrade, so no
  forced audit fix was run.
- M015 `npm audit --json` could not record advisory data because sandbox execution failed and
  escalation was rejected due dependency metadata egress to npm.
- M015 full backend pytest is blocked by Docker/Testcontainers named-pipe access in this
  environment.
- Browser E2E harness remains deferred, but M014 production smoke was executed with temporary
  Playwright/Edge automation. M015 captured mocked local browser UI screenshots with system Edge.

## Archive Location

Historical milestone reports:

```text
docs/archive/milestones/
```

Archived reports are evidence. Do not load them into default working context unless investigating a
specific milestone.
