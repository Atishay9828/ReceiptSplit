"use client";

import {
  Check,
  Copy,
  Loader2,
  Lock,
  ReceiptText,
  RotateCcw,
  Share2,
  ShieldCheck,
  Sparkles,
  Unlock
} from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import QRCode from "qrcode";


import { ErrorState } from "@/components/error-state";
import { ItemForm } from "@/components/item-form";
import { ReceiptUpload } from "@/components/receipt-upload";
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
import type {
  AbuseReportInput,
  AdjustmentType,
  ClaimPayload,
  Item,
  OpenPaymentResponse,
  PayerDetailsInput,
  RoomSummary,
  SettlementStatus,
  SettlementSummary,
  SplitPreview
} from "@/types/api";

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
  const [settlement, setSettlement] = useState<SettlementSummary | null>(null);
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
      try {
        setSettlement(await api.getSettlement(roomId, activeToken));
      } catch {
        setSettlement(null);
      }

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
    return (
      <main className="mx-auto grid min-h-dvh max-w-md content-center px-4 py-6 text-ink">
        <section className="rounded-md border border-[#dbe5df] bg-white p-5 shadow-soft">
          <div className="flex items-center gap-3 text-sm font-medium text-[#63706b]">
            <Loader2 size={18} className="animate-spin text-leaf" aria-hidden="true" />
            Loading room...
          </div>
        </section>
      </main>
    );
  }

  const readiness = getSplitPreviewReadiness(summary);

  return (
    <main className="mx-auto grid w-full max-w-6xl gap-4 px-4 py-5 pb-20 text-ink sm:px-6">
      <RoomHeader summary={summary} connected={connected} />
      {mode === "creator" && session.role === "creator" ? (
        <CreatorTools
          session={session}
          summary={summary}
          preview={preview}
          settlement={settlement}
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
          settlement={settlement}
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
    <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-leaf">ReceiptSplit room</p>
          <h1 className="mt-1 text-2xl font-bold sm:text-3xl">{summary.room.payer_name || "ReceiptSplit"}</h1>
          <p className="mt-1 text-sm text-[#63706b]">
            {summary.room.split_mode === "item_wise" ? "Item-wise" : "Equal"} · {summary.room.status}
          </p>
        </div>
        <span className="rounded-full bg-cloud px-3 py-1 text-xs font-semibold text-[#52625b]">
          {connected ? "Live" : "Syncing"}
        </span>
      </div>
      <LifecycleIndicator status={summary.room.status} />
    </section>
  );
}

function LifecycleIndicator({ status }: { status: RoomSummary["room"]["status"] }) {
  const steps = [
    { key: "draft", label: "Draft" },
    { key: "active", label: "Claiming" },
    { key: "settling", label: "Locked" },
    { key: "settled", label: "Settled" }
  ];
  const activeIndex = Math.max(
    0,
    steps.findIndex((step) => step.key === status)
  );

  return (
    <div className="mt-4 grid grid-cols-4 gap-2 text-[11px] font-semibold text-[#63706b]" aria-label="Room lifecycle">
      {steps.map((step, index) => (
        <div
          key={step.key}
          className={
            index <= activeIndex
              ? "rounded-full bg-mint px-2 py-1 text-center text-leaf"
              : "rounded-full bg-cloud px-2 py-1 text-center"
          }
        >
          {step.label}
        </div>
      ))}
    </div>
  );
}

export function CreatorNextActionCard({
  roomStatus,
  canLock,
  itemCount
}: {
  roomStatus: RoomSummary["room"]["status"];
  canLock: boolean;
  itemCount: number;
}) {
  const copy = getCreatorNextAction(roomStatus, canLock, itemCount);

  return (
    <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft sm:p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-mint text-leaf">
          <Sparkles size={20} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-lg font-bold">Next step</h2>
          <p className="mt-1 text-xl font-bold">{copy.title}</p>
          <p className="mt-1 text-sm leading-6 text-[#63706b]">{copy.description}</p>
        </div>
      </div>
    </section>
  );
}

function getCreatorNextAction(
  roomStatus: RoomSummary["room"]["status"],
  canLock: boolean,
  itemCount: number
) {
  if (roomStatus === "draft") {
    if (itemCount === 0) {
      return {
        title: "Add receipt items first",
        description: "Add items manually or scan a receipt before opening claims."
      };
    }
    return {
      title: "Open claiming",
      description: "Items are ready. Share the link so friends can join and claim what they had."
    };
  }
  if (roomStatus === "active") {
    return canLock
      ? {
          title: "Lock bill",
          description: "Everyone has claimed their items. Lock when ready to settle."
        }
      : {
          title: "Share and collect claims",
          description: "Share the invite link. Lock the bill once everyone has claimed their items."
        };
  }
  if (roomStatus === "settling") {
    return {
      title: "Confirm payments",
      description: "Participants pay you directly. Confirm each payment manually below."
    };
  }
  if (roomStatus === "settled") {
    return {
      title: "All payments confirmed",
      description: "This split is fully settled. Nothing left to do."
    };
  }
  return {
    title: "Review room",
    description: "Check room status and participant activity before taking another action."
  };
}

function CreatorTools({
  session,
  summary,
  preview,
  settlement,
  previewError,
  readiness,
  locked,
  onRefresh,
  onPreviewRetry
}: {
  session: CreatorSession;
  summary: RoomSummary;
  preview: SplitPreview | null;
  settlement: SettlementSummary | null;
  previewError: string | null;
  readiness: SplitPreviewReadiness;
  locked: boolean;
  onRefresh: () => Promise<void>;
  onPreviewRetry: () => Promise<void>;
}) {
  const [actionError, setActionError] = useState<string | null>(null);
  const [removeConfirm, setRemoveConfirm] = useState<string | null>(null);
  const lockReady = canLockSplit({ locked, preview, readiness });
  const itemCount = summary.items.length;
  // Find creator participant for self-claim
  const creatorParticipant = summary.participants.find((p) => p.role === "creator");
  const participantsById = useMemo(
    () => new Map(summary.participants.map((participant) => [participant.id, participant.nickname])),
    [summary.participants]
  );

  async function run(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      await onRefresh();
    } catch (err) {
      setActionError(friendlyError(err));
    }
  }

  async function removeParticipant(participantId: string) {
    setRemoveConfirm(null);
    await run(() => api.removeParticipant(summary.room.id, participantId, session.token));
  }

  return (
    <>
      {actionError ? <ErrorState message={actionError} onRetry={() => setActionError(null)} /> : null}
      <CreatorNextActionCard
        roomStatus={summary.room.status}
        canLock={lockReady}
        itemCount={itemCount}
      />
      <InvitePanel roomId={summary.room.id} inviteToken={session.inviteToken} />
      <Participants
        participants={summary.participants}
        mode="creator"
        roomStatus={summary.room.status}
        confirmRemoveId={removeConfirm}
        onRequestRemove={(id) => setRemoveConfirm(id)}
        onCancelRemove={() => setRemoveConfirm(null)}
        onConfirmRemove={removeParticipant}
      />
      <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft">
        <h2 className="text-lg font-bold">Items</h2>
        {!locked ? (
          <div className="mt-3 grid gap-4">
            <ReceiptUpload
              roomId={summary.room.id}
              token={session.token}
              onConfirmed={onRefresh}
            />
            <ItemForm
              onSubmit={(payload) => run(() => api.addItem(summary.room.id, session.token, payload))}
            />
          </div>
        ) : null}
        {summary.room.status === "draft" ? (
          <div className="mt-4">
            <Button
              type="button"
              disabled={itemCount === 0}
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
            {itemCount === 0 ? (
              <p className="mt-2 text-sm text-[#63706b]">Add at least one item before opening claims.</p>
            ) : null}
          </div>
        ) : null}
        <ItemList
          summary={summary}
          locked={locked}
          creatorToken={session.token}
          onRefresh={onRefresh}
        />
      </section>
      {/* Creator self-claim — available in active mode */}
      {summary.room.status === "active" && creatorParticipant ? (
        <CreatorClaimSection
          summary={summary}
          creatorParticipantId={creatorParticipant.id}
          onClaim={(itemId, payload) =>
            run(() => api.claimItem(summary.room.id, session.token, itemId, payload))
          }
          onUnclaim={(itemId) => run(() => api.unclaimItem(summary.room.id, session.token, itemId))}
        />
      ) : null}
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
        <CreatorSettlementPanel
          settlement={settlement}
          participantsById={participantsById}
          locked={locked}
          onSavePayer={(payload) =>
            run(() => api.savePayerDetails(summary.room.id, session.token, payload))
          }
          onPrepare={() => run(() => api.prepareSettlement(summary.room.id, session.token))}
          onConfirm={(requestId) =>
            run(() => api.confirmSettlement(summary.room.id, requestId, session.token))
          }
          onDispute={(requestId, reason) =>
            run(() =>
              api.disputeSettlement(summary.room.id, requestId, session.token, {
                reason: reason || null
              })
            )
          }
        />
      ) : null}
      <AbuseReportPanel
        onReport={async (payload) => {
          await api.reportAbuse(summary.room.id, session.token, payload);
        }}
      />
    </>
  );
}

