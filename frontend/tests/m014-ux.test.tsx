import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import CreatePage from "@/app/create/page";
import JoinPage from "@/app/join/[inviteToken]/page";
import {
  AbuseReportPanel,
  CreatorNextActionCard,
  CreatorSettlementPanel,
  ParticipantClaimList,
  ParticipantSettlementPanel,
  ParticipantTotalCard,
  SettlementStatusBadge
} from "@/components/room-client";
import { api } from "@/lib/api";
import { saveAccountSession } from "@/lib/auth-session";
import { encodeInviteParam } from "@/lib/invite";
import type {
  Assignment,
  Item,
  OpenPaymentResponse,
  Participant,
  RoomSummary,
  SettlementRequestSummary,
  SettlementSummary
} from "@/types/api";

const push = vi.fn();
let params: Record<string, string> = {};

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useParams: () => params
}));

afterEach(() => {
  window.localStorage.clear();
});

const participant: Participant = {
  id: "participant-2",
  room_id: "room-1",
  nickname: "Bob",
  color: "#2f7d5a",
  role: "participant",
  joined_at: "2026-07-08T00:00:00Z"
};

const item: Item = {
  id: "item-1",
  receipt_id: "receipt-1",
  name: "Paneer roll",
  quantity: 1,
  total_paise: 16000,
  source: "manual",
  confidence: 1,
  sort_order: 0,
  version: 3,
  created_at: "2026-07-08T00:00:00Z"
};

const summary: RoomSummary = {
  room: {
    id: "room-1",
    status: "active",
    split_mode: "item_wise",
    payer_vpa: "receiptsplit.test@upi",
    payer_name: "AJ",
    version: 2,
    created_at: "2026-07-08T00:00:00Z",
    updated_at: "2026-07-08T00:00:00Z",
    expires_at: "2026-07-09T00:00:00Z"
  },
  participants: [participant],
  items: [item],
  adjustments: [],
  assignments: []
};

const claimedAssignment: Assignment = {
  id: "assignment-1",
  room_id: "room-1",
  line_item_id: "item-1",
  participant_id: "participant-2",
  claimed_qty: 1,
  created_at: "2026-07-08T00:01:00Z"
};

const request: SettlementRequestSummary = {
  id: "request-1",
  room_id: "room-1",
  participant_id: "participant-2",
  amount_paise: 16000,
  amount_display: "160.00",
  confirmed_amount_paise: 0,
  pending_claim_amount_paise: 16000,
  remaining_amount_paise: 16000,
  remaining_amount_display: "160.00",
  currency: "INR",
  payee_vpa: "receiptsplit.test@upi",
  payee_name: "AJ Payer",
  payment_reference: "RS-ROOM-BOB",
  status: "claimed_paid",
  created_at: "2026-07-08T00:00:00Z",
  updated_at: "2026-07-08T00:02:00Z",
  opened_at: "2026-07-08T00:01:00Z",
  claimed_paid_at: "2026-07-08T00:02:00Z",
  payer_confirmed_at: null,
  disputed_at: null
};

const settlement: SettlementSummary = {
  room_id: "room-1",
  payer_details_configured: true,
  payee_vpa: "receiptsplit.test@upi",
  payee_name: "AJ Payer",
  requests: [request],
  aggregates: {
    due_count: 0,
    payment_opened_count: 0,
    claimed_paid_count: 1,
    payer_confirmed_count: 0,
    disputed_count: 0,
    total_due_paise: 16000,
    total_confirmed_paise: 0,
    total_original_paise: 16000
  }
};

const opened: OpenPaymentResponse = {
  settlement_request_id: "request-1",
  status: "payment_opened",
  amount_paise: 16000,
  amount_display: "160.00",
  payee_vpa: "receiptsplit.test@upi",
  payee_name: "AJ Payer",
  payment_reference: "RS-ROOM-BOB",
  upi_uri: "upi://pay?pa=receiptsplit.test%40upi&am=160.00",
  qr_payload: "upi://pay?pa=receiptsplit.test%40upi&am=160.00",
  copy_vpa: "receiptsplit.test@upi",
  disclaimer: "ReceiptSplit does not verify bank transfers. Check the recipient and amount in your UPI app before paying."
};

