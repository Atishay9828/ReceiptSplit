import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ClaimButton } from "@/components/claim-button";
import { CreateRoomForm } from "@/components/create-room-form";
import { ErrorState } from "@/components/error-state";
import { ItemForm } from "@/components/item-form";
import { JoinForm } from "@/components/join-form";

describe("forms and controls", () => {
  it("Create room form submits valid payload", async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    render(<CreateRoomForm onCreate={onCreate} />);

    await userEvent.type(screen.getByLabelText(/payer name/i), "AJ");
    await userEvent.click(screen.getByRole("button", { name: /create room/i }));

    await waitFor(() =>
      expect(onCreate).toHaveBeenCalledWith({
        split_mode: "item_wise",
        payer_name: "AJ",
        payer_vpa: undefined
      })
    );
  });

  it("Join form validates nickname", async () => {
    const onJoin = vi.fn();
    render(<JoinForm onJoin={onJoin} />);

    await userEvent.click(screen.getByRole("button", { name: /join room/i }));

    expect(await screen.findByText(/nickname is required/i)).toBeInTheDocument();
    expect(onJoin).not.toHaveBeenCalled();
  });

  it("Item form converts rupees to paise", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ItemForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/item name/i), "Dosa");
    await userEvent.clear(screen.getByLabelText(/quantity/i));
    await userEvent.type(screen.getByLabelText(/quantity/i), "2");
    await userEvent.type(screen.getByLabelText(/amount/i), "120.50");
    await userEvent.click(screen.getByRole("button", { name: /save item/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        name: "Dosa",
        quantity: 2,
        total_paise: 12050,
        allocation_mode: "individual"
      })
    );
  });

  it("lets a shared item bypass individual claiming", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ItemForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/item name/i), "Pizza");
    await userEvent.type(screen.getByLabelText(/amount/i), "600");
    await userEvent.selectOptions(screen.getByLabelText(/how should this item be split/i), "equal");
    await userEvent.click(screen.getByRole("button", { name: /save item/i }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Pizza", allocation_mode: "equal" })
      )
    );
  });

  it("Claim button calls correct API helper", async () => {
    const onClaim = vi.fn().mockResolvedValue(undefined);
    render(<ClaimButton itemVersion={4} onClaim={onClaim} />);

    await userEvent.click(screen.getByRole("button", { name: /claim/i }));

    await waitFor(() => expect(onClaim).toHaveBeenCalledWith({ item_version: 4, claimed_qty: 1 }));
  });

  it("Error state renders backend error message", () => {
    render(<ErrorState message="Version conflict" onRetry={() => undefined} />);

    expect(screen.getByText("Version conflict")).toBeInTheDocument();
  });
});
