"use client";

import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  ListChecks,
  ReceiptText,
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
    <div className="min-h-dvh text-ink">
      <header className="sticky top-0 z-40 border-b border-border bg-surface/90 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 pr-16 sm:px-6 sm:pr-20">
          <Link className="inline-flex min-h-11 items-center gap-2 font-bold" href="/">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-mint text-leaf">
              <ReceiptText size={20} aria-hidden="true" />
            </span>
            ReceiptSplit
          </Link>
          <Link className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-muted hover:text-ink" href="/">
            <ArrowLeft size={16} aria-hidden="true" />
            Back home
          </Link>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 sm:px-6 sm:py-10 lg:grid-cols-[minmax(0,1fr)_430px] lg:items-start lg:gap-10">
        <section className="grid gap-6 lg:sticky lg:top-24">
          <div className="grid gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-leaf">Quick bill</p>
            <h1 className="max-w-2xl text-4xl font-bold leading-[1.02] tracking-[-0.04em] sm:text-6xl">
              Split a receipt with friends. Keep every share clear.
            </h1>
            <p className="max-w-2xl text-base leading-7 text-muted sm:text-lg">
              Create the bill, share one private invite, and let everyone claim their food. Payment
              can stay pending until each person is ready.
            </p>
          </div>

          <ol className="grid gap-3 sm:grid-cols-3" aria-label="What happens after creating a bill">
            <FlowStep icon={<ListChecks size={19} aria-hidden="true" />} label="1. Add the bill" detail="Scan a receipt or enter items manually." />
            <FlowStep icon={<UsersRound size={19} aria-hidden="true" />} label="2. Collect claims" detail="Friends join and claim what they had." />
            <FlowStep icon={<Clock3 size={19} aria-hidden="true" />} label="3. Settle later" detail="Due shares remain visible until confirmed." />
          </ol>

          <div className="grid gap-2 text-sm sm:grid-cols-3">
            <TrustPill icon={<Smartphone size={16} aria-hidden="true" />} label="No app needed for friends" />
            <TrustPill icon={<WalletCards size={16} aria-hidden="true" />} label="No shared wallet" />
            <TrustPill icon={<CheckCircle2 size={16} aria-hidden="true" />} label="Direct UPI payment" />
          </div>
        </section>

        <section className="rounded-lg border border-border bg-surface p-5 shadow-soft sm:p-6" aria-labelledby="create-room-title">
          <div className="mb-5 border-b border-border pb-5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-info">Bill setup</p>
            <h2 className="mt-2 text-2xl font-bold" id="create-room-title">Create split room</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              This creates one shareable bill. For trips or recurring groups, use My rooms to keep
              several bills and their pending or cleared totals together.
            </p>
            <Link className="mt-3 inline-flex min-h-11 items-center font-semibold text-info" href="/dashboard">
              Create a persistent room instead →
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
    <li className="rounded-md border border-border bg-surface p-4">
      <span className="grid h-10 w-10 place-items-center rounded-md bg-info-soft text-info">{icon}</span>
      <p className="mt-4 font-bold">{label}</p>
      <p className="mt-1 text-sm leading-6 text-muted">{detail}</p>
    </li>
  );
}

function TrustPill({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border bg-cloud px-3 font-semibold">
      {icon}
      {label}
    </span>
  );
}