describe("M014 frontend polish", () => {
  it("create page leads with a fast clear room creation CTA and trust copy", () => {
    render(<CreatePage />);

    expect(screen.getByRole("heading", { name: /split a receipt with friends/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create split room/i })).toBeInTheDocument();
    expect(screen.getByText(/no app needed for friends/i)).toBeInTheDocument();
    expect(screen.getByText(/direct UPI payment/i)).toBeInTheDocument();
  });

  it("requires an account before opening the invited bill", async () => {
    params = { inviteToken: encodeInviteParam("room-1", "invite-demo") };

    const accountGate = render(<JoinPage />);
    expect(
      await screen.findByRole("heading", { name: /create your account to join/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/account is created automatically/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/name shown on this bill/i)).not.toBeInTheDocument();
    accountGate.unmount();

    saveAccountSession({
      token: "google-account-token",
      user: {
        id: "user-sam",
        provider: "google",
        subject: "google-sam",
        email: "sam@example.com",
        username: "sam",
        display_name: "Sam"
      }
    });
    const joinRoom = vi.spyOn(api, "joinRoom").mockResolvedValue({
      participant: { ...participant, id: "participant-sam", user_id: "user-sam", nickname: "Sam" },
      participant_token: "legacy-participant-token"
    });
    render(<JoinPage />);

    expect(
      await screen.findByRole("heading", { name: /choose your share/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/name shown on this bill/i)).toHaveValue("Sam");
    await userEvent.click(screen.getByRole("button", { name: /open bill/i }));

    await waitFor(() =>
      expect(joinRoom).toHaveBeenCalledWith(
        "room-1",
        "invite-demo",
        "Sam",
        "google-account-token"
      )
    );
    expect(push).toHaveBeenCalledWith("/rooms/room-1");
  });

  it("participant summary makes amount and next action obvious", () => {
    render(<ParticipantTotalCard amountPaise={16000} status="claim_items" participantName="Bob" />);

    expect(screen.getByText(/you owe/i)).toBeInTheDocument();
    expect(screen.getByText("₹160.00")).toBeInTheDocument();
    expect(screen.getByText(/add what you had to your share/i)).toBeInTheDocument();
  });

  it("participant claim list exposes clear item actions and statuses", async () => {
    const onClaim = vi.fn().mockResolvedValue(undefined);
    const onUnclaim = vi.fn().mockResolvedValue(undefined);

    render(
      <ParticipantClaimList
        summary={summary}
        participantId="participant-2"
        locked={false}
        onClaim={onClaim}
        onUnclaim={onUnclaim}
      />
    );

    expect(screen.getByText("Paneer roll")).toBeInTheDocument();
    expect(screen.getByText(/available/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /add paneer roll to my share/i }));
    await waitFor(() => expect(onClaim).toHaveBeenCalledWith("item-1", { item_version: 3, claimed_qty: 1 }));
  });

  it("participant claim list shows claimed-by-you state without a green final badge", () => {
    render(
      <ParticipantClaimList
        summary={{ ...summary, assignments: [claimedAssignment] }}
        participantId="participant-2"
        locked={false}
        onClaim={vi.fn()}
        onUnclaim={vi.fn()}
      />
    );

    expect(screen.getByText(/in your share/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /remove paneer roll from my share/i })).toBeInTheDocument();
  });

  it("payment card shows all trust-critical payment details and safe status copy", async () => {
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

    expect(screen.getByText("₹160.00")).toBeInTheDocument();
    expect(screen.getByText("AJ Payer")).toBeInTheDocument();
    expect(screen.getByText("receiptsplit.test@upi")).toBeInTheDocument();
    expect(screen.getByText("RS-ROOM-BOB")).toBeInTheDocument();

    expect(screen.getByText(/ReceiptSplit does not verify bank transfers/i)).toBeInTheDocument();
    expect(screen.queryByText(/verified paid|payment successful/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /open upi/i }));
    expect(await screen.findByText(/Scan with your phone's camera or UPI app/i)).toBeInTheDocument();
  });

  it("status badges keep claimed paid visually distinct from payer confirmed", () => {
    const { rerender } = render(<SettlementStatusBadge status="claimed_paid" />);
    const claimed = screen.getByText(/marked paid/i);
    expect(claimed).toHaveAttribute("data-tone", "pending");

    rerender(<SettlementStatusBadge status="payer_confirmed" />);
    expect(screen.getByText(/payer confirmed/i)).toHaveAttribute("data-tone", "success");
  });

  it("creator next action card explains the one primary action", () => {
    render(<CreatorNextActionCard roomStatus="active" canLock itemCount={2} />);

    expect(screen.getByRole("heading", { name: /next step/i })).toBeInTheDocument();
    expect(screen.getByText(/review and lock the bill/i)).toBeInTheDocument();
    expect(screen.getByText(/every item has a share/i)).toBeInTheDocument();
  });

  it("creator settlement dashboard shows confirm and dispute without verification language", () => {
    render(
      <CreatorSettlementPanel
        settlement={settlement}
        participantsById={new Map([["participant-2", "Bob"]])}
        locked
        onSavePayer={vi.fn()}
        onPrepare={vi.fn()}
        onConfirm={vi.fn()}
        onDispute={vi.fn()}
      />
    );

    expect(screen.getByText(/settlement dashboard/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm ₹160\.00/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /mark disputed/i })).toBeInTheDocument();
    expect(screen.queryByText(/verified/i)).not.toBeInTheDocument();
  });

  it("abuse report remains visible and lightweight", async () => {
    const onReport = vi.fn().mockResolvedValue(undefined);

    render(<AbuseReportPanel onReport={onReport} />);

    expect(screen.getByText(/report suspicious or abusive split/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /report abuse/i }));
    await userEvent.selectOptions(screen.getByLabelText(/reason/i), "wrong_payee");
    await userEvent.click(screen.getByRole("button", { name: /submit report/i }));

    await waitFor(() => expect(onReport).toHaveBeenCalledWith({ reason: "wrong_payee", message: null }));
  });
});
