"use client";

import { Link2, ShieldCheck } from "lucide-react";
import { useParams, useRouter } from "next/navigation";

import { ErrorState } from "@/components/error-state";
import { JoinForm } from "@/components/join-form";
import { api } from "@/lib/api";
import { decodeInviteParam } from "@/lib/invite";
import { saveParticipantSession } from "@/lib/storage";

export default function JoinPage() {
  const params = useParams<{ inviteToken: string }>();
  const router = useRouter();
  const decoded = decodeInviteParam(params.inviteToken);

  if (!decoded) {
    return (
      <main className="mx-auto max-w-md px-4 py-8">
        <ErrorState message="Invalid invite link" />
      </main>
    );
  }

  const invite = decoded;

  async function join(nickname: string) {
    const joined = await api.joinRoom(invite.roomId, invite.inviteToken, nickname);
    saveParticipantSession({
      roomId: invite.roomId,
      role: "participant",
      token: joined.participant_token,
      participantId: joined.participant.id,
      nickname: joined.participant.nickname,
      lastSequence: 0
    });
    router.push(`/rooms/${invite.roomId}`);
  }

  return (
    <main className="mx-auto grid min-h-dvh max-w-md content-center px-4 py-8 text-ink">
      <section className="rounded-md border border-border bg-surface p-5 shadow-soft">
        <div className="mb-5 grid gap-3">
          <span className="inline-grid h-11 w-11 place-items-center rounded-md bg-mint text-leaf">
            <Link2 size={22} aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-semibold uppercase text-leaf">ReceiptSplit invite</p>
            <h1 className="mt-1 text-3xl font-bold">Join this split</h1>
            <p className="mt-2 text-sm leading-6 text-muted">
              Add your name, claim your items, and see exactly what you owe.
            </p>
          </div>
        </div>
        <div>
          <JoinForm onJoin={join} inputLabel="Your name" submitLabel="Join split" />
          <p className="mt-4 inline-flex items-center gap-2 rounded-md bg-cloud px-3 py-2 text-sm font-medium text-muted">
            <ShieldCheck size={16} aria-hidden="true" />
            No account needed. Use any nickname.
          </p>
        </div>
      </section>
    </main>
  );
}
