"use client";

import {
  Activity,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  LayoutDashboard,
  LogOut,
  Plus,
  ReceiptText,
  UserPlus,
  UsersRound
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

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

  function signOut() {
    clearAccountSession();
    setSession(null);
    setGroups([]);
    setFriends([]);
  }

  if (!loaded) return null;

  return (
    <div className="rs-page-shell rs-dashboard-page">
      <header className="rs-topbar">
        <div className="rs-app-header-inner">
          <Link className="rs-reference-brand" href="/">
            ReceiptSplit
          </Link>
          <nav className="rs-reference-nav" aria-label="Main navigation">
            <Link className="is-active" href="/dashboard"><LayoutDashboard size={15} aria-hidden="true" /> Dashboard</Link>
            <Link href="/dashboard"><ReceiptText size={15} aria-hidden="true" /> Rooms</Link>
            <Link href="/dashboard"><span className="rs-nav-activity-dot" aria-hidden="true" /> Activity</Link>
          </nav>
          <div className="rs-reference-actions">
            {session ? <span className="rs-dashboard-user">{session.user.display_name ?? session.user.username ?? "You"}</span> : null}
            {session ? (
              <button className="rs-dashboard-signout" type="button" onClick={signOut}>
                <LogOut size={15} aria-hidden="true" /> Sign out
              </button>
            ) : null}
            <Link className="rs-reference-quiet-action" href="/#invite">
              Open invite <ArrowRight size={15} aria-hidden="true" />
            </Link>
            <Link className="rs-reference-cta" href="/create">
              Create a split
            </Link>
          </div>
        </div>
      </header>

      {!session ? (
        <main className="rs-dashboard-main rs-account-main">
          <section className="rs-account-gate" aria-labelledby="account-title">
            <div className="rs-account-gate-copy">
              <p className="rs-kicker">Your account</p>
              <h1 id="account-title">Keep rooms, friends, and bills together.</h1>
              <p>Sign in to create rooms, join bill invites, keep friends, and return to your bills on any device.</p>
            </div>
            <div className="rs-account-gate-action">
              <GoogleSignIn onSignedIn={(next) => { setSession(next); if (next.user.username) void refresh(next); }} />
            </div>
          </section>
        </main>
      ) : !session.user.username ? (
        <main className="rs-dashboard-main">
          <ProfileSetup session={session} onSave={saveProfile} />
        </main>
      ) : (
        <main className="rs-dashboard-main">
          <section className="rs-dashboard-heading">
            <div>
              <nav className="rs-dashboard-breadcrumb" aria-label="Breadcrumb"><Link href="/dashboard">Dashboard</Link><span aria-hidden="true">/</span><strong aria-current="page">My rooms</strong></nav>
              <p className="rs-kicker">@{session.user.username}</p>
              <div className="rs-dashboard-title-row">
                <h1>Your rooms</h1>
                <Link className="rs-dashboard-create" href="/create"><Plus size={16} aria-hidden="true" /> New room</Link>
              </div>
              <p className="rs-dashboard-lead">Keep trips and recurring groups together. Bills stay open until the payer confirms each share.</p>
            </div>
            <div className="rs-dashboard-heading-note"><span className="rs-live-dot" aria-hidden="true" /> Synced just now</div>
          </section>

          {error ? <p className="rs-dashboard-alert" role="alert">{error}</p> : null}

          <RoomSwitcher groups={groups} />

          <section className="rs-dashboard-metrics" aria-label="Room totals">
            <DashboardMetric label="Rooms" value={String(groups.length)} detail="Persistent spaces" icon={<UsersRound size={17} aria-hidden="true" />} />
            <DashboardMetric label="Tracked bills" value={String(groups.reduce((sum, group) => sum + group.bills.length, 0))} detail="Across your rooms" icon={<ReceiptText size={17} aria-hidden="true" />} />
            <DashboardMetric label="Pending" value={formatPaise(groups.reduce((sum, group) => sum + group.pending_paise, 0))} detail="Still to settle" icon={<Clock3 size={17} aria-hidden="true" />} tone="coral" />
            <DashboardMetric label="Cleared" value={formatPaise(groups.reduce((sum, group) => sum + group.cleared_paise, 0))} detail="Payer confirmed" icon={<CheckCircle2 size={17} aria-hidden="true" />} tone="green" />
          </section>

          <div className="rs-dashboard-layout">
            <section className="rs-dashboard-bills" aria-labelledby="rooms-title">
              <div className="rs-section-heading">
                <div><p className="rs-section-label">Workspace</p><h2 id="rooms-title">Recent rooms</h2></div>
                <span className="rs-section-count">{groups.length} {groups.length === 1 ? "room" : "rooms"}</span>
              </div>
              {groups.length === 0 ? (
                <div className="rs-empty-workspace">
                  <span className="rs-empty-icon"><ReceiptText size={20} aria-hidden="true" /></span>
                  <h3>No persistent rooms yet</h3>
                  <p>Add friends, then create a room for a trip, flat, team, or recurring group.</p>
                  <Link className="rs-dashboard-create" href="/create"><Plus size={16} aria-hidden="true" /> Create your first room</Link>
                </div>
              ) : null}
              {groups.map((group) => <GroupCard key={group.id} group={group} session={session} onOpenBill={openBill} onChanged={() => refresh(session)} />)}
            </section>

            <aside className="rs-dashboard-rail">
              <FriendsPanel friends={friends} onAdd={async (username) => { await api.addFriend(session.token, username); await refresh(session); }} />
              <RecentActivityPanel groups={groups} />
              <section className="rs-dashboard-rail-card rs-you-owe-card">
                <p className="rs-section-label">Your balance</p>
                <h2>You owe</h2>
                <strong>{formatPaise(groups.reduce((sum, group) => sum + group.pending_paise, 0))}</strong>
                <p>Pending shares remain visible until the payer confirms them.</p>
              </section>
              <section className="rs-dashboard-rail-card rs-how-card">
                <p className="rs-section-label">How it works</p>
                <h2>One room. Many bills.</h2>
                <ol>
                  <li><span>01</span><p>Create a room for your group.</p></li>
                  <li><span>02</span><p>Add bills as they happen.</p></li>
                  <li><span>03</span><p>Keep pending and cleared shares together.</p></li>
                </ol>
              </section>
              <CreateGroupPanel friends={friends} onCreate={async (name, memberUsernames) => { await api.createGroup(session.token, { name, member_usernames: memberUsernames }); await refresh(session); }} />
            </aside>
          </div>
        </main>
      )}
    </div>
  );
}