function ParticipantTools({
  session,
  summary,
  preview,
  settlement,
  previewError,
  readiness,
  locked,
  onRefresh,
  onPreviewRetry
}: {
  session: ParticipantSession;
  summary: RoomSummary;
  preview: SplitPreview | null;
  settlement: SettlementSummary | null;
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
  const mySettlement =
    settlement?.requests.find((entry) => entry.participant_id === session.participantId) ?? null;
  const totalPaise = mySettlement?.amount_paise ?? myTotal?.total_paise ?? 0;
  const participantStatus = getParticipantTotalStatus({
    locked,
    settlementStatus: mySettlement?.status,
    readiness
  });

  async function run(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      await onRefresh();
    } catch (err) {
      setActionError(friendlyError(err));
      await onRefresh();
    }
  }

  return (
    <>
      {actionError ? <ErrorState message={actionError} onRetry={() => setActionError(null)} /> : null}
      <ParticipantTotalCard
        amountPaise={totalPaise}
        status={participantStatus}
        participantName={session.nickname}
      />
      <Participants participants={summary.participants} mode="participant" roomStatus={summary.room.status} />
      <ParticipantClaimList
        summary={summary}
        participantId={session.participantId}
        locked={locked}
        onClaim={(itemId, payload) =>
          run(() => api.claimItem(summary.room.id, session.token, itemId, payload))
        }
        onUnclaim={(itemId) => run(() => api.unclaimItem(summary.room.id, session.token, itemId))}
      />
      <SplitPreviewCard
        preview={preview}
        previewError={previewError}
        readiness={readiness}
        summary={summary}
        onRetry={onPreviewRetry}
      />
      {locked ? (
        <ParticipantSettlementPanel
          settlement={settlement}
          participantId={session.participantId}
          onOpenPayment={(requestId) =>
            api.openPayment(summary.room.id, requestId, session.token).then(async (result) => {
              await onRefresh();
              try {
                window.open(result.upi_uri, "_self");
              } catch {
                // UPI navigation is best-effort; QR and copy fallback remain available.
              }
              return result;
            })
          }
          onClaimPaid={(requestId) =>
            run(() => api.claimPaid(summary.room.id, requestId, session.token))
          }
        />
      ) : null}
      <AbuseReportPanel
        onReport={async (payload) => {
          await api.reportAbuse(summary.room.id, session.token, payload);
        }}
      />
    </>
  );
}

