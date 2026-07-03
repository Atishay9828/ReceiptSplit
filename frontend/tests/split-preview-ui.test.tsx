import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CreatorLockControls, SplitPreviewCard } from "@/components/room-client";
import { getSplitPreviewReadiness } from "@/lib/split-readiness";
import type { RoomSummary } from "@/types/api";

const summary: RoomSummary = {
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
  items: [
    {
      id: "item-1",
      receipt_id: "receipt-1",
      name: "Dosa",
      quantity: 1,
      total_paise: 12000,
      source: "manual",
      confidence: 1,
      sort_order: 0,
      version: 1,
      created_at: "2026-07-01T00:00:00Z"
    }
  ],
  adjustments: [],
  assignments: []
};

describe("split preview UI states", () => {
  it("test_incomplete_split_message_rendered", () => {
    const readiness = getSplitPreviewReadiness(summary);

    render(
      <SplitPreviewCard
        preview={null}
        previewError={null}
        readiness={readiness}
        summary={summary}
        onRetry={vi.fn()}
      />
    );

    expect(screen.getByText("Split preview is not ready yet.")).toBeInTheDocument();
    expect(screen.getByText("Finish claiming all items to see totals.")).toBeInTheDocument();
  });

  it("renders disabled lock helper when preview is not ready", () => {
    const readiness = getSplitPreviewReadiness(summary);

    render(
      <CreatorLockControls
        canLock={false}
        locked={false}
        readiness={readiness}
        onLock={vi.fn()}
        onUnlock={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: /^lock$/i })).toBeDisabled();
    expect(screen.getByText("Complete all claims before locking the split.")).toBeInTheDocument();
  });
});
