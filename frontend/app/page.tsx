import {
  ArrowRight,
  Check,
  CheckCircle2,
  IndianRupee,
  LockKeyhole,
  Radio,
  ScanLine,
  ShieldCheck,
  UsersRound
} from "lucide-react";
import Link from "next/link";

import { JoinInviteForm } from "@/components/home/join-invite-form";

import "./homepage-artifacts.css";
import "./homepage.css";

const roomSteps = [
  {
    label: "Draft",
    description: "Scan or enter the receipt, then correct the draft.",
    icon: ScanLine
  },
  {
    label: "Claiming",
    description: "Share one link. Everyone claims exactly what they had.",
    icon: UsersRound
  },
  {
    label: "Locked",
    description: "Freeze the bill only when every claim and total is ready.",
    icon: LockKeyhole
  },
  {
    label: "Settling",
    description: "Each friend pays the payer directly through their UPI app.",
    icon: IndianRupee
  },
  {
    label: "Settled",
    description: "The payer manually confirms each share and closes the room.",
    icon: CheckCircle2
  }
] as const;

export default function HomePage() {
  return (
    <div className="home-shell">
      <a className="home-skip-link" href="#main-content">
        Skip to content
      </a>

      <header className="home-header">
        <Link className="home-wordmark" href="/" aria-label="ReceiptSplit home">
          <span className="home-wordmark-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>ReceiptSplit</span>
        </Link>

        <nav className="home-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <Link href="/build">Build story</Link>
          <Link className="home-nav-action" href="/create">
            Create a split
          </Link>
        </nav>
      </header>

      <main id="main-content">
        <section className="home-hero" aria-labelledby="home-title">
          <div className="home-hero-copy">
            <p className="home-kicker">
              <span className="home-live-dot" aria-hidden="true" />
              Receipt-first splitting for real groups
            </p>
            <h1 id="home-title">
              A receipt should end the debate.
              <span>Not start one.</span>
            </h1>
            <p className="home-hero-summary">
              Scan one bill, let friends claim what they had, see exact totals, and settle directly
              with the payer. No shared wallet. No mystery maths.
            </p>

            <div className="home-hero-actions">
              <Link className="home-primary-action" href="/create">
                Create a split
                <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <Link className="home-text-action" href="/build">
                See how I built it
              </Link>
            </div>

            <ul className="home-trust-line" aria-label="Product facts">
              <li>
                <Check size={15} aria-hidden="true" /> No account for friends
              </li>
              <li>
                <Check size={15} aria-hidden="true" /> Integer-paise totals
              </li>
              <li>
                <Check size={15} aria-hidden="true" /> Direct UPI handoff
              </li>
            </ul>
          </div>

          <SplitReceiptArtifact />
        </section>

        <section className="home-section home-flow" id="how-it-works" aria-labelledby="flow-title">
          <div className="home-section-heading">
            <p className="home-section-label">Inside one room</p>
            <h2 id="flow-title">The bill moves forward. Everyone sees where it stands.</h2>
          </div>

          <ol className="room-step-list">
            {roomSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <li key={step.label}>
                  <div className="room-step-index" aria-hidden="true">
                    <Icon size={17} />
                    <span>{String(index + 1).padStart(2, "0")}</span>
                  </div>
                  <div>
                    <h3>{step.label}</h3>
                    <p>{step.description}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>

        <section
          className="home-section learning-section"
          id="what-we-learned"
          aria-labelledby="learning-title"
        >
          <div className="learning-intro">
            <p className="home-section-label">What I learned by shipping it</p>
            <h2 id="learning-title">Every hard lesson became a product guardrail.</h2>
            <p>
              I built ReceiptSplit by following the failure points in a real group bill—from an
              imperfect scan to the final manual confirmation. These are not skill badges. They are
              decisions you can see in the room.
            </p>
            <Link className="home-text-action" href="/build">
              Read all six decisions
            </Link>
          </div>

          <div className="learning-ledger">
            <article className="learning-entry">
              <div className="learning-entry-copy">
                <p className="learning-number">Lesson 01 / uncertain input</p>
                <h3>A scan starts a draft, not a fact.</h3>
                <p>
                  OCR is useful precisely because it saves typing—not because it is always right.
                  Every detected item stays editable before it reaches the shared bill.
                </p>
              </div>
              <div className="artifact-panel scan-artifact" aria-label="Editable receipt scan example">
                <div className="artifact-panel-header">
                  <span>OCR draft</span>
                  <span className="artifact-status artifact-status-review">Review</span>
                </div>
                <div className="scan-line scan-line-ready">
                  <span>Cold Coffee × 3</span>
                  <strong>₹360.00</strong>
                  <small>ready</small>
                </div>
                <div className="scan-line scan-line-edit">
                  <span>Masala Frles × 2</span>
                  <strong>₹240.00</strong>
                  <small>edit name</small>
                </div>
                <p className="artifact-caption">Review item names and amounts before adding them.</p>
              </div>
            </article>

            <article className="learning-entry">
              <div className="learning-entry-copy">
                <p className="learning-number">Lesson 02 / shared state</p>
                <h3>Reconnects should not rewrite the story.</h3>
                <p>
                  Room events are durable and ordered. Live updates are a fast signal to refetch the
                  truth, so a dropped connection does not invent a second version of the bill.
                </p>
              </div>
              <div className="artifact-panel event-artifact" aria-label="Ordered room event example">
                <div className="artifact-panel-header">
                  <span>Room event trace</span>
                  <span className="artifact-status artifact-status-live">
                    <Radio size={12} aria-hidden="true" /> live
                  </span>
                </div>
                <ol>
                  <li>
                    <span>#016</span>
                    <strong>room.claiming_opened</strong>
                    <small>applied</small>
                  </li>
                  <li>
                    <span>#017</span>
                    <strong>assignment.claimed</strong>
                    <small>applied</small>
                  </li>
                  <li className="event-current">
                    <span>#018</span>
                    <strong>split.locked</strong>
                    <small>current</small>
                  </li>
                </ol>
                <p className="artifact-caption">Replayed in sequence after reconnect.</p>
              </div>
            </article>

            <article className="learning-entry">
              <div className="learning-entry-copy">
                <p className="learning-number">Lesson 03 / money math</p>
                <h3>Money refuses “close enough.”</h3>
                <p>
                  Amounts stay in integer paise; percentages use basis points. Tax, discounts, and
                  quantity claims add up exactly before anyone is asked to pay.
                </p>
              </div>
              <div className="artifact-panel math-artifact" aria-label="Exact bill calculation example">
                <div className="artifact-panel-header">
                  <span>Split calculation</span>
                  <span className="artifact-status">paise</span>
                </div>
                <dl>
                  <div>
                    <dt>Item subtotal</dt>
                    <dd>₹780.00</dd>
                  </div>
                  <div>
                    <dt>Tax · 500 bp</dt>
                    <dd>+ ₹39.00</dd>
                  </div>
                  <div>
                    <dt>Table coupon</dt>
                    <dd>− ₹60.00</dd>
                  </div>
                  <div className="math-total">
                    <dt>Final total</dt>
                    <dd>₹759.00</dd>
                  </div>
                </dl>
                <p className="artifact-caption">78000 + 3900 − 6000 = 75900 paise</p>
              </div>
            </article>

            <article className="learning-entry">
              <div className="learning-entry-copy">
                <p className="learning-number">Lesson 04 / payment truth</p>
                <h3>Honest states are a safety feature.</h3>
                <p>
                  ReceiptSplit coordinates a direct UPI handoff. A friend can mark that they paid;
                  the payer can confirm it. The product never pretends it verified a bank transfer.
                </p>
              </div>
              <div className="artifact-panel payment-artifact" aria-label="Manual payment status example">
                <div className="artifact-panel-header">
                  <span>Payment RS–018–KU</span>
                  <span className="artifact-status artifact-status-safe">manual</span>
                </div>
                <div className="payment-person">
                  <div className="payment-avatar" aria-hidden="true">K</div>
                  <div>
                    <strong>Kunal</strong>
                    <span>₹450.00</span>
                  </div>
                  <span className="payment-state">Payer confirmed</span>
                </div>
                <p className="payment-note">
                  <ShieldCheck size={15} aria-hidden="true" /> ReceiptSplit does not verify bank
                  transfers.
                </p>
              </div>
            </article>
          </div>
        </section>

        <section className="home-section home-start" id="start" aria-labelledby="start-title">
          <div className="home-start-copy">
            <p className="home-section-label">Run the next bill</p>
            <h2 id="start-title">Start with the receipt already on your table.</h2>
            <p>
              The payer creates the room. Everyone else joins from one private invite link—no app
              install and no account setup.
            </p>
            <Link className="home-primary-action" href="/create">
              Create a split room
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
          </div>

          <JoinInviteForm />
        </section>
      </main>

      <footer className="home-footer">
        <Link className="home-wordmark" href="/" aria-label="ReceiptSplit home">
          ReceiptSplit
        </Link>
        <p>One receipt. Shared context. Direct settlement.</p>
        <a href="#main-content">Back to top ↑</a>
      </footer>
    </div>
  );
}

function SplitReceiptArtifact() {
  return (
    <div className="split-artifact" aria-label="Example item-wise receipt split">
      <div className="receipt-paper">
        <div className="receipt-heading">
          <div>
            <span>ROOM / AJ&apos;S TABLE</span>
            <strong>RECEIPT 018</strong>
          </div>
          <span className="receipt-live">
            <span aria-hidden="true" /> live
          </span>
        </div>

        <div className="receipt-rule" aria-hidden="true" />

        <div className="receipt-item">
          <div className="receipt-item-line">
            <span>Cold Coffee × 3</span>
            <strong>₹360.00</strong>
          </div>
          <div className="claim-row">
            <span className="claim claim-aj">AJ · 1</span>
            <span className="claim claim-kunal">Kunal · 2</span>
            <small>3 / 3 claimed</small>
          </div>
        </div>

        <div className="receipt-item">
          <div className="receipt-item-line">
            <span>Masala Fries × 2</span>
            <strong>₹240.00</strong>
          </div>
          <div className="claim-row">
            <span className="claim claim-aj">AJ · 1</span>
            <span className="claim claim-kunal">Kunal · 1</span>
            <small>2 / 2 claimed</small>
          </div>
        </div>

        <div className="receipt-item">
          <div className="receipt-item-line">
            <span>Lime Soda × 2</span>
            <strong>₹180.00</strong>
          </div>
          <div className="claim-row">
            <span className="claim claim-aj">AJ · 1</span>
            <span className="claim claim-kunal">Kunal · 1</span>
            <small>2 / 2 claimed</small>
          </div>
        </div>

        <div className="receipt-rule receipt-rule-double" aria-hidden="true" />

        <div className="receipt-total">
          <span>TOTAL / 7 ITEMS CLAIMED</span>
          <strong>₹780.00</strong>
        </div>

        <div className="receipt-splits">
          <div>
            <span className="split-person-dot split-person-aj" aria-hidden="true" />
            <p>AJ owes</p>
            <strong>₹330.00</strong>
          </div>
          <div>
            <span className="split-person-dot split-person-kunal" aria-hidden="true" />
            <p>Kunal owes</p>
            <strong>₹450.00</strong>
          </div>
        </div>

        <div className="receipt-footer-line">
          <span>ITEM-WISE / EXACT IN PAISE</span>
          <span>LOCK READY ✓</span>
        </div>
      </div>
    </div>
  );
}