function ProfileSetup({ session, onSave }: { session: AccountSession; onSave: (username: string, displayName: string) => Promise<void> }) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState(session.user.email?.split("@")[0] ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <form className="rs-profile-setup" onSubmit={async (event) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        await onSave(username.trim().toLowerCase(), displayName.trim());
      } catch (saveError) {
        setError(saveError instanceof Error ? saveError.message : "Could not save profile");
      } finally {
        setBusy(false);
      }
    }}>
      <div><p className="rs-kicker">Set up your profile</p><h1>Choose how friends find you.</h1><p>Usernames use lowercase letters, numbers, and underscores.</p></div>
      <Input label="Display name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
      <Input label="Username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="aj_98" />
      {error ? <p className="rs-dashboard-alert" role="alert">{error}</p> : null}
      <Button type="submit" disabled={busy || !username || !displayName}>{busy ? "Saving..." : "Save profile"}</Button>
    </form>
  );
}

function RoomSwitcher({ groups }: { groups: Group[] }) {
  const railRef = useRef<HTMLDivElement>(null);

  function scrollRooms(direction: number) {
    railRef.current?.scrollBy({ left: direction * 280, behavior: "smooth" });
  }

  if (groups.length === 0) return null;

  return (
    <section className="rs-room-switcher" aria-labelledby="room-switcher-title">
      <div className="rs-room-switcher-heading">
        <div>
          <p className="rs-section-label">Jump back in</p>
          <h2 id="room-switcher-title">Jump between rooms</h2>
        </div>
        <div className="rs-room-switcher-controls">
          <button type="button" className="rs-icon-button" onClick={() => scrollRooms(-1)} aria-label="Previous rooms" title="Previous rooms">
            <ChevronLeft size={17} aria-hidden="true" />
          </button>
          <button type="button" className="rs-icon-button" onClick={() => scrollRooms(1)} aria-label="Next rooms" title="Next rooms">
            <ChevronRight size={17} aria-hidden="true" />
          </button>
        </div>
      </div>
      <div className="rs-room-switcher-rail" ref={railRef} role="list">
        {groups.map((group) => {
          const total = Math.max(group.total_paise, 1);
          const clearedPercent = Math.min(100, Math.round((group.cleared_paise / total) * 100));
          return (
            <a className="rs-room-switch-card" href={`#room-${group.id}`} key={group.id} role="listitem">
              <span className="rs-room-switch-card-top"><strong>{group.name}</strong><ArrowRight size={15} aria-hidden="true" /></span>
              <span className="rs-room-switch-card-meta">{group.bills.length} {group.bills.length === 1 ? "bill" : "bills"} - {group.members.length} {group.members.length === 1 ? "person" : "people"}</span>
              <span className="rs-room-switch-card-track" aria-hidden="true"><span style={{ width: `${clearedPercent}%` }} /></span>
              <span className="rs-room-switch-card-total"><span>{formatPaise(group.pending_paise)} pending</span><strong>{formatPaise(group.total_paise)}</strong></span>
            </a>
          );
        })}
      </div>
    </section>
  );
}

