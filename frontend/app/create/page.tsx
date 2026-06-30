"use client";

import { ReceiptText } from "lucide-react";
import { useRouter } from "next/navigation";

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
    <main className="mx-auto grid min-h-dvh max-w-xl content-center gap-5 px-4 py-8 text-ink">
      <section className="rounded-md bg-white p-5 shadow-soft">
        <div className="mb-5 flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-md bg-mint text-leaf">
            <ReceiptText size={24} aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-2xl font-bold">ReceiptSplit</h1>
            <p className="text-sm text-[#63706b]">Create a room, add items, share the link.</p>
          </div>
        </div>
        <CreateRoomForm onCreate={createRoom} />
      </section>
    </main>
  );
}
