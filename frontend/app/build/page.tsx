import type { Metadata } from "next";
import { ArrowLeft, ArrowRight, Check, Code2, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { BuildJourney, type BuildJourneyStage } from "@/components/build-journey";
import { receiptSplitWebsiteContent as content } from "@/lib/website-content";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: content.meta.title,
  description: content.meta.description
};

const journeyTones = ["cyan", "amber", "violet", "cyan", "rose", "violet"] as const;

const journeyStages: readonly BuildJourneyStage[] = content.learnings.themes.map((theme, index) => ({
  marker: "Decision",
  phase: theme.eyebrow.replace(/^\d+\s*\/\s*/, ""),
  title: theme.title,
  outcome: theme.principle,
  decision: theme.principle,
  learned: theme.story,
  tradeoff: theme.tradeoff,
  evidence: theme.proof.join(" · "),
  tone: journeyTones[index]
}));

const evidenceLabels = {
  "verified-source": "Source-backed",
  "verified-test": "Test-backed",
  "verified-browser": "Browser-tested",
  "mocked-browser": "Mocked UI proof",
  "known-limit": "Known limit"
} as const;

export default function BuildStoryPage() {
  return (
    <main className={styles.page}>
      <a className={styles.skipLink} href="#build-story">
        Skip to the build story
      </a>

      <header className={styles.header}>
        <Link className={styles.brand} href="/" aria-label="ReceiptSplit product homepage">
          <span>ReceiptSplit</span>
          <small>Build story</small>
        </Link>
        <nav aria-label="Build story navigation">
          <Link href="/">
            <ArrowLeft size={15} aria-hidden="true" /> Product
          </Link>
          <a href="https://github.com/Atishay9828/ReceiptSplit" target="_blank" rel="noreferrer">
            <Code2 size={15} aria-hidden="true" /> Source
          </a>
        </nav>
      </header>

      <div id="build-story">
        <section className={styles.hero} aria-labelledby="build-title">
          <div>
            <p className={styles.eyebrow}>{content.hero.eyebrow}</p>
            <h1 id="build-title">{content.hero.title}</h1>
            <p className={styles.summary}>{content.hero.summary}</p>
            <p className={styles.boundary}>
              <ShieldCheck size={18} aria-hidden="true" /> {content.hero.boundary}
            </p>
            <div className={styles.actions}>
              <a className={styles.primaryAction} href={content.hero.ctas[0].href}>
                {content.hero.ctas[0].label} <ArrowRight size={17} aria-hidden="true" />
              </a>
              <a
                className={styles.secondaryAction}
                href={content.hero.ctas[1].href}
                target="_blank"
                rel="noreferrer"
              >
                {content.hero.ctas[1].label}
              </a>
            </div>
          </div>

          <aside className={styles.heroReceipt} aria-label="ReceiptSplit engineering thesis">
            <p>BUILD RECEIPT / AJ</p>
            <strong>TRUST IS A SYSTEM PROPERTY</strong>
            <dl>
              <div>
                <dt>Input</dt>
                <dd>uncertain</dd>
              </div>
              <div>
                <dt>Money</dt>
                <dd>exact</dd>
              </div>
              <div>
                <dt>State</dt>
                <dd>recoverable</dd>
              </div>
              <div>
                <dt>Payment</dt>
                <dd>honest</dd>
              </div>
            </dl>
            <small>Make the risky state explicit. Prove it. Then make it feel simple.</small>
          </aside>
        </section>

        <ul className={styles.proofStrip} aria-label="Fast proof">
          {content.proofStrip.map((point) => (
            <li key={point.value}>
              <span><Check size={14} aria-hidden="true" /> {point.value}</span>
              <strong>{point.label}</strong>
              <p>{point.detail}</p>
            </li>
          ))}
        </ul>

        <section className={styles.problem} id={content.problem.id} aria-labelledby="problem-title">
          <div>
            <p className={styles.eyebrow}>{content.problem.eyebrow}</p>
            <h2 id="problem-title">{content.problem.title}</h2>
          </div>
          <div className={styles.problemCopy}>
            {content.problem.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            <blockquote>{content.problem.takeaway}</blockquote>
          </div>
        </section>

        <section className={styles.flow} id={content.flow.id} aria-labelledby="flow-story-title">
          <header>
            <p className={styles.eyebrow}>{content.flow.eyebrow}</p>
            <h2 id="flow-story-title">{content.flow.title}</h2>
            <p>{content.flow.intro}</p>
          </header>
          <ol>
            {content.flow.steps.map((step) => (
              <li key={step.number}>
                <span>{step.number}</span>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <BuildJourney
          id={content.learnings.id}
          className={styles.journey}
          stages={journeyStages}
          title={content.learnings.title}
          intro={content.learnings.intro}
        />

        <section className={styles.evidence} id={content.evidence.id} aria-labelledby="evidence-title">
          <header>
            <p className={styles.eyebrow}>{content.evidence.eyebrow}</p>
            <h2 id="evidence-title">{content.evidence.title}</h2>
            <p>{content.evidence.intro}</p>
          </header>
          <div className={styles.evidenceGrid}>
            {content.evidence.notes.map((note) => (
              <article key={note.title} data-state={note.state}>
                <span>{evidenceLabels[note.state]}</span>
                <h3>{note.title}</h3>
                <p>{note.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.close} id={content.close.id} aria-labelledby="close-title">
          <div>
            <p className={styles.eyebrow}>{content.close.eyebrow}</p>
            <h2 id="close-title">{content.close.title}</h2>
            <p>{content.close.body}</p>
          </div>
          <div className={styles.closeActions}>
            <a className={styles.primaryAction} href={content.close.ctas[0].href} target="_blank" rel="noreferrer">
              {content.close.ctas[0].label} <ArrowRight size={17} aria-hidden="true" />
            </a>
            <a className={styles.secondaryAction} href={content.close.ctas[1].href}>
              {content.close.ctas[1].label}
            </a>
          </div>
        </section>
      </div>

      <footer className={styles.footer}>
        <span>Designed and built by AJ.</span>
        <Link href="/">Open the ReceiptSplit product</Link>
      </footer>
    </main>
  );
}
