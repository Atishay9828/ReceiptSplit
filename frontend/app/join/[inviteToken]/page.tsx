"use client";

import { Link2, Loader2, LogIn, ShieldCheck } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/error-state";
import { GoogleSignIn } from "@/components/google-sign-in";
import { JoinForm } from "@/components/join-form";
import { api } from "@/lib/api";
import { getAccountSession, type AccountSession } from "@/lib/auth-session";
import { decodeInviteParam } from "@/lib/invite";
import { saveCreatorSession, saveParticipantSession } from "@/lib/storage";

export default function JoinPage() {
  const params = useParams<{ inviteToken: string }>();
  const router = useRouter();
  const decoded = decodeInviteParam(params.inviteToken);
  const [account, setAccount] = useState<AccountSession | null>(null);
  const [sessionLoaded, setSessionLoaded] = useState(false);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setAccount(getAccountSession());
      setSessionLoaded(true);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  if (!decoded) {
    return (
      <main className="rs-page-shell rs-auth-page mx-auto grid min-h-dvh max-w-md content-center px-4 py-8">
        <ErrorState
          message="Invalid invite link"
          detail="This invite may have expired. Ask the host for a new private link."
        />
      </main>
    );
  }

  if (!sessionLoaded) {
    return (
      <main className="rs-page-shell rs-auth-page mx-auto grid min-h-dvh max-w-md content-center px-4 py-8 text-ink">
        <section className="rs-auth-card rs-panel rounded-md border border-border bg-surface p-5 shadow-soft">
          <div className="flex items-center gap-3 text-sm font-medium text-muted">
            <Loader2 size={18} className="animate-spin text-info" aria-hidden="true" />
            Opening invite...
          </div>
        </section>
      </main>
    );
  }

  const invite = decoded;

  if (!account) {
    return (
      <main className="rs-page-shell rs-auth-page mx-auto grid min-h-dvh max-w-md content-center px-4 py-8 text-ink">
        <section className="rs-auth-card rs-panel rounded-md border border-border bg-surface p-5 shadow-soft">
          <span className="inline-grid h-11 w-11 place-items-center rounded-md bg-info-soft text-info">
            <LogIn size={22} aria-hidden="true" />
          </span>
          <p className="mt-5 text-sm font-semibold uppercase text-info">ReceiptSplit invite</p>
          <h1 className="mt-1 text-3xl font-bold">Create your account to join</h1>
          <p className="mt-3 text-sm leading-6 text-muted">
            Continue with Google. If you are new, your ReceiptSplit account is created
            automatically, then you can open this bill.
          </p>
          <div className="mt-6">
            <GoogleSignIn onSignedIn={setAccount} />
          </div>
          <p className="mt-5 rounded-md bg-cloud px-3 py-2 text-sm text-muted">
            Everyone on a bill signs in so their share stays linked to the right person.
          </p>
        </section>
      </main>
    );
  }
  const signedInAccount = account;

  async function join(nickname: string) {
    const joined = await api.joinRoom(
      invite.roomId,
      invite.inviteToken,
      nickname,
      signedInAccount.token
    );
    if (joined.participant.role === "creator") {
      saveCreatorSession({
        roomId: invite.roomId,
        role: "creator",
        token: signedInAccount.token,
        inviteToken: invite.inviteToken,
        lastSequence: 0
      });
      router.push(`/rooms/${invite.roomId}/creator`);
      return;
    }
    saveParticipantSession({
      roomId: invite.roomId,
      role: "participant",
      token: signedInAccount.token,
      participantId: joined.participant.id,
      nickname: joined.participant.nickname,
      lastSequence: 0
    });
    router.push(`/rooms/${invite.roomId}`);
  }

  const accountName =
    signedInAccount.user.display_name ?? signedInAccount.user.username ?? signedInAccount.user.email?.split("@")[0] ?? "";

  return (
    <main className="rs-page-shell rs-auth-page mx-auto grid min-h-dvh max-w-md content-center px-4 py-8 text-ink">
      <section className="rs-auth-card rs-panel rounded-md border border-border bg-surface p-5 shadow-soft">
        <div className="mb-5 grid gap-3">
          <span className="inline-grid h-11 w-11 place-items-center rounded-md bg-info-soft text-info">
            <Link2 size={22} aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-semibold uppercase text-info">ReceiptSplit invite</p>
            <h1 className="mt-1 text-3xl font-bold">Choose your share</h1>
            <p className="mt-2 text-sm leading-6 text-muted">
              Confirm the name people will see, then add the items you had to your share.
            </p>
          </div>
        </div>
        <div>
          <JoinForm
            onJoin={join}
            inputLabel="Name shown on this bill"
            submitLabel="Open bill"
            initialNickname={accountName}
          />
          <p className="mt-4 inline-flex items-center gap-2 rounded-md bg-cloud px-3 py-2 text-sm font-medium text-muted">
            <ShieldCheck size={16} aria-hidden="true" />
            Signed in{accountName ? ` as ${accountName}` : ""}. Your account stays linked to this share.
          </p>
        </div>
      </section>
    </main>
  );
}
