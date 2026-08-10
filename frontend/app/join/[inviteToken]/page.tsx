"use client";

import { ArrowRight, CheckCircle2, Link2, Loader2, LogIn, ShieldCheck, UsersRound } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

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
      <JoinShell>
        <main className="rs-join-main rs-join-error-main">
          <section className="rs-join-error-panel">
            <p className="rs-kicker">Invite unavailable</p>
            <ErrorState message="Invalid invite link" detail="This invite may have expired. Ask the host for a new private link." />
            <Link className="rs-reference-quiet-action" href="/">Back to ReceiptSplit <ArrowRight size={15} aria-hidden="true" /></Link>
          </section>
        </main>
      </JoinShell>
    );
  }

  if (!sessionLoaded) {
    return (
      <JoinShell>
        <main className="rs-join-main rs-join-loading-main">
          <section className="rs-join-form-panel"><Loader2 size={19} className="animate-spin" aria-hidden="true" /> Opening invite...</section>
        </main>
      </JoinShell>
    );
  }

  const invite = decoded;

  if (!account) {
    return (
      <JoinShell>
        <main className="rs-join-main">
          <JoinIntro />
          <section className="rs-join-form-panel" aria-labelledby="join-account-title">
            <div className="rs-join-form-heading"><span className="rs-join-icon"><LogIn size={19} aria-hidden="true" /></span><div><p className="rs-form-label">ReceiptSplit invite</p><h1 id="join-account-title">Create your account to join</h1></div></div>
            <p>Continue with Google. If you are new, your ReceiptSplit account is created automatically, then you can open this bill.</p>
            <div className="rs-join-google"><GoogleSignIn onSignedIn={setAccount} /></div>
            <p className="rs-join-safety"><ShieldCheck size={16} aria-hidden="true" /> Everyone on a bill signs in so their share stays linked to the right person.</p>
          </section>
        </main>
      </JoinShell>
    );
  }

  const signedInAccount = account;
  async function join(nickname: string) {
    const joined = await api.joinRoom(invite.roomId, invite.inviteToken, nickname, signedInAccount.token);
    if (joined.participant.role === "creator") {
      saveCreatorSession({ roomId: invite.roomId, role: "creator", token: signedInAccount.token, inviteToken: invite.inviteToken, lastSequence: 0 });
      router.push(`/rooms/${invite.roomId}/creator`);
      return;
    }
    saveParticipantSession({ roomId: invite.roomId, role: "participant", token: signedInAccount.token, participantId: joined.participant.id, nickname: joined.participant.nickname, lastSequence: 0 });
    router.push(`/rooms/${invite.roomId}`);
  }

  const accountName = signedInAccount.user.display_name ?? signedInAccount.user.username ?? signedInAccount.user.email?.split("@")[0] ?? "";

  return (
    <JoinShell>
      <main className="rs-join-main">
        <JoinIntro />
        <section className="rs-join-form-panel" aria-labelledby="join-share-title">
          <div className="rs-join-form-heading"><span className="rs-join-icon"><Link2 size={19} aria-hidden="true" /></span><div><p className="rs-form-label">ReceiptSplit invite</p><h1 id="join-share-title">Choose your share</h1></div></div>
          <p>Confirm the name people will see, then add the items you had to your share.</p>
          <JoinForm onJoin={join} inputLabel="Name shown on this bill" submitLabel="Open bill" initialNickname={accountName} />
          <p className="rs-join-safety"><ShieldCheck size={16} aria-hidden="true" /> Signed in{accountName ? ` as ${accountName}` : ""}. Your account stays linked to this share.</p>
        </section>
      </main>
    </JoinShell>
  );
}

function JoinShell({ children }: { children: ReactNode }) {
  return (
    <div className="rs-page-shell rs-join-page">
      <header className="rs-topbar">
        <div className="rs-app-header-inner">
          <Link className="rs-reference-brand" href="/">ReceiptSplit</Link>
          <nav className="rs-reference-nav" aria-label="Main navigation"><Link href="/#how-it-works">How it works</Link><Link href="/dashboard">My rooms</Link></nav>
          <div className="rs-reference-actions"><Link className="rs-reference-quiet-action" href="/#invite">Open invite <ArrowRight size={15} aria-hidden="true" /></Link><Link className="rs-reference-cta" href="/create">Create a split</Link></div>
        </div>
      </header>
      {children}
    </div>
  );
}

function JoinIntro() {
  return (
    <section className="rs-join-intro" aria-labelledby="join-intro-title">
      <div><p className="rs-kicker">Private bill invite</p><h1 id="join-intro-title">Open the bill without joining the group chat.</h1><p className="rs-join-lead">Choose only what belongs in your share. The payer receives a clear total, and the payment stays direct.</p></div>
      <ol className="rs-join-steps">
        <JoinStep icon={<Link2 size={18} aria-hidden="true" />} label="Open the private link" detail="The invite identifies one bill and one room." />
        <JoinStep icon={<UsersRound size={18} aria-hidden="true" />} label="Choose your items" detail="Claim only what you had, with quantities visible." />
        <JoinStep icon={<CheckCircle2 size={18} aria-hidden="true" />} label="Pay the payer directly" detail="The payer confirms the share manually." />
      </ol>
      <p className="rs-join-boundary"><ShieldCheck size={16} aria-hidden="true" /> No wallet. No escrow. No payment verification claim.</p>
    </section>
  );
}

function JoinStep({ icon, label, detail }: { icon: ReactNode; label: string; detail: string }) {
  return <li><span className="rs-join-step-icon">{icon}</span><div><strong>{label}</strong><span>{detail}</span></div></li>;
}
