"use client";

import { CheckCircle2, ReceiptText, Smartphone, WalletCards } from "lucide-react";
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
    <main className="mx-auto grid min-h-dvh w-full max-w-5xl content-center gap-5 px-4 py-8 text-ink sm:px-6">
      <section className="grid gap-5 rounded-md border border-[#dbe5df] bg-white p-5 shadow-soft sm:p-7 lg:grid-cols-[1fr_420px] lg:items-center">
        <div className="grid gap-5">
          <span className="inline-grid h-12 w-12 place-items-center rounded-md bg-mint text-leaf">
            <ReceiptText size={26} aria-hidden="true" />
          </span>
          <div className="grid gap-3">
            <p className="text-sm font-semibold uppercase text-leaf">ReceiptSplit</p>
            <h1 className="max-w-xl text-3xl font-bold leading-tight sm:text-5xl">
              Split a receipt with friends in under a minute.
            </h1>
            <p className="max-w-xl text-base leading-7 text-[#52625b]">
              Upload a bill, let friends claim what they had, and settle directly through UPI.
            </p>
          </div>
          <div className="grid gap-2 text-sm sm:grid-cols-3">
            <TrustPill icon={<Smartphone size={16} aria-hidden="true" />} label="No app needed for friends" />
            <TrustPill icon={<WalletCards size={16} aria-hidden="true" />} label="No wallet" />
            <TrustPill icon={<CheckCircle2 size={16} aria-hidden="true" />} label="Direct UPI payment" />
          </div>
        </div>
        <div className="rounded-md border border-[#dbe5df] bg-cloud/70 p-4 sm:p-5">
          <div className="mb-4">
            <h2 className="text-xl font-bold">Create split room</h2>
            <p className="mt-1 text-sm text-[#63706b]">No awkward maths. Claim food, split cleanly.</p>
          </div>
          <CreateRoomForm onCreate={createRoom} submitLabel="Create split room" />
        </div>
      </section>
    </main>
  );
}

function TrustPill({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="inline-flex min-h-11 items-center gap-2 rounded-md border border-[#dbe5df] bg-cloud px-3 font-semibold">
      {icon}
      {label}
    </span>
  );
}