function FriendsPanel({ friends, onAdd }: { friends: CommunityUser[]; onAdd: (username: string) => Promise<void> }) {
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <section className="rs-dashboard-rail-card rs-friends-card">
      <div className="rs-rail-card-heading"><div><p className="rs-section-label">People</p><h2>Friends</h2></div><UserPlus size={18} aria-hidden="true" /></div>
      <form className="rs-friend-form" onSubmit={async (event) => {
        event.preventDefault();
        setError(null);
        try {
          await onAdd(username.trim().toLowerCase());
          setUsername("");
        } catch (addError) {
          setError(addError instanceof Error ? addError.message : "Could not add friend");
        }
      }}>
        <Input label="Add by username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="friend_username" />
        <Button type="submit" variant="secondary" disabled={!username.trim()}><Plus size={15} aria-hidden="true" /> Add friend</Button>
      </form>
      {error ? <p className="rs-inline-error" role="alert">{error}</p> : null}
      <div className="rs-friend-list">
        {friends.map((friend) => { const display = friend.display_name ?? friend.username ?? "Friend"; return <div className="rs-friend-row" key={friend.id}><span className="rs-friend-avatar">{initials(display)}</span><div><strong>{display}</strong><span>@{friend.username ?? "friend"}</span></div></div>; })}
        {friends.length === 0 ? <p className="rs-empty-copy">No friends added yet.</p> : null}
      </div>
    </section>
  );
}

