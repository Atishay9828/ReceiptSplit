import styles from "./build-journey.module.css";

export type BuildJourneyStage = {
  marker: string;
  phase: string;
  title: string;
  outcome: string;
  decision: string;
  learned: string;
  evidence: string;
  tone: "cyan" | "violet" | "amber" | "rose";
};

export const receiptSplitJourney: readonly BuildJourneyStage[] = [
  {
    marker: "M004",
    phase: "Correctness",
    title: "Model money before screens.",
    outcome: "Integer paise and invariants turned edge cases into rules.",
    decision:
      "Keep the split engine pure: no I/O, no floats, and deterministic allocation and rounding.",
    learned:
      "Property tests found a negative payer-total edge case that ordinary examples missed. Correctness became a product feature, not cleanup work.",
    evidence:
      "M004 passed 135 non-property tests and 12 property suites covering conservation, non-negative totals, and determinism.",
    tone: "cyan"
  },
  {
    marker: "M009",
    phase: "Collaboration",
    title: "Make live updates recoverable.",
    outcome: "Durable room events stayed the truth; SSE only prompted a refetch.",
    decision:
      "Persist each event with its mutation, replay by sequence number, and publish only after the transaction commits.",
    learned:
      "Realtime UX is trustworthy only when disconnects and rollbacks cannot invent a second version of the room.",
    evidence:
      "M009 added durable room events, replay endpoints, authenticated SSE, and a rollback regression test.",
    tone: "violet"
  },
  {
    marker: "M011.1",
    phase: "Reviewable AI",
    title: "Treat OCR as a draft, not an answer.",
    outcome: "Scanning saved typing while the creator stayed in control.",
    decision:
      "Use a provider boundary, private image storage, redacted display text, and an editable confirmation step.",
    learned:
      "AI belongs behind a review surface when one wrong digit changes everyone's share.",
    evidence:
      "M011.1 passed the upload, review, edit, confirm, claim, lock, and unlock flow in local browser smoke.",
    tone: "amber"
  },
  {
    marker: "M012",
    phase: "Settlement",
    title: "Coordinate payment without pretending to process it.",
    outcome: "UPI opens directly; payment status remains a manual agreement.",
    decision:
      "Generate amount, VPA, payee name, and reference on the server. Let participants mark paid and the payer confirm or dispute.",
    learned:
      "An honest product boundary creates more trust than a success screen the system cannot prove.",
    evidence:
      "M012 DB/API, frontend, and browser evidence covered marked paid, payer confirmed, and disputed states.",
    tone: "cyan"
  },
  {
    marker: "M014.1",
    phase: "Pilot repair",
    title: "Let real flows break the prototype.",
    outcome: "Quantity claims, participant removal, and settled transitions repaired the happy path.",
    decision:
      "Run the whole room lifecycle in the production UI, then fix the points where people actually got stuck.",
    learned:
      "A feature list can pass while the product loop still fails. End-to-end behavior is the sharper test.",
    evidence:
      "M014.1 repaired claim quantities, payment visibility, participant removal, and the room's settled transition.",
    tone: "rose"
  },
  {
    marker: "M015.1",
    phase: "Flow clarity",
    title: "Make state visible before adding polish.",
    outcome: "Each room phase got its own next action, language, and completion view.",
    decision:
      "Separate draft, claiming, locked, settling, and settled views; keep adjustment math server-owned and theme semantics consistent.",
    learned:
      "Visual polish matters after the flow tells people exactly where they are and what happens next.",
    evidence:
      "M015.1 completed focused calculator tests, full frontend validation, and 14 dark-mode browser screenshots.",
    tone: "violet"
  }
];

export type BuildJourneyProps = {
  id?: string;
  className?: string;
  stages?: readonly BuildJourneyStage[];
  title?: string;
  intro?: string;
};

export function BuildJourney({
  id = "build-journey",
  className,
  stages = receiptSplitJourney,
  title = "What I learned by shipping the whole loop.",
  intro =
    "ReceiptSplit started as bill-splitting math. Rounding, disconnects, OCR mistakes, and real payment states kept rewriting the product."
}: BuildJourneyProps) {
  const headingId = `${id}-title`;
  const descriptionId = `${id}-description`;
  const rootClassName = [styles.root, className].filter(Boolean).join(" ");

  return (
    <section id={id} className={rootClassName} aria-labelledby={headingId}>
      <header className={styles.header}>
        <div className={styles.headingBlock}>
          <p className={styles.eyebrow}>Build journey / ReceiptSplit</p>
          <h2 id={headingId} className={styles.heading}>
            {title}
          </h2>
        </div>

        <div className={styles.introBlock}>
          <p id={descriptionId} className={styles.intro}>
            {intro}
          </p>
          <p className={styles.instruction}>
            Open any build receipt for the decision, lesson, and proof.
          </p>
        </div>
      </header>

      <ol className={styles.list} aria-describedby={descriptionId}>
        {stages.map((stage, index) => (
          <li key={`${stage.marker}-${stage.title}`} className={styles.item} data-tone={stage.tone}>
            <span className={styles.sequence} aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </span>

            <details className={styles.entry} open={index === 0}>
              <summary className={styles.summary}>
                <span className={styles.summaryCopy}>
                  <span className={styles.phase}>
                    {stage.marker} <span aria-hidden="true">/</span> {stage.phase}
                  </span>
                  <span className={styles.stageTitle}>{stage.title}</span>
                  <span className={styles.outcome}>{stage.outcome}</span>
                </span>
                <span className={styles.toggle} aria-hidden="true" />
              </summary>

              <div className={styles.body}>
                <div className={styles.bodyItem}>
                  <span className={styles.label}>Decision</span>
                  <p>{stage.decision}</p>
                </div>
                <div className={styles.bodyItem}>
                  <span className={styles.label}>What changed in me</span>
                  <p>{stage.learned}</p>
                </div>
                <div className={styles.evidence}>
                  <span className={styles.label}>Build receipt</span>
                  <p>{stage.evidence}</p>
                </div>
              </div>
            </details>
          </li>
        ))}
      </ol>

      <p className={styles.closing}>
        The pattern I kept: make the risky state explicit, prove it, then make it feel simple.
      </p>
    </section>
  );
}
