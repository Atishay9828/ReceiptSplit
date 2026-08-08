"use client";

import { CheckCircle2, Clock3, LogOut, Plus, ReceiptText, UserPlus, UsersRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { GoogleSignIn } from "@/components/google-sign-in";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { clearAccountSession, getAccountSession, saveAccountSession, type AccountSession } from "@/lib/auth-session";
import { formatPaise } from "@/lib/money";
import { getCreatorSession, saveCreatorSession, saveParticipantSession } from "@/lib/storage";
import type { CommunityUser, Group, GroupBillSummary, SplitMode } from "@/types/api";

export default function DashboardPage() {
  const router = useRouter();
  const [session, setSession] = useState<AccountSession | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [groups, setGroups] = useState<Group[]>([]);
  const [friends, setFriends] = useState<CommunityUser[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (active: AccountSession) => {
    try {
      setError(null);
      const [groupResult, friendResult] = await Promise.all([
        api.listGroups(active.token),
        api.listFriends(active.token)
      ]);
      setGroups(groupResult.groups);
      setFriends(friendResult.friends);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Could not load your rooms");
    }
  }, []);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const saved = getAccountSession();
      setSession(saved);
      setLoaded(true);
      if (saved?.user.username) void refresh(saved);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [refresh]);

  async function saveProfile(username: string, displayName: string) {
    if (!session) return;
    const updated = await api.updateProfile(session.token, { username, display_name: displayName });
    const next = { ...session, user: { ...session.user, ...updated } };
    saveAccountSession(next);
    setSession(next);
    await refresh(next);
  }

  function openBill(bill: GroupBillSummary) {
    if (!session || !bill.current_participant_id) return;
    if (bill.is_creator) {
      const existing = getCreatorSession(bill.id);
      saveCreatorSession({
        roomId: bill.id,
        role: "creator",
        token: session.token,
        inviteToken: existing?.inviteToken ?? "",
        lastSequence: existing?.lastSequence ?? 0
      });
      router.push(`/rooms/${bill.id}/creator`);
      return;
    }
    saveParticipantSession({
      roomId: bill.id,
      role: "participant",
      token: session.token,
      participantId: bill.current_participant_id,
      nickname: session.user.display_name ?? session.user.username ?? "You",
      lastSequence: 0
    });
    router.push(`/rooms/${bill.id}`);
  }

  if (!loaded) return null;

  return (
    <main className="rs-page-shell rs-dashboard-page mx-auto min-h-dvh w-full max-w-6xl px-4 py-8 sm:px-6">
      <header className="rs-topbar flex flex-wrap items-center justify-between gap-4 border-b border-border pb-5">
        <Link className="flex items-center gap-2 text-lg font-bold" href="/"><ReceiptText size={22} /> ReceiptSplit</Link>
        {session ? <Button type="button" variant="ghost" onClick={() => { clearAccountSession(); setSession(null); setGroups([]); setFriends([]); }}><LogOut size={16} /> Sign out</Button> : null}
      </header>

      {!session ? (
        <section className="rs-panel mx-auto mt-16 max-w-lg rounded-lg border border-border bg-surface p-6 shadow-soft">
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-info">Your account</p>
          <h1 className="mt-2 text-3xl font-bold">Keep rooms, friends, and bills together.</h1>
          <p className="mt-3 text-sm leading-6 text-muted">Sign in to create rooms, join bill invites, keep friends, and return to your bills on any device.</p>
          <div className="mt-6"><GoogleSignIn onSignedIn={(next) => { setSession(next); if (next.user.username) void refresh(next); }} /></div>
        </section>
      ) : !session.user.username ? (
        <ProfileSetup session={session} onSave={saveProfile} />
      ) : (
        <div className="mt-8 grid gap-8">
          <section><p className="text-sm font-semibold text-info">@{session.user.username}</p><h1 className="mt-1 text-4xl font-bold">Your rooms</h1><p className="mt-2 text-muted">A room stays open across many bills. Settled bills move to cleared; unpaid shares stay pending.</p></section>
          {error ? <p className="rounded-md bg-danger-soft p-4 font-semibold text-coral">{error}</p> : null}
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
            <section className="grid gap-4">
              {groups.length === 0 ? <div className="rounded-lg border border-dashed border-border bg-surface p-8 text-center"><UsersRound className="mx-auto text-info" /><h2 className="mt-3 text-xl font-bold">No persistent rooms yet</h2><p className="mt-2 text-sm text-muted">Add friends, then create a trip or group room.</p></div> : null}
              {groups.map((group) => <GroupCard key={group.id} group={group} session={session} onOpenBill={openBill} onChanged={() => refresh(session)} />)}
            </section>
            <aside className="grid content-start gap-5">
              <FriendsPanel friends={friends} onAdd={async (username) => { await api.addFriend(session.token, username); await refresh(session); }} />
              <CreateGroupPanel friends={friends} onCreate={async (name, memberUsernames) => { await api.createGroup(session.token, { name, member_usernames: memberUsernames }); await refresh(session); }} />
            </aside>
          </div>
        </div>
      )}
    </main>
  );
}

