"use client";

import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  ListChecks,
  Smartphone,
  UsersRound,
  WalletCards
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { CreateRoomForm } from "@/components/create-room-form";
import { api } from "@/lib/api";
import { saveCreatorSession } from "@/lib/storage";
import type { RoomCreateRequest } from "@/types/api";

export default function CreatePage() {
  const router = useRouter();

  async function createRoom(payload: RoomCreateRequest) {
    const created = await api.createRoom(payload);
    saveCreatorSession({
      roomId: created.room.id,
      role: "creator",
      token: created.creator_token,
      inviteToken: created.invite_token,
      lastSequence: 0
    });
    router.push(`/rooms/${created.room.id}/creator`);
  }

  return (
    <div className="rs-page-shell rs-create-page text-ink">
      <header className="rs-topbar">
        <div className="rs-app-header-inner">
          <Link className="rs-reference-brand" href="/">
            ReceiptSplit
          </Link>
          <nav className="rs-reference-nav" aria-label="Main navigation">
            <Link href="/#how-it-works">How it works</Link>
            <Link href="/dashboard">My rooms</Link>
          </nav>
          <div className="rs-reference-actions">
            <Link className="rs-reference-quiet-action" href="/#invite">
              Open invite <ArrowRight size={15} aria-hidden="true" />
            </Link>
            <Link className="rs-reference-cta" href="/create">
              Create a split
            </Link>
          </div>
        </div>
      </header>

      <main className="rs-create-main">
        <section className="rs-create-intro">
          <div>
            <p className="rs-kicker">Quick bill</p>
            <h1>Split a receipt with friends.</h1>
            <p className="rs-create-lead">
              Create the bill, share one private invite, and let everyone claim their food. Payment
              can stay pending until each person is ready.
            </p>
          </div>

          <ol className="rs-create-steps" aria-label="What happens after creating a bill">
            <FlowStep icon={<ListChecks size={19} aria-hidden="true" />} label="1. Add the bill" detail="Scan a receipt or enter items manually." />
            <FlowStep icon={<UsersRound size={19} aria-hidden="true" />} label="2. Collect claims" detail="Friends join and claim what they had." />
            <FlowStep icon={<Clock3 size={19} aria-hidden="true" />} label="3. Settle later" detail="Due shares remain visible until confirmed." />
          </ol>

          <div className="rs-create-trust">
            <TrustPill icon={<Smartphone size={16} aria-hidden="true" />} label="No app needed for friends" />
            <TrustPill icon={<WalletCards size={16} aria-hidden="true" />} label="No shared wallet" />
            <TrustPill icon={<CheckCircle2 size={16} aria-hidden="true" />} label="Direct UPI payment" />
          </div>
        </section>

        <section className="rs-create-form-panel" aria-labelledby="create-room-title">
          <div className="rs-form-panel-heading">
            <p className="rs-form-label">Bill setup</p>
            <h2 id="create-room-title">Create split room</h2>
            <p>
              This creates one shareable bill. For trips or recurring groups, use My rooms to keep
              several bills and their pending or cleared totals together.
            </p>
            <Link className="rs-form-panel-link" href="/dashboard">
              Create a persistent room instead <ArrowRight size={15} aria-hidden="true" />
            </Link>
          </div>
          <CreateRoomForm onCreate={createRoom} submitLabel="Create split room" />
        </section>
      </main>
    </div>
  );
}

function FlowStep({ icon, label, detail }: { icon: ReactNode; label: string; detail: string }) {
  return (
    <li className="rs-create-step">
      <span className="rs-create-step-icon">{icon}</span>
      <div>
        <p>{label}</p>
        <span>{detail}</span>
      </div>
    </li>
  );
}

function TrustPill({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="rs-create-trust-pill">
      {icon}
      {label}
    </span>
  );
}
