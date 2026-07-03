"use client";

import { Check, Copy, Lock, RotateCcw, Share2, Unlock } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import QRCode from "qrcode";

import { ClaimButton } from "@/components/claim-button";
import { ErrorState } from "@/components/error-state";
import { ItemForm } from "@/components/item-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { RoomEventSync } from "@/lib/events";
import { encodeInviteParam } from "@/lib/invite";
import { formatPaise, parseRupeesToPaise } from "@/lib/money";
import {
  canLockSplit,
  getSplitPreviewReadiness,
  getSplitPreviewRequestKey,
  shouldRequestSplitPreview,
  type SplitPreviewReadiness
} from "@/lib/split-readiness";
import {
  getCreatorSession,
  getParticipantSession,
  updateLastSequence,
  type CreatorSession,
  type ParticipantSession
} from "@/lib/storage";
import type { AdjustmentType, Item, RoomSummary, SplitPreview } from "@/types/api";

type RoomClientProps = {
  roomId: string;
  mode: "creator" | "participant";
};

export function RoomClient({ roomId, mode }: RoomClientProps) {
  const [session] = useState<CreatorSession | ParticipantSession | null>(() =>
    mode === "creator" ? getCreatorSession(roomId) : getParticipantSession(roomId)
  );
  const [summary, setSummary] = useState<RoomSummary | null>(null);
  const [preview, setPreview] = useState<SplitPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const suppressedPreviewKeyRef = useRef<string | null>(null);

  const token = session?.token;
  const locked = summary?.room.status === "settling" || summary?.room.status === "settled";

  const refresh = useCallback(
    async (activeToken = token, options: { forcePreview?: boolean } = {}) => {
      if (!activeToken) {
        return;
      }
      const nextSummary = await api.getSummary(roomId, activeToken);
      setSummary(nextSummary);

      const suppressedKey = options.forcePreview ? null : suppressedPreviewKeyRef.current;
      if (!shouldRequestSplitPreview(nextSummary, suppressedKey)) {
        setPreview(null);
        if (!getSplitPreviewReadiness(nextSummary).ready) {
          setPreviewError(null);
        }
        return;
      }

      try {
        const nextPreview = await api.previewSplit(roomId, activeToken);
        suppressedPreviewKeyRef.current = null;
        setPreview(nextPreview);
        setPreviewError(null);
      } catch (err) {
        if (isPreviewValidationError(err)) {
          suppressedPreviewKeyRef.current = getSplitPreviewRequestKey(nextSummary);
          setPreviewError("Split preview is not ready yet. Refresh after claims update and try again.");
        } else {
          setPreviewError("Could not load split preview. Refresh and try again.");
        }
        setPreview(null);
      }
    },
    [roomId, token]
  );

  useEffect(() => {
    if (!session) {
      return;
    }
    // Initial room fetch synchronizes server state after the local capability token is loaded.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh(session.token).catch((err) =>
      setError(err instanceof Error ? err.message : "Could not load room")
    );
  }, [refresh, session]);

  useEffect(() => {
    if (!session) {
      return;
    }
    const sync = new RoomEventSync({
      roomId,
      token: session.token,
      initialSequence: session.lastSequence,
      onRefetch: () => refresh(session.token),
      onSequence: (sequence) => updateLastSequence(roomId, session.role, sequence),
      onConnectionChange: setConnected
    });
    sync.start();
    return () => sync.stop();
  }, [refresh, roomId, session]);

  if (error) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  if (!session) {
    return (
      <ErrorState
        message={mode === "creator" ? "Creator session not found" : "Participant session not found"}
      />
    );
  }

  if (!summary) {
    return <main className="mx-auto max-w-3xl px-4 py-6 text-ink">Loading room...</main>;
  }

  const readiness = getSplitPreviewReadiness(summary);

  return (
    <main className="mx-auto grid max-w-3xl gap-4 px-4 py-5 pb-12 text-ink">
      <RoomHeader summary={summary} connected={connected} />
      {mode === "creator" && session.role === "creator" ? (
        <CreatorTools
          session={session}
          summary={summary}
          preview={preview}
          previewError={previewError}
          readiness={readiness}
          locked={locked}
          onRefresh={() => refresh(session.token)}
          onPreviewRetry={() => refresh(session.token, { forcePreview: true })}
        />
      ) : (
        <ParticipantTools
          session={session as ParticipantSession}
          summary={summary}
          preview={preview}
          previewError={previewError}
          readiness={readiness}
          locked={locked}
          onRefresh={() => refresh(session.token)}
          onPreviewRetry={() => refresh(session.token, { forcePreview: true })}
        />
      )}
    </main>
  );
}