function ProfileSetup({ session, onSave }: { session: AccountSession; onSave: (username: string, displayName: string) => Promise<void> }) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState(session.user.email?.split("@")[0] ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return <form className="rs-panel rs-form mx-auto mt-16 grid max-w-lg gap-4 rounded-lg border border-border bg-surface p-6 shadow-soft" onSubmit={async (event) => { event.preventDefault(); setBusy(true); setError(null); try { await onSave(username.trim().toLowerCase(), displayName.trim()); } catch (saveError) { setError(saveError instanceof Error ? saveError.message : "Could not save profile"); } finally { setBusy(false); } }}>
    <h1 className="text-3xl font-bold">Choose how friends find you</h1><p className="text-sm text-muted">Usernames use lowercase letters, numbers, and underscores.</p>
    <Input label="Display name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
    <Input label="Username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="aj_98" />
    {error ? <p className="text-sm font-semibold text-coral">{error}</p> : null}<Button type="submit" disabled={busy || !username || !displayName}>{busy ? "Saving..." : "Save profile"}</Button>
  </form>;
}

function FriendsPanel({ friends, onAdd }: { friends: CommunityUser[]; onAdd: (username: string) => Promise<void> }) {
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  return <section className="rs-panel rounded-lg border border-border bg-surface p-5 shadow-soft"><h2 className="flex items-center gap-2 text-xl font-bold"><UserPlus size={19} /> Friends</h2>
    <form className="mt-4 grid gap-3" onSubmit={async (event) => { event.preventDefault(); setError(null); try { await onAdd(username.trim().toLowerCase()); setUsername(""); } catch (addError) { setError(addError instanceof Error ? addError.message : "Could not add friend"); } }}>
      <Input label="Add by username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="friend_username" /><Button type="submit" variant="secondary" disabled={!username.trim()}>Add friend</Button>
    </form>{error ? <p className="mt-2 text-sm font-semibold text-coral">{error}</p> : null}
    <div className="mt-4 grid gap-2">{friends.map((friend) => <div className="rounded-md bg-cloud px-3 py-2 text-sm" key={friend.id}><strong>{friend.display_name ?? friend.username}</strong><p className="text-muted">@{friend.username}</p></div>)}{friends.length === 0 ? <p className="text-sm text-muted">No friends added yet.</p> : null}</div>
  </section>;
}

function CreateGroupPanel({ friends, onCreate }: { friends: CommunityUser[]; onCreate: (name: string, members: string[]) => Promise<void> }) {
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  return <form className="rs-panel rs-form rounded-lg border border-border bg-surface p-5 shadow-soft" onSubmit={async (event) => { event.preventDefault(); await onCreate(name.trim(), selected); setName(""); setSelected([]); }}>
    <h2 className="text-xl font-bold">New room</h2><p className="mt-1 text-sm text-muted">For a trip, flat, team, or recurring group.</p><div className="mt-4"><Input label="Room name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Goa trip" /></div>
    <fieldset className="mt-4 grid gap-2"><legend className="text-sm font-semibold">Friends in this room</legend>{friends.map((friend) => <label className="flex min-h-11 items-center gap-3 rounded-md bg-cloud px-3" key={friend.id}><input type="checkbox" checked={Boolean(friend.username && selected.includes(friend.username))} onChange={() => friend.username && setSelected((current) => current.includes(friend.username!) ? current.filter((entry) => entry !== friend.username) : [...current, friend.username!])} /><span>{friend.display_name ?? friend.username}</span></label>)}</fieldset>
    <Button className="mt-4 w-full" type="submit" disabled={!name.trim()}><Plus size={16} /> Create room</Button>
  </form>;
}

