import {
  ArrowRight,
  Check,
  CheckCircle2,
  IndianRupee,
  LockKeyhole,
  ScanLine,
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