function RoomHeader({ summary, connected }: { summary: RoomSummary; connected: boolean }) {
  return (
    <section className="rounded-md bg-white p-4 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#63706b]">Room</p>
          <h1 className="mt-1 text-2xl font-bold">{summary.room.payer_name || "ReceiptSplit"}</h1>
          <p className="mt-1 text-sm text-[#63706b]">
            {summary.room.split_mode === "item_wise" ? "Item-wise" : "Equal"} · {summary.room.status}
          </p>
        </div>
        <span className="rounded-full bg-cloud px-3 py-1 text-xs font-semibold">
          {connected ? "Live" : "Syncing"}
        </span>
      </div>
    </section>
  );
}

function CreatorTools({
  session,
  summary,
  preview,
  previewError,
  readiness,
  locked,
  onRefresh,
  onPreviewRetry
}: {
  session: CreatorSession;
  summary: RoomSummary;
  preview: SplitPreview | null;
  previewError: string | null;
  readiness: SplitPreviewReadiness;
  locked: boolean;
  onRefresh: () => Promise<void>;
  onPreviewRetry: () => Promise<void>;
}) {
  const [actionError, setActionError] = useState<string | null>(null);
  const lockReady = canLockSplit({ locked, preview, readiness });

  async function run(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      await onRefresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action failed");
    }
  }

  return (
    <>
      {actionError ? <ErrorState message={actionError} onRetry={() => setActionError(null)} /> : null}
      <InvitePanel roomId={summary.room.id} inviteToken={session.inviteToken} />
      <Participants participants={summary.participants} />
      {summary.room.status === "draft" ? (
        <Button
          type="button"
          onClick={() =>
            run(() =>
              api.updateRoom(summary.room.id, session.token, {
                version: summary.room.version,
                status: "active"
              })
            )
          }
        >
          <Check size={16} aria-hidden="true" />
          Open claiming
        </Button>
      ) : null}
      <section className="rounded-md bg-white p-4 shadow-soft">
        <h2 className="text-lg font-bold">Items</h2>
        {!locked ? (
          <div className="mt-3">
            <ItemForm
              onSubmit={(payload) => run(() => api.addItem(summary.room.id, session.token, payload))}
            />
          </div>
        ) : null}
        <ItemList
          summary={summary}
          locked={locked}
          creatorToken={session.token}
          onRefresh={onRefresh}
        />
      </section>
      {!locked ? (
        <AdjustmentForm
          roomId={summary.room.id}
          token={session.token}
          onSaved={onRefresh}
          onError={setActionError}
        />
      ) : null}
      <SplitPreviewCard
        preview={preview}
        previewError={previewError}
        readiness={readiness}
        summary={summary}
        onRetry={onPreviewRetry}
      />
      <CreatorLockControls
        canLock={lockReady}
        locked={locked}
        readiness={readiness}
        onLock={() => run(() => api.lockSplit(summary.room.id, session.token, summary.room.version))}
        onUnlock={() => run(() => api.unlockSplit(summary.room.id, session.token, summary.room.version))}
      />
      {locked ? (
        <p className="rounded-md bg-mint p-3 text-sm font-medium">
          Room is locked. Settlement tools are coming later.
        </p>
      ) : null}
    </>
  );
}

