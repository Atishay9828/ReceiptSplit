# Website UX Notes: Build Journey

## Purpose

`frontend/components/build-journey.tsx` tells the ReceiptSplit story as a sequence of product
decisions, not a resume-style skill cloud. The six stages are tied to milestone evidence:

1. M004: integer-paise split correctness and property testing.
2. M009: durable events and recoverable realtime collaboration.
3. M011.1: provider-based OCR with an editable review step.
4. M012: server-owned UPI requests and manual settlement status.
5. M014.1: real-flow repairs discovered during pilot use.
6. M015.1: explicit room states, adjustment ownership, completion UX, and visual clarity.

The first-person framing is intentional: it shows how AJ's decisions changed as the product met
harder constraints. The signature treatment is a build receipt: chronological entries expand into
`Decision`, `What changed in me`, and `Build receipt` evidence.

## Recommended Placement

Place this section on a future marketing or project-story page after the product flow or live UI
proof and before a deeper architecture section. It should not interrupt `/create` or any room task;
the current `/` route redirects directly into that transactional flow.

Integration is intentionally separate from `page.tsx`:

```tsx
import { BuildJourney } from "@/components/build-journey";

export default function ProjectStoryPage() {
  return (
    <main>
      {/* Product thesis and working-flow proof */}
      <BuildJourney />
      {/* Architecture or repository evidence */}
    </main>
  );
}
```

The component accepts `id`, `className`, `stages`, `title`, and `intro` when a page needs a different
wrapper, anchor, or evidence set. Set a unique `id` if more than one journey appears on a page.

## Interaction

- Each stage uses native `<details>` and `<summary>` elements. It works without a client component,
  hydration, or custom JavaScript.
- The first receipt is open on initial render so the interaction is self-explanatory. Other receipts
  remain independently expandable; reading one never collapses another unexpectedly.
- The collapsed row still carries the milestone, decision title, and outcome. Expansion adds the
  trade-off, learning, and evidence instead of hiding the entire story.
- The whole summary row is the target, not the small plus mark.

## Mobile Behavior

- Below 736px, the header and receipt details become one column.
- Below 448px, the rail, type, and spacing tighten while the disclosure target remains at least
  44px tall.
- Outcome copy stays visible when collapsed and wraps naturally; no horizontal scrolling or swipe
  interaction is required.
- The component uses the existing theme variables, so both light and dark modes remain readable.

## Accessibility

- A labelled `<section>`, ordered list, native disclosures, and real headings preserve a meaningful
  reading order.
- Native summaries are keyboard and touch operable. The component adds a high-contrast
  `:focus-visible` outline without replacing browser semantics.
- Color distinguishes stages but never carries meaning alone; every stage has a milestone and phase
  label.
- Motion is limited to a short reveal and plus rotation. Both are removed under
  `prefers-reduced-motion: reduce`.
- All payment language stays coordinator-safe: `marked paid`, `payer confirmed`, and `disputed`.
  The section does not claim that ReceiptSplit processes or verifies transfers.