function GroupCard({ group, session, onOpenBill, onChanged }: { group: Group; session: AccountSession; onOpenBill: (bill: GroupBillSummary) => void; onChanged: () => Promise<void> }) {
  const [adding, setAdding] = useState(false);
  return <article className="rs-panel rounded-lg border border-border bg-surface p-5 shadow-soft">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-2xl font-bold">{group.name}</h2><p className="mt-1 text-sm text-muted">{group.members.map((member) => member.display_name ?? member.username).join(", ")}</p></div>{group.role === "owner" ? <Button type="button" onClick={() => setAdding((value) => !value)}><Plus size={16} /> Add bill</Button> : null}</div>
    <div className="mt-4 grid grid-cols-3 gap-2"><Stat label="All bills" value={formatPaise(group.total_paise)} /><Stat label="Pending" value={formatPaise(group.pending_paise)} icon={<Clock3 size={14} />} /><Stat label="Cleared" value={formatPaise(group.cleared_paise)} icon={<CheckCircle2 size={14} />} /></div>
    {adding ? <NewBillForm onCreate={async (payload) => { const created = await api.createGroupBill(session.token, group.id, payload); saveCreatorSession({ roomId: created.bill.room.id, role: "creator", token: session.token, inviteToken: created.bill.invite_token, lastSequence: 0 }); setAdding(false); await onChanged(); }} /> : null}
    <div className="mt-5 grid gap-3">{group.bills.map((bill) => <button key={bill.id} type="button" className="flex min-h-16 w-full items-center justify-between gap-4 rounded-md border border-border bg-cloud px-4 py-3 text-left hover:border-info" onClick={() => onOpenBill(bill)}><span><strong>{bill.title}</strong><span className="mt-1 block text-xs text-muted">{new Date(bill.created_at).toLocaleDateString()} · {bill.status}</span></span><span className="text-right text-sm"><strong>{formatPaise(bill.grand_total_paise)}</strong><span className="block text-xs text-muted">{formatPaise(bill.pending_paise)} pending</span></span></button>)}{group.bills.length === 0 ? <p className="rounded-md bg-cloud p-4 text-sm text-muted">No bills yet. Add the first receipt without closing this room.</p> : null}</div>
  </article>;
}

function NewBillForm({ onCreate }: { onCreate: (payload: { title: string; split_mode: SplitMode; payer_name?: string; payer_vpa?: string }) => Promise<void> }) {
  const [title, setTitle] = useState(""); const [mode, setMode] = useState<SplitMode>("item_wise"); const [payerName, setPayerName] = useState(""); const [payerVpa, setPayerVpa] = useState("");
  return <form className="mt-4 grid gap-3 rounded-md border border-border bg-cloud p-4" onSubmit={async (event) => { event.preventDefault(); await onCreate({ title: title.trim(), split_mode: mode, payer_name: payerName.trim() || undefined, payer_vpa: payerVpa.trim() || undefined }); }}><h3 className="font-bold">Add another bill</h3><Input label="Bill title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Dinner - day 2" /><Select label="Default split" value={mode} onChange={(event) => setMode(event.target.value as SplitMode)}><option value="item_wise">Mixed items</option><option value="equal">Everything equal</option></Select><div className="grid gap-3 sm:grid-cols-2"><Input label="Payer name" value={payerName} onChange={(event) => setPayerName(event.target.value)} /><Input label="Payer VPA" value={payerVpa} onChange={(event) => setPayerVpa(event.target.value)} placeholder="name@bank" /></div><Button type="submit" disabled={!title.trim()}>Create bill</Button></form>;
}

function Stat({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) { return <div className="rounded-md bg-cloud p-3"><p className="flex items-center gap-1 text-xs font-semibold text-muted">{icon}{label}</p><strong className="mt-1 block text-sm sm:text-base">{value}</strong></div>; }