function ParticipantTools({
  session,
  summary,
  preview,
  previewError,
  readiness,
  locked,
  onRefresh,
  onPreviewRetry
}: {
  session: ParticipantSession;
  summary: RoomSummary;
  preview: SplitPreview | null;
  previewError: string | null;
  readiness: SplitPreviewReadiness;
  locked: boolean;
  onRefresh: () => Promise<void>;
  onPreviewRetry: () => Promise<void>;
}) {
  const [actionError, setActionError] = useState<string | null>(null);
  const myTotal = preview?.participant_totals.find(
    (total) => total.participant_id === session.participantId
  );

  async function run(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      await onRefresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Refresh and try again");
      await onRefresh();
    }
  }

  return (
    <>
      {actionError ? <ErrorState message={actionError} onRetry={() => setActionError(null)} /> : null}
      <Participants participants={summary.participants} />
      <section className="rounded-md bg-white p-4 shadow-soft">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">My Total</h2>
          <strong>{formatPaise(myTotal?.total_paise ?? 0)}</strong>
        </div>
      </section>
      <section className="rounded-md bg-white p-4 shadow-soft">
        <h2 className="text-lg font-bold">Claims</h2>
        <div className="mt-3 grid gap-3">
          {summary.items.map((item) => {
            const itemAssignments = summary.assignments.filter(
              (assignment) => assignment.line_item_id === item.id
            );
            const myClaim = itemAssignments.find(
              (assignment) => assignment.participant_id === session.participantId
            );
            const claimed = itemAssignments.reduce((sum, assignment) => sum + assignment.claimed_qty, 0);
            const available = Math.max(item.quantity - claimed, 0);
            return (
              <div key={item.id} className="rounded-md border border-[#dbe5df] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold">{item.name}</h3>
                    <p className="text-sm text-[#63706b]">
                      {formatPaise(item.total_paise)} · {available} of {item.quantity} open
                    </p>
                  </div>
                  {myClaim ? (
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={locked}
                      onClick={() => run(() => api.unclaimItem(summary.room.id, session.token, item.id))}
                    >
                      Unclaim
                    </Button>
                  ) : (
                    <ClaimButton
                      itemVersion={item.version}
                      disabled={locked || available < 1 || summary.room.split_mode !== "item_wise"}
                      onClaim={(payload) =>
                        run(() => api.claimItem(summary.room.id, session.token, item.id, payload))
                      }
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>
      <SplitPreviewCard
        preview={preview}
        previewError={previewError}
        readiness={readiness}
        summary={summary}
        onRetry={onPreviewRetry}
      />
      {locked ? (
        <p className="rounded-md bg-mint p-3 text-sm font-medium">
          Room is locked. Settlement tools are coming later.
        </p>
      ) : null}
    </>
  );
}

function InvitePanel({ roomId, inviteToken }: { roomId: string; inviteToken: string }) {
  const [origin] = useState(() => (typeof window === "undefined" ? "" : window.location.origin));
  const [qr, setQr] = useState("");
  const link = `${origin}/join/${encodeInviteParam(roomId, inviteToken)}`;

  useEffect(() => {
    if (link) {
      void QRCode.toDataURL(link, { margin: 1, width: 160 }).then(setQr);
    }
  }, [link]);

  return (
    <section className="rounded-md bg-white p-4 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Invite</h2>
          <p className="break-all text-sm text-[#63706b]">{link}</p>
        </div>
        {qr ? (
          <Image
            className="h-24 w-24 rounded-md border border-[#dbe5df]"
            src={qr}
            alt="Invite QR"
            width={96}
            height={96}
            unoptimized
          />
        ) : null}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Button type="button" variant="secondary" onClick={() => navigator.clipboard.writeText(link)}>
          <Copy size={16} aria-hidden="true" />
          Copy
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => window.open(`https://wa.me/?text=${encodeURIComponent(link)}`, "_blank")}
        >
          <Share2 size={16} aria-hidden="true" />
          WhatsApp
        </Button>
      </div>
    </section>
  );
}

function Participants({ participants }: { participants: RoomSummary["participants"] }) {
  return (
    <section className="rounded-md bg-white p-4 shadow-soft">
      <h2 className="text-lg font-bold">Participants</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {participants.map((participant) => (
          <span
            key={participant.id}
            className="rounded-full px-3 py-1 text-sm font-semibold text-white"
            style={{ backgroundColor: participant.color }}
          >
            {participant.nickname}
          </span>
        ))}
      </div>
    </section>
  );
}

function ItemList({
  summary,
  locked,
  creatorToken,
  onRefresh
}: {
  summary: RoomSummary;
  locked: boolean;
  creatorToken: string;
  onRefresh: () => Promise<void>;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", quantity: "1", amount: "" });

  function startEdit(item: Item) {
    setEditing(item.id);
    setDraft({
      name: item.name,
      quantity: String(item.quantity),
      amount: (item.total_paise / 100).toFixed(2)
    });
  }

  async function save(item: Item) {
    await api.updateItem(summary.room.id, creatorToken, item.id, {
      version: item.version,
      name: draft.name.trim(),
      quantity: Number.parseInt(draft.quantity, 10),
      total_paise: parseRupeesToPaise(draft.amount)
    });
    setEditing(null);
    await onRefresh();
  }

  return (
    <div className="mt-4 grid gap-3">
      {summary.items.length === 0 ? <p className="text-sm text-[#63706b]">No items yet.</p> : null}
      {summary.items.map((item) => {
        const claimed = summary.assignments
          .filter((assignment) => assignment.line_item_id === item.id)
          .reduce((sum, assignment) => sum + assignment.claimed_qty, 0);
        return (
          <div key={item.id} className="rounded-md border border-[#dbe5df] p-3">
            {editing === item.id ? (
              <div className="grid gap-3">
                <Input label="Item name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
                <div className="grid grid-cols-[96px_1fr] gap-3">
                  <Input label="Quantity" value={draft.quantity} onChange={(e) => setDraft({ ...draft, quantity: e.target.value })} />
                  <Input label="Amount" value={draft.amount} onChange={(e) => setDraft({ ...draft, amount: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Button type="button" onClick={() => save(item)}>
                    Save
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setEditing(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">{item.name}</h3>
                  <p className="text-sm text-[#63706b]">
                    {formatPaise(item.total_paise)} · {claimed}/{item.quantity} claimed
                  </p>
                </div>
                {!locked ? (
                  <div className="grid gap-2">
                    <Button type="button" variant="ghost" onClick={() => startEdit(item)}>
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      onClick={async () => {
                        await api.deleteItem(summary.room.id, creatorToken, item.id, item.version);
                        await onRefresh();
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function AdjustmentForm({
  roomId,
  token,
  onSaved,
  onError
}: {
  roomId: string;
  token: string;
  onSaved: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const [type, setType] = useState<AdjustmentType>("tax");
  const [label, setLabel] = useState("");
  const [amount, setAmount] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const paise = parseRupeesToPaise(amount);
      await api.addAdjustment(roomId, token, {
        type,
        label: label.trim() || type,
        amount_paise: type === "discount" ? -paise : paise,
        allocation_method: "equal"
      });
      setLabel("");
      setAmount("");
      await onSaved();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not save adjustment");
    }
  }

  return (
    <section className="rounded-md bg-white p-4 shadow-soft">
      <h2 className="text-lg font-bold">Adjustments</h2>
      <form className="mt-3 grid gap-3" onSubmit={submit}>
        <Select label="Type" value={type} onChange={(event) => setType(event.target.value as AdjustmentType)}>
          <option value="tax">Tax</option>
          <option value="service_charge">Service charge</option>
          <option value="delivery_fee">Delivery fee</option>
          <option value="discount">Discount</option>
          <option value="adjustment">Custom</option>
        </Select>
        <Input label="Label" value={label} onChange={(event) => setLabel(event.target.value)} />
        <Input label="Amount" inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} />
        <Button type="submit">Add adjustment</Button>
      </form>
    </section>
  );
}

export function CreatorLockControls({
  canLock,
  locked,
  readiness,
  onLock,
  onUnlock
}: {
  canLock: boolean;
  locked: boolean;
  readiness: SplitPreviewReadiness;
  onLock: () => void;
  onUnlock: () => void;
}) {
  const helper = !readiness.ready
    ? "Complete all claims before locking the split."
    : "Preview totals before locking the split.";

  return (
    <section className="grid gap-2">
      <div className="grid grid-cols-2 gap-3">
        <Button type="button" disabled={!canLock} onClick={onLock}>
          <Lock size={16} aria-hidden="true" />
          Lock
        </Button>
        <Button type="button" variant="secondary" disabled={!locked} onClick={onUnlock}>
          <Unlock size={16} aria-hidden="true" />
          Unlock
        </Button>
      </div>
      {!locked && !canLock ? <p className="text-sm text-[#63706b]">{helper}</p> : null}
    </section>
  );
}

export function SplitPreviewCard({
  preview,
  previewError,
  readiness,
  summary,
  onRetry
}: {
  preview: SplitPreview | null;
  previewError: string | null;
  readiness: SplitPreviewReadiness;
  summary: RoomSummary;
  onRetry: () => Promise<void> | void;
}) {
  const participantsById = useMemo(
    () => new Map(summary.participants.map((participant) => [participant.id, participant])),
    [summary.participants]
  );

  return (
    <section className="rounded-md bg-white p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold">Split Preview</h2>
        <strong>{formatPaise(preview?.grand_total_paise ?? 0)}</strong>
      </div>
      <div className="mt-3 grid gap-2">
        {!readiness.ready ? (
          <div className="rounded-md bg-cloud p-3 text-sm">
            <p className="font-semibold">Split preview is not ready yet.</p>
            <p className="mt-1 text-[#63706b]">{readiness.message}</p>
          </div>
        ) : previewError ? (
          <div className="rounded-md bg-cloud p-3 text-sm">
            <p className="font-semibold">{previewError}</p>
            <Button className="mt-3" type="button" variant="secondary" onClick={onRetry}>
              <RotateCcw size={16} aria-hidden="true" />
              Retry preview
            </Button>
          </div>
        ) : preview ? (
          preview.participant_totals.map((total) => (
            <div
              key={total.participant_id}
              className="flex items-center justify-between rounded-md bg-cloud px-3 py-2 text-sm"
            >
              <span>{participantsById.get(total.participant_id)?.nickname ?? "Participant"}</span>
              <strong>{formatPaise(total.total_paise)}</strong>
            </div>
          ))
        ) : (
          <div className="rounded-md bg-cloud p-3 text-sm">
            <p className="font-semibold">Split preview is ready.</p>
            <p className="mt-1 text-[#63706b]">Refresh to calculate totals.</p>
            <Button className="mt-3" type="button" variant="secondary" onClick={onRetry}>
              <RotateCcw size={16} aria-hidden="true" />
              Retry preview
            </Button>
          </div>
        )}
      </div>
    </section>
  );
}

function isPreviewValidationError(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "status" in err &&
    [400, 409, 422, 423].includes(Number((err as { status: unknown }).status))
  );
}
