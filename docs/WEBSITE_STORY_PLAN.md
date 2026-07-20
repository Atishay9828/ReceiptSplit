# ReceiptSplit Website Story Plan

## Implemented Route

The engineering story is implemented at `/build`. The existing `/` route remains the product-facing
front door, with a prominent link into the deeper first-person build story. This keeps the working
product flow concise while giving engineering reviewers the proof-led narrative below.

## Recommendation

Build this as a product-first engineering story, not a milestone timeline and not a generic stack
portfolio. The page should open on the recognizable receipt problem, prove that a working system
exists, then reveal the engineering lessons underneath it.

The page thesis is:

> The hard part was not splitting a bill. It was designing a trustworthy shared workflow around
> exact money, uncertain OCR, recoverable realtime state, and a payment handoff the product does not
> pretend to verify.

The canonical implementation copy lives in `frontend/lib/website-content.ts`. This plan explains
the content hierarchy, evidence bar, and intended rendering.

## Audience

### Primary

Software engineering recruiters and hiring managers. Their first question is not "which framework
did AJ use?" It is whether AJ can turn a familiar problem into a correct, secure, understandable
system and explain the tradeoffs.

### Secondary

- Product-minded engineers who want architecture, failure modes, and source evidence.
- Early-stage founders who want to see scope control and product judgment.

### Not the target

This is not currently a conversion page for restaurant users. There is no verified public
deployment or real-device UPI proof to support "start splitting now" acquisition copy.

## Voice

- First person for lessons and decisions: `I built`, `I changed`, `I learned`.
- Product-first language before framework names.
- Concrete nouns and verbs; no broad `AI engineer / full-stack / systems thinker` identity claims.
- Confident about proven artifacts, precise about mocked or deferred proof.
- Coordinator-safe payment language only: `marked paid`, `payer confirmed`, and `disputed`.

## Narrative Arc And Proof Order

1. **Hero: the trust problem.** One strong thesis, one product sentence, and the coordinator-only
   boundary.
2. **Fast proof strip.** Four compact artifacts: integer-paise math, editable OCR, durable events,
   and manual payer confirmation.
3. **Problem reframe.** Explain why a shared receipt is more than arithmetic.
4. **Product flow.** Show the six-state receipt artifact moving from capture to confirmation.
5. **What I learned.** Six decision-led themes, each paired with a source/test/visual artifact.
6. **Build evidence.** Separate DB-backed flow proof, mocked visual proof, and known limits in a
   short lower-page block.
7. **Takeaway and CTA.** End on engineering growth, with source as the conversion target.

This order gives a recruiter a usable story in the first screen and lets an engineer go deeper
without forcing either audience through milestone history.

## Exact Public Copy

### Hero

- Eyebrow: `ReceiptSplit / Built end to end`
- Headline: `The hard part wasn't splitting the bill. It was designing trust.`
- Summary: `I built ReceiptSplit around a familiar restaurant problem: turn one receipt into fair,
  claimable shares and a clear UPI handoff - without asking the group to install an app or trust a
  new payment intermediary.`
- Boundary: `ReceiptSplit coordinates the flow. It does not process or verify payments.`
- Primary CTA: `Explore the decisions`
- Secondary CTA: `View the repository`

### Proof Strip

| Value | Label | Supporting line |
|---|---|---|
| `Integer paise` | `Money stays exact` | `No floats in the calculation path; every remainder has a deterministic owner.` |
| `Editable draft` | `OCR asks for review` | `Receipt scanning saves typing, but only a creator can confirm the parsed result.` |
| `Durable events` | `Realtime can recover` | `The database owns room history; SSE tells clients when to refetch it.` |
| `Manual confirmation` | `Payment claims stay honest` | `Participants mark paid; the payer confirms or disputes. The app never invents bank evidence.` |

### Problem Reframe

- Eyebrow: `A deceptively small problem`
- Headline: `A receipt is shared state, money math, and human trust in one photo.`
- Body 1: `People do not split clean database rows. They share dishes, change claims, lose network,
  misread receipts, and pay through another app.`
- Body 2: `I kept the system a modular monolith and made the rules explicit: one durable source of
  truth, server-owned money, recoverable clients, and manual confirmation where the product has no
  bank evidence.`
- Pull quote: `The architecture came from the failure modes, not from the framework list.`

### Product Flow

- Eyebrow: `The working loop`
- Headline: `From receipt to payer-confirmed share`
- Intro: `One room moves through six explicit states instead of hiding the handoffs.`

