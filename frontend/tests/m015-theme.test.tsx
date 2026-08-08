import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CreatePage from "@/app/create/page";
import JoinPage from "@/app/join/[inviteToken]/page";
import { ParticipantSettlementPanel } from "@/components/room-client";
import { ThemeToggle } from "@/components/theme-toggle";
import { encodeInviteParam } from "@/lib/invite";
import type { SettlementRequestSummary, SettlementSummary } from "@/types/api";

const push = vi.fn();
let params: Record<string, string> = {};

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useParams: () => params
}));

const baseRequest: SettlementRequestSummary = {
  id: "request-1",
  room_id: "room-1",
  participant_id: "participant-2",
  amount_paise: 36000,
  amount_display: "360.00",
  confirmed_amount_paise: 0,
  pending_claim_amount_paise: null,
  remaining_amount_paise: 36000,
  remaining_amount_display: "360.00",
  currency: "INR",
  payee_vpa: "receiptsplit.test@upi",
  payee_name: "AJ",
  payment_reference: "RS-ROOM-KUNAL",
  status: "payment_opened",
  created_at: "2026-07-09T00:00:00Z",
  updated_at: "2026-07-09T00:01:00Z",
  opened_at: "2026-07-09T00:01:00Z",
  claimed_paid_at: null,
  payer_confirmed_at: null,
  disputed_at: null
};

function settlementWith(request: SettlementRequestSummary): SettlementSummary {
  const isConfirmed = request.status === "payer_confirmed";
  const normalizedRequest = {
    ...request,
    confirmed_amount_paise: isConfirmed ? request.amount_paise : 0,
    pending_claim_amount_paise: request.status === "claimed_paid" ? request.amount_paise : null,
    remaining_amount_paise: isConfirmed ? 0 : request.amount_paise,
    remaining_amount_display: isConfirmed ? "0.00" : request.amount_display
  };

  return {
    room_id: "room-1",
    payer_details_configured: true,
    payee_vpa: request.payee_vpa,
    payee_name: request.payee_name,
    requests: [normalizedRequest],
    aggregates: {
      due_count: request.status === "due" ? 1 : 0,
      payment_opened_count: request.status === "payment_opened" ? 1 : 0,
      claimed_paid_count: request.status === "claimed_paid" ? 1 : 0,
      payer_confirmed_count: request.status === "payer_confirmed" ? 1 : 0,
      disputed_count: request.status === "disputed" ? 1 : 0,
      total_due_paise: isConfirmed ? 0 : request.amount_paise,
      total_confirmed_paise: isConfirmed ? request.amount_paise : 0,
      total_original_paise: request.amount_paise
    }
  };
}

describe("M015 dark mode and pilot readiness UI", () => {
  beforeEach(() => {
    params = {};
    push.mockReset();
    window.localStorage.clear();
    document.documentElement.className = "";
    document.documentElement.removeAttribute("data-theme");
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes("dark"),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn()
      }))
    });
  });

  it("theme toggle renders accessibly, applies dark mode, and persists preference", async () => {
    render(<ThemeToggle />);

    await waitFor(() => expect(document.documentElement).toHaveClass("dark"));
    await userEvent.click(screen.getByRole("button", { name: /toggle theme/i }));

    expect(document.documentElement).not.toHaveClass("dark");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("receiptsplit:theme")).toBe("light");
  });

  it("create page uses the dark-aware shell and keeps the form usable", () => {
    document.documentElement.classList.add("dark");

    render(<CreatePage />);

    expect(screen.getByRole("heading", { name: /create split room/i }).closest("div")).toBeInTheDocument();
    expect(screen.getByLabelText(/split mode/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/payer vpa/i)).toHaveAttribute("placeholder", "name@bank");
    expect(screen.getByRole("button", { name: /create split room/i })).toBeEnabled();
  });

  it("join page keeps the required account gate usable in dark mode", async () => {
    document.documentElement.classList.add("dark");
    params = { inviteToken: encodeInviteParam("room-1", "invite-demo") };

    render(<JoinPage />);

    expect(
      await screen.findByRole("heading", { name: /create your account to join/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/account is created automatically/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/name shown on this bill/i)).not.toBeInTheDocument();
  });

  it("payment card keeps QR and copy fallbacks visible in dark mode", async () => {
    document.documentElement.classList.add("dark");

    render(
      <ParticipantSettlementPanel
        settlement={settlementWith(baseRequest)}
        participantId="participant-2"
        onOpenPayment={vi.fn()}
        onClaimPaid={vi.fn()}
      />
    );

    expect(screen.getByText("receiptsplit.test@upi")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy upi id/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy upi payment link/i })).toBeInTheDocument();
    expect(await screen.findByAltText(/upi payment qr code/i)).toHaveClass("bg-qr");
    expect(screen.getByText(/ReceiptSplit does not verify bank transfers/i)).toBeInTheDocument();
  });

  it("payer confirmed state hides pay actions and avoids unsafe payment copy", () => {
    const confirmed = {
      ...baseRequest,
      status: "payer_confirmed" as const,
      payer_confirmed_at: "2026-07-09T00:02:00Z"
    };

    render(
      <ParticipantSettlementPanel
        settlement={settlementWith(confirmed)}
        participantId="participant-2"
        onOpenPayment={vi.fn()}
        onClaimPaid={vi.fn()}
      />
    );

    expect(screen.getByText(/payer confirmed this payment/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /open upi/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /copy upi id/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /mark payment as done/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/verified paid|payment verified|bank confirmed|payment successful/i)).not.toBeInTheDocument();
  });
});
