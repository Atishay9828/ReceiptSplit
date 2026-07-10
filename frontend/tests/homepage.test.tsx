import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push })
}));

describe("ReceiptSplit public homepage", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("leads into the real create flow and explains the product through concrete artifacts", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: /a receipt should end the debate/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /create a split/i })[0]).toHaveAttribute("href", "/create");
    expect(screen.getByText(/a scan starts a draft/i)).toBeInTheDocument();
    expect(screen.getByText(/reconnects should not rewrite/i)).toBeInTheDocument();
    expect(screen.getByText(/money refuses/i)).toBeInTheDocument();
    expect(screen.getByText(/honest states are a safety feature/i)).toBeInTheDocument();
    expect(screen.queryByText(/verified paid|payment verified|bank confirmed/i)).not.toBeInTheDocument();
  });

  it("opens a pasted invite through the existing join route", async () => {
    render(<HomePage />);

    await userEvent.type(
      screen.getByLabelText(/paste your private invite link/i),
      "https://receiptsplit.test/join/room-1%3Ainvite-demo"
    );
    await userEvent.click(screen.getByRole("button", { name: /open invite/i }));

    expect(push).toHaveBeenCalledWith("/join/room-1%3Ainvite-demo");
  });

  it("keeps malformed links out of the join flow", async () => {
    render(<HomePage />);

    await userEvent.type(screen.getByLabelText(/paste your private invite link/i), "https://example.test/not-an-invite");
    await userEvent.click(screen.getByRole("button", { name: /open invite/i }));

    expect(push).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/complete ReceiptSplit invite link/i);
  });
});
