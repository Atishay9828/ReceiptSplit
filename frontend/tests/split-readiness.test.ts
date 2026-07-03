import { describe, expect, it } from "vitest";

import {
  canLockSplit,
  getSplitPreviewRequestKey,
  getSplitPreviewReadiness,
  shouldRequestSplitPreview
} from "@/lib/split-readiness";
import type { Assignment, Item, RoomSummary, SplitPreview } from "@/types/api";

const baseSummary: RoomSummary = {
  room: {
    id: "room-1",
    status: "active",
    split_mode: "item_wise",
    payer_vpa: null,
    payer_name: "AJ",
    version: 1,
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
    expires_at: "2026-07-02T00:00:00Z"
  },
  participants: [
    {
      id: "participant-1",
      room_id: "room-1",
      nickname: "AJ",
      color: "#2f7a55",
      role: "creator",
      joined_at: "2026-07-01T00:00:00Z"
    }
  ],
  items: [],
  adjustments: [],
  assignments: []
};

function item(overrides: Partial<Item> = {}): Item {
  return {
    id: "item-1",
    receipt_id: "receipt-1",
    name: "Dosa",
    quantity: 2,
    total_paise: 12000,
    source: "manual",
    confidence: 1,
    sort_order: 0,
    version: 1,
    created_at: "2026-07-01T00:00:00Z",
    ...overrides
  };
}

function assignment(overrides: Partial<Assignment> = {}): Assignment {
  return {
    id: "assignment-1",
    room_id: "room-1",
    line_item_id: "item-1",
    participant_id: "participant-1",
    claimed_qty: 1,
    created_at: "2026-07-01T00:00:00Z",
    ...overrides
  };
}

type SummaryOverrides = Omit<Partial<RoomSummary>, "room"> & {
  room?: Partial<RoomSummary["room"]>;
};

function summary(overrides: SummaryOverrides = {}): RoomSummary {
  return {
    ...baseSummary,
    room: { ...baseSummary.room, ...overrides.room },
    participants: overrides.participants ?? baseSummary.participants,
    items: overrides.items ?? baseSummary.items,
    adjustments: overrides.adjustments ?? baseSummary.adjustments,
    assignments: overrides.assignments ?? baseSummary.assignments
  };
}

const preview: SplitPreview = {
  grand_total_paise: 12000,
  participant_totals: [
    {
      participant_id: "participant-1",
      items_paise: 12000,
      discount_paise: 0,
      tax_paise: 0,
      service_charge_paise: 0,
      delivery_fee_paise: 0,
      adjustment_paise: 0,
      total_paise: 12000,
      is_payer: true
    }
  ]
};

describe("split preview readiness", () => {
  it("test_preview_not_called_when_item_wise_claims_incomplete", () => {
    const incomplete = summary({
      items: [item()],
      assignments: [assignment()]
    });

    expect(getSplitPreviewReadiness(incomplete).ready).toBe(false);
    expect(shouldRequestSplitPreview(incomplete)).toBe(false);
  });

  it("test_preview_called_after_item_wise_claims_complete", () => {
    const complete = summary({
      items: [item()],
      assignments: [assignment({ claimed_qty: 2 })]
    });

    expect(getSplitPreviewReadiness(complete).ready).toBe(true);
    expect(shouldRequestSplitPreview(complete)).toBe(true);
  });

  it("treats an unclaimed item-wise item as not ready", () => {
    expect(getSplitPreviewReadiness(summary({ items: [item()], assignments: [] }))).toMatchObject({
      ready: false,
      code: "item_claims_incomplete"
    });
  });

  it("treats equal split without participants as not ready", () => {
    const equal = summary({
      room: { split_mode: "equal" },
      participants: [],
      items: [item()]
    });

    expect(getSplitPreviewReadiness(equal).ready).toBe(false);
  });

  it("treats equal split with participant and items as ready", () => {
    const equal = summary({
      room: { split_mode: "equal" },
      items: [item()]
    });

    expect(getSplitPreviewReadiness(equal).ready).toBe(true);
  });

  it("handles settling state safely when claims remain complete", () => {
    const locked = summary({
      room: { status: "settling" },
      items: [item()],
      assignments: [assignment({ claimed_qty: 2 })]
    });

    expect(getSplitPreviewReadiness(locked).ready).toBe(true);
    expect(shouldRequestSplitPreview(locked)).toBe(true);
  });

  it("suppresses repeated preview requests after validation failed for the same summary key", () => {
    const complete = summary({
      items: [item()],
      assignments: [assignment({ claimed_qty: 2 })]
    });
    const failedKey = getSplitPreviewRequestKey(complete);

    expect(shouldRequestSplitPreview(complete, failedKey)).toBe(false);
  });

  it("test_lock_button_disabled_when_preview_not_ready", () => {
    const notReady = getSplitPreviewReadiness(summary({ items: [item()], assignments: [] }));

    expect(canLockSplit({ locked: false, preview, readiness: notReady })).toBe(false);
  });

  it("allows lock only when preview data exists and readiness is valid", () => {
    const ready = getSplitPreviewReadiness(
      summary({ items: [item()], assignments: [assignment({ claimed_qty: 2 })] })
    );

    expect(canLockSplit({ locked: false, preview, readiness: ready })).toBe(true);
    expect(canLockSplit({ locked: true, preview, readiness: ready })).toBe(false);
    expect(canLockSplit({ locked: false, preview: null, readiness: ready })).toBe(false);
  });
});
