import type { RoomSummary, SplitPreview } from "@/types/api";

export type SplitPreviewBlockerCode =
  | "room_closed"
  | "no_participants"
  | "no_items"
  | "empty_total"
  | "item_claims_incomplete";

export type SplitPreviewReadiness = {
  ready: boolean;
  code: SplitPreviewBlockerCode | "ready";
  message: string;
  blockers: string[];
};

export function getSplitPreviewReadiness(summary: RoomSummary): SplitPreviewReadiness {
  if (summary.room.status === "archived" || summary.room.status === "expired") {
    return blocked("room_closed", "This room is no longer available for split preview.");
  }

  if (summary.participants.length < 2) {
    return blocked(
      "no_participants",
      "Invite at least one other person to preview and lock the split."
    );
  }

  if (summary.items.length === 0) {
    return blocked("no_items", "Add at least one item to preview the split.");
  }

  const itemTotal = summary.items.reduce((sum, item) => sum + item.total_paise, 0);
  if (itemTotal <= 0) {
    return blocked("empty_total", "Add item totals before previewing the split.");
  }

  if (summary.room.split_mode === "item_wise" && !areItemClaimsComplete(summary)) {
    return blocked("item_claims_incomplete", "Finish claiming all items to see totals.");
  }

  return {
    ready: true,
    code: "ready",
    message: "Split preview is ready.",
    blockers: []
  };
}

export function shouldRequestSplitPreview(summary: RoomSummary, suppressedKey?: string | null): boolean {
  const readiness = getSplitPreviewReadiness(summary);
  return readiness.ready && getSplitPreviewRequestKey(summary) !== suppressedKey;
}

export function getSplitPreviewRequestKey(summary: RoomSummary): string {
  const items = [...summary.items]
    .sort((left, right) => left.id.localeCompare(right.id))
    .map(
      (item) =>
        `${item.id}:${item.version}:${item.quantity}:${item.total_paise}:${item.allocation_mode}`
    )
    .join(",");
  const assignments = [...summary.assignments]
    .sort((left, right) => left.id.localeCompare(right.id))
    .map(
      (assignment) =>
        `${assignment.id}:${assignment.line_item_id}:${assignment.participant_id}:${assignment.claimed_qty}`
    )
    .join(",");
  const adjustments = [...summary.adjustments]
    .sort((left, right) => left.id.localeCompare(right.id))
    .map((adjustment) => `${adjustment.id}:${adjustment.version}:${adjustment.amount_paise}`)
    .join(",");
  const participants = [...summary.participants]
    .sort((left, right) => left.id.localeCompare(right.id))
    .map((participant) => `${participant.id}:${participant.role}`)
    .join(",");

  return [
    summary.room.id,
    summary.room.version,
    summary.room.status,
    summary.room.split_mode,
    participants,
    items,
    assignments,
    adjustments
  ].join("|");
}

export function canLockSplit({
  locked,
  preview,
  readiness
}: {
  locked: boolean;
  preview: SplitPreview | null;
  readiness: SplitPreviewReadiness;
}): boolean {
  return !locked && readiness.ready && preview !== null;
}

function areItemClaimsComplete(summary: RoomSummary): boolean {
  const claimedByItem = new Map<string, number>();
  for (const assignment of summary.assignments) {
    claimedByItem.set(
      assignment.line_item_id,
      (claimedByItem.get(assignment.line_item_id) ?? 0) + assignment.claimed_qty
    );
  }

  return summary.items.every(
    (item) =>
      item.allocation_mode === "equal" ||
      (claimedByItem.get(item.id) ?? 0) === item.quantity
  );
}

function blocked(code: SplitPreviewBlockerCode, message: string): SplitPreviewReadiness {
  return {
    ready: false,
    code,
    message,
    blockers: [message]
  };
}