| Step | Copy |
|---|---|
| Capture | `Add items manually or scan a receipt into an editable draft.` |
| Claim | `Friends join by link and claim the item quantities they shared.` |
| Calculate | `The server allocates discounts, taxes, fees, and remainder paise deterministically.` |
| Lock | `The room freezes a split snapshot before settlement requests are prepared.` |
| Coordinate | `Each participant opens a server-generated UPI intent or QR, then marks paid.` |
| Confirm | `The payer confirms or disputes manually while durable events keep every view in sync.` |

### Learning Section Intro

- Eyebrow: `What building it changed`
- Headline: `Six lessons I would carry into the next product.`
- Intro: `The useful part of this project was not the stack. It was learning where correctness
  belongs - and where confidence has to stop.`

### Learning 01: Money Correctness

- Headline: `Financial math needs invariants, not formatting.`
- Principle: `Store paise. Conserve totals. Make remainders deterministic.`
- Story: `A property test found that normal round-half-up could push the payer below zero. I
  changed the policy, derived the payer as the residual, and made conservation a post-condition of
  every result.`
- Tradeoff: `Floor rounding is intentionally asymmetric: non-payers pay whole-rupee floors and the
  payer absorbs the residual.`

### Learning 02: OCR And AI

- Headline: `Useful automation should lower effort without pretending certainty.`
- Principle: `Generate a draft, expose uncertainty, and keep the human in control.`
- Story: `OCR output never becomes bill state directly. It is validated, redacted, parsed into an
  editable draft, and only converted into items after the creator reviews it.`
- Tradeoff: `Local Tesseract keeps the default free and private, but advanced preprocessing and
  worker-backed jobs remain deliberate follow-ups.`

### Learning 03: Realtime Systems

- Headline: `Realtime is a delivery path, not the source of truth.`
- Principle: `Commit first, broadcast second, and always leave a replay path.`
- Story: `Room events are written inside the transaction and broadcast only after commit. Clients
  subscribe, replay missed sequence numbers, deduplicate, and refetch durable state.`
- Tradeoff: `The broker is intentionally in-process. Horizontal scale would need shared pub/sub,
  but the durable log already defines the recovery model.`

### Learning 04: Product Scope

- Headline: `The safest payment feature was the one I refused to build.`
- Principle: `Coordinate the handoff; never claim evidence the system does not have.`
- Story: `The server owns the amount, VPA, reference, and UPI payload. A participant can mark paid,
  but only the payer can confirm or dispute. ReceiptSplit never treats that as bank verification.`
- Tradeoff: `Manual confirmation is less magical than gateway automation, but it is honest, cheap,
  and appropriate for this MVP.`

### Learning 05: Security Design

- Headline: `Security got clearer when I named the assets and abuse paths.`
- Principle: `Separate identities, hash capabilities, limit expensive actions, and audit safely.`
- Story: `Account JWTs and room capability tokens stay separate. OCR upload, room access, and
  settlement actions have scoped authorization, rate limits, and audit events that exclude raw
  credentials and receipt text.`
- Tradeoff: `The current limiter is single-process. Distributed enforcement belongs before
  multi-instance deployment, not before product evidence exists.`

### Learning 06: Product Engineering

- Headline: `Polish starts when the interface mirrors the real workflow.`
- Principle: `Show one current step, one next action, and honest status language.`
- Story: `Manual browser runs exposed failures that component work missed: a blocked settlement
  request, confusing locked states, quantity-claim gaps, and a weak completion state. The interface
  now follows draft, claiming, locked, settling, and settled views.`
- Tradeoff: `Demo screenshots prove rendering and local flow behavior. They do not prove
  real-device UPI handoff or production readiness.`

### Evidence And Limits

- Eyebrow: `Build evidence`
- Headline: `Claims stay attached to the artifact that earns them.`
- Intro: `The repository keeps source, tests, architecture notes, and demo screenshots together -
  and labels the limits of each.`
- Validated: `The backend suite and frontend lint, typecheck, tests, and production build passed at
  the latest flow-repair closeout.`
- Browser proof: `A DB-backed demo covered create, join, claim, lock, UPI handoff, marked paid, and
  payer confirmation with fake data.`
- Mocked proof: `The newest dark-mode and completion screenshots prove UI states with demo
  responses, not live database or bank behavior.`
- Still to prove: `Real-device UPI behavior, distributed rate limiting, committed browser E2E, and
  the current Next/PostCSS advisory remain follow-up work.`

### Close

- Eyebrow: `The takeaway`
- Headline: `I learned to make the system honest before making it feel smart.`
- Body: `ReceiptSplit made me better at turning a messy real-world workflow into explicit domain
  rules, recoverable collaboration, and a product boundary users can understand.`
