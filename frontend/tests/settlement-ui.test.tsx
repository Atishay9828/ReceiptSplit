import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CreatorSettlementPanel, ParticipantSettlementPanel } from "@/components/room-client";
import type { OpenPaymentResponse, SettlementSummary } from "@/types/api";

const settlement: SettlementSummary = {
  room_id: "room-1",
  payer_details_configured: true,
  payee_vpa: "receiptsplit.test@upi",
  payee_name: "AJ Payer",
  requests: [
    {
      id: "request-1",
      room_id: "room-1",
      participant_id: "participant-2",
      amount_paise: 500,
      amount_display: "5.00",
      currency: "INR",
      payee_vpa: "receiptsplit.test@upi",
      payee_name: "AJ Payer",
      payment_reference: "RS-ROOM-BOB",
      status: "claimed_paid",
      created_at: "2026-07-06T00:00:00Z",
      updated_at: "2026-07-06T00:01:00Z",
      opened_at: "2026-07-06T00:01:00Z",
      claimed_paid_at: "2026-07-06T00:02:00Z",
      payer_confirmed_at: null,
      disputed_at: null
    }
  ],
  aggregates: {
    due_count: 0,
    payment_opened_count: 0,
    claimed_paid_count: 1,
    payer_confirmed_count: 0,
    disputed_count: 0,
    total_due_paise: 500,
    total_confirmed_paise: 0
  }
};

const opened: OpenPaymentResponse = {
  settlement_request_id: "request-1",
  status: "payment_opened",
  amount_paise: 500,
  amount_display: "5.00",
  payee_vpa: "receiptsplit.test@upi",
  payee_name: "AJ Payer",
  payment_reference: "RS-ROOM-BOB",
  upi_uri: "upi://pay?pa=receiptsplit.test%40upi&am=5.00",
  qr_payload: "upi://pay?pa=receiptsplit.test%40upi&am=5.00",
  copy_vpa: "receiptsplit.test@upi",
  disclaimer: "ReceiptSplit does not verify bank transfer."
};

describe("settlement UI", () => {
  it("renders creator dashboard without verified-paid language", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onDispute = vi.fn().mockResolvedValue(undefined);

    render(
      <CreatorSettlementPanel
        settlement={settlement}
        participantsById={new Map([["participant-2", "Bob"]])}
        locked
        onSavePayer={vi.fn()}
        onPrepare={vi.fn()}
        onConfirm={onConfirm}
        onDispute={onDispute}
      />
    );

    expect(screen.getByText("Settlement status")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("marked paid")).toBeInTheDocument();
    expect(screen.queryByText(/verified/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /confirm payment/i }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith("request-1"));
  });

  it("opens participant payment and exposes QR and copy fallback", async () => {
    const onOpenPayment = vi.fn().mockResolvedValue(opened);
    const onClaimPaid = vi.fn().mockResolvedValue(undefined);

    render(
      <ParticipantSettlementPanel
        settlement={settlement}
        participantId="participant-2"
        onOpenPayment={onOpenPayment}
        onClaimPaid={onClaimPaid}
      />
    );

    expect(screen.getByText("Pay your share")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /open upi app/i }));

    await waitFor(() => expect(onOpenPayment).toHaveBeenCalledWith("request-1"));
    expect(await screen.findByText("QR fallback")).toBeInTheDocument();
    expect(screen.getAllByText("receiptsplit.test@upi").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/payment successful/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^i paid$/i }));
    await waitFor(() => expect(onClaimPaid).toHaveBeenCalledWith("request-1"));
  });
});
