export type StorySectionId =
  | "why-it-got-hard"
  | "system-flow"
  | "what-i-learned"
  | "build-evidence"
  | "takeaway";

export type EvidenceState =
  | "verified-source"
  | "verified-test"
  | "verified-browser"
  | "mocked-browser"
  | "known-limit";

export interface WebsiteLink {
  readonly label: string;
  readonly href: string;
  readonly external?: boolean;
  readonly ariaLabel?: string;
}

export interface EvidenceReference {
  readonly label: string;
  readonly repositoryPath: string;
  readonly supports: string;
  readonly state: EvidenceState;
}

export interface ProofPoint {
  readonly value: string;
  readonly label: string;
  readonly detail: string;
  readonly evidence: readonly EvidenceReference[];
}

export interface FlowStep {
  readonly number: string;
  readonly title: string;
  readonly body: string;
}

export interface StoryVisual {
  readonly repositoryPath: string;
  readonly alt: string;
  readonly caption: string;
  readonly evidenceState: "verified-demo" | "mocked-demo";
}

export interface LearningTheme {
  readonly id: string;
  readonly eyebrow: string;
  readonly title: string;
  readonly principle: string;
  readonly story: string;
  readonly tradeoff: string;
  readonly proof: readonly string[];
  readonly evidence: readonly EvidenceReference[];
  readonly visual?: StoryVisual;
}

export interface WebsiteContent {
  readonly meta: {
    readonly title: string;
    readonly description: string;
  };
  readonly audience: {
    readonly primary: string;
    readonly secondary: readonly string[];
    readonly visitorQuestion: string;
  };
  readonly hero: {
    readonly eyebrow: string;
    readonly title: string;
    readonly summary: string;
    readonly boundary: string;
    readonly ctas: readonly WebsiteLink[];
  };
  readonly proofStrip: readonly ProofPoint[];
  readonly problem: {
    readonly id: StorySectionId;
    readonly eyebrow: string;
    readonly title: string;
    readonly body: readonly string[];
    readonly takeaway: string;
  };
  readonly flow: {
    readonly id: StorySectionId;
    readonly eyebrow: string;
    readonly title: string;
    readonly intro: string;
    readonly steps: readonly FlowStep[];
  };
  readonly learnings: {
    readonly id: StorySectionId;
    readonly eyebrow: string;
    readonly title: string;
    readonly intro: string;
    readonly themes: readonly LearningTheme[];
  };
  readonly evidence: {
    readonly id: StorySectionId;
    readonly eyebrow: string;
    readonly title: string;
    readonly intro: string;
    readonly notes: readonly {
      readonly title: string;
      readonly body: string;
      readonly state: EvidenceState;
    }[];
  };
  readonly close: {
    readonly id: StorySectionId;
    readonly eyebrow: string;
    readonly title: string;
    readonly body: string;
    readonly ctas: readonly WebsiteLink[];
  };
}

