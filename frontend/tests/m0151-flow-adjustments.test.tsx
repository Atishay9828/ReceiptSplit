import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  AdjustmentForm,
  CreatorSettledView,
  Participants,
  RoomStepHeader
} from "@/components/room-client";
import { api } from "@/lib/api";
import type { RoomSummary, SettlementSummary, SplitPreview } from "@/types/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      addAdjustment: vi.fn()
    }
  };
});

const summary: RoomSummary = {
  room: {
    id: "room-1",
    status: "settled",
    split_mode: "item_wise",
    payer_vpa: "receiptsplit.test@upi",
    payer_name: "AJ",
    version: 4,
    created_at: "2026-07-09T00:00:00Z",
    updated_at: "2026-07-09T00:02:00Z",
    expires_at: "2026-07-10T00:00:00Z"
  },
  participants: [
    {
      id: "participant-1",
      room_id: "room-1",
      nickname: "Creator",
      color: "#4F46E5",
      role: "creator",
      joined_at: "2026-07-09T00:00:00Z"
    },
    {
      id: "participant-2",
      room_id: "room-1",
      nickname: "Kunal",
      color: "#0284c7",
      role: "participant",
      joined_at: "2026-07-09T00:01:00Z"
    }
  ],
  items: [
    {
      id: "item-1",
      receipt_id: "receipt-1",
      name: "Cold Coffee",
      quantity: 3,
      total_paise: 36000,
      source: "manual",
      confidence: 1,
      sort_order: 0,
      version: 1,
      created_at: "2026-07-09T00:00:00Z"
    }
  ],
  adjustments: [],
  assignments: []
};

const settlement: SettlementSummary = {
  room_id: "room-1",
  payer_details_configured: true,
  payee_vpa: "receiptsplit.test@upi",
  payee_name: "AJ",
  requests: [
    {
      id: "request-1",
      room_id: "room-1",
      participant_id: "participant-2",
      amount_paise: 24000,
      amount_display: "240.00",
      confirmed_amount_paise: 24000,
      pending_claim_amount_paise: null,
      remaining_amount_paise: 0,
      remaining_amount_display: "0.00",
      currency: "INR",
      payee_vpa: "receiptsplit.test@upi",
      payee_name: "AJ",
      payment_reference: "RS-ROOM-KUNAL",
      status: "payer_confirmed",
      created_at: "2026-07-09T00:00:00Z",
      updated_at: "2026-07-09T00:02:00Z",
      opened_at: "2026-07-09T00:01:00Z",
      claimed_paid_at: "2026-07-09T00:01:30Z",
      payer_confirmed_at: "2026-07-09T00:02:00Z",
      disputed_at: null
    }
  ],
  aggregates: {
    due_count: 0,
    payment_opened_count: 0,
    claimed_paid_count: 0,
    payer_confirmed_count: 1,
    disputed_count: 0,
    total_due_paise: 0,
    total_confirmed_paise: 24000,
    total_original_paise: 24000
  }
};

const preview: SplitPreview = {
  grand_total_paise: 36000,
  participant_totals: []
};

describe("M015.1 flow and adjustment repair", () => {
  it("renders creator chip as payer name plus role badge", () => {
    render(<Participants participants={summary.participants} mode="creator" payerName="AJ" />);

    expect(screen.getByText("AJ")).toBeInTheDocument();
    expect(screen.getByText("Creator")).toBeInTheDocument();
    expect(screen.queryByText(/Creator\s+Creator/i)).not.toBeInTheDocument();
  });

  it("sends discount flat amounts as positive subtractive payloads", async () => {
    vi.mocked(api.addAdjustment).mockResolvedValueOnce({} as never);
    const onSaved = vi.fn().mockResolvedValue(undefined);

    render(<AdjustmentForm roomId="room-1" token="token" onSaved={onSaved} onError={vi.fn()} />);

    await userEvent.selectOptions(screen.getByLabelText(/type/i), "discount");
    await userEvent.type(screen.getByLabelText(/amount/i), "60");
    expect(screen.getByText(/Subtracts 60 as a flat amount/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /add adjustment/i }));

    await waitFor(() =>
      expect(api.addAdjustment).toHaveBeenCalledWith("room-1", "token", {
        type: "discount",
        label: "discount",
        amount_paise: 6000,
        rate_basis_points: undefined,
        allocation_method: "proportional"
      })
    );
  });

  it("supports percentage adjustment mode with integer basis points", async () => {
    vi.mocked(api.addAdjustment).mockResolvedValueOnce({} as never);

    render(<AdjustmentForm roomId="room-1" token="token" onSaved={vi.fn()} onError={vi.fn()} />);

    await userEvent.selectOptions(screen.getByLabelText(/type/i), "tax");
    await userEvent.selectOptions(screen.getByLabelText(/mode/i), "percentage");
    await userEvent.type(screen.getByLabelText(/percentage/i), "5");
    expect(screen.getByText(/Adds 5% from the item subtotal/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /add adjustment/i }));

    await waitFor(() =>
      expect(api.addAdjustment).toHaveBeenCalledWith("room-1", "token", {
        type: "tax",
        label: "tax",
        amount_paise: 0,
        rate_basis_points: 500,
        allocation_method: "proportional"
      })
    );
  });

  it("renders only the active step inside the current-step card", () => {
    const { rerender } = render(<RoomStepHeader step="locked" />);
    expect(screen.getByRole("heading", { name: "Review totals" })).toBeInTheDocument();
    expect(screen.getByText(/Check every share/i)).toBeInTheDocument();
    expect(screen.queryByText("draft")).not.toBeInTheDocument();
    expect(screen.queryByText("settling")).not.toBeInTheDocument();

    rerender(<RoomStepHeader step="settled" />);
    expect(screen.getByRole("heading", { name: "Complete" })).toBeInTheDocument();
    expect(screen.getByText(/manually confirmed by the payer/i)).toBeInTheDocument();
  });

  it("renders completion screen without payment verification claims", () => {
    render(
      <CreatorSettledView
        summary={summary}
        preview={preview}
        settlement={settlement}
        participantsById={new Map([["participant-2", "Kunal"]])}
      />
    );

    expect(screen.getByText(/All payments confirmed/i)).toBeInTheDocument();
    expect(screen.getByText(/This split is cleared/i)).toBeInTheDocument();
    expect(screen.getByText("Kunal")).toBeInTheDocument();
    expect(screen.getByText("payer confirmed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy summary/i })).toBeInTheDocument();
    expect(screen.queryByText(/verified paid|payment verified|bank confirmed|payment successful/i)).not.toBeInTheDocument();
  });
});

