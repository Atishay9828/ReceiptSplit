"use client";

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
      <section className="rounded-md bg-white p-5 shadow-soft">
        <h1 className="text-2xl font-bold">Join Room</h1>
        <div className="mt-5">
          <JoinForm onJoin={join} />
        </div>
      </section>
    </main>
  );
}