export const receiptSplitWebsiteContent: WebsiteContent = {
  meta: {
    title: "ReceiptSplit - Engineering trust into a shared bill",
    description:
      "A build story about deterministic money, editable OCR, recoverable realtime state, and coordinator-safe UPI flows."
  },
  audience: {
    primary: "Software engineering recruiters and hiring managers",
    secondary: ["Product-minded engineers", "Early-stage founders"],
    visitorQuestion:
      "Can AJ turn a familiar problem into a correct, secure, understandable system and explain the tradeoffs?"
  },
  hero: {
    eyebrow: "ReceiptSplit / Built end to end",
    title: "The hard part wasn't splitting the bill. It was designing trust.",
    summary:
      "I built ReceiptSplit around a familiar restaurant problem: turn one receipt into fair, claimable shares and a clear UPI handoff - without asking the group to install an app or trust a new payment intermediary.",
    boundary: "ReceiptSplit coordinates the flow. It does not process or verify payments.",
    ctas: [
      { label: "Explore the decisions", href: "#what-i-learned" },
      {
        label: "View the repository",
        href: "https://github.com/Atishay9828/ReceiptSplit",
        external: true,
        ariaLabel: "View the ReceiptSplit source repository on GitHub"
      }
    ]
  },
  proofStrip: [
    {
      value: "Integer paise",
      label: "Money stays exact",
      detail: "No floats in the calculation path; every remainder has a deterministic owner.",
      evidence: [
        {
          label: "Split engine architecture",
          repositoryPath: "docs/architecture/split-engine.md",
          supports: "Integer-paise storage and deterministic allocation policy.",
          state: "verified-source"
        },
        {
          label: "Split engine tests",
          repositoryPath: "backend/tests/split/test_property_based.py",
          supports: "Randomized conservation, non-negative total, and determinism checks.",
          state: "verified-test"
        }
      ]
    },
    {
      value: "Editable draft",
      label: "OCR asks for review",
      detail: "Receipt scanning saves typing, but only a creator can confirm the parsed result.",
      evidence: [
        {
          label: "OCR architecture",
          repositoryPath: "docs/architecture/ocr.md",
          supports: "Provider-based OCR pipeline with editable drafts and explicit confirmation.",
          state: "verified-source"
        },
        {
          label: "OCR review screenshot",
          repositoryPath: "docs/reports/screenshots/M011.1/ocr-draft-review.png",
          supports: "The review-and-correct step is visible in a tested local flow.",
          state: "verified-browser"
        }
      ]
    },
    {
      value: "Durable events",
      label: "Realtime can recover",
      detail: "The database owns room history; SSE tells clients when to refetch it.",
      evidence: [
        {
          label: "Event synchronization architecture",
          repositoryPath: "docs/architecture/events.md",
          supports: "Durability-first room events, replay, ordering, and post-commit broadcast.",
          state: "verified-source"
        },
        {
          label: "Event API tests",
          repositoryPath: "backend/tests/api/test_events_api.py",
          supports: "Replay, stream, authorization, and missed-event recovery behavior.",
          state: "verified-test"
        }
      ]
    },
    {
      value: "Manual confirmation",
      label: "Payment claims stay honest",
      detail: "Participants mark paid; the payer confirms or disputes. The app never invents bank evidence.",
      evidence: [
        {
          label: "Settlement architecture",
          repositoryPath: "docs/architecture/settlement.md",
          supports: "Coordinator-only boundary and server-owned settlement requests.",
          state: "verified-source"
        },
        {
          label: "Settlement API tests",
          repositoryPath: "backend/tests/api/test_settlement.py",
          supports: "Authorized status transitions and server-owned payment fields.",
          state: "verified-test"
        }
      ]
    }
  ],
  problem: {
    id: "why-it-got-hard",
    eyebrow: "A deceptively small problem",
    title: "A receipt is shared state, money math, and human trust in one photo.",
    body: [
      "People do not split clean database rows. They share dishes, change claims, lose network, misread receipts, and pay through another app.",
      "I kept the system a modular monolith and made the rules explicit: one durable source of truth, server-owned money, recoverable clients, and manual confirmation where the product has no bank evidence."
    ],
    takeaway: "The architecture came from the failure modes, not from the framework list."
  },
  flow: {
    id: "system-flow",
    eyebrow: "The working loop",
    title: "From receipt to payer-confirmed share",
    intro: "One room moves through six explicit states instead of hiding the handoffs.",
    steps: [
      {
        number: "01",
        title: "Capture",
        body: "Add items manually or scan a receipt into an editable draft."
      },
      {
        number: "02",
        title: "Claim",
        body: "Friends join by link and claim the item quantities they shared."
      },
      {
        number: "03",
        title: "Calculate",
        body: "The server allocates discounts, taxes, fees, and remainder paise deterministically."
      },
      {
        number: "04",
        title: "Lock",
        body: "The room freezes a split snapshot before settlement requests are prepared."
      },
      {
        number: "05",
        title: "Coordinate",
        body: "Each participant opens a server-generated UPI intent or QR, then marks paid."
      },
      {
        number: "06",
        title: "Confirm",
        body: "The payer confirms or disputes manually while durable events keep every view in sync."
      }
    ]
  },
  learnings: {
    id: "what-i-learned",
    eyebrow: "What building it changed",
    title: "Six lessons I would carry into the next product.",
    intro:
      "The useful part of this project was not the stack. It was learning where correctness belongs - and where confidence has to stop.",
    themes: [
      {
        id: "money-needs-invariants",
        eyebrow: "01 / Money correctness",
        title: "Financial math needs invariants, not formatting.",
        principle: "Store paise. Conserve totals. Make remainders deterministic.",
        story:
          "A property test found that normal round-half-up could push the payer below zero. I changed the policy, derived the payer as the residual, and made conservation a post-condition of every result.",
        tradeoff:
          "Floor rounding is intentionally asymmetric: non-payers pay whole-rupee floors and the payer absorbs the residual.",
        proof: [
          "Pure, I/O-free calculation pipeline",
          "Integer arithmetic from input to stored total",
          "Randomized and golden-receipt coverage"
        ],
        evidence: [
          {
            label: "Split engine implementation",
            repositoryPath: "backend/app/split/calculator.py",
            supports: "Pure calculation pipeline and explicit post-calculation invariants.",
            state: "verified-source"
          },
          {
            label: "Rounding policy",
            repositoryPath: "backend/app/split/rounding.py",
            supports: "Floor rounding and payer-residual conservation policy.",
            state: "verified-source"
          },
          {
            label: "Split engine milestone evidence",
            repositoryPath: "docs/archive/milestones/M004-split-engine.md",
            supports: "Falsifying case, design tradeoff, test counts, and fixed regressions.",
            state: "verified-test"
          }
        ]
      },
      {
        id: "automation-needs-review",
        eyebrow: "02 / OCR and AI",
        title: "Useful automation should lower effort without pretending certainty.",
        principle: "Generate a draft, expose uncertainty, and keep the human in control.",
        story:
          "OCR output never becomes bill state directly. It is validated, redacted, parsed into an editable draft, and only converted into items after the creator reviews it.",
        tradeoff:
          "Local Tesseract keeps the default free and private, but advanced preprocessing and worker-backed jobs remain deliberate follow-ups.",
        proof: [
          "Provider boundary for mock and Tesseract OCR",
          "MIME, magic-byte, size, and dimension checks",
          "Editable draft before confirmation"
        ],
        evidence: [
          {
            label: "OCR service",
            repositoryPath: "backend/app/ocr/service.py",
            supports: "Validation, provider execution, parsing, persistence, and draft lifecycle.",
            state: "verified-source"
          },
          {
            label: "OCR parser tests",
            repositoryPath: "backend/tests/ocr/test_parser.py",
            supports: "Conservative Indian restaurant parsing and warning behavior.",
            state: "verified-test"
          },
          {
            label: "OCR draft review",
            repositoryPath: "docs/reports/screenshots/M011.1/ocr-draft-review.png",
            supports: "A creator can inspect and correct parsed output before confirmation.",
            state: "verified-browser"
          }
        ],
        visual: {
          repositoryPath: "docs/reports/screenshots/M011.1/ocr-draft-review.png",
          alt: "ReceiptSplit creator reviewing editable OCR items before adding them to the room",
          caption: "OCR proposes. The creator decides.",
          evidenceState: "verified-demo"
        }
      },
      {
        id: "realtime-needs-recovery",
        eyebrow: "03 / Realtime systems",
        title: "Realtime is a delivery path, not the source of truth.",
        principle: "Commit first, broadcast second, and always leave a replay path.",
        story:
          "Room events are written inside the transaction and broadcast only after commit. Clients subscribe, replay missed sequence numbers, deduplicate, and refetch durable state.",
        tradeoff:
          "The broker is intentionally in-process. Horizontal scale would need shared pub/sub, but the durable log already defines the recovery model.",
        proof: [
          "Per-room monotonic event sequence",
          "Subscribe-first replay without handoff gaps",
          "Slow clients disconnect and recover instead of silently dropping events"
        ],
        evidence: [
          {
            label: "Event publisher",
            repositoryPath: "backend/app/services/event_publisher.py",
            supports: "Deferred post-commit event broadcast.",
            state: "verified-source"
          },
          {
            label: "Event architecture",
            repositoryPath: "docs/architecture/events.md",
            supports: "Ordering, replay, deduplication, queue limits, and scaling boundary.",
            state: "verified-source"
          },
          {
            label: "Event API tests",
            repositoryPath: "backend/tests/api/test_events_api.py",
            supports: "Stream and replay behavior plus room-scoped authorization.",
            state: "verified-test"
          }
        ]
      },
      {
        id: "payment-needs-a-boundary",
        eyebrow: "04 / Product scope",
        title: "The safest payment feature was the one I refused to build.",
        principle: "Coordinate the handoff; never claim evidence the system does not have.",
        story:
          "The server owns the amount, VPA, reference, and UPI payload. A participant can mark paid, but only the payer can confirm or dispute. ReceiptSplit never treats that as bank verification.",
        tradeoff:
          "Manual confirmation is less magical than gateway automation, but it is honest, cheap, and appropriate for this MVP.",
        proof: [
          "Server-generated settlement requests",
          "Role-scoped status transitions",
          "Durable history for marked-paid, payer-confirmed, and disputed states"
        ],
        evidence: [
          {
            label: "Settlement service",
            repositoryPath: "backend/app/services/settlement_service.py",
            supports: "Server-owned settlement data and status transition rules.",
            state: "verified-source"
          },
          {
            label: "Settlement architecture",
            repositoryPath: "docs/architecture/settlement.md",
            supports: "Coordinator-only scope, safe language, and deferred real-device checks.",
            state: "verified-source"
          },
          {
            label: "Payer-confirmed browser evidence",
            repositoryPath: "docs/reports/screenshots/M012/payer-confirmed.png",
            supports: "The tested local flow reaches manual payer confirmation with demo data.",
            state: "verified-browser"
          }
        ],
        visual: {
          repositoryPath: "docs/reports/screenshots/M012/payer-confirmed.png",
          alt: "ReceiptSplit participant view showing a share manually confirmed by the payer",
          caption: "A human confirmation, clearly labeled as one.",
          evidenceState: "verified-demo"
        }
      },
      {
        id: "security-follows-assets",
        eyebrow: "05 / Security design",
        title: "Security got clearer when I named the assets and abuse paths.",
        principle: "Separate identities, hash capabilities, limit expensive actions, and audit safely.",
        story:
          "Account JWTs and room capability tokens stay separate. OCR upload, room access, and settlement actions have scoped authorization, rate limits, and audit events that exclude raw credentials and receipt text.",
        tradeoff:
          "The current limiter is single-process. Distributed enforcement belongs before multi-instance deployment, not before product evidence exists.",
        proof: [
          "Cross-room capability rejection",
          "Hashed token storage and fail-closed auth paths",
          "Safe audit metadata plus abuse-report controls"
        ],
        evidence: [
          {
            label: "Auth architecture",
            repositoryPath: "docs/architecture/auth.md",
            supports: "Separation of account and room-scoped identities and hashed capability storage.",
            state: "verified-source"
          },
          {
            label: "Security architecture",
            repositoryPath: "docs/architecture/security.md",
            supports: "Threat model, rate limits, safe audit rules, and explicit scaling limits.",
            state: "verified-source"
          },
          {
            label: "Security API tests",
            repositoryPath: "backend/tests/api/test_m013_security.py",
            supports: "Rate limits, unsafe input handling, audit behavior, and token boundaries.",
            state: "verified-test"
          }
        ]
      },
      {
        id: "ux-mirrors-state",
        eyebrow: "06 / Product engineering",
        title: "Polish starts when the interface mirrors the real workflow.",
        principle: "Show one current step, one next action, and honest status language.",
        story:
          "Manual browser runs exposed failures that component work missed: a blocked settlement request, confusing locked states, quantity-claim gaps, and a weak completion state. The interface now follows draft, claiming, locked, settling, and settled views.",
        tradeoff:
          "Demo screenshots prove rendering and local flow behavior. They do not prove real-device UPI handoff or production readiness.",
        proof: [
          "Distinct creator room states",
          "Mobile claim and payment views",
          "Settled completion screen with manual-confirmation copy"
        ],
        evidence: [
          {
            label: "Room state UI",
            repositoryPath: "frontend/components/room-client.tsx",
            supports: "State-derived creator and participant views.",
            state: "verified-source"
          },
          {
            label: "Flow and adjustment tests",
            repositoryPath: "frontend/tests/m0151-flow-adjustments.test.tsx",
            supports: "Step headers, adjustment behavior, creator identity, and completion copy.",
            state: "verified-test"
          },
          {
            label: "Settled completion screenshot",
            repositoryPath: "docs/reports/screenshots/M015.1/settled-completion-screen.png",
            supports: "The final room state renders with demo API data.",
            state: "mocked-browser"
          }
        ],
        visual: {
          repositoryPath: "docs/reports/screenshots/M015.1/mobile-dark-settled-view.png",
          alt: "ReceiptSplit mobile settled view with final shares and manual payer confirmation",
          caption: "The room ends with closure, not another dashboard.",
          evidenceState: "mocked-demo"
        }
      }
    ]
  },
  evidence: {
    id: "build-evidence",
    eyebrow: "Build evidence",
    title: "Claims stay attached to the artifact that earns them.",
    intro:
      "The repository keeps source, tests, architecture notes, and demo screenshots together - and labels the limits of each.",
    notes: [
      {
        title: "Validated system paths",
        body: "The backend suite and frontend lint, typecheck, tests, and production build passed at the latest flow-repair closeout.",
        state: "verified-test"
      },
      {
        title: "Local browser proof",
        body: "A DB-backed demo covered create, join, claim, lock, UPI handoff, marked paid, and payer confirmation with fake data.",
        state: "verified-browser"
      },
      {
        title: "Mocked visual proof",
        body: "The newest dark-mode and completion screenshots prove UI states with demo responses, not live database or bank behavior.",
        state: "mocked-browser"
      },
      {
        title: "Still to prove",
        body: "Real-device UPI behavior, distributed rate limiting, committed browser E2E, and the current Next/PostCSS advisory remain follow-up work.",
        state: "known-limit"
      }
    ]
  },
  close: {
    id: "takeaway",
    eyebrow: "The takeaway",
    title: "I learned to make the system honest before making it feel smart.",
    body:
      "ReceiptSplit made me better at turning a messy real-world workflow into explicit domain rules, recoverable collaboration, and a product boundary users can understand.",
    ctas: [
      {
        label: "Review the source",
        href: "https://github.com/Atishay9828/ReceiptSplit",
        external: true,
        ariaLabel: "Review the ReceiptSplit source repository on GitHub"
      },
      { label: "Revisit the system flow", href: "#system-flow" }
    ]
  }
};