type ParticipantTotalStatus =
  | "claim_items"
  | "ready_to_pay"
  | "payment_opened"
  | "claimed_paid"
  | "payer_confirmed"
  | "disputed";

export function ParticipantTotalCard({
  amountPaise,
  status,
  participantName
}: {
  amountPaise: number;
  status: ParticipantTotalStatus;
  participantName?: string;
}) {
  const copy = getParticipantTotalCopy(status);

  return (
    <section className="rounded-md border border-[#dbe5df] bg-white p-5 shadow-soft">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-[#63706b]">{participantName ? `${participantName}, you owe` : "You owe"}</p>
          <p className="mt-2 text-4xl font-bold tracking-normal sm:text-5xl">{formatPaise(amountPaise)}</p>
        </div>
        <StatusBadge tone={copy.tone}>{copy.label}</StatusBadge>
      </div>
      <div className="mt-4 rounded-md bg-cloud p-3 text-sm leading-6 text-[#52625b]">
        <p className="font-semibold text-ink">{copy.title}</p>
        <p>{copy.description}</p>
      </div>
    </section>
  );
}

function getParticipantTotalCopy(status: ParticipantTotalStatus) {
  switch (status) {
    case "claim_items":
      return {
        label: "Claim your items",
        title: "Claim what you had.",
        description: "Tap the food or drinks you shared. Your total updates when the split is ready.",
        tone: "info" as const
      };
    case "ready_to_pay":
      return {
        label: "Ready to pay",
        title: "Pay your share directly to the payer.",
        description: "Use the payment card below when the creator prepares settlement.",
        tone: "info" as const
      };
    case "payment_opened":
      return {
        label: "Payment opened",
        title: "Complete payment in your UPI app.",
        description: "Return here and tap I paid after checking recipient and amount.",
        tone: "info" as const
      };
    case "claimed_paid":
      return {
        label: "Marked paid",
        title: "Waiting for payer confirmation.",
        description: "The payer still needs to manually confirm this request.",
        tone: "pending" as const
      };
    case "payer_confirmed":
      return {
        label: "Payer confirmed",
        title: "Payer confirmed this payment.",
        description: "No bank verification is implied by ReceiptSplit.",
        tone: "success" as const
      };
    case "disputed":
      return {
        label: "Disputed",
        title: "Check with the payer.",
        description: "The payer marked this as disputed. Reopen payment if you need to try again.",
        tone: "danger" as const
      };
  }
}

function getParticipantTotalStatus({
  locked,
  settlementStatus,
  readiness
}: {
  locked: boolean;
  settlementStatus?: SettlementStatus;
  readiness: SplitPreviewReadiness;
}): ParticipantTotalStatus {
  if (settlementStatus) {
    return settlementStatus === "due" ? "ready_to_pay" : settlementStatus;
  }
  if (locked || readiness.ready) {
    return "ready_to_pay";
  }
  return "claim_items";
}

export function ParticipantClaimList({
  summary,
  participantId,
  locked,
  onClaim,
  onUnclaim
}: {
  summary: RoomSummary;
  participantId: string;
  locked: boolean;
  onClaim: (itemId: string, payload: ClaimPayload) => Promise<void> | void;
  onUnclaim: (itemId: string) => Promise<void> | void;
}) {
  return (
    <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Claim your items</h2>
          <p className="mt-1 text-sm text-[#63706b]">Tap what you had. No awkward maths.</p>
        </div>
        <ReceiptText size={22} className="text-leaf" aria-hidden="true" />
      </div>
      <div className="mt-4 grid gap-3">
        {summary.items.length === 0 ? (
          <EmptyState
            title="No items yet."
            description="Wait for the creator to upload a receipt or add items manually."
          />
        ) : null}
        {summary.items.map((item) => {
          const itemAssignments = summary.assignments.filter(
            (assignment) => assignment.line_item_id === item.id
          );
          const myClaim = itemAssignments.find((assignment) => assignment.participant_id === participantId);
          const totalClaimed = itemAssignments.reduce((sum, a) => sum + a.claimed_qty, 0);
          const available = Math.max(item.quantity - totalClaimed, 0);
          const status = myClaim ? "claimed_by_you" : available > 0 ? "available" : "claimed";
          const unitPaise = item.quantity > 1 ? Math.round(item.total_paise / item.quantity) : null;

          return (
            <div key={item.id} className="rounded-md border border-[#dbe5df] bg-cloud/50 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-base font-bold">{item.name}</h3>
                  <p className="mt-1 text-sm text-[#63706b]">
                    {unitPaise
                      ? `${formatPaise(item.total_paise)} total · ${formatPaise(unitPaise)}/unit`
                      : formatPaise(item.total_paise)}
                  </p>
                  {item.quantity > 1 ? (
                    <p className="text-xs text-[#63706b]">
                      {available} of {item.quantity} available
                      {itemAssignments.length > 0 ? (
                        <> · {itemAssignments.map((a) => {
                          const others = summary.participants.find((p) => p.id === a.participant_id);
                          return `${others?.nickname ?? "Someone"} ×${a.claimed_qty}`;
                        }).join(", ")}</>
                      ) : null}
                    </p>
                  ) : null}
                </div>
                <ItemClaimStatusBadge status={status} />
              </div>
              <div className="mt-3">
                {myClaim ? (
                  <div className="flex items-center gap-3">
                    <StatusBadge tone="info">You claimed {myClaim.claimed_qty}</StatusBadge>
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={locked}
                      aria-label={`Unclaim ${item.name}`}
                      onClick={() => onUnclaim(item.id)}
                    >
                      Unclaim
                    </Button>
                  </div>
                ) : item.quantity > 1 && available > 0 && !locked && summary.room.split_mode === "item_wise" ? (
                  <QuantityClaimControl
                    item={item}
                    available={available}
                    onClaim={onClaim}
                  />
                ) : (
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={locked || available < 1 || summary.room.split_mode !== "item_wise"}
                    aria-label={`Claim ${item.name}`}
                    onClick={() => onClaim(item.id, { item_version: item.version, claimed_qty: 1 })}
                  >
                    Claim
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function QuantityClaimControl({
  item,
  available,
  onClaim
}: {
  item: Item;
  available: number;
  onClaim: (itemId: string, payload: ClaimPayload) => Promise<void> | void;
}) {
  const [qty, setQty] = useState(1);
  const [busy, setBusy] = useState(false);

  async function claim() {
    setBusy(true);
    try {
      await onClaim(item.id, { item_version: item.version, claimed_qty: qty });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 rounded-md border border-[#dbe5df] bg-white">
        <button
          type="button"
          className="grid h-8 w-8 place-items-center rounded-l-md text-sm font-bold text-[#52625b] hover:bg-cloud disabled:opacity-40"
          disabled={qty <= 1 || busy}
          onClick={() => setQty((q) => Math.max(1, q - 1))}
          aria-label="Decrease quantity"
        >
          −
        </button>
        <span className="min-w-6 text-center text-sm font-bold">{qty}</span>
        <button
          type="button"
          className="grid h-8 w-8 place-items-center rounded-r-md text-sm font-bold text-[#52625b] hover:bg-cloud disabled:opacity-40"
          disabled={qty >= available || busy}
          onClick={() => setQty((q) => Math.min(available, q + 1))}
          aria-label="Increase quantity"
        >
          +
        </button>
      </div>
      <Button
        type="button"
        variant="secondary"
        disabled={busy}
        onClick={claim}
        aria-label={`Claim ${qty} of ${item.name}`}
      >
        Claim {qty}
      </Button>
    </div>
  );
}

function ItemClaimStatusBadge({ status }: { status: "available" | "claimed_by_you" | "claimed" }) {
  if (status === "claimed_by_you") {
    return <StatusBadge tone="info">Claimed by you</StatusBadge>;
  }
  if (status === "claimed") {
    return <StatusBadge tone="muted">Claimed</StatusBadge>;
  }
  return <StatusBadge tone="success">Available</StatusBadge>;
}

export function CreatorSettlementPanel({
  settlement,
  participantsById,
  locked,
  onSavePayer,
  onPrepare,
  onConfirm,
  onDispute
}: {
  settlement: SettlementSummary | null;
  participantsById: Map<string, string>;
  locked: boolean;
  onSavePayer: (payload: PayerDetailsInput) => Promise<void> | void;
  onPrepare: () => Promise<void> | void;
  onConfirm: (requestId: string) => Promise<void> | void;
  onDispute: (requestId: string, reason?: string) => Promise<void> | void;
}) {
  const [payeeName, setPayeeName] = useState(() => settlement?.payee_name ?? "");
  const [payeeVpa, setPayeeVpa] = useState(() => settlement?.payee_vpa ?? "");
  const [submitting, setSubmitting] = useState(false);

  async function submitPayer(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSavePayer({ payee_name: payeeName.trim(), payee_vpa: payeeVpa.trim() });
    } finally {
      setSubmitting(false);
    }
  }

  if (!locked) {
    return (
      <section className="rounded-md bg-white p-4 shadow-soft">
        <h2 className="text-lg font-bold">Settlement status</h2>
        <p className="mt-2 text-sm text-[#63706b]">Lock the bill before preparing settlement.</p>
      </section>
    );
  }

  const requests = settlement?.requests ?? [];
  const configured = Boolean(settlement?.payer_details_configured);

  return (
    <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Settlement dashboard</h2>
          <p className="mt-1 text-sm text-[#63706b]">Payer confirmation is manual. ReceiptSplit does not verify bank transfers.</p>
        </div>
        {settlement?.aggregates.payer_confirmed_count === requests.length && requests.length > 0 ? (
          <StatusBadge tone="success">All payer confirmed</StatusBadge>
        ) : null}
      </div>

      {!configured ? (
        <form className="mt-4 grid gap-3" onSubmit={submitPayer}>
          <Input
            label="Payer display name"
            value={payeeName}
            onChange={(event) => setPayeeName(event.target.value)}
          />
          <Input
            label="UPI ID"
            value={payeeVpa}
            onChange={(event) => setPayeeVpa(event.target.value)}
          />
          <Button type="submit" disabled={submitting || !payeeName.trim() || !payeeVpa.trim()}>
            Save payout details
          </Button>
        </form>
      ) : null}

      {configured && requests.length === 0 ? (
        <div className="mt-4 grid gap-3 rounded-md bg-cloud p-3 text-sm">
          <p className="font-semibold">{settlement?.payee_name}</p>
          <p className="break-all text-[#63706b]">{settlement?.payee_vpa}</p>
          <Button type="button" onClick={onPrepare}>
            Prepare settlement
          </Button>
        </div>
      ) : null}

      {requests.length > 0 ? (
        <div className="mt-4 grid gap-3">
          {requests.map((request) => {
            const canConfirm = request.status === "claimed_paid";
            const canDispute = request.status === "claimed_paid";
            const isTerminal = request.status === "payer_confirmed";
            const statusMessage = {
              due: "Waiting for participant to open payment.",
              payment_opened: "Participant opened the UPI link.",
              claimed_paid: "Participant marked paid — waiting for your confirmation.",
              payer_confirmed: "Payment confirmed.",
              disputed: "Marked disputed."
            }[request.status];
            return (
              <div
                key={request.id}
                className={`rounded-md border p-3 ${
                  isTerminal
                    ? "border-[#c3e6d4] bg-mint/30"
                    : "border-[#dbe5df] bg-cloud/40"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold">
                      {participantsById.get(request.participant_id) ?? "Participant"}
                    </h3>
                    <p className="text-sm text-[#63706b]">
                      {formatPaise(request.amount_paise)}
                    </p>
                    <p className="mt-0.5 text-xs text-[#63706b]">{statusMessage}</p>
                  </div>
                  <SettlementStatusBadge status={request.status} />
                </div>
                {!isTerminal ? (
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={!canConfirm}
                      onClick={() => onConfirm(request.id)}
                    >
                      Confirm payment
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      disabled={!canDispute}
                      onClick={() => onDispute(request.id)}
                    >
                      Mark disputed
                    </Button>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

export function ParticipantSettlementPanel({
  settlement,
  participantId,
  onOpenPayment,
  onClaimPaid
}: {
  settlement: SettlementSummary | null;
  participantId: string;
  onOpenPayment: (requestId: string) => Promise<OpenPaymentResponse>;
  onClaimPaid: (requestId: string) => Promise<void> | void;
}) {
  const request = settlement?.requests.find((entry) => entry.participant_id === participantId) ?? null;
  const [qr, setQr] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const isIOS = typeof navigator !== "undefined" && /iphone|ipad|ipod/i.test(navigator.userAgent);
  const isMobile = typeof navigator !== "undefined" && /android|iphone|ipad|ipod/i.test(navigator.userAgent);

  // Build UPI URI directly from request data for immediate QR display
  const upiUri = useMemo(() => {
    if (!request) return "";
    const params = new URLSearchParams({
      pa: request.payee_vpa,
      pn: request.payee_name,
      am: (Math.floor(request.amount_paise / 100) + "." + String(request.amount_paise % 100).padStart(2, "0")),
      cu: "INR",
      tn: `ReceiptSplit ${request.payment_reference}`,
      tr: request.payment_reference
    });
    return `upi://pay?${params.toString()}`;
  }, [request]);

  useEffect(() => {
    if (!upiUri || request?.status === "payer_confirmed") {
      return;
    }
    void QRCode.toDataURL(upiUri, { margin: 1, width: 200 }).then(setQr);
  }, [upiUri, request?.status]);

  if (!request) {
    return (
      <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft">
        <h2 className="text-lg font-bold">Pay your share</h2>
        <p className="mt-2 text-sm text-[#63706b]">Waiting for payer to prepare settlement.</p>
      </section>
    );
  }

  const isConfirmed = request.status === "payer_confirmed";
  const isDisputed = request.status === "disputed";
  const canPay = !isConfirmed && !isDisputed || isDisputed;

  async function openPayment() {
    if (!request) return;
    setBusy(true);
    setActionError(null);
    try {
      await onOpenPayment(request.id);
    } catch (err) {
      setActionError(friendlyError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Pay your share</h2>
          <p className="mt-1 text-sm text-[#63706b]">Pay directly to the payer. No wallet, no middle step.</p>
        </div>
        <SettlementStatusBadge status={request.status} />
      </div>

      {/* Payment details — always shown */}
      <div className="mt-4 grid gap-3 rounded-md bg-cloud p-4 text-sm">
        <div className="grid gap-1">
          <span className="text-[#63706b]">{isConfirmed ? "Amount" : "Amount due"}</span>
          <strong className={`text-4xl font-bold ${isConfirmed ? "text-leaf" : "text-ink"}`}>
            {formatPaise(request.amount_paise)}
          </strong>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-[#63706b]">Payer</span>
          <strong className="text-right">{request.payee_name}</strong>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-[#63706b]">UPI ID</span>
          <strong className="break-all text-right font-mono text-sm">{request.payee_vpa}</strong>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-[#63706b]">Reference</span>
          <strong className="break-all text-right text-xs">{request.payment_reference}</strong>
        </div>
      </div>

      {/* Confirmed final state */}
      {isConfirmed ? (
        <div className="mt-4 rounded-md border border-[#c3e6d4] bg-mint/40 p-4 text-center">
          <p className="font-bold text-leaf">Payer confirmed this payment.</p>
          <p className="mt-1 text-sm text-[#52625b]">You&apos;re all set.</p>
          <p className="mt-2 text-xs text-[#63706b]">ReceiptSplit does not verify bank transfers.</p>
        </div>
      ) : null}

      {/* Disputed state */}
      {isDisputed ? (
        <div className="mt-4 rounded-md border border-[#ffd6d0] bg-[#fff0ea] p-4">
          <p className="font-bold text-coral">Payment disputed by payer.</p>
          <p className="mt-1 text-sm text-[#52625b]">Check with the payer and retry if needed.</p>
        </div>
      ) : null}

      {/* QR for non-confirmed states */}
      {!isConfirmed ? (
        <div className="mt-4 grid gap-3">
          {qr ? (
            <div className="grid gap-2">
              <p className="text-xs font-semibold text-[#63706b]">
                {isMobile ? "Scan or tap Open UPI app" : "Scan with your phone's camera or UPI app"}
              </p>
              <Image
                className="h-48 w-48 rounded-md border border-[#dbe5df] bg-white p-1"
                src={qr}
                alt="UPI payment QR code"
                width={192}
                height={192}
                unoptimized
              />
            </div>
          ) : null}
          <SafetyNotice />
          {actionError ? <p className="text-sm font-medium text-coral">{actionError}</p> : null}
          <div className="grid grid-cols-2 gap-2">
            {isMobile ? (
              <Button
                type="button"
                size="lg"
                disabled={busy}
                onClick={openPayment}
                aria-label="Open UPI payment app"
              >
                Open UPI app
              </Button>
            ) : (
              <Button
                type="button"
                size="lg"
                variant="secondary"
                disabled={busy}
                onClick={openPayment}
                aria-label="Try to open UPI deep link"
              >
                Open UPI link
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigator.clipboard?.writeText(request.payee_vpa)}
              aria-label="Copy UPI ID to clipboard"
            >
              <Copy size={16} aria-hidden="true" />
              Copy UPI ID
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="col-span-2"
              onClick={() => navigator.clipboard?.writeText(upiUri)}
              aria-label="Copy UPI payment link"
            >
              <Copy size={16} aria-hidden="true" />
              Copy payment link
            </Button>
          </div>
          {!isMobile ? (
            <p className="text-xs text-[#63706b]">
              On desktop, scan the QR with your phone or copy the UPI ID into your banking app.
            </p>
          ) : null}
          {isIOS ? (
            <p className="text-xs text-[#63706b]">
              On iOS, copy the UPI ID and enter it in your preferred UPI app.
            </p>
          ) : null}
          {canPay ? (
            <Button
              type="button"
              variant="secondary"
              disabled={request.status === "claimed_paid"}
              onClick={() => onClaimPaid(request.id)}
              aria-label="Mark payment as done"
            >
              I paid
            </Button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export function AbuseReportPanel({
  onReport
}: {
  onReport: (payload: AbuseReportInput) => Promise<void> | void;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<AbuseReportInput["reason"]>("spam");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "success">("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setStatus("submitting");
    try {
      await onReport({ reason, message: message.trim() || null });
      setMessage("");
      setStatus("success");
    } catch (err) {
      setStatus("idle");
      setError(err instanceof Error ? err.message : "Could not submit report");
    }
  }

  return (
    <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Safety</h2>
          <p className="mt-1 text-sm text-[#63706b]">Report suspicious or abusive split.</p>
        </div>
        <Button type="button" variant="secondary" onClick={() => setOpen((value) => !value)}>
          Report abuse
        </Button>
      </div>
      {open ? (
        <form className="mt-4 grid gap-3" onSubmit={submit}>
          <Select
            label="Reason"
            value={reason}
            onChange={(event) => setReason(event.target.value as AbuseReportInput["reason"])}
          >
            <option value="spam">Spam</option>
            <option value="fraud_suspected">Fraud suspected</option>
            <option value="wrong_payee">Wrong payee</option>
            <option value="harassment">Harassment</option>
            <option value="other">Other</option>
          </Select>
          <label className="grid gap-1 text-sm font-medium">
            Message
            <textarea
              className="min-h-24 rounded-md border border-[#dbe5df] px-3 py-2 text-sm outline-none focus:border-leaf"
              maxLength={500}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
          </label>
          {error ? <p className="text-sm font-medium text-coral">{error}</p> : null}
          {status === "success" ? (
            <p className="text-sm font-medium text-leaf">Report received.</p>
          ) : null}
          <Button type="submit" disabled={status === "submitting"}>
            Submit report
          </Button>
        </form>
      ) : null}
    </section>
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
        <Button type="button" variant="secondary" onClick={() => navigator.clipboard?.writeText(link)}>
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

function Participants({
  participants,
  mode = "participant",
  roomStatus,
  confirmRemoveId,
  onRequestRemove,
  onCancelRemove,
  onConfirmRemove
}: {
  participants: RoomSummary["participants"];
  mode?: "creator" | "participant";
  roomStatus?: RoomSummary["room"]["status"];
  confirmRemoveId?: string | null;
  onRequestRemove?: (id: string) => void;
  onCancelRemove?: () => void;
  onConfirmRemove?: (id: string) => void;
}) {
  const canRemove = mode === "creator" && (roomStatus === "draft" || roomStatus === "active");
  return (
    <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft">
      <h2 className="text-lg font-bold">Participants</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {participants.map((participant) => {
          const isCreator = participant.role === "creator";
          const isBeingRemoved = confirmRemoveId === participant.id;
          return (
            <div key={participant.id} className="flex items-center gap-1">
              <span
                className="flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold text-white"
                style={{ backgroundColor: participant.color }}
              >
                {participant.nickname}
                {isCreator ? (
                  <span className="rounded-full bg-white/25 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide">
                    Creator
                  </span>
                ) : null}
              </span>
              {canRemove && !isCreator ? (
                isBeingRemoved ? (
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      className="rounded-full bg-coral px-2 py-0.5 text-xs font-bold text-white"
                      onClick={() => onConfirmRemove?.(participant.id)}
                      aria-label={`Confirm remove ${participant.nickname}`}
                    >
                      Remove
                    </button>
                    <button
                      type="button"
                      className="rounded-full bg-cloud px-2 py-0.5 text-xs font-bold text-[#52625b]"
                      onClick={() => onCancelRemove?.()}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="grid h-5 w-5 place-items-center rounded-full bg-[#ffd6d0] text-xs font-bold text-coral hover:bg-coral hover:text-white"
                    onClick={() => onRequestRemove?.(participant.id)}
                    aria-label={`Remove ${participant.nickname}`}
                    title={`Remove ${participant.nickname}`}
                  >
                    ×
                  </button>
                )
              ) : null}
            </div>
          );
        })}
      </div>
      {confirmRemoveId ? (
        <p className="mt-2 text-xs text-[#63706b]">
          Removing this participant will release their item claims.
        </p>
      ) : null}
    </section>
  );
}

function CreatorClaimSection({
  summary,
  creatorParticipantId,
  onClaim,
  onUnclaim
}: {
  summary: RoomSummary;
  creatorParticipantId: string;
  onClaim: (itemId: string, payload: ClaimPayload) => Promise<void>;
  onUnclaim: (itemId: string) => Promise<void>;
}) {
  return (
    <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Your items</h2>
          <p className="mt-1 text-sm text-[#63706b]">Claim what you had too.</p>
        </div>
        <StatusBadge tone="info">Creator</StatusBadge>
      </div>
      <div className="mt-4 grid gap-3">
        {summary.items.length === 0 ? (
          <EmptyState title="No items yet." description="Add items above before claiming." />
        ) : null}
        {summary.items.map((item) => {
          const itemAssignments = summary.assignments.filter(
            (a) => a.line_item_id === item.id
          );
          const myClaim = itemAssignments.find((a) => a.participant_id === creatorParticipantId);
          const totalClaimed = itemAssignments.reduce((sum, a) => sum + a.claimed_qty, 0);
          const available = Math.max(item.quantity - totalClaimed, 0);

          return (
            <div key={item.id} className="rounded-md border border-[#dbe5df] bg-cloud/50 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate font-semibold">{item.name}</h3>
                  <p className="mt-1 text-sm text-[#63706b]">
                    {formatPaise(item.total_paise)}
                    {item.quantity > 1 ? ` · ${available} of ${item.quantity} available` : ""}
                  </p>
                </div>
                {myClaim ? (
                  <StatusBadge tone="info">You claimed {myClaim.claimed_qty}</StatusBadge>
                ) : null}
              </div>
              <div className="mt-3">
                {myClaim ? (
                  <Button
                    type="button"
                    variant="ghost"
                    aria-label={`Unclaim ${item.name}`}
                    onClick={() => onUnclaim(item.id)}
                  >
                    Unclaim
                  </Button>
                ) : item.quantity > 1 && available > 0 ? (
                  <QuantityClaimControl
                    item={item}
                    available={available}
                    onClaim={onClaim}
                  />
                ) : (
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={available < 1 || summary.room.split_mode !== "item_wise"}
                    aria-label={`Claim ${item.name}`}
                    onClick={() => onClaim(item.id, { item_version: item.version, claimed_qty: 1 })}
                  >
                    Claim
                  </Button>
                )}
              </div>
            </div>
          );
        })}
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

type StatusTone = "muted" | "info" | "pending" | "success" | "danger";

function StatusBadge({ tone, children }: { tone: StatusTone; children: ReactNode }) {
  const toneClass = {
    muted: "bg-cloud text-[#52625b]",
    info: "bg-[#e8f1ff] text-[#2563eb]",
    pending: "bg-amber/20 text-[#8a5b00]",
    success: "bg-mint text-leaf",
    danger: "bg-[#fff0ea] text-coral"
  }[tone];

  return (
    <span
      data-tone={tone}
      className={`inline-flex min-h-8 items-center rounded-full px-3 py-1 text-xs font-bold ${toneClass}`}
    >
      {children}
    </span>
  );
}

function SafetyNotice() {
  return (
    <div className="mt-2 flex items-start gap-2 rounded-md border border-[#dbe5df] bg-cloud p-3 text-sm leading-6 text-[#52625b]">
      <ShieldCheck size={18} className="mt-0.5 shrink-0 text-leaf" aria-hidden="true" />
      <div>
        <p>ReceiptSplit does not verify bank transfers.</p>
        <p>Check the recipient and amount in your UPI app before paying.</p>
        <p>Payer confirmation is manual.</p>
      </div>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-md border border-dashed border-[#ccd8d1] bg-cloud p-4 text-sm">
      <p className="font-semibold">{title}</p>
      <p className="mt-1 text-[#63706b]">{description}</p>
    </div>
  );
}

export function SettlementStatusBadge({ status }: { status: SettlementStatus }) {
  return <StatusBadge tone={settlementStatusTone(status)}>{settlementStatusLabel(status)}</StatusBadge>;
}

function settlementStatusTone(status: SettlementStatus): StatusTone {
  switch (status) {
    case "due":
      return "muted";
    case "payment_opened":
      return "info";
    case "claimed_paid":
      return "pending";
    case "payer_confirmed":
      return "success";
    case "disputed":
      return "danger";
  }
}

function settlementStatusLabel(status: SettlementStatus): string {
  switch (status) {
    case "due":
      return "due";
    case "payment_opened":
      return "payment opened";
    case "claimed_paid":
      return "marked paid";
    case "payer_confirmed":
      return "payer confirmed";
    case "disputed":
      return "disputed";
  }
}


function friendlyError(err: unknown): string {
  if (typeof err === "object" && err !== null && "code" in err && "message" in err) {
    const e = err as { code: string; message: string; status?: number };
    // Map known API error codes to human-friendly messages
    if (e.code === "RATE_LIMIT_EXCEEDED" || e.status === 429) {
      return "Too many attempts. Please wait a moment and try again.";
    }
    if (e.code === "QUANTITY_EXCEEDED") {
      return "Someone may have claimed the remaining quantity. Refresh and try again.";
    }
    if (e.code === "INVALID_STATE_TRANSITION") {
      return "This action is not available in the current room state.";
    }
    if (e.code === "VERSION_CONFLICT") {
      return "The room changed while you were acting. Refresh and try again.";
    }
    if (e.code === "CLAIM_NOT_FOUND") {
      return "No active claim found for this item. Refresh and try again.";
    }
    if (e.code === "PARTICIPANT_NOT_FOUND") {
      return "This participant was already removed or does not exist.";
    }
    if (e.code === "FORBIDDEN") {
      return "You do not have permission to do this.";
    }
    if (e.message) {
      if (e.message.includes("Failed to fetch") || e.message.includes("NetworkError")) {
        return "Network connection failed. Please check your internet and try again.";
      }
      return e.message;
    }
  }
  if (err instanceof Error) {
    if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
      return "Network connection failed. Please check your internet and try again.";
    }
    return err.message || "Something went wrong. Please refresh.";
  }
  return "Something went wrong. Please check your connection and refresh.";
}

function isPreviewValidationError(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "status" in err &&
    [400, 409, 422, 423].includes(Number((err as { status: unknown }).status))
  );
}
