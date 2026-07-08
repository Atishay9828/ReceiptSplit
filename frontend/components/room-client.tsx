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

import { ClaimButton } from "@/components/claim-button";
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
  canLock
}: {
  roomStatus: RoomSummary["room"]["status"];
  canLock: boolean;
}) {
  const copy = getCreatorNextAction(roomStatus, canLock);

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

function getCreatorNextAction(roomStatus: RoomSummary["room"]["status"], canLock: boolean) {
  if (roomStatus === "draft") {
    return {
      title: "Open claiming",
      description: "Share the link when you are ready. Friends can join without installing an app."
    };
  }
  if (roomStatus === "active") {
    return canLock
      ? {
          title: "Lock bill",
          description: "Friends can stop changing claims once everything looks right."
        }
      : {
          title: "Wait for claims",
          description: "Some items still need claims before you can lock the bill."
        };
  }
  if (roomStatus === "settling") {
    return {
      title: "Confirm payments",
      description: "Participants pay you directly, then you manually confirm or dispute each request."
    };
  }
  if (roomStatus === "settled") {
    return {
      title: "View summary",
      description: "All payments that needed payer confirmation are complete."
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
  const lockReady = canLockSplit({ locked, preview, readiness });
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
      setActionError(err instanceof Error ? err.message : "Action failed");
    }
  }

  return (
    <>
      {actionError ? <ErrorState message={actionError} onRetry={() => setActionError(null)} /> : null}
      <CreatorNextActionCard roomStatus={summary.room.status} canLock={lockReady} />
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
      setActionError(err instanceof Error ? err.message : "Refresh and try again");
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
      <Participants participants={summary.participants} />
      <ParticipantClaimList
        summary={summary}
        participantId={session.participantId}
        locked={locked}
        onClaim={(itemId, payload) =>
          run(() => api.claimItem(summary.room.id, session.token, itemId, payload))
        }
        onUnclaim={(itemId) => run(() => api.unclaimItem(summary.room.id, session.token, itemId))}
      />
      <section aria-hidden="true" className="hidden">
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
          const claimed = itemAssignments.reduce((sum, assignment) => sum + assignment.claimed_qty, 0);
          const available = Math.max(item.quantity - claimed, 0);
          const status = myClaim ? "claimed_by_you" : available > 0 ? "available" : "claimed";

          return (
            <div key={item.id} className="rounded-md border border-[#dbe5df] bg-cloud/50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-base font-bold">{item.name}</h3>
                  <p className="mt-1 text-sm text-[#63706b]">
                    {formatPaise(item.total_paise)} - {available} of {item.quantity} open
                  </p>
                </div>
                <ItemClaimStatusBadge status={status} />
              </div>
              <div className="mt-3">
                {myClaim ? (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={locked}
                    aria-label={`Unclaim ${item.name}`}
                    onClick={() => onUnclaim(item.id)}
                  >
                    Unclaim
                  </Button>
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
          {requests.map((request) => (
            <div key={request.id} className="rounded-md border border-[#dbe5df] bg-cloud/40 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">
                    {participantsById.get(request.participant_id) ?? "Participant"}
                  </h3>
                  <p className="text-sm text-[#63706b]">
                    {formatPaise(request.amount_paise)} · {settlementStatusLabel(request.status)}
                  </p>
                  <p className="break-all text-xs text-[#63706b]">{request.payment_reference}</p>
                </div>
                <SettlementStatusBadge status={request.status} />
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!["claimed_paid", "disputed"].includes(request.status)}
                  onClick={() => onConfirm(request.id)}
                >
                  Confirm payment
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  disabled={!["due", "payment_opened", "claimed_paid"].includes(request.status)}
                  onClick={() => onDispute(request.id)}
                >
                  Mark disputed
                </Button>
              </div>
            </div>
          ))}
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
  const [openedPayment, setOpenedPayment] = useState<OpenPaymentResponse | null>(null);
  const [qr, setQr] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!openedPayment?.qr_payload) {
      return;
    }
    void QRCode.toDataURL(openedPayment.qr_payload, { margin: 1, width: 180 }).then(setQr);
  }, [openedPayment?.qr_payload]);

  if (!request) {
    return (
      <section className="rounded-md border border-[#dbe5df] bg-white p-4 shadow-soft">
        <h2 className="text-lg font-bold">Pay your share</h2>
        <p className="mt-2 text-sm text-[#63706b]">Waiting for payer to prepare settlement.</p>
      </section>
    );
  }

  async function openPayment() {
    if (!request) {
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      setOpenedPayment(await onOpenPayment(request.id));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Too many attempts. Please try again later.");
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
      <div className="mt-4 grid gap-3 rounded-md bg-cloud p-4 text-sm">
        <div className="grid gap-1">
          <span>Amount due</span>
          <strong className="text-4xl font-bold text-ink">{formatPaise(request.amount_paise)}</strong>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span>Payer</span>
          <strong className="text-right">{request.payee_name}</strong>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span>UPI ID</span>
          <strong className="break-all text-right">{request.payee_vpa}</strong>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span>Reference</span>
          <strong className="break-all text-right">{request.payment_reference}</strong>
        </div>
      </div>

      <div className="mt-3 grid gap-1 text-sm">
        <p className="font-medium">{settlementStatusLabel(request.status)}. {participantSettlementCopy(request.status)}</p>
        <SafetyNotice />
      </div>
      {actionError ? <p className="mt-3 text-sm font-medium text-coral">{actionError}</p> : null}

      <div className="mt-4 grid grid-cols-2 gap-2">
        <Button type="button" size="lg" disabled={busy} onClick={openPayment}>
          Open UPI app
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => navigator.clipboard?.writeText(request.payee_vpa)}
        >
          <Copy size={16} aria-hidden="true" />
          Copy UPI ID
        </Button>
        <Button
          type="button"
          className="col-span-2"
          variant="secondary"
          disabled={request.status === "payer_confirmed"}
          onClick={() => onClaimPaid(request.id)}
        >
          I paid
        </Button>
      </div>

      {openedPayment ? (
        <div className="mt-4 grid gap-3 rounded-md border border-[#dbe5df] p-3">
          <h3 className="font-semibold">QR fallback</h3>
          {qr ? (
            <Image
              className="h-36 w-36 rounded-md border border-[#dbe5df]"
              src={qr}
              alt="UPI payment QR"
              width={144}
              height={144}
              unoptimized
            />
          ) : null}
          <p className="break-all text-sm text-[#63706b]">{openedPayment.copy_vpa}</p>
          <p className="text-xs text-[#63706b]">{openedPayment.disclaimer}</p>
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

function participantSettlementCopy(status: SettlementStatus): string {
  switch (status) {
    case "due":
      return "Pay your share directly to the payer.";
    case "payment_opened":
      return "Complete payment in your UPI app, then return and tap I paid.";
    case "claimed_paid":
      return "Waiting for payer confirmation.";
    case "payer_confirmed":
      return "Payer confirmed this payment.";
    case "disputed":
      return "Payer marked this payment as disputed. Check with them and try again if needed.";
  }
}

function isPreviewValidationError(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "status" in err &&
    [400, 409, 422, 423].includes(Number((err as { status: unknown }).status))
  );
}
