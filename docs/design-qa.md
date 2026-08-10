# ReceiptSplit Design QA

Status: PASSED
Date: 2026-08-10

## Evidence Setup

- Browser: Chromium via Playwright.
- Capture mode: Next dev server on `http://localhost:3001`; production build verified separately.
- Data: synthetic demo rooms, names, amounts, invite tokens, and payment identifiers only.
- Reference images: `C:\Users\adish\.codex\attachments\bcfc0e25-a5cf-4e4b-b49d-81beda63da7c\image-1.png` and `image-2.png`.

## Requirement Matrix

| Route and state | Expected result | Evidence | Status |
| --- | --- | --- | --- |
| `/`, desktop 1440px | Editorial receipt-led entry, clear CTA, ledger preview, no gradients or decorative AI artwork | `docs/design-qa/screens/home-desktop.png` | PASS |
| `/`, mobile 390px | Headline wraps cleanly, receipt media remains readable, no horizontal overflow | `docs/design-qa/screens/home-mobile.png` | PASS |
| `/create`, desktop and mobile | Bordered bill setup surface, three-step rail, payment safety language | `docs/design-qa/screens/create-desktop.png`, `create-mobile.png` | PASS |
| `/dashboard`, authenticated demo, desktop and mobile | Persistent-room shell, metrics, room bill tables, friends and balance rails | `docs/design-qa/screens/dashboard-desktop.png`, `dashboard-mobile.png` | PASS |
| `/dashboard`, authenticated demo, pattern pass | Scroll-snap room switcher, budget summary cards, expandable activity event, breadcrumb | `docs/design-qa/screens/dashboard-patterns-desktop.png`, `dashboard-event-expanded.png`, `dashboard-patterns-mobile.png` | PASS |
| `/rooms/demo-room/creator`, desktop | Dense workbench with lifecycle rail, source receipt canvas, share controls, participant rail, safety rail | `docs/design-qa/screens/room-creator-desktop.png` | PASS |
| `/rooms/demo-room`, participant, mobile | Compact claim flow, item rows, share preview, pending state, safety action | `docs/design-qa/screens/room-participant-mobile.png` | PASS |
| `/rooms/demo-room`, community state pass | Shared room-state card shows participant progress without implying payment verification | `docs/design-qa/screens/room-community-desktop.png`, `room-community-mobile.png` | PASS |
| `/join/invalid-token`, desktop | Invalid invite state remains calm and actionable | `docs/design-qa/screens/join-invalid-desktop.png` | PASS |

## Browser Assertions

- Dashboard and room capture script reported `errors: []`.
- Participant mobile capture reported `bodyWidth: 390` and `viewport: 390`.
- Desktop and mobile captures were visually inspected for clipping, overlap, unreadable text, and empty layout rails.
- Receipt image rendered at the intended proof section size.
- Room switcher controls, expandable event card, budget cards, and community state card rendered at desktop and mobile widths.
- Community state copy preserves the payment boundary: participants can see progress, while only the payer confirms payment.
- Temporary server and browser artifacts were stopped/removed after capture.

## Iteration Log

- Replaced palette-only treatment with structural reference language: serif hierarchy, thin borders, compact app shell, lifecycle progress, workbench columns, ledger tables, and safety rails.
- Fixed mobile header spacing and hidden desktop-only account controls at narrow widths.
- Fixed room workbench side rails stretching through empty canvas.
- Kept OCR explicitly draft-only and settlement language limited to payer confirmation or marked-paid states.
- Updated stale homepage and dashboard test expectations to match the intentional UI contract.
- Added Watermelon-inspired room navigation, budget summaries, expandable activity, breadcrumb semantics, and an invite-aware sign-in swap surface using native details and CSS motion primitives.

## Checks

- `npm.cmd test -- --pool=threads --maxWorkers=1 --reporter=dot`: 20 files, 82 tests passed.
- `npm.cmd run typecheck -- --pretty false`: passed.
- `npm.cmd run lint`: passed.
- `npm.cmd run build`: passed.
- `git diff --check`: passed.

## Unverified States

- Production Google OAuth callback and live Supabase data were not used in visual captures.
- No deployment was performed in this pass; the captures use synthetic data and the local build.
- The full Google sign-in test suite still emits an existing async `act(...)` warning, but the test passes and no browser console errors were observed.