- Primary CTA: `Review the source`
- Secondary CTA: `Revisit the system flow`

## Claims And Evidence Map

| Claim | Evidence | Public scope |
|---|---|---|
| Money uses integer paise | `backend/app/split/*`, `docs/architecture/split-engine.md` | Calculation and storage paths; rupee strings only at display/UPI boundaries. |
| Rounding is deterministic | `backend/app/split/rounding.py`, `backend/tests/split/test_property_based.py` | Explicit floor-and-residual policy, not a claim of universal fairness. |
| OCR is editable and human-confirmed | `docs/architecture/ocr.md`, `backend/app/ocr/service.py`, M011.1 review screenshot | Tested local OCR flow; not a receipt-accuracy benchmark. |
| OCR is provider-based | `backend/app/ocr/contracts.py`, `backend/app/ocr/providers.py` | Mock and local Tesseract providers exist; paid/cloud providers are deferred. |
| Room events are durable and replayable | `docs/architecture/events.md`, event repository/API tests | Current DB log plus SSE transport; broker is not horizontally distributed. |
| Settlement fields are server-owned | `backend/app/services/settlement_service.py`, settlement API tests | Amount, VPA, name, reference, and UPI payload are not trusted from participant clients. |
| Payment status is manual | `docs/architecture/settlement.md`, M012 screenshots/tests | `marked paid`, `payer confirmed`, `disputed`; never bank-verified. |
| Auth identities are separated | `docs/architecture/auth.md`, auth API tests | Account JWT and room capability scopes are distinct. Production OIDC/JWKS remains deferred. |
| Abuse controls exist | `docs/architecture/security.md`, `test_m013_security.py` | MVP in-process rate limits and safe audit events; not distributed fraud prevention. |
| The full room flow was exercised | M014 milestone report and screenshots | Local DB-backed demo data, not production traffic or a public deployment. |
| Latest visual states were exercised | M015.1 screenshots and frontend tests | Mocked/demo API state proves rendering, not DB, UPI app, or bank behavior. |
| Current validation passed | `docs/ACTIVE_CONTEXT.md`, M015.1 report | Full backend suite and frontend checks at closeout; repo-wide strict mypy remains known-red. |

## Visual Pairing

- **Hero receipt artifact:** use a stylized receipt that reveals the six flow states. It should be
  a narrative device, not a fake transaction record.
- **Money learning:** show paise allocation/remainder movement as a small deterministic diagram.
- **OCR learning:** use `docs/reports/screenshots/M011.1/ocr-draft-review.png` or a cropped/redrawn
  representation of the edit-before-confirm interaction.
- **Realtime learning:** use a compact `commit -> durable event -> notify -> refetch/replay` flow.
- **Payment-boundary learning:** pair participant UPI handoff with creator confirmation, never a
  green bank-success animation.
- **UX learning:** use the room-state progression and the final mobile settled state.

Screenshots currently live under `docs/`, not `frontend/public/`. An integration pass should copy
only chosen demo-safe assets into a public asset folder after privacy review. Do not render raw
repository paths as public URLs.

## CTA Strategy

- Hero primary CTA scrolls to the decision/learning section.
- Hero secondary CTA opens the verified GitHub repository.
- The closing CTA returns to source, because source is the strongest conversion proof currently
  available.
- Do not add `Try it live`, `Start splitting`, or app-store CTAs until a public deployment and
  real-device UPI behavior are verified.

## Integration Contract

`frontend/lib/website-content.ts` exports:

- `receiptSplitWebsiteContent`: the canonical story content.
- `WebsiteContent` and supporting types for page/component props.
- Evidence references with repository paths and proof state.
- Visual candidates labeled as `verified-demo` or `mocked-demo`.

The page implementation should consume this data rather than retyping copy into JSX. Evidence
metadata may drive build-note labels, but repository paths should not be shown in the main story.

## Guardrails

- Do not turn the page into a chronological M001-M015 report.
- Do not lead with FastAPI, Next.js, PostgreSQL, or a skills cloud.
- Do not call the product a wallet, gateway, escrow service, payment processor, or verification
  system.
- Do not use bank-success language or imply bank/UPI provider integrations.
- Do not present mocked screenshots as end-to-end proof.
- Do not call the project production-ready while real-device UPI, distributed limiting, committed
  E2E, dependency advisory, and strict typing follow-ups remain.
- Do not publish screenshots containing real receipts, real UPI IDs, raw tokens, invite links, or
  personal data.
