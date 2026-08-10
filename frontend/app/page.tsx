import {
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  FileText,
  UsersRound,
  WalletCards
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { JoinInviteForm } from "@/components/home/join-invite-form";

import "./homepage-artifacts.css";
import "./homepage.css";

const receiptRows = [
  { item: "Margherita Pizza", person: "Alex", amount: "Rs 18.00", tone: "coral" },
  { item: "Truffle Fries", person: "Bella", amount: "Rs 7.50", tone: "gold" },
  { item: "Grilled Salmon", person: "Chris", amount: "Rs 24.00", tone: "blue" },
  { item: "Sparkling Water", person: "Dana", amount: "Rs 4.50", tone: "lilac" }
];

const workflow = [
  {
    number: "1",
    label: "Add the receipt",
    detail: "Upload a photo of your receipt. We will read the items and amounts.",
    icon: FileText
  },
  {
    number: "2",
    label: "Choose who had what",
    detail: "Assign each item to the person who ordered it.",
    icon: UsersRound
  },
  {
    number: "3",
    label: "Settle up",
    detail: "See who owes what and settle up however works for you.",
    icon: WalletCards
  }
];

export default function HomePage() {
  return (
    <div className="home-shell">
      <a className="home-skip-link" href="#main-content">
        Skip to content
      </a>

      <header className="home-header">
        <Link className="home-brand" href="/" aria-label="ReceiptSplit home">
          ReceiptSplit
        </Link>

        <nav className="home-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <Link href="/dashboard">My rooms</Link>
        </nav>

        <div className="home-header-actions">
          <a className="home-open-invite" href="#invite">
            Open invite
            <ArrowRight size={15} aria-hidden="true" />
          </a>
          <Link className="home-header-cta" href="/create">
            Create a split
          </Link>
        </div>
      </header>

      <main id="main-content">
        <section className="home-hero" aria-labelledby="home-title">
          <div className="home-hero-copy">
            <p className="home-eyebrow">Receipt-first bill splitting</p>
            <h1 id="home-title" aria-label="Split the bill without the group chat maths.">
              Split the bill
              <br />
              without the
              <br />
              group chat maths.
            </h1>
            <p className="home-hero-summary">
              Upload a receipt, assign items, and see who owes what.
              <br className="home-desktop-break" /> Settle up in seconds.
            </p>

            <div className="home-hero-actions">
              <Link className="home-primary-action" href="/create">
                Create a split
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
              <a className="home-text-action" href="#invite">
                Open invite
                <ArrowRight size={16} aria-hidden="true" />
              </a>
            </div>

            <p className="home-trust-line">
              <CheckCircle2 size={16} aria-hidden="true" />
              Free to use. No sign up required.
            </p>
          </div>

          <div className="home-ledger-preview" aria-label="Example of a settled bill">
            <div className="home-ledger-card">
              <div className="home-ledger-header">
                <div>
                  <strong>Riverside Bistro</strong>
                  <span>Sat, 18 May 2024 - 7:42 PM</span>
                </div>
                <div className="home-ledger-meta">
                  <span>Receipt #1847</span>
                  <span>4 items</span>
                </div>
              </div>

              <div className="home-ledger-columns" aria-hidden="true">
                <span>Item</span>
                <span>Paid by</span>
                <span>Amount</span>
              </div>

              <div className="home-ledger-rows">
                {receiptRows.map((row) => (
                  <div className="home-ledger-row" key={row.item}>
                    <span>{row.item}</span>
                    <span className="home-ledger-person">
                      <i className={`home-person-dot ${row.tone}`} aria-hidden="true" />
                      {row.person}
                    </span>
                    <strong>{row.amount}</strong>
                  </div>
                ))}
              </div>

              <div className="home-ledger-total">
                <span>Total</span>
                <strong>Rs 54.00</strong>
              </div>

              <div className="home-ledger-settled">
                <span>You owe</span>
                <strong>Rs 13.50</strong>
                <CheckCircle2 size={17} aria-hidden="true" />
              </div>

              <p className="home-ledger-note">
                <CheckCircle2 size={14} aria-hidden="true" /> All set! Everyone&apos;s balances are up to date.
              </p>
            </div>
          </div>
        </section>

        <section className="home-how" id="how-it-works" aria-labelledby="how-title">
          <div className="home-how-heading">
            <p className="home-section-label">How it works</p>
            <h2 id="how-title">From receipt to resolved.</h2>
          </div>
          <ol className="home-workflow">
            {workflow.map((step) => {
              const Icon = step.icon;
              return (
                <li key={step.number}>
                  <div className="home-workflow-icon" aria-hidden="true">
                    <Icon size={23} strokeWidth={1.8} />
                  </div>
                  <div className="home-workflow-copy">
                    <span className="home-workflow-number">{step.number}</span>
                    <h3>{step.label}</h3>
                    <p>{step.detail}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>

        <section className="home-proof" aria-labelledby="proof-title">
          <div className="home-proof-copy">
            <p className="home-section-label">Built for real receipts</p>
            <h2 id="proof-title">The receipt stays visible while the maths gets sorted.</h2>
            <p>
              OCR creates an editable draft, not a payment claim. Check item names and amounts before
              anyone settles.
            </p>
            <Link className="home-text-action" href="/create">
              Start with a receipt
              <ArrowUpRight size={16} aria-hidden="true" />
            </Link>
          </div>
          <div className="home-proof-media">
            <Image
              src="/assets/receipt-riverside.png"
              alt="A restaurant receipt ready to review"
              width={888}
              height={1776}
              priority
            />
            <span className="home-proof-tag">Editable draft</span>
          </div>
        </section>

        <section className="home-invite" id="invite" aria-labelledby="invite-title">
          <div>
            <p className="home-section-label">Have an invite?</p>
            <h2 id="invite-title">Open the bill your friend sent.</h2>
            <p>Join with your private link and choose only what belongs in your share.</p>
          </div>
          <JoinInviteForm />
        </section>
      </main>

      <footer className="home-footer">
        <Link className="home-brand" href="/" aria-label="ReceiptSplit home">
          ReceiptSplit
        </Link>
        <p>One receipt. Shared context. Direct settlement.</p>
        <Link href="#main-content">Back to top</Link>
      </footer>
    </div>
  );
}