function RecentActivityPanel({ groups }: { groups: Group[] }) {
  const events = groups
    .flatMap((group) => group.bills.slice(0, 3).map((bill) => ({ group, bill })))
    .sort((a, b) => new Date(b.bill.created_at).getTime() - new Date(a.bill.created_at).getTime())
    .slice(0, 4);

  return (
    <section className="rs-dashboard-rail-card rs-activity-card">
      <div className="rs-rail-card-heading">
        <div><p className="rs-section-label">Timeline</p><h2>Recent activity</h2></div>
        <Activity size={18} aria-hidden="true" />
      </div>
      <div className="rs-event-list">
        {events.length === 0 ? <p className="rs-empty-copy">Room activity will appear here as bills are added.</p> : null}
        {events.map(({ group, bill }) => (
          <details className="rs-event-card" key={`${group.id}-${bill.id}`}>
            <summary>
              <span className="rs-event-icon"><ReceiptText size={15} aria-hidden="true" /></span>
              <span className="rs-event-summary"><strong>{bill.title}</strong><small>{group.name} - {new Date(bill.created_at).toLocaleDateString()}</small></span>
              <span className={`rs-bill-status rs-bill-status-${bill.status}`}>{bill.status === "active" ? "Open" : bill.status}</span>
            </summary>
            <div className="rs-event-details">
              <p>{formatPaise(bill.grand_total_paise)} tracked with {formatPaise(bill.pending_paise)} still pending.</p>
              <a href={`#room-${group.id}`}>View room <ArrowRight size={14} aria-hidden="true" /></a>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

function CreateGroupPanel({ friends, onCreate }: { friends: CommunityUser[]; onCreate: (name: string, members: string[]) => Promise<void> }) {
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<string[]>([]);

  return (
    <form className="rs-dashboard-rail-card rs-new-room-card" onSubmit={async (event) => {
      event.preventDefault();
      await onCreate(name.trim(), selected);
      setName("");
      setSelected([]);
    }}>
      <p className="rs-section-label">New workspace</p>
      <h2>Create a room</h2>
      <p>For a trip, flat, team, or recurring group.</p>
      <Input label="Room name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Goa trip" />
      <fieldset className="rs-member-picker">
        <legend>Friends in this room</legend>
        {friends.length === 0 ? <p className="rs-empty-copy">Add friends first.</p> : null}
        {friends.map((friend) => <label key={friend.id}><input type="checkbox" checked={Boolean(friend.username && selected.includes(friend.username))} onChange={() => friend.username && setSelected((current) => current.includes(friend.username!) ? current.filter((entry) => entry !== friend.username) : [...current, friend.username!])} /><span>{friend.display_name ?? friend.username}</span></label>)}
      </fieldset>
      <Button type="submit" disabled={!name.trim()}><Plus size={16} aria-hidden="true" /> Create room</Button>
    </form>
  );
}

function GroupCard({ group, session, onOpenBill, onChanged }: { group: Group; session: AccountSession; onOpenBill: (bill: GroupBillSummary) => void; onChanged: () => Promise<void> }) {
  const [adding, setAdding] = useState(false);

  return (
    <article className="rs-group-section" id={`room-${group.id}`}>
      <header className="rs-group-heading">
        <div>
          <div className="rs-group-title-line"><h3>{group.name}</h3><span className="rs-group-role">{group.role === "owner" ? "Owner" : "Member"}</span></div>
          <div className="rs-group-members">
            {group.members.slice(0, 5).map((member) => { const display = member.display_name ?? member.username ?? "Friend"; return <span className="rs-group-avatar" key={member.id} title={display}>{initials(display)}</span>; })}
            <span>{group.members.length} {group.members.length === 1 ? "person" : "people"}</span>
          </div>
        </div>
        {group.role === "owner" ? <Button type="button" variant="secondary" onClick={() => setAdding((value) => !value)}><Plus size={16} aria-hidden="true" /> Add a bill</Button> : null}
      </header>

      <div className="rs-budget-cards" aria-label={`${group.name} budget summary`}>
        <BudgetCard label="All bills" value={formatPaise(group.total_paise)} detail={`${group.bills.length} tracked`} progress={100} />
        <BudgetCard label="Pending" value={formatPaise(group.pending_paise)} detail="Needs attention" progress={Math.min(100, Math.round((group.pending_paise / Math.max(group.total_paise, 1)) * 100))} tone="coral" />
        <BudgetCard label="Cleared" value={formatPaise(group.cleared_paise)} detail="Payer confirmed" progress={Math.min(100, Math.round((group.cleared_paise / Math.max(group.total_paise, 1)) * 100))} tone="green" />
      </div>

      {adding ? <NewBillForm onCreate={async (payload) => { const created = await api.createGroupBill(session.token, group.id, payload); saveCreatorSession({ roomId: created.bill.room.id, role: "creator", token: session.token, inviteToken: created.bill.invite_token, lastSequence: 0 }); setAdding(false); await onChanged(); }} /> : null}

      <div className="rs-bills-table" role="table" aria-label={`${group.name} bills`}>
        <div className="rs-bills-table-head" role="row"><span>Bill</span><span>Date</span><span>Status</span><span className="rs-table-amount">Total</span><span aria-hidden="true" /></div>
        {group.bills.map((bill) => <button key={bill.id} type="button" className="rs-bill-row" role="row" onClick={() => onOpenBill(bill)}><span className="rs-bill-name"><ReceiptText size={16} aria-hidden="true" /><strong>{bill.title}</strong></span><span>{new Date(bill.created_at).toLocaleDateString()}</span><span><span className={`rs-bill-status rs-bill-status-${bill.status}`}>{bill.status === "active" ? "Open" : bill.status}</span></span><span className="rs-table-amount"><strong>{formatPaise(bill.grand_total_paise)}</strong><small>{formatPaise(bill.pending_paise)} pending</small></span><ArrowRight size={16} aria-hidden="true" /></button>)}
        {group.bills.length === 0 ? <p className="rs-empty-table">No bills yet. Add the first receipt without closing this room.</p> : null}
      </div>
    </article>
  );
}

function NewBillForm({ onCreate }: { onCreate: (payload: { title: string; split_mode: SplitMode; payer_name?: string; payer_vpa?: string }) => Promise<void> }) {
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<SplitMode>("item_wise");
  const [payerName, setPayerName] = useState("");
  const [payerVpa, setPayerVpa] = useState("");

  return (
    <form className="rs-new-bill-form" onSubmit={async (event) => { event.preventDefault(); await onCreate({ title: title.trim(), split_mode: mode, payer_name: payerName.trim() || undefined, payer_vpa: payerVpa.trim() || undefined }); }}>
      <div><p className="rs-section-label">Add another bill</p><h4>Start a new receipt</h4></div>
      <Input label="Bill title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Dinner - day 2" />
      <Select label="Default split" value={mode} onChange={(event) => setMode(event.target.value as SplitMode)}><option value="item_wise">Mixed items</option><option value="equal">Everything equal</option></Select>
      <div className="rs-new-bill-fields"><Input label="Payer name" value={payerName} onChange={(event) => setPayerName(event.target.value)} /><Input label="Payer VPA" value={payerVpa} onChange={(event) => setPayerVpa(event.target.value)} placeholder="name@bank" /></div>
      <Button type="submit" disabled={!title.trim()}>Create bill <ArrowRight size={15} aria-hidden="true" /></Button>
    </form>
  );
}

function DashboardMetric({ label, value, detail, icon, tone = "blue" }: { label: string; value: string; detail: string; icon: React.ReactNode; tone?: "blue" | "coral" | "green" }) {
  return <div className={`rs-dashboard-metric rs-dashboard-metric-${tone}`}><span>{icon}</span><div><p>{label}</p><strong>{value}</strong><small>{detail}</small></div></div>;
}

function BudgetCard({ label, value, detail, progress, tone = "default" }: { label: string; value: string; detail: string; progress: number; tone?: "default" | "coral" | "green" }) {
  return (
    <div className={`rs-budget-card rs-budget-card-${tone}`}>
      <div className="rs-budget-card-heading"><span>{label}</span><small>{detail}</small></div>
      <strong>{value}</strong>
      <span className="rs-budget-track" aria-hidden="true"><span style={{ width: `${progress}%` }} /></span>
    </div>
  );
}

function initials(value: string) {
  return value.trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "?";
}
